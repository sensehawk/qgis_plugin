from ..constants import THERMAL_TAGGING_URL
import requests
import json
from qgis.PyQt import QtWidgets, uic
from qgis.utils import iface
from qgis.core import QgsApplication, QgsTask, Qgis, QgsField
from PyQt5.QtCore import QVariant
from qgis.PyQt.QtCore import Qt 
from PyQt5.QtGui import QImage, QIcon
from PyQt5 import QtCore, QtGui, QtWidgets 
import os
import cv2
import tempfile
from urllib import request
import threading
from .thermliteQc import PhotoViewer
from ..utils import get_image_urls

THERM_VIEWER, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'therm_viewer.ui'))


class PhotoViewer(QtWidgets.QGraphicsView):
    photoClicked = QtCore.pyqtSignal(QtCore.QPoint)

    def __init__(self):
        super(PhotoViewer, self).__init__()
        self._zoom = 0
        self._empty = True
        self._scene = QtWidgets.QGraphicsScene(self)
        self._photo = QtWidgets.QGraphicsPixmapItem()
        self._scene.addItem(self._photo)
        self.setScene(self._scene)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(30, 30, 30)))
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)

    def hasPhoto(self): 
        return not self._empty

    def fitInView(self, scale=True):
        rect = QtCore.QRectF(self._photo.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)
            if self.hasPhoto():
                unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
                self.scale(1 / unity.width(), 1 / unity.height())
                viewrect = self.viewport().rect()
                scenerect = self.transform().mapRect(rect)
                factor = min(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height())
                self.scale(factor, factor)
            self._zoom = 0

    def setPhoto(self, pixmap=None):
        self._zoom = 0
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        if pixmap and not pixmap.isNull():
            self._empty = False
            self._photo.setPixmap(pixmap)
        else:
            self._empty = True
            self._photo.setPixmap(QtGui.QPixmap())
        self.fitInView()

    def wheelEvent(self, event):
        if self.hasPhoto():
            if event.angleDelta().y() > 0:
                factor = 1.25
                self._zoom += 1
            else:
                factor = 0.8
                self._zoom -= 1
            if self._zoom > 0:
                self.scale(factor, factor)
            elif self._zoom == 0:
                self.fitInView()
            else:
                self._zoom = 0

