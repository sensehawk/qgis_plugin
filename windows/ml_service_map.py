import os
from qgis.PyQt import QtWidgets, uic
from qgis.gui import QgsCheckableComboBox
from qgis.core import Qgis
from qgis.PyQt.QtCore import Qt
from ..sensehawk_apis.scm_apis import train


ML_SERVICE_MAP_UI, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ml_service_map.ui'))

class MLServiceMapWindow(QtWidgets.QDockWidget, ML_SERVICE_MAP_UI):

    def __init__(self, iface, class_maps, tools_window):
        super(MLServiceMapWindow, self).__init__()
        self.setupUi(self)
        self.class_maps = class_maps
        self.tools_window = tools_window
        self.logger = self.tools_window.logger
        self.backButton.clicked.connect(self.show_tools_window)
        self.iface = iface
        # Add to the left docking area by default
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self)
        # Add items to the lists
        self.populate_combo_boxes()
        # TODO:
        # Refresh list if checked items change
        self.trainButton.clicked.connect(self.train)

    def show_tools_window(self):
        self.logger(str(self.class_maps))
        self.tools_window.ml_service_map_window = self
        self.tools_window.show()
        self.hide()

    def populate_combo_boxes(self):
        items = list(self.class_maps.keys())
        self.detectionComboBox.addItems(items)
        self.segmentationComboBox.addItems(items)

    def train(self):
        ml_service_map = {"segmentation": list(self.detectionComboBox.checkedItems()),
                          "detection": list(self.segmentationComboBox.checkedItems())}
        if list(set(ml_service_map["detection"]) & set(ml_service_map["segmentation"])):
            self.logger("Detection list and Segmentation list are not mutually exclusive!", level=Qgis.Warning)
            return None

        # TODO: Train API

