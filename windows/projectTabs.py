from qgis.PyQt.QtCore import Qt
import os
from PyQt5 import QtCore, QtGui, QtWidgets


class ProjectTabsWindow(QtWidgets.QWidget):
    def __init__(self, load_window):
        super().__init__()
        self.load_window = load_window
        self.logger = self.load_window.logger

        # Save projects loaded list | index in list is the index of its tab
        self.projects_loaded = []
        self.setupUi()

    def setupUi(self):

        # Create a group of widgets and define layout
        projects_group = QtWidgets.QGroupBox('Projects', self)
        projects_group_layout = QtWidgets.QVBoxLayout(projects_group)

        # Create base widget for the group
        projects_group_widget = QtWidgets.QWidget(projects_group)

        # Create a tabs widget and add it to the group layout
        self.project_tabs_widget = QtWidgets.QTabWidget(projects_group_widget)
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

    def create_feature_count_table(self, feature_counts):
        # Create a table of feature counts
        feature_counts_table = QtWidgets.QTableWidget(self)

        # Hide headers
        feature_counts_table.verticalHeader().setVisible(False)
        feature_counts_table.horizontalHeader().setVisible(False)

        # Disable editing
        feature_counts_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.project_details_layout.addWidget(feature_counts_table)

        # Populate feature counts
        feature_counts_table.setRowCount(len(feature_counts))
        feature_counts_table.setColumnCount(2)
        for i, (feature_type, feature_count) in enumerate(feature_counts):
            feature_type_item = QtWidgets.QTableWidgetItem(feature_type)
            feature_count_item = QtWidgets.QTableWidgetItem(str(feature_count))
            feature_counts_table.setItem(i, 0, feature_type_item)
            feature_counts_table.setItem(i, 1, feature_count_item)
        feature_counts_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)

    def show_project_details(self, project_details):
        # Create project UID label
        project_uid_label = QtWidgets.QLabel(self)
        project_uid_label.setText(f"UID: {project_details['uid']}")
        self.project_details_layout.addWidget(project_uid_label)
        # Create project type label
        project_type_label = QtWidgets.QLabel(self)
        project_type_label.setText(f"Project type: {project_details['project_type']}")
        self.project_details_layout.addWidget(project_type_label)

    def add_project(self, project_details, feature_counts):
        project_uid = project_details["uid"]
        project_name = project_details["name"]
        # Create tab widget and add to the tabs widget
        tab = QtWidgets.QWidget()
        self.projects_loaded.append(project_uid)
        self.project_tabs_widget.addTab(tab, project_name)
        self.project_type = project_details["project_type"]
        # Create a layout that contains project details
        self.project_details_layout = QtWidgets.QVBoxLayout(tab)
        # Show project details
        self.show_project_details(project_details)
        # Create feature count table
        self.create_feature_count_table(feature_counts)

