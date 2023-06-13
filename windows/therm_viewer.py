from ..constants import THERMAL_TAGGING_URL
import requests
import json
from qgis.PyQt import QtWidgets, uic
from qgis.utils import iface
from qgis.PyQt.QtCore import Qt 
from PyQt5.QtGui import QImage
from PyQt5 import QtCore, QtGui, QtWidgets 
import os
import tempfile
from urllib import request
import threading
from .thermliteQc import PhotoViewer


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
        self.generate_service_objects()
        self.get_image_urls()
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
            if not raw_images or not uid:
                continue
            self.uid_map[uid] = raw_images
            self.service_objects += [r["service"] for r in raw_images] 

    def get_image_urls(self):
        data = {"project_uid": self.project.project_details["uid"], 
                "organization": self.project.project_details.get("organization", {}).get("uid", None),
                "service_objects": self.service_objects}
        self.image_urls = requests.get(THERMAL_TAGGING_URL+"/get_object_urls", headers={"Authorization": f"Token {self.project.core_token}"}, json=data).json()
    
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
        uid = feature["uid"]
        if uid not in self.uid_map:
            print("No raw images for this feature")
            return None
        raw_images = self.uid_map[uid]
        self.image_paths = []
        # Download images
        for r in raw_images:
            key = r["service"]["key"]
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
        self.show_image(self.image_paths[0])
    
    def show_image(self, image_path):
        self.photo_viewer.setPhoto(QtGui.QPixmap(image_path))

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

        self.show_image(self.image_paths[self.image_index])

