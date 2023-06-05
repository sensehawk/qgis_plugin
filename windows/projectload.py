from qgis.PyQt.QtCore import Qt
from PyQt5 import QtCore, QtGui, QtWidgets 
from qgis.core import Qgis, QgsApplication, QgsTask, QgsProject, QgsMessageLog
from ..tasks import loadTask
from PyQt5.QtWidgets import QLineEdit, QCompleter, QVBoxLayout, QPushButton, QComboBox
from PyQt5.QtCore import QRect
from ..utils import download_file, load_vectors, categorize_layer , group_details, combobox_modifier, project_details
from .projectTabs import ProjectTabsWindow, Project


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
            button.clicked.connect(project_selection_window.load_project_layers)
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
        self.iface = iface
        self.home = homeobj
        self.core_token = self.home.core_token
        self.asset_uid = self.home.asset_uid
        self.org_uid = self.home.org_uid
        self.org_contianer_details = self.home.org_contianer_details
        self.group_details = group_details(self.asset_uid, self.org_uid, self.core_token) # list of all groups in asset and there respective projects are loaded all at once 

        group_list = list(self.group_details.keys())
        self.group_combobox = QComboBox(self) 
        self.group = combobox_modifier(self.group_combobox, group_list)
        self.group_uid = self.group_details[self.group.currentText()][0]
        self.associated_group_app = next((item['app_types'][0]['name'] for item in self.org_contianer_details if list(filter(lambda group: group['uid'] == self.group_uid, item['groups']))), None)
        self.group.currentIndexChanged.connect(self.group_tree)

        # self.project_details = project_details(self.group_uid, self.org_uid, self.core_token)
        self.project_details = self.group_details[self.group.currentText()][1]
        project_list = list(self.project_details.keys())

        self.project_tabs_window = ProjectTabsWindow(self)

        self.back_button = QPushButton(self)
        self.back_button.setText('home')
        self.back_button.clicked.connect(self.back_to_home)

        self.project_selection_layout = QtWidgets.QVBoxLayout(self)
        self.project_selection_layout.addWidget(self.group)
        self.project_selection_layout.addWidget(self.back_button)
        self.project_selection_layout.setGeometry(QRect(500, 400, 400, 200))
        self.projects_form = ProjectForm(project_list, self.project_selection_layout, self)

    def logger(self, message, level=Qgis.Info):
        QgsMessageLog.logMessage(message, 'SenseHawk QC', level=level)

    def group_tree(self):
        self.group_uid = self.group_details[self.group.currentText()][0]
        self.associated_group_app = next((item['app_types'][0]['name'] for item in self.org_contianer_details if list(filter(lambda group: group['uid'] == self.group_uid, item['groups']))), None)
        
        # self.project_details = project_details(self.group_uid, self.org_uid, self.core_token)
        self.project_details = self.group_details[self.group.currentText()][1]
        project_list = list(self.project_details.keys())
        self.projects_form = ProjectForm(project_list, self.project_selection_layout, self)

    def load_project_layers(self):
        app_dict = {"Solar Construction Monitoring": "terra", "Thermal analysis": "therm"}
        if not self.associated_group_app:
            self.logger("No application assigned to group...", level=Qgis.Warning)
            return None
        clicked_button = self.sender()
        project_uid = self.project_details[clicked_button.text()]
        project_type = app_dict[self.associated_group_app]
        self.start_project_load(project_uid, project_type)

    def load_callback(self, load_task_status, load_task):
        new_project_index = len(self.project_tabs_window.project_uids)
        if load_task_status != 3:
            return None
        result = load_task.returned_values
        if not result:
            self.logger("Load failed...", level=Qgis.Warning)
            return None
        # Create a project object from the callback result
        project = Project(result)

        # Add project to project tab
        project.project_tab_index = new_project_index
        self.project_tabs_window.add_project(project)
        self.project_tabs_window.project_tabs_widget.setCurrentIndex(new_project_index)
        self.show_project_tabs()

        # Apply styling
        self.categorized_renderer = categorize_layer(project_type=project.project_details["project_type"],
                                                     class_maps=project.class_maps)

    def start_project_load(self, project_uid, project_type):
        if not project_uid:
            self.logger("No project uid given", level=Qgis.Warning)
            return None
        # Load only if it is not already present in project tabs
        if project_uid in self.project_tabs_window.projects_loaded:
            self.logger("Project loaded already!")
            project_index = self.project_tabs_window.project_uids.index(project_uid)
            project = self.project_tabs_window.projects_loaded[project_uid]
            self.show_project_tabs()
            self.project_tabs_window.activate_project_layers(project)
            self.project_tabs_window.project_tabs_widget.setCurrentIndex(project_index)
            return None

        load_task_inputs = {"project_uid": project_uid,
                            "project_type": project_type,
                            "core_token": self.core_token,
                            "logger": self.logger}
        load_task = QgsTask.fromFunction("Load", loadTask, load_task_inputs)
        QgsApplication.taskManager().addTask(load_task)
        load_task.statusChanged.connect(lambda load_task_status: self.load_callback(load_task_status, load_task))

    def show_project_tabs(self):
        self.hide()
        self.project_tabs_window.show()
       
    def back_to_home(self):
        self.home.show()
        self.hide()


