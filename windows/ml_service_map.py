import os
from qgis.PyQt import QtWidgets, uic
from qgis.gui import QgsCheckableComboBox
from qgis.core import Qgis, QgsApplication, QgsTask
from qgis.PyQt.QtCore import Qt
from ..sensehawk_apis.scm_apis import train
import json


ML_SERVICE_MAP_UI, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ml_service_map.ui'))

class MLServiceMapWindow(QtWidgets.QDockWidget, ML_SERVICE_MAP_UI):

    def __init__(self, iface, class_groups, tools_window):
        super(MLServiceMapWindow, self).__init__()
        self.setupUi(self)
        self.class_groups = class_groups
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
        self.tools_window.ml_service_map_window = self
        self.tools_window.show()
        self.hide()

    def populate_combo_boxes(self):
        items = self.class_groups.get("Components", self.class_groups.get("components", []))
        # self.detectionComboBox.addItems(items)
        # self.segmentationComboBox.addItems(items)
        self.classesComboBox.addItems(items)

    def train(self):
        # ml_service_map = {"segmentation": list(self.segmentationComboBox.checkedItems()),
        #                   "detection": list(self.detectionComboBox.checkedItems())}
        # Only segmentation service is enabled and all classes are modeled using UNet
        ml_service_map = {"segmentation": list(self.classesComboBox.checkedItems()),
                          "detection": []}
        # if list(set(ml_service_map["detection"]) & set(ml_service_map["segmentation"])):
        #     self.logger("Detection list and Segmentation list are not mutually exclusive!", level=Qgis.Warning)
        #     return None
        self.logger("ML Service map: {}".format(str(ml_service_map)))
        with open(self.tools_window.load_window.geojson_path, 'r') as fi:
            geojson = json.load(fi)

        def callback(task, logger):
            result = task.returned_values
            status = None
            if result:
                status = result.get("status")
            if status == 503:
                logger("Trainer service is off. Please request to turn it on before trying again!", level=Qgis.Warning)
            elif status == 202:
                logger("Train request sent successfully!")
            else:
                logger(str(status))

        self.logger(str(self.tools_window.class_maps))
        train_inputs = [self.tools_window.project_details, geojson, ml_service_map, self.tools_window.class_maps,
                        self.tools_window.load_window.user_email, self.tools_window.core_token]
        train_task = QgsTask.fromFunction("Train request", train, train_inputs=train_inputs)
        train_task.statusChanged.connect(lambda:callback(train_task, self.logger))
        QgsApplication.taskManager().addTask(train_task)
