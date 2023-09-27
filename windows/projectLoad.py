from qgis.PyQt.QtCore import Qt, QSize
from PyQt5 import QtCore, QtGui, QtWidgets 
from qgis.utils import iface
from qgis.core import Qgis, QgsApplication, QgsTask, QgsProject, QgsMessageLog
from PyQt5.QtWidgets import QLineEdit, QLabel,QCompleter, QVBoxLayout, QPushButton, QComboBox
from PyQt5.QtCore import QRect
from ..utils import download_file, load_vectors, categorize_layer , groups_details, combobox_modifier, containers_details
from .projectTabs import ProjectTabsWidget, Project
from ..event_filters import KeypressFilter, KeypressEmitter, KeypressShortcut, MousepressFilter

class ProjectForm:
    def __init__(self, project_list, project_selection_layout, project_selection_window):
        self.project_groupbox = QtWidgets.QGroupBox('Projects:')
        self.myform = QtWidgets.QFormLayout()
        for project in project_list:
            button = QtWidgets.QPushButton(f'{project}')
            button.clicked.connect(project_selection_window.load_project_layers)
            self.myform.addRow(button)

        self.project_groupbox.setLayout(self.myform)

        self.scroll_widget = QtWidgets.QScrollArea()
        self.scroll_widget.setWidget(self.project_groupbox)
        self.scroll_widget.setWidgetResizable(True)
        self.scroll_widget.setFixedHeight(400)
        # Replace the scroll widget if it exists
        if project_selection_window.projects_form:
            project_selection_layout.replaceWidget(project_selection_window.projects_form.scroll_widget, self.scroll_widget)
        else:
            project_selection_layout.addWidget(self.scroll_widget, 0, Qt.AlignTop)
