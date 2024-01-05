import os
from qgis.PyQt import QtWidgets, uic
from qgis.gui import QgsCheckableComboBox
from qgis.core import Qgis, QgsApplication, QgsTask
from qgis.PyQt import QtCore
from ..sensehawk_apis.scm_apis import train
import json


class MLServiceMapWidget(QtWidgets.QDialog):
    def __init__(self, project):
        super(MLServiceMapWidget, self).__init__()
        self.mlservice_ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'ml_service_map.ui'))
        self.project = project
        self.logger = self.project.tools_widget.logger
        self.iface = self.project.iface
        self.setWindowTitle("Request Model")
        layout = QtWidgets.QVBoxLayout(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        button_box = QtWidgets.QDialogButtonBox()
        button_box.addButton("Train", QtWidgets.QDialogButtonBox.AcceptRole)
        button_box.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
        button_box.accepted.connect(self.train)
        button_box.rejected.connect(self.close_dialogbox)
        button_box.setCenterButtons(True)
        layout.addWidget(self.mlservice_ui)
        layout.addWidget(button_box)
        # Add items to the lists
        self.populate_combo_boxes()
        self.exec_()

    def populate_combo_boxes(self):
        items = self.project.class_groups.get("Components", self.project.class_groups.get("components", []))
        self.mlservice_ui.detectionComboBox.addItems(items)
        self.mlservice_ui.segmentationComboBox.addItems(items)
        self.mlservice_ui.keypointComboBox.addItems(items)

    def train(self):
        self.accept()
        ml_service_map = {"segmentation": list(self.mlservice_ui.segmentationComboBox.checkedItems()),
                          "detection": list(self.mlservice_ui.detectionComboBox.checkedItems()),
                          "keypoint": list(self.mlservice_ui.keypointComboBox.checkedItems())}
        # Check for mutual exclusivity
        all_checked_items = [j for i in ml_service_map.values() for j in i]
        if len(all_checked_items) != len(set(all_checked_items)):
            self.logger("Detection list, Segmentation list and Keypoint list are not mutually exclusive!",
                        level=Qgis.Warning)
            return None
        with open(self.project.geojson_path, 'r') as fi:
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
                logger("Error: " + str(status) + str(result))

        train_inputs = [self.project.project_details, geojson, ml_service_map,
                        self.project.class_maps,
                        self.project.user_email,
                        self.project.core_token,
                        self.logger
                        ]


        # self.logger("--------- Payload Before calling Train() -----------")
        # self.logger(str(train_inputs))
        # self.logger("--------- End calling Train() -----------")

        train_task = QgsTask.fromFunction("Train request", train, train_inputs=train_inputs)
        train_task.statusChanged.connect(lambda: callback(train_task, self.logger))
        QgsApplication.taskManager().addTask(train_task)

    def close_dialogbox(self):
        self.close()