from qgis.PyQt.QtCore import Qt
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from qgis.core import QgsProject
from qgis.utils import iface
from .terra_tools import TerraToolsWindow
from .therm_tools import ThermToolsWindow


class Project:
    def __init__(self, load_task_result):
        self.project_details = load_task_result['project_details']
        self.vlayer = load_task_result['vlayer']
        self.rlayer = load_task_result['rlayer']
        self.feature_counts = load_task_result['feature_counts']
        self.class_maps = load_task_result['class_maps']
        self.class_groups = load_task_result['class_groups']
        self.project_tab_index = None
        self.project_tab = QtWidgets.QWidget()
        # Create a layout that contains project details
        self.project_tab_layout = QtWidgets.QVBoxLayout(self.project_tab)
        self.tools_window = None
        self.project_tabs_window = None
        self.project_shortcuts = {}

    def connect_tools(self):
        if self.project_details["project_type"] == "terra":
            # Connect terra tools
            self.tools_window = TerraToolsWindow(self)
        elif self.project_details["project_type"] == "therm":
            # Connect therm tools
            self.tools_window = ThermToolsWindow(self)
        # Hide window for now
        self.tools_window.hide()

    def show_tools_window(self):
        self.tools_window.show()
        self.project_tabs_window.hide()

    def create_feature_count_table(self):
        # Create a table of feature counts
        feature_counts_table = QtWidgets.QTableWidget(self.project_tab)

        # Hide headers
        feature_counts_table.verticalHeader().setVisible(False)
        feature_counts_table.horizontalHeader().setVisible(False)

        # Disable editing
        feature_counts_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.project_tab_layout.addWidget(feature_counts_table)

        # Populate feature counts
        feature_counts_table.setRowCount(len(self.feature_counts))
        feature_counts_table.setColumnCount(2)
        for i, (feature_type, feature_count) in enumerate(self.feature_counts):
            feature_type_item = QtWidgets.QTableWidgetItem(feature_type)
            feature_count_item = QtWidgets.QTableWidgetItem(str(feature_count))
            feature_counts_table.setItem(i, 0, feature_type_item)
            feature_counts_table.setItem(i, 1, feature_count_item)
        feature_counts_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)

    def populate_project_tab(self):
        project_details = self.project_details
        # Create project UID label
        project_uid_label = QtWidgets.QLabel(self.project_tab)
        project_uid_label.setText(f"UID: {project_details['uid']}")
        self.project_tab_layout.addWidget(project_uid_label)
        # Create project type label
        project_type_label = QtWidgets.QLabel(self.project_tab)
        project_type_label.setText(f"Project type: {project_details['project_type'].capitalize()}")
        self.project_tab_layout.addWidget(project_type_label)
        # Create feature count table
        self.create_feature_count_table()
        # Create a tools button
        tools_button = QtWidgets.QPushButton(self.project_tab)
        tools_button.setText("Tools")
        self.project_tab_layout.addWidget(tools_button)
        # Connect this button to tools
        tools_button.clicked.connect(self.show_tools_window)


class ProjectTabsWindow(QtWidgets.QWidget):
    def __init__(self, load_window):
        super().__init__()
        self.load_window = load_window
        self.logger = self.load_window.logger
        # Save projects loaded dict mapping uid to project object
        self.projects_loaded = {}
        # Track index through uid list - index in list is the index of its tab
        self.project_uids = []
        self.setupUi()
        self.qgis_project = QgsProject.instance()
        self.layer_tree = self.qgis_project.layerTreeRoot()
        self.active_project = None

    def setupUi(self):

        # Create a group of widgets and define layout
        projects_group = QtWidgets.QGroupBox('Projects', self)
        projects_group_layout = QtWidgets.QVBoxLayout(projects_group)

        # Create base widget for the group
        projects_group_widget = QtWidgets.QWidget(projects_group)

        # Create a tabs widget and add it to the group layout
        self.project_tabs_widget = QtWidgets.QTabWidget(projects_group_widget)
        # Connect tab change event to activate project layers
        self.project_tabs_widget.currentChanged.connect(lambda x: self.activate_project_layers(self.projects_loaded[self.project_uids[x]]))
        projects_group_layout.addWidget(self.project_tabs_widget)

        # Create main layout for the main widget and add the widgets group
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(projects_group)

        # Create a back button
        back_button = QtWidgets.QPushButton(self)
        back_button.setText("Back")
        back_button.clicked.connect(self.back_to_load)
        main_layout.addWidget(back_button)

        self.hide()

    def back_to_load(self):
        self.hide()
        self.load_window.show()

    def add_project(self, project):
        # Add uid to a list to track tab index
        self.project_uids.append(project.project_details["uid"])
        self.projects_loaded[project.project_details["uid"]] = project
        # Add project tab to the tabs widget
        self.project_tabs_widget.addTab(project.project_tab, project.project_details["name"])
        # Show all project details in the project tab
        project.populate_project_tab()
        # Add project layers to the project
        self.qgis_project.addMapLayer(project.rlayer)
        self.qgis_project.addMapLayer(project.vlayer)
        # Set active layer and zoom to layer
        iface.setActiveLayer(project.vlayer)
        iface.actionZoomToLayer().trigger()
        project.project_tabs_window = self
        # Connect project tools
        project.connect_tools()
        # Activate project
        self.activate_project_layers(project)

    def activate_project_layers(self, project):
        """
        Make only the selected project layers visible and zoom to layer
        """
        for layer in self.layer_tree.layerOrder():
            if layer.id() in [project.rlayer.id(), project.vlayer.id()]:
                self.layer_tree.findLayer(layer.id()).setItemVisibilityChecked(True)
                if layer.id() == project.vlayer.id():
                    iface.setActiveLayer(layer)
                    iface.actionZoomToLayer().trigger()
            else:
                self.layer_tree.findLayer(layer.id()).setItemVisibilityChecked(False)


