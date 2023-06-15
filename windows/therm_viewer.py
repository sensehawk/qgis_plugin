from ..constants import THERMAL_TAGGING_URL
import requests
import json
from qgis.PyQt import QtWidgets, uic
from qgis.utils import iface
from qgis.core import QgsApplication, QgsTask
from qgis.PyQt.QtCore import Qt 
from PyQt5.QtGui import QImage
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

class ThermViewerDockWidget(QtWidgets.QDockWidget, THERM_VIEWER):

    def __init__(self, therm_tools, project):
        """Constructor."""
        super(ThermViewerDockWidget, self).__init__()
        self.setupUi(self)
        self.therm_tools = therm_tools
        self.project = project
        self.active_layer = self.project.vlayer
        self.generate_service_objects()
        # self.get_image_urls()
        iface.addDockWidget(Qt.RightDockWidgetArea, self)
        self.project.project_tabs_widget.currentChanged.connect(self.hide_widget)
        self.project.vlayer.selectionChanged.connect(lambda x: self.show_raw_images(x))
        self.images_dir = os.path.join(tempfile.gettempdir(), self.project.project_details["uid"])
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)
        self.photo_viewer = PhotoViewer()
        self.image_layout.addWidget(self.photo_viewer)
        self.previous_img.clicked.connect(lambda: self.change_image_index(-1))
        self.nxt_img.clicked.connect(lambda: self.change_image_index(1))

    def generate_service_objects(self):
        self.uid_map = {}
        self.service_objects = []
        g = json.load(open(self.project.geojson_path))
        for f in g["features"]:
            raw_images = f["properties"].get("raw_images")
            uid = f["properties"].get("uid")
            if not raw_images and not uid:
                continue
            self.uid_map[uid] = raw_images
            self.service_objects +=  [r["service"] for r in raw_images] 
        
        # get all rawimages download urls 
        self.start_get_image_urls()

    def get_img_urls_callback(self, get_img_url_task_status, get_img_urls):
        if get_img_url_task_status != 3:
            return None
        result = get_img_urls.returned_values
        self.image_urls = result['image_urls']

    def start_get_image_urls(self):
        data = {"project_uid": self.project.project_details["uid"], 
                "organization": self.project.project_details.get("organization", {}).get("uid", None),
                "service_objects": self.service_objects}
        image_urls_input = {'data':data,
                            'token':self.project.core_token}
        get_img_urls = QgsTask.fromFunction("Get image urls", get_image_urls, image_urls_input)
        QgsApplication.taskManager().addTask(get_img_urls)
        get_img_urls.statusChanged.connect(lambda get_img_url_task_status: self.get_img_urls_callback(get_img_url_task_status, get_img_urls))

        # self.image_urls = requests.get(THERMAL_TAGGING_URL+"/get_object_urls", headers={"Authorization": f"Token {self.project.core_token}"}, json=data).json()
    
    def hide_widget(self):
        self.hide()
        self.therm_tools.uncheck_all_buttons()
    
    def download_image(self, url, savepath):
        if not os.path.exists(savepath):
            request.urlretrieve(url, savepath)
    

    def show_raw_images(self, selected_features):
        if not selected_features:
            return None
        feature = self.project.vlayer.getFeature(selected_features[-1])
        self.uid = feature["uid"]
        
        if not self.active_layer.fields().indexFromName('uid') == -1:  self.uid_name.setText(feature['uid']) 
        else: self.uid_name.setText("N/A") 
        if not self.active_layer.fields().indexFromName('timestamp') == -1: self.timestamp.setText(feature['timestamp'])
        else: self.timestamp.setText("N/A")
        if not self.active_layer.fields().indexFromName('string_number') == -1:  self.string_number.setText(feature['string_number'])
        else: self.string_number.setText("N/A")
        if not self.active_layer.fields().indexFromName('tempereature_min') == -1:  self.min_temp.setText(str(feature['temperature_min']))
        else: self.min_temp.setText("N/A")
        if not self.active_layer.fields().indexFromName('tempereature_max') == -1:   self.max_temp.setTexts(str(feature['temperature_max']))
        else: self.max_temp.setText("N/A")
        if not self.active_layer.fields().indexFromName('temperature_difference') == -1:  self.delta_temp.setText(str(feature['temperature_difference']))
        else: self.delta_temp.setText('N/A')

        if self.uid not in self.uid_map:
            print("No raw images for this feature")
            return None
        raw_images = self.uid_map[self.uid]
        self.image_paths = []
        self.marker_location = []
        # Download images
        # service_objects = [r["service"] for r in raw_images] 
        # self.get_image_urls(service_objects)

        for r in raw_images:
            key = r["service"]["key"]
            self.marker_location.append(r['location'])
            url = self.image_urls.get(key, None)
            save_path = os.path.join(self.images_dir, key.split("/")[-1])
            self.image_paths.append(save_path)
            t = threading.Thread(target=self.download_image, args=(url, save_path))
            t.start()
        # Only join the last download thread to the main thread
        t.join()
        self.image_index = 0
        self.previous_img.setEnabled(False)
        self.nxt_img.setEnabled(True)
        self.show_image(self.image_paths[0],self.marker_location[0])

    def draw_box(self, imagecopy, x, y, w=32, h=32, image_w=640, image_h=512):
        x1 = max(int(x-w/2), 0)
        y1 = max(int(y-h/2), 0)
        x2 = min(int(x+w/2), image_w)
        y2 = min(int(y+h/2), image_h)
        image = cv2.drawMarker(imagecopy, (x, y), [0, 255, 0], cv2.MARKER_CROSS, 2, 2)
        if  x and y :
            image = cv2.rectangle(imagecopy, (x1, y1), (x2, y2), [0, 0, 255], 2, 1)
        return image
    
    def show_image(self, image_path, marker):
        x = marker[0]
        y = marker[1]
        img = cv2.imread(image_path)
        self.painted_img = self.draw_box(img, x , y)
        self.height, self.width, self.channel = self.painted_img.shape
        self.bytesPerLine = 3 * self.width
        qImg = QImage(self.painted_img.data, self.width, self.height, self.bytesPerLine, QImage.Format_RGB888).rgbSwapped()
        self.photo_viewer.setPhoto(QtGui.QPixmap(qImg))

    def change_image_index(self, change):
        self.image_index += change
        if self.image_index <= 0:
            self.image_index = 0
            self.previous_img.setEnabled(False)
        else:
            self.previous_img.setEnabled(True)
        if self.image_index >= len(self.image_paths) - 1:
            self.image_index = len(self.image_paths) - 1
            self.nxt_img.setEnabled(False)
        else:
            self.nxt_img.setEnabled(True)

        self.show_image(self.image_paths[self.image_index], self.marker_location[self.image_index])

