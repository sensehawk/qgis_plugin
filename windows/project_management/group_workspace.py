from PyQt5 import QtCore
from PyQt5.QtWidgets import  QComboBox
from ..project_management.datatypes import Asset
from qgis.PyQt import QtGui, QtWidgets, uic, QtGui
from qgis.PyQt.QtCore import Qt
from qgis.core import Qgis, QgsTask, QgsApplication
from .groups_homepage import GroupsForm
from functools import partial
from ..projectTabs import ProjectTabsWidget, Project
from ...tasks import Project_loadTask 
from ...utils import categorize_layer
import os
import time

therm_logo_png = QtGui.QPixmap(os.path.join(os.path.dirname(__file__), 'therm_logo.svg'))
terra_logo_png = QtGui.QPixmap(os.path.join(os.path.dirname(__file__), 'terra_logo.svg'))


class GroupWorkspace(QtWidgets.QWidget):
    def __init__(self, workspace_window, group_obj):
        """Constructor."""
        super(GroupWorkspace, self).__init__()
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'group_workspace.ui'), self)
        self.group_obj = group_obj
        self.logger = workspace_window.logger
        self.canvas_logger = workspace_window.canvas_logger
        self.core_token = workspace_window.core_token
        self.user_email = workspace_window.user_email
        self.workspace_window = workspace_window
        self.project_form = None
        self.therm_project_tabs_widget = ProjectTabsWidget(self)
        self.terra_project_tabs_widget = ProjectTabsWidget(self)
        self.back_button.clicked.connect(self.load_group_workspace)
        self.setupUi()
    
    def setupUi(self):
        self.projects_form = QtWidgets.QFormLayout()
        self.project_groupbox = QtWidgets.QGroupBox('Projects:')
        self.projects_dict = self.group_obj.projects_details
        self.project_count_label.setText(f"Project Count: {len(self.projects_dict)}")
        self.group_label.setText(f"Group: {self.group_obj.name}")
        
        if self.group_obj.container:
            self.app_list = [a.get("name", None) for a in self.group_obj.container.applications]
            self.container_label.setText(f"Container: {self.group_obj.container.name}")
        else:
            self.app_list = []
            self.container_label.setText("Container: N/A")

        self.show_applications()
        self.create_projects_buttons()

    def create_projects_buttons(self):
        # Create a lit of buttons for all projects in the group
        for project_uid, project_name in sorted(self.projects_dict.items(), key=lambda x: x[1]):
            hlayout = QtWidgets.QHBoxLayout()
            project_button = QtWidgets.QPushButton(f'{project_name}')
            project_button.setFixedSize(250, 26)
            edit_button = QtWidgets.QPushButton('📝')
            edit_button.setFixedSize(38, 26)
            delete_button = QtWidgets.QPushButton('🗑️')
            delete_button.setFixedSize(38, 26)
            hlayout.addWidget(project_button)
            hlayout.addWidget(edit_button)
            hlayout.addWidget(delete_button)
            project_button.clicked.connect(partial(self.checkapp_and_loadproject, project_uid, project_name))
            edit_button.clicked.connect(partial(self.edit_project, project_uid))
            delete_button.clicked.connect(partial(self.delete_project, project_uid))
            self.projects_form.addRow(hlayout)

        self.project_groupbox.setLayout(self.projects_form)
        self.project_selection_scrollarea.setWidget(self.project_groupbox)
    
    def show_applications(self):
        # Show application logos which are associated to the container to which this group belongs
        logo_map = {"therm": therm_logo_png, "terra": terra_logo_png}
        logo_spaces = [self.app1, self.app2, self.app3]
        for i in range(len(self.app_list)):
            logo = logo_map[self.app_list[i]]
            logo.scaled(logo_spaces[i].size(), aspectRatioMode=QtCore.Qt.KeepAspectRatio)
            logo_spaces[i].setPixmap(logo)
            logo_spaces[i].setAlignment(Qt.AlignCenter)

    def checkapp_and_loadproject(self, project_uid, project_name):
        # Each project button when clicked will be opened in the associated application if only one is associated, 
        # or user is notified to choose if multiple applications are associated or if no app is associated 
        clicked_button = self.sender()
        if not self.group_obj.container:
            self.canvas_logger('No Container associated to this group.', level=Qgis.Warning)
        if not self.app_list and self.group_obj.container:
            self.canvas_logger(f'No application associated to the {self.group_obj.container.name} container.', level=Qgis.Warning)
        elif len(self.app_list) > 1:
            self.app_selection_window = self.select_application(project_uid, clicked_button, project_name)
        elif len(self.app_list) == 1:
            if self.app_list[0] == "therm":
                application_type = 'therm'
            elif self.app_list[0] == "terra":
                application_type = 'terra'
            self.load_project(project_uid, clicked_button, project_name, application_type)

    def disable_button(self, button):
        print('button disabling')
        button.setEnabled(False)
        time.sleep(2)
        button.setEnabled(True)

    def select_application(self, project_uid, clicked_button, project_name):
        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle("Select the Application")
        layout = QtWidgets.QVBoxLayout(dialog)
        combo_box = QComboBox()
        combo_box.addItems(self.app_list)
        layout.addWidget(combo_box)
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected_option = combo_box.currentText()
            if selected_option == 'therm':
                application_type = 'therm'
            elif selected_option == 'terra':
                application_type = 'terra'
            self.load_project(project_uid, clicked_button, project_name, application_type)   
        else:
            self.canvas_logger('No application selected, choose application to load the project', level=Qgis.Warning)
    
    def load_group_workspace(self):
        self.workspace_window.active_widget.hide()
        self.workspace_window.group_selection_widget.show()
        self.workspace_window.active_widget = self.workspace_window.group_selection_widget
        
    def show_projects_loaded(self, application_type):
        if application_type == 'therm':
            if not self.workspace_window.therm_project_tabs_widget:
                self.workspace_window.therm_project_tabs_widget = self.therm_project_tabs_widget
                self.workspace_window.pm_workspace_grid.addWidget(self.therm_project_tabs_widget, 0,1, Qt.AlignTop)
                self.workspace_window.active_widget.hide()
                self.workspace_window.active_widget = self.therm_project_tabs_widget
            else:
                self.workspace_window.therm_project_tabs_widget.show()
                self.workspace_window.active_widget.hide()
                self.workspace_window.active_widget = self.therm_project_tabs_widget
        elif application_type == 'terra':
            # TODO set active_widget and load terra tab widget
            if not self.workspace_window.terra_project_tabs_widget:
                self.workspace_window.terra_project_tabs_widget = self.terra_project_tabs_widget
                self.workspace_window.pm_workspace_grid.addWidget(self.terra_project_tabs_widget, 0,1, Qt.AlignTop)
                self.workspace_window.active_widget.hide()
                self.workspace_window.active_widget = self.terra_project_tabs_widget
            else:
                self.workspace_window.terra_project_tabs_widget.show()
                self.workspace_window.active_widget.hide()
                self.workspace_window.active_widget = self.terra_project_tabs_widget

    def project_load_callback(self, load_task_status, load_task, application_type):
        if load_task_status != 3:
            return None
        result = load_task.returned_values
        self.logger(result)
        if not result:
            self.logger("Load failed...", level=Qgis.Warning)
            return None
        # Create a project object from the callback result
        project = Project(result)
        project.user_email = self.user_email
        project.canvas_logger = self.canvas_logger
        project.logger = self.logger
        project.group_details = self.group_obj
        
        # Add project to therm project tab
        if application_type == 'therm':
            new_project_index = len(self.therm_project_tabs_widget.project_uids)
            project.project_tab_index = new_project_index
            self.therm_project_tabs_widget.add_project(project)
            self.therm_project_tabs_widget.project_tabs_widget.setCurrentIndex(new_project_index)
            # Apply styling
            self.categorized_renderer = categorize_layer(project)
            # self.therm_project_tabs_widget.show()
            self.show_projects_loaded(application_type)
        elif application_type == 'terra':
            # TODO add terra project in terra tab widget 
            new_project_index = len(self.terra_project_tabs_widget.project_uids)
            project.project_tab_index = new_project_index
            self.terra_project_tabs_widget.add_project(project)
            self.terra_project_tabs_widget.project_tabs_widget.setCurrentIndex(new_project_index)
            # Apply styling
            self.categorized_renderer = categorize_layer(project)
            # self.therm_project_tabs_widget.show()
            self.show_projects_loaded(application_type)
        
    def load_project(self, project_uid, clicked_button, project_name, application_type):
        if application_type == 'therm':
            if project_uid in self.therm_project_tabs_widget.projects_loaded:
                self.logger("Project loaded already!")
                project_index = self.therm_project_tabs_widget.project_uids.index(project_uid)
                self.therm_project_tabs_widget.project_tabs_widget.setCurrentIndex(project_index)
                self.therm_project_tabs_widget.activate_project()
                self.show_projects_loaded(application_type)
                return None
            
        elif application_type == 'terra':
            if project_uid in self.terra_project_tabs_widget.projects_loaded:
                self.logger("Project loaded already!")
                project_index = self.terra_project_tabs_widget.project_uids.index(project_uid)
                self.terra_project_tabs_widget.project_tabs_widget.setCurrentIndex(project_index)
                self.terra_project_tabs_widget.activate_project()
                self.show_projects_loaded(application_type)
                return None
        
        load_task_inputs = {"project_uid": project_uid,
                            "project_type": application_type,
                            "core_token": self.core_token,
                            "org_uid":self.group_obj.org_info.get('uid', None),
                            'container_uid':self.group_obj.container.uid,
                            "logger": self.logger}
        project_load_task = QgsTask.fromFunction(f"{project_name} Project Load", Project_loadTask, load_task_inputs)
        QgsApplication.taskManager().addTask(project_load_task)
        project_load_task.statusChanged.connect(lambda load_task_status: self.project_load_callback(load_task_status, project_load_task, application_type))

        # disable clicked project button for a while
        self.disable_button(clicked_button)
        print("Loading therm project", project_uid)
       



    def edit_project(self, project_uid):
        print('Edit project', project_uid)
    
    def delete_project(self, project_uid):
        print('Delete project', project_uid)
