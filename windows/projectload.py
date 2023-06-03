from qgis.PyQt.QtCore import Qt
from PyQt5 import QtCore, QtGui, QtWidgets 
from qgis.core import Qgis, QgsApplication, QgsTask, QgsProject, QgsMessageLog
from ..tasks import loadTask
from PyQt5.QtWidgets import QLineEdit, QCompleter, QVBoxLayout, QPushButton, QComboBox
from PyQt5.QtCore import QRect
from ..utils import download_file, load_vectors, categorize_layer , group_details, combobox_modifier,  project_details
import time 

class ProjectForm:
    def __init__(self, project_list, project_selection_layout, project_selection_window):
        if project_selection_window.projects_form :
            project_selection_layout.removeWidget(project_selection_window.projects_form.scroll_widget)
            project_selection_window.projects_form.scroll_widget.deleteLater()
            project_selection_window.projects_form.scroll_widget =None

        project_groupbox = QtWidgets.QGroupBox('Project details')
        myform = QtWidgets.QFormLayout()
        for project in project_list:
            button = QtWidgets.QPushButton(f'{project}')
            button.clicked.connect(project_selection_window.project_info)
            myform.addRow(button)

        project_groupbox.setLayout(myform)

        self.scroll_widget = QtWidgets.QScrollArea()
        self.scroll_widget.setWidget(project_groupbox)
        self.scroll_widget.setWidgetResizable(True)
        self.scroll_widget.setFixedHeight(200)
        project_selection_layout.addWidget(self.scroll_widget)


class ProjectLoadWindow(QtWidgets.QWidget):
    def __init__(self, homeobj, iface):
        super().__init__()
        self.projects_form = None
        self.project_details = None
        self.iface = iface
        self.home = homeobj
        self.core_token = self.home.core_token
        self.asset_uid = self.home.asset_uid
        self.org_uid = self.home.org_uid
        self.group_details = group_details(self.asset_uid, self.org_uid, self.core_token)

        group_list = list(self.group_details.keys())
        self.group_combobox = QComboBox(self) 
        self.group = combobox_modifier(self.group_combobox, group_list)
        self.group_uid = self.group_details[self.group.currentText()]
        # self.group.currentIndexChanged.connect(self.group_tree)

        # self.project_details = project_details(self.group_uid, self.org_uid, self.core_token)
        # project_list = list(self.project_details.keys())

        # self.back_button = QPushButton(self)
        # self.back_button.setText('home')
        # self.back_button.clicked.connect(self.back_to_home)

        # self.project_selection_layout = QtWidgets.QVBoxLayout(self)
        # self.project_selection_layout.addWidget(self.group)
        # self.project_selection_layout.addWidget(self.back_button)
        # self.project_selection_layout.setGeometry(QRect(500, 400, 400, 200))
        # self.projects_form = ProjectForm(project_list, self.project_selection_layout, self)

        load_project_task = QgsTask.fromFunction("load_asset_task", project_details, self.group_uid, self.org_uid, self.core_token )
        QgsApplication.taskManager().addTask(load_project_task)
        load_project_task.statusChanged.connect(lambda load_task_status: self.project_callback(load_task_status, load_project_task, project_window=self))

    def project_callback(self, load_task_status, load_project_task, project_window):
 
        project_window.group.currentIndexChanged.connect(project_window.group_tree)
        project_window.back_button = QPushButton(project_window)
        project_window.back_button.setText('home')
        project_window.back_button.clicked.connect(project_window.back_to_home)
        project_window.project_selection_layout = QtWidgets.QVBoxLayout(project_window)
        project_window.project_selection_layout.addWidget(project_window.group)
        project_window.project_selection_layout.addWidget(project_window.back_button)
        project_window.project_selection_layout.setGeometry(QRect(500, 400, 400, 200))
        result = load_project_task.returned_values
        try:
            project_window.project_details = result['project_list']
        except:
            project_window.project_details = result['project_list']
        project_list = list(project_window.project_details.keys())
        project_window.projects_form = ProjectForm(project_list, project_window.project_selection_layout, project_window)
       

    def project_info(self):
        clicked_button = self.sender()
        print(clicked_button.text())

    def group_tree(self):
        self.group_uid = self.group_details[self.group.currentText()]
        self.project_details = project_details(self.group_uid, self.org_uid, self.core_token)
        project_list = list(self.project_details.keys())
        self.projects_form = ProjectForm(project_list, self.project_selection_layout, self)
       
    def back_to_home(self):
        self.home.show()
        self.hide()