class ThermViewerDockWidget(QtWidgets.QWidget, THERM_VIEWER):

    def __init__(self, therm_tools, project):
        """Constructor."""
        super(ThermViewerDockWidget, self).__init__()
        self.setupUi(self)
        self.canvas_logger = therm_tools.canvas_logger
        self.logger = therm_tools.logger
        self.therm_tools = therm_tools
        self.project = project
        self.num_raw_images = 0
        self.editbutton.setText('📝')
        self.savebutton.setText('✅')
        self.editbutton.clicked.connect(self.startediting)
        self.savebutton.clicked.connect(self.savestringnumber)
        self.generate_service_objects()
        self.project.project_tabs_widget.currentChanged.connect(self.hide_widget)
        self.images_dir = os.path.join(tempfile.gettempdir(), self.project.project_details["uid"])
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)
        self.photo_viewer = PhotoViewer()
        self.image_layout.addWidget(self.photo_viewer)
        self.previous_img.clicked.connect(lambda: self.change_image_index(-1))
        self.nxt_img.clicked.connect(lambda: self.change_image_index(1))
        self.height, self.width = 512, 640
        # Feature Selection changed signal
        self.signal_connected = False
        self.signal_slot = lambda x: self.show_raw_images(x)
        self.connect_signal()
        if self.project.vlayer.fields().indexFromName('string_number') == -1:
                fieldz = QgsField('string_number', QVariant.String)
                self.project.vlayer.dataProvider().addAttributes([fieldz])
                self.project.vlayer.updateFields()

    def connect_signal(self):
        if not self.signal_connected:
            self.project.vlayer.selectionChanged.connect(self.signal_slot)
        self.signal_connected = True

    def disconnect_signal(self):
        # See if vector layer exists
        try:
            self.project.vlayer.isValid()
        except RuntimeError:
            return None
        if self.signal_connected:
            self.project.vlayer.selectionChanged.disconnect(self.signal_slot)
        self.signal_connected = False
    
    def toggle_signal_connection(self, visibility):
        if visibility and self.project.active_docktool_widget == self:
            self.connect_signal()
        else:
            self.disconnect_signal()

    def hide_widget(self):
        self.project.docktool_widget.hide()
        self.therm_tools.uncheck_all_buttons()

    def generate_service_objects(self):
        self.canvas_logger('Getting image urls')
        # Initially keep the buttons disabled
        for b in [self.nxt_img, self.previous_img]:
            b.setEnabled(False)
        self.uid_map = {}
        self.service_objects = []
        self.image_urls_loaded = False
        g = json.load(open(self.project.geojson_path))
        for f in g["features"]:
            raw_images = f["properties"].get("raw_images")
            uid = f["properties"].get("uid")
            if not raw_images and not uid:
                continue
            self.uid_map[uid] = raw_images
            self.service_objects +=  [r["service"] for r in raw_images if r]
        
        # get all rawimages download urls 
        self.start_get_image_urls()

    def get_img_urls_callback(self, get_img_url_task_status, get_img_urls):
        if get_img_url_task_status != 3:
            return None
        result = get_img_urls.returned_values
        self.image_urls = result['image_urls']
        self.image_urls_loaded = True
        self.canvas_logger(f'{self.project.project_details["name"]} : Therm viewer ready ')

    def start_get_image_urls(self):
        data = {"project_uid": self.project.project_details["uid"], 
                "organization": self.project.project_details.get("organization", {}).get("uid", None),
                "service_objects": self.service_objects}
        image_urls_input = {'data':data,
                            'token':self.project.core_token}
        get_img_urls = QgsTask.fromFunction("Get image urls", get_image_urls, image_urls_input)
        QgsApplication.taskManager().addTask(get_img_urls)
        get_img_urls.statusChanged.connect(lambda get_img_url_task_status: self.get_img_urls_callback(get_img_url_task_status, get_img_urls))

    def download_image(self, url, savepath):
        if not os.path.exists(savepath):
            try:
                request.urlretrieve(url, savepath)
            except Exception as e:
                print(url, savepath)
    
    def show_raw_images(self, selected_features):
        if not self.image_urls_loaded:
            self.canvas_logger("Still loading image urls", level=Qgis.Info)
            return None
        if not selected_features:
            return None
        self.sfeature = self.project.vlayer.getFeature(selected_features[-1])
        self.uid = self.sfeature["uid"]

        if not self.project.vlayer.fields().indexFromName('timestamp') == -1:
            try:
                timestamp = self.sfeature["timestamp"].toString()
            except AttributeError:
                timestamp = str(self.sfeature["timestamp"])

        if not self.project.vlayer.fields().indexFromName('uid') == -1 and self.sfeature['uid'] :  self.uid_name.setText(self.sfeature['uid']) 
        else: self.uid_name.setText("N/A") 
        if not self.project.vlayer.fields().indexFromName('timestamp') == -1 and self.sfeature['timestamp']: self.timestamp.setText(timestamp)
        else: self.timestamp.setText("N/A")
        if not self.project.vlayer.fields().indexFromName('string_number') == -1 and self.sfeature['string_number']:  self.string_number.setText(self.sfeature['string_number'])
        else: self.string_number.setText("N/A")
        if not self.project.vlayer.fields().indexFromName('temperature_min') == -1 and self.sfeature['temperature_min']:  self.min_temp.setText("{:.2f}".format(float(self.sfeature['temperature_min'])))
        else: self.min_temp.setText("N/A")
        if not self.project.vlayer.fields().indexFromName('temperature_max') == -1 and self.sfeature['temperature_max']:   self.max_temp.setText("{:.2f}".format(float(self.sfeature['temperature_max'])))
        else: self.max_temp.setText("N/A")
        if not self.project.vlayer.fields().indexFromName('temperature_difference') == -1 and self.sfeature['temperature_difference']:  self.delta_temp.setText("{:.2f}".format(float(self.sfeature['temperature_difference'])))
        else: self.delta_temp.setText('N/A')

        raw_images = self.uid_map.get(self.uid, [])
        self.num_raw_images = len(raw_images)
        if not raw_images:
            print("No raw images for this feature")
            return None
        self.image_paths = []
        self.marker_location = []
        for r in raw_images:
            key = r["service"]["key"]
            self.marker_location.append(r['location'])
            url = self.image_urls.get(key, None)
            save_path = os.path.join(self.images_dir, key.split("/")[-1])
            self.image_paths.append(save_path)
            t = threading.Thread(target=self.download_image, args=(url, save_path))
            t.start()
        # Only join the last download thread to the main thread
        if raw_images:
            t.join()
            self.image_index = 0
            self.change_image_index(0)

    def draw_box(self, imagecopy, x, y, w=32, h=32, image_w=640, image_h=512):
        x1 = max(int(x-w/2), 0)
        y1 = max(int(y-h/2), 0)
        x2 = min(int(x+w/2), image_w)
        y2 = min(int(y+h/2), image_h)
        image = cv2.rectangle(imagecopy, (x1, y1), (x2, y2), [255, 206, 85], 2, 1)
        if x or y:   
            image = cv2.drawMarker(imagecopy, (x, y), [0, 255, 0], cv2.MARKER_CROSS, 2, 2)
        return image
    
    def show_image(self, image_path, marker):
        x = marker[0]
        y = marker[1]
        image = cv2.imread(image_path)
        height, width, _ = image.shape
        bytesPerLine = 3 * width
        self.painted_image = self.draw_box(image.copy(), x, y)
        qImg = QImage(self.painted_image.data, width, height, bytesPerLine, QImage.Format_RGB888).rgbSwapped()
        img = QtGui.QPixmap(qImg)
        self.photo_viewer.setPhoto(img)

    def change_image_index(self, change):
        self.image_index += change
        if 0 > self.image_index > (self.num_raw_images - 1):
            self.previous_img.setEnabled(True)
            self.nxt_img.setEnabled(True)
        if self.image_index <= 0:
            self.image_index = 0
            self.previous_img.setEnabled(False)
        if self.image_index >= self.num_raw_images - 1:
            self.image_index = self.num_raw_images - 1
            self.nxt_img.setEnabled(False)

        self.show_image(self.image_paths[self.image_index], self.marker_location[self.image_index])

    def startediting(self):
        self.string_number.setReadOnly(False)

    def savestringnumber(self):
        self.sfeature['string_number'] = str(self.string_number.text())
        self.project.vlayer.updateFeature(self.sfeature)
        self.canvas_logger(f'{self.sfeature["uid"]} string number updated')
        self.string_number.setReadOnly(True)