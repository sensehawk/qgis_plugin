from PyQt5 import QtCore
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt5.QtWidgets import  QComboBox
from ..project_management.datatypes import Container
from qgis.PyQt import QtGui, QtWidgets, uic, QtGui
from qgis.PyQt.QtCore import Qt
from qgis.core import Qgis, QgsTask, QgsApplication
from functools import partial
from ..projectTabs import ProjectTabsWidget, Project
from ...tasks import project_loadtask 
from ...utils import categorize_layer, StringNumberTableWidget
from qgis.utils import iface
from ...constants import CORE_URL
from pathlib import Path
import os
import json
import requests
from ..nextracker.utils import nextracker_org_uid, generate_group_points
from ...event_filters import KeypressEmitter, KeypressFilter


therm_logo_png = QtGui.QPixmap(os.path.join(os.path.dirname(__file__), 'therm_logo.svg'))
terra_logo_png = QtGui.QPixmap(os.path.join(os.path.dirname(__file__), 'terra_logo.svg'))
add_logo_png = QtGui.QPixmap(os.path.join(os.path.dirname(__file__), 'add.png'))

class GroupWorkspace(QtWidgets.QWidget):
    def __init__(self, workspace_window, group_obj, group_dict):
        """Constructor."""
        super(GroupWorkspace, self).__init__()
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'group_workspace.ui'), self)
        self.logger = workspace_window.logger
        self.canvas_logger = workspace_window.canvas_logger
        self.core_token = workspace_window.core_token
        self.user_email = workspace_window.user_email
        self.workspace_window = workspace_window
        self.iface = iface
        self.org_uid = workspace_window.org_uid
        self.project_form = None
        self.group_delete_button.clicked.connect(self.delete_group)
        self.back_button.clicked.connect(self.load_group_workspace)
        self.group_edit_button.clicked.connect(lambda : GroupEdit(self, workspace_window, self.group_obj))
        self.terra_project_tabs_widget = ProjectTabsWidget(self)
        self.therm_project_tabs_widget = ProjectTabsWidget(self)
        self.group_action_button = None
        self.project_uids = []
        self.setupUi(group_obj, group_dict)
        self.intialize_keyboard_signals()
        self.stringnumber_widget = StringNumberTableWidget(self)
    
    def intialize_keyboard_signals(self):
        # Create a key emitter that sends the key presses
        self.key_emitter = KeypressEmitter()
        # Create keypress event filter to consume the key presses from iface and send it to key_emitter
        self.keypress_filter = KeypressFilter(self.key_emitter)
        # Install key press filter to iface's map canvas
        self.iface.mapCanvas().installEventFilter(self.keypress_filter)

    def setupUi(self, group_obj, group_dict):
        self.group_obj = group_obj
        self.group_dict = group_dict
        self.projects_form = QtWidgets.QFormLayout()
        self.project_groupbox = QtWidgets.QGroupBox('Projects:')
        self.projects_dict = self.group_obj.projects_details
        self.project_count_label.setText(f"Project Count: {len(self.projects_dict)}")
        self.group_label.setText(f"Group: {self.group_obj.name}")
        container_menu = QtWidgets.QMenu()
        assign_container_btn = QtWidgets.QAction('Assign CTR', self)
        remove_container_btn = QtWidgets.QAction("Remove", self)
        edit_container_btn = QtWidgets.QAction("Edit", self)
        create_container_btn = QtWidgets.QAction("Create", self)
        assign_app_btn = QtWidgets.QAction("Assign App", self)
        assign_container_btn.triggered.connect(lambda : AssignContainer(self, self.workspace_window, self.group_obj))
        edit_container_btn.triggered.connect(lambda :EditContainer(self, self.workspace_window, self.group_obj))
        create_container_btn.triggered.connect(lambda : CreateContainer(self, self.workspace_window, self.group_obj))
        remove_container_btn.triggered.connect(lambda : self.remove_container())
        assign_app_btn.triggered.connect(lambda : AssignApplication(self, self.workspace_window, self.group_obj))
        container_menu.addActions([edit_container_btn, create_container_btn ,remove_container_btn, assign_container_btn, assign_app_btn])
        self.container_btn.setMenu(container_menu) 

        # For Nextracker org, group action button is connected to Nextracker group points generation 
        if self.org_uid == nextracker_org_uid and not self.group_action_button:
            self.group_action_button = QtWidgets.QPushButton("Generate Nextracker Points")
            self.group_action_button.setFixedSize(280, 26)
            self.group_action_button.setStyleSheet("background-color:rgba(91, 160, 125, 100);")
            self.group_layout.addWidget(self.group_action_button)
            self.group_action_button.clicked.connect(lambda: generate_group_points(self.group_obj, self.org_uid, self.user_email, self.core_token, self.canvas_logger))
       
        if self.group_obj.container:
            # self.app_list = [a.get("name", None) for a in self.group_obj.container.applications]
            self.group_app_types = { app['name'] : app  for app in self.group_obj.container.applications}
            self.app_list = [app.get('application', None).get('name', None)   for app_name, app in self.group_app_types.items()]
            self.container_label.setText(f"Container: {self.group_obj.container.name}")
            self.container_btn.setText(':')
              
        else:
            self.app_list = []
            self.container_label.setText("Container: N/A")
            self.container_btn.setText('+')
            
        #clear if any existing application is already assigned
        self.remove_applications()

        #update assigned application
        self.show_applications()
        self.create_projects_buttons()

    def create_projects_buttons(self):
        # Create a lit of buttons for all projects in the group
        for project_uid, project_name in sorted(self.projects_dict.items(), key=lambda x: x[1]):
            hlayout = QtWidgets.QHBoxLayout()
            project_button = QtWidgets.QPushButton(f'{project_name}')
            project_button.setFixedSize(290, 26)
            project_button.setCheckable(True)
            opt_button = QtWidgets.QPushButton()
            opt_button.setFixedSize(38, 26)
            edit_btn = QtWidgets.QAction("Edit", self)
            move_btn = QtWidgets.QAction('Move', self)
            delete_btn = QtWidgets.QAction("Delete", self)
            report_btn = QtWidgets.QAction("Reports", self)
            duplicate_btn = QtWidgets.QAction("Duplicate", self)
            project_menu = QtWidgets.QMenu()
            project_menu.addActions([edit_btn, move_btn, delete_btn,  report_btn, duplicate_btn])
            opt_button.setMenu(project_menu)
            hlayout.addWidget(project_button)
            hlayout.addWidget(opt_button)
            project_button.clicked.connect(partial(self.checkapp_and_loadproject, project_uid, project_name))
            edit_btn.triggered.connect(partial( ProjectCreateAndEdit, self.workspace_window, self.group_obj, 'Edit', project_uid, project_name))
            move_btn.triggered.connect(partial ( MoveProject, self.workspace_window, self.group_dict, project_uid, self.group_obj, project_name))
            delete_btn.triggered.connect(partial(self.delete_project, project_uid, project_name))
            duplicate_btn.triggered.connect(partial ( DuplicateProject, self.workspace_window, self.group_dict, project_name, project_uid, self.group_obj))
            report_btn.triggered.connect(partial (ReportsDashboard, self.workspace_window, project_uid, project_name, self))
            self.projects_form.addRow(hlayout)

        self.new_project_btn = QtWidgets.QPushButton('+')
        self.new_project_btn.setFixedSize(290, 26)
        self.new_project_btn.clicked.connect(lambda : ProjectCreateAndEdit(self.workspace_window, self.group_obj, 'Create'))
        self.projects_form.addRow(self.new_project_btn)

        self.project_groupbox.setLayout(self.projects_form)
        self.project_selection_scrollarea.setWidget(self.project_groupbox)
        
        
    def remove_applications(self):
        logo_spaces = [self.app1, self.app2, self.app3, self.app4]
        for i in range(4):
            logo_spaces[i].clear()

    def show_applications(self):
        # Show application logos which are associated to the container to which this group belongs
        logo_map = {"therm": therm_logo_png, "terra": terra_logo_png}
        logo_spaces = [self.app1, self.app2, self.app3, self.app4]
        for i in range(len(self.app_list)):
            logo = logo_map[self.app_list[i]]
            logo.scaled(logo_spaces[i].size(), aspectRatioMode=QtCore.Qt.KeepAspectRatio)
            logo_spaces[i].setPixmap(logo)
            logo_spaces[i].setAlignment(Qt.AlignCenter)

    def delete_group(self):
        message_box = QtWidgets.QMessageBox()
        message_box.setIcon(QtWidgets.QMessageBox.Warning)
        message_box.setWindowTitle('Sensehawk Plugin')
        message_box.setText('Are you sure you want to delete this group')
        message_box.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        ret = message_box.exec_()
        if ret == QtWidgets.QMessageBox.Ok:
            org_uid = self.group_obj.org_info['uid']
            headers = {'Authorization':f'Token {self.workspace_window.core_token}'}
            url = f'https://core-server.sensehawk.com/api/v1/groups/{self.group_obj.uid}/?organization={org_uid}'
            delete_group_response = requests.delete(url, headers=headers)

            if delete_group_response.status_code == 204:
                self.canvas_logger(f'{self.group_obj.name} Group deleted Sucessfully...')
                self.workspace_window.home_window.groups_dict.pop(self.group_obj.uid)
                self.workspace_window.group_selection_widget.setup_ui(self.workspace_window)
                self.workspace_window.group_selection_widget.show()
                self.workspace_window.active_widget.hide()
                self.workspace_window.active_widget = self.workspace_window.group_selection_widget
                self.workspace_window.dashboard_ui.project_management_button.setChecked(True)
        else:
            pass

    def checkapp_and_loadproject(self, project_uid, project_name):
        # If multiple application assigned then user will be promated with an option to load project by either of them (Therm OR Terra)
        clicked_button = self.sender()
        clicked_button.setEnabled(False)
        clicked_button.setStyleSheet("background-color:#f7b7ad;")
        if not self.group_obj.container:
            self.canvas_logger('No Container associated to this group.', level=Qgis.Warning)
            clicked_button.setEnabled(True)
        if not self.app_list and self.group_obj.container:
            clicked_button.setEnabled(True)
            self.canvas_logger(f'No application associated to the {self.group_obj.container.name} container.', level=Qgis.Warning)
        elif len(self.app_list) > 1:
            self.app_selection_window = self.select_application(project_uid, clicked_button, project_name)
        elif len(self.app_list) == 1:
            if self.app_list[0] == "therm":
                application_type = 'therm'
            elif self.app_list[0] == "terra":
                application_type = 'terra'
            self.load_project(project_uid, clicked_button, project_name, application_type, self.group_obj, self.group_dict)

    def select_application(self, project_uid, clicked_button, project_name):
        dialog = QtWidgets.QDialog()
        dialog.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
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
            self.load_project(project_uid, clicked_button, project_name, application_type, self.group_obj, self.group_dict)   
        else:
            self.canvas_logger('Selection Cancelled', level=Qgis.Warning)
    
    def load_group_workspace(self):
        self.workspace_window.active_widget.hide()
        self.workspace_window.group_selection_widget.show()
        self.workspace_window.active_widget = self.workspace_window.group_selection_widget
        self.workspace_window.dashboard_ui.project_management_button.setChecked(True)
        
    def show_projects_loaded(self, application_type):
        if application_type == 'therm':
            if not self.workspace_window.therm_tab_button:
                self.workspace_window.therm_tab_button = QtWidgets.QPushButton('Therm')
                self.workspace_window.therm_tab_button.setFixedSize(62, 62)
                self.workspace_window.therm_tab_button.clicked.connect(self.workspace_window.load_therm_tab_widget)
                self.workspace_window.therm_tab_button.setCheckable(True)
                self.workspace_window.therm_tab_button.setChecked(True)
                self.workspace_window.dashboard_ui.module_layout.addWidget(self.workspace_window.therm_tab_button)

            if not self.workspace_window.therm_project_tabs_widget:
                self.workspace_window.therm_project_tabs_widget = self.therm_project_tabs_widget
                self.workspace_window.pm_workspace_grid.addWidget(self.therm_project_tabs_widget, 0, 1)
                self.workspace_window.load_therm_tab_widget()
            else:
                self.workspace_window.therm_tab_button.setChecked(True)
                self.workspace_window.load_therm_tab_widget()

        elif application_type == 'terra':
            if not self.workspace_window.terra_tab_button:
                self.workspace_window.terra_tab_button = QtWidgets.QPushButton('Terra')
                self.workspace_window.terra_tab_button.setFixedSize(62, 62)
                self.workspace_window.terra_tab_button.clicked.connect(self.workspace_window.load_terra_tab_widget)
                self.workspace_window.terra_tab_button.setCheckable(True)
                self.workspace_window.terra_tab_button.setChecked(True)
                self.workspace_window.dashboard_ui.module_layout.addWidget(self.workspace_window.terra_tab_button)

            if not self.workspace_window.terra_project_tabs_widget:
                self.workspace_window.terra_project_tabs_widget = self.terra_project_tabs_widget
                self.workspace_window.pm_workspace_grid.addWidget(self.terra_project_tabs_widget, 0,1)
                self.workspace_window.load_terra_tab_widget()
            else:
                self.workspace_window.terra_tab_button.setChecked(True)
                self.workspace_window.load_terra_tab_widget()

    def project_load_callback(self, load_task_status, load_task, application_type, group_obj, group_dict):
        if load_task_status != 3:
            return None
        result = load_task.returned_values
        
        if not result:
            self.logger("Load failed...", level=Qgis.Warning)
            return None
        # Create a project object from the callback result
        project = Project(result, application_type)
        project.user_email = self.user_email
        project.canvas_logger = self.canvas_logger
        project.logger = self.logger
        project.group_dict = group_dict
        project.group_obj = group_obj
        project.org_uid = self.group_obj.org_info.get('uid', None)
        project.home_window = self.workspace_window.home_window 
        project.stringnumber_widget = self.stringnumber_widget
        
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


    def load_project(self, project_uid, clicked_button, project_name, application_type, group_obj, group_dict):
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
        if project_uid not in self.project_uids:
            self.project_uids.append(project_uid)
        self.logger(f"Deal ID: {self.group_obj.deal_id}")
        self.logger(f"Asset UID: {self.group_obj.container.asset.uid}")
        
        load_task_inputs = {"project_uid": project_uid,
                            "project_type": application_type,
                            "core_token": self.core_token,
                            "org_uid":self.group_obj.org_info.get('uid', None),
                            "container_uid":self.group_obj.container.uid,
                            "container_name":self.group_obj.container.name,
                            "logger": self.logger}
        project_load_task = QgsTask.fromFunction(f"{project_name} Project Load", project_loadtask, load_task_inputs)
        QgsApplication.taskManager().addTask(project_load_task)
        project_load_task.statusChanged.connect(lambda load_task_status: self.project_load_callback(load_task_status, project_load_task, application_type, group_obj, group_dict))
        clicked_button.setEnabled(True)
    
    def delete_project(self, project_uid, project_name):
        message_box = QtWidgets.QMessageBox()
        message_box.setIcon(QtWidgets.QMessageBox.Warning)
        message_box.setWindowTitle('Delete Project')
        message_box.setText('Are you sure you want to delete this Project')
        message_box.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        ret = message_box.exec_()
        if ret == QtWidgets.QMessageBox.Ok:
            headers = {'Authorization':f'Token {self.workspace_window.core_token}'}
            url = CORE_URL+f'/api/v1/groups/{self.group_obj.uid}/projects/{project_uid}?organization={self.workspace_window.org_uid}'
            delete_group_response = requests.delete(url, headers=headers)

            if delete_group_response.status_code == 204:
                self.group_obj.projects_details.pop(project_uid)
                self.setupUi(self.group_obj, self.group_dict)
                self.canvas_logger(f'{project_name} Project deleted Sucessfully...')
        else:
            pass
    

    def remove_container(self):
        message_box = QtWidgets.QMessageBox()
        message_box.setIcon(QtWidgets.QMessageBox.Warning)
        message_box.setWindowTitle('Remove Container')
        message_box.setText('Are you sure you want to move out of the container?')
        message_box.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        if self.group_obj.container:
            ret = message_box.exec_()
        else:
            self.workspace_window.canvas_logger('No Container assigned to the Current Group...', level=Qgis.Warning)
            return None
        
        if ret == QtWidgets.QMessageBox.Ok:
            headers = {'Authorization':f'Token {self.workspace_window.core_token}'}
            url = CORE_URL+f'/api/v1/containers/{self.group_obj.container.uid}/?organization={self.workspace_window.org_uid}'
            groups_info = []
            for group_info in self.group_obj.container.group_info:
                if group_info['uid'] != self.group_obj.uid:
                    groups_info.append(group_info)
            json = {'groups':groups_info}
            remove_container_response = requests.patch(url, headers=headers, json=json)
            if remove_container_response.status_code == 200:
                container_obj = self.workspace_window.home_window.containers_dict[self.group_obj.container.uid]
                container_obj.group_info = groups_info
                self.group_obj.container = None
                self.setupUi(self.group_obj, self.group_dict)
                self.workspace_window.canvas_logger('Container Detached from the Current Group...', level=Qgis.Success)
        else:
            pass
        

class DuplicateProject(QtWidgets.QDialog):
    def __init__(self, workspace_window, group_dict, project_name, project_uid, group_obj):
        super(DuplicateProject, self).__init__()
        self.workspace_window = workspace_window 
        self.group_dict = group_dict
        self.project_name = project_name
        self.project_uid = project_uid
        self.group_obj = group_obj
        layout = QtWidgets.QVBoxLayout(self)
        self.setWindowTitle("Duplicate Project")
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.group_details = {group_obj.name:group_uid for group_uid, group_obj in self.group_dict.items()}
        self.duplicate_project_ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'duplicate_project.ui'))
        self.duplicate_project_ui.group_list.addItems(list(self.group_details.keys()))
        self.duplicate_project_ui.project_name.setText(self.project_name)
        button_box = QtWidgets.QDialogButtonBox()
        button_box.addButton("Duplicate", QtWidgets.QDialogButtonBox.AcceptRole)
        button_box.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
        button_box.accepted.connect(self.duplicate_project)
        button_box.rejected.connect(self.close_dialogbox)
        button_box.setCenterButtons(True)
        layout.addWidget(self.duplicate_project_ui)
        layout.addWidget(button_box)
        self.exec_()

    def duplicate_project(self):
        if self.duplicate_project_ui.project_name.text() and self.duplicate_project_ui.group_list.currentText() != 'Select a Group':
            self.accept()
            headers = {'Authorization':f'Token {self.workspace_window.core_token}'}
            foster_group_uid = self.group_details[self.duplicate_project_ui.group_list.currentText()]
            json = [{'name':self.duplicate_project_ui.project_name.text(), 'uid':self.project_uid}]
            url = CORE_URL+f'/api/v1/groups/{foster_group_uid}/copy-projects/?organization={self.workspace_window.org_uid}'
            duplicate_project_response = requests.post(url, headers=headers, json=json)
            if duplicate_project_response.status_code == 200:
                child_project_uid = duplicate_project_response.json()[0]['uid']
                foster_group_obj = self.group_dict[foster_group_uid]
                foster_group_obj.projects_details[child_project_uid] = self.duplicate_project_ui.project_name.text()
                self.workspace_window.group_workspace.setupUi(self.group_obj, self.workspace_window.home_window.groups_dict)
                self.workspace_window.canvas_logger('Project Duplicated Successfully...', level=Qgis.Success)
        else:
            if not self.duplicate_project_ui.project_name.text():
                self.workspace_window.canvas_logger('Project name field is Empty...', level=Qgis.Warning)
            elif self.duplicate_project_ui.group_list.currentText == 'Select a Group':
                self.workspace_window.canvas_logger('Select a group to duplicate the Project...', level=Qgis.Warning)

    def close_dialogbox(self):
        self.reject()

class MoveProject(QtWidgets.QDialog):
    def __init__(self, workspace_window, group_dict, project_uid, group_obj, project_name):
        super(MoveProject, self).__init__()
        self.workspace_window = workspace_window 
        self.group_dict = group_dict
        self.project_uid = project_uid
        self.group_obj = group_obj
        self.project_name = project_name
        self.setWindowTitle("Move Project")
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        layout = QtWidgets.QVBoxLayout(self)
        self.group_details = {group_obj.name:group_uid for group_uid, group_obj in self.group_dict.items()}
        self.move_project_ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'move_project.ui'))
        self.move_project_ui.group_list.addItems(list(self.group_details.keys()))
        button_box = QtWidgets.QDialogButtonBox()
        button_box.addButton("Move", QtWidgets.QDialogButtonBox.AcceptRole)
        button_box.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
        button_box.accepted.connect(self.move_project)
        button_box.rejected.connect(self.close_dialogbox)
        button_box.setCenterButtons(True)
        layout.addWidget(self.move_project_ui)
        layout.addWidget(button_box)
        self.exec_()
    
    def move_project(self):
        if self.move_project_ui.group_list.currentText() != 'Select a Group':
            self.accept()
            headers = {'Authorization':f'Token {self.workspace_window.core_token}'}
            selected_group_name = self.move_project_ui.group_list.currentText()
            foster_group_uid = self.group_details[selected_group_name]
            url = CORE_URL + f'/api/v1/groups/{foster_group_uid}/move-projects/?organization={self.group_obj.org_info.get("uid", None)}'
            json = {'projects':[self.project_uid]}
            move_project_response = requests.post(url, headers=headers, json=json)
            if move_project_response.status_code == 200 :
                self.group_obj.projects_details.pop(self.project_uid)
                foster_group_obj = self.group_dict[foster_group_uid]
                foster_group_obj.projects_details[self.project_uid] = self.project_name
                self.workspace_window.group_workspace.setupUi(self.group_obj, self.workspace_window.home_window.groups_dict)
                self.workspace_window.canvas_logger(f'{self.project_name} Project moved to {selected_group_name} Group....', level=Qgis.Success)
        else:
            self.workspace_window.canvas_logger('Select a Group to move the Project...', level=Qgis.Warning)

    def close_dialogbox(self):
        self.reject()

class ProjectCreateAndEdit(QtWidgets.QDialog):
    def __init__(self, workspace_window, group_obj, method, project_uid=None, project_name=None):
        super(ProjectCreateAndEdit, self).__init__()
        self.workspace_window = workspace_window
        self.group_obj = group_obj
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Create Project")
        layout = QtWidgets.QVBoxLayout(self)
        button_box = QtWidgets.QDialogButtonBox()
        if method == 'Create':
            self.project_create_ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'create_project.ui'))
            button_box.addButton("Create", QtWidgets.QDialogButtonBox.AcceptRole)
            button_box.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
            button_box.accepted.connect(self.create_project)
            button_box.rejected.connect(self.close_dialogbox)
            button_box.setCenterButtons(True)
            layout.addWidget(self.project_create_ui)
        elif method == 'Edit':
            self.project_edit_ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'create_project.ui'))
            self.project_uid = project_uid
            self.project_edit_ui.project_name.setText(project_name)
            button_box.addButton("Update", QtWidgets.QDialogButtonBox.AcceptRole)
            button_box.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
            button_box.accepted.connect(self.update_project)
            button_box.rejected.connect(self.close_dialogbox)
            button_box.setCenterButtons(True)
            layout.addWidget(self.project_edit_ui)
        
        layout.addWidget(button_box)
        self.headers = {'Authorization':f'Token {self.workspace_window.core_token}'}
        self.exec_()
    
    def update_project(self):
        if self.project_edit_ui.project_name.text():
            self.accept()
            json = {'name':self.project_edit_ui.project_name.text(),
                                                        'organization':{'uid':self.group_obj.org_info.get('uid', None)}
                                                       ,'group':{'uid':self.group_obj.uid}}
            url = CORE_URL + f'/api/v1/groups/{self.group_obj.uid}/projects/{self.project_uid}/?organization={self.group_obj.org_info.get("uid", None)}'
            update_project_response = requests.put(url, headers=self.headers, json=json)
            if update_project_response.status_code == 200:
                self.group_obj.projects_details[self.project_uid] = self.project_edit_ui.project_name.text()
                self.workspace_window.group_workspace.setupUi(self.group_obj, self.workspace_window.home_window.groups_dict)
                self.workspace_window.canvas_logger('Project Name updated Successfully...', level=Qgis.Success)
        else:
            self.workspace_window.canvas_logger('Project Name Field is Empty...', level=Qgis.Warning)


    def create_project(self):
        if self.project_create_ui.project_name.text():
            self.accept()
            json = {'name':self.project_create_ui.project_name.text()}
            url = CORE_URL+f'/api/v1/groups/{self.group_obj.uid}/projects/?organization={self.group_obj.org_info.get("uid", None)}' 
            create_project_response = requests.post(url, headers=self.headers,json=json)
            new_project_uid = create_project_response.json()['uid']
            if create_project_response.status_code == 201:
                self.group_obj.projects_details[new_project_uid] = self.project_create_ui.project_name.text()
                self.workspace_window.group_workspace.setupUi(self.group_obj, self.workspace_window.home_window.groups_dict)
                self.workspace_window.canvas_logger(f'{self.project_create_ui.project_name.text()} Project is created Successfully...', level=Qgis.Success)
        else:
            self.workspace_window.canvas_logger('Project Name Field is Empty...', level=Qgis.Warning)

    def close_dialogbox(self):
        self.reject()


class GroupEdit(QtWidgets.QDialog):
    def __init__(self, group_workspace, workspace_window, group_obj):
        super(GroupEdit, self).__init__()
        self.group_workspace = group_workspace
        self.workspace_window = workspace_window
        self.group_obj = group_obj
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Group Create")
        layout = QtWidgets.QVBoxLayout(self)
        self.group_edit_ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'edit_group.ui'))
        button_box = QtWidgets.QDialogButtonBox()
        button_box.addButton("Update", QtWidgets.QDialogButtonBox.AcceptRole)
        button_box.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
        button_box.accepted.connect(self.edit_group)
        button_box.rejected.connect(self.close_dialogbox)
        button_box.setCenterButtons(True)
        layout.addWidget(self.group_edit_ui)
        layout.addWidget(button_box)
        self.group_edit_ui.group_name.setText(group_obj.name)
        self.group_edit_ui.deal_id.setText(group_obj.deal_id)
        self.exec_()

    

    def edit_group(self):
        if self.group_edit_ui.deal_id.text() and self.group_edit_ui.group_name.text():
            self.accept()
            url = CORE_URL+f'/api/v1/groups/{self.group_obj.uid}/?organization={self.workspace_window.org_uid}'
            headers = {'Authorization':f'Token {self.workspace_window.core_token}'}
            json = {'name':self.group_edit_ui.group_name.text(),'organization':{'uid':self.workspace_window.org_uid},
                                                                  'deal_id':self.group_edit_ui.deal_id.text(),
                                                                  'asset':{'uid':self.workspace_window.asset.uid},
                                                                  'owner':{'uid':self.workspace_window.user_id}}
            group_create_response = requests.put(url, headers=headers, json=json)
            if group_create_response.status_code == 200 :
                self.group_workspace.group_label.setText(self.group_edit_ui.group_name.text())
                self.group_obj.name = self.group_edit_ui.group_name.text()
                self.group_obj.deal_id = self.group_edit_ui.deal_id.text()
                if self.group_obj.container:
                    for dict in self.group_obj.container.group_info:
                        if dict['uid'] == self.group_obj.uid:
                            dict['name'] = self.group_edit_ui.group_name.text()
                self.workspace_window.canvas_logger('Group Name updated Successfully...', level=Qgis.Success)
        else:
            if not self.group_edit_ui.group_name.text():
                self.workspace_window.canvas_logger('Group Name Field is Empty...', level=Qgis.Warning)
            elif not self.group_edit_ui.deal_id.text():
                self.workspace_window.canvas_logger('Deal ID Field is Empty..', level=Qgis.Warning)

    def close_dialogbox(self):
        self.reject()

class EditContainer(QtWidgets.QDialog):
    def __init__(self, group_workspace, workspace_window, group_obj):
        super(EditContainer, self).__init__()
        self.group_workspace = group_workspace
        self.workspace_window = workspace_window
        self.group_obj = group_obj
        self.setWindowTitle("Edit Container")
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        layout = QtWidgets.QVBoxLayout(self)
        self.edit_container_ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'container_edit.ui'))
        button_box = QtWidgets.QDialogButtonBox()
        button_box.addButton("Update", QtWidgets.QDialogButtonBox.AcceptRole)
        button_box.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
        button_box.accepted.connect(self.edit_container)
        button_box.rejected.connect(self.close_dialogbox)
        button_box.setCenterButtons(True)
        layout.addWidget(self.edit_container_ui)
        layout.addWidget(button_box)
        if self.group_obj.container:
            self.edit_container_ui.container_name.setText(self.group_obj.container.name)
            self.exec_()
        else:
            self.workspace_window.canvas_logger('No container assigned to this group for editing...', level=Qgis.Warning)
    
    def edit_container(self):
        if self.edit_container_ui.container_name.text():
            self.accept()
            headers = {'Authorization':f'Token {self.workspace_window.core_token}'}
            json = {"name":self.edit_container_ui.container_name.text(),
                    "organization":{"uid":self.workspace_window.org_uid},
                    "asset":{"uid":self.workspace_window.asset_uid},"owner":{"uid":self.workspace_window.user_id}}
            url = CORE_URL+f'/api/v1/containers/{self.group_obj.container.uid}/?organization={self.workspace_window.org_uid}'
            edit_container_response = requests.put(url, headers=headers, json=json)
            if edit_container_response.status_code == 200:
                self.group_obj.container.name = self.edit_container_ui.container_name.text()
                self.group_workspace.container_label.setText(f"Container:{self.edit_container_ui.container_name.text()}")
                self.workspace_window.canvas_logger('Container name edited Suscessfully..', level=Qgis.Success)
        else:
            self.workspace_window.canvas_logger('Container Name Field is Empty..', level=Qgis.Warning)

    def close_dialogbox(self):
        self.reject()


class AssignContainer(QtWidgets.QDialog):
    def __init__(self, group_workspace, workspace_window, group_obj):
        super(AssignContainer, self).__init__()
        self.group_workspace = group_workspace
        self.workspace_window = workspace_window
        self.group_obj = group_obj
        self.setWindowTitle("Assign Container")
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        layout = QtWidgets.QVBoxLayout(self)
        self.assign_container_ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'assign_container.ui'))
        self.containers_detail = { container.name:[container_uid, container.group_info] for container_uid, container in self.workspace_window.home_window.containers_dict.items()}
        container_list = list(self.containers_detail.keys())
        try:
            if self.group_obj.container.name in container_list:
                container_list.remove(self.group_obj.container.name)
        except AttributeError:
            pass
        self.assign_container_ui.container_list.addItems(container_list)
        button_box = QtWidgets.QDialogButtonBox()
        button_box.addButton("Assign", QtWidgets.QDialogButtonBox.AcceptRole)
        button_box.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
        button_box.accepted.connect(self.assign_container)
        button_box.rejected.connect(self.close_dialogbox)
        button_box.setCenterButtons(True)
        layout.addWidget(self.assign_container_ui)
        layout.addWidget(button_box)
        self.headers = {'Authorization':f'Token {self.workspace_window.core_token}'}
        self.exec_()
    
    def assign_container(self):
        if self.assign_container_ui.container_list.currentText() != 'Select Container':
            self.accept()
            
            if self.group_obj.container:
                remove_url = CORE_URL + f'/api/v1/containers/{self.group_obj.container.uid}/?organization={self.workspace_window.org_uid}'
                groups_info = self.group_obj.container.group_info
                for group_info in groups_info:
                    if group_info['uid'] == self.group_obj.uid:
                        groups_info.remove(group_info)
                remove_json = {'groups':groups_info}
                remove_group_from_container = requests.patch(remove_url, headers=self.headers, json=remove_json)

                if remove_group_from_container.status_code == 200:
                    current_container_obj = self.workspace_window.home_window.containers_dict[self.group_obj.container.uid]
                    for group in current_container_obj.group_info:
                        if group['uid'] == self.group_obj.uid:
                            current_container_obj.group_info.remove(group)
                    current_container_obj.groups_dict.pop(self.group_obj.uid)
                    container_name = self.assign_container_ui.container_list.currentText()
                    container_uid = self.containers_detail[container_name][0]
                    container_group_info = self.containers_detail[container_name][1]
                    add_json = {'groups':container_group_info}
                    add_json['groups'].append({'uid':self.group_obj.uid, 'name':self.group_obj.name})
                    add_url = CORE_URL + f'/api/v1/containers/{container_uid}/?organization={self.workspace_window.org_uid}'
                    add_group_to_container = requests.patch(add_url, headers=self.headers, json=add_json)
                    if add_group_to_container.status_code == 200:
                        container_obj = self.workspace_window.home_window.containers_dict[container_uid]
                        container_obj.groups_dict[self.group_obj.uid] = self.group_obj
                        self.group_obj.container = container_obj
                        self.workspace_window.group_workspace.setupUi(self.group_obj, self.workspace_window.home_window.groups_dict)
                        self.workspace_window.canvas_logger(f'Assigned {container_name} Container Successfully...', level=Qgis.Success)
                else:
                    self.workspace_window.canvas_logger(remove_group_from_container.json(), level=Qgis.Warning)

            else:
                container_name = self.assign_container_ui.container_list.currentText()
                container_uid = self.containers_detail[container_name][0]
                container_group_info = self.containers_detail[container_name][1]
                add_json = {'groups':container_group_info}
                add_json['groups'].append({'uid':self.group_obj.uid, 'name':self.group_obj.name})
                add_url = CORE_URL + f'/api/v1/containers/{container_uid}/?organization={self.workspace_window.org_uid}'
                add_group_to_container = requests.patch(add_url, headers=self.headers, json=add_json)
                if add_group_to_container.status_code == 200:
                        container_obj = self.workspace_window.home_window.containers_dict[container_uid]
                        container_obj.groups_dict[self.group_obj.uid] = self.group_obj
                        self.group_obj.container = container_obj
                        self.workspace_window.group_workspace.setupUi(self.group_obj, self.workspace_window.home_window.groups_dict)
                        self.workspace_window.canvas_logger(f'Assigned {container_name} Container Successfully...', level=Qgis.Success)
                else:
                    self.workspace_window.canvas_logger(add_group_to_container.json(), level=Qgis.Warning)


    def close_dialogbox(self):
        self.reject()

    

class CreateContainer(QtWidgets.QDialog):
    def __init__(self, group_workspace, workspace_window, group_obj):
        super(CreateContainer, self).__init__()
        self.group_workspace = group_workspace
        self.workspace_window = workspace_window
        self.group_obj = group_obj
        self.setWindowTitle("Create Container")
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        layout = QtWidgets.QVBoxLayout(self)
        self.create_container_ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'container_edit.ui'))
        button_box = QtWidgets.QDialogButtonBox()
        button_box.addButton("Create", QtWidgets.QDialogButtonBox.AcceptRole)
        button_box.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
        button_box.accepted.connect(self.create_container)
        button_box.rejected.connect(self.close_dialogbox)
        button_box.setCenterButtons(True)
        layout.addWidget(self.create_container_ui)
        layout.addWidget(button_box)
        self.exec_()
    
    def create_container(self):
        if self.create_container_ui.container_name.text():
            self.accept()
            json = {"name":self.create_container_ui.container_name.text(),"organization":{"uid":self.workspace_window.org_uid},
                                                                          "asset":{"uid":self.workspace_window.asset_uid},
                                                                          "owner":{"uid":self.workspace_window.user_id}}
            headers = {'Authorization':f'Token {self.workspace_window.core_token}'} 
            url = CORE_URL + f'/api/v1/containers/?organization={self.workspace_window.org_uid}'
            create_container_response = requests.post(url, headers=headers, json=json)
            if create_container_response.status_code == 201:
                response_json = create_container_response.json()
                new_container_uid = response_json['uid']
                new_container_name = response_json['name']
                new_container_obj = Container(new_container_uid, new_container_name,self.workspace_window.home_window.asset)
                self.workspace_window.home_window.containers_dict[new_container_uid] = new_container_obj
                self.workspace_window.canvas_logger(f'{self.create_container_ui.container_name.text()} Container Created Successfully...', level=Qgis.Success)
        else:
            self.workspace_window.canvas_logger('Container name Field is Empty...', level=Qgis.Warning)

    def close_dialogbox(self):
        self.reject()

class AssignApplication(QtWidgets.QDialog):
    def __init__(self, group_workspace, workspace_window, group_obj):
        super(AssignApplication, self).__init__()
        self.group_workspace = group_workspace
        self.workspace_window = workspace_window
        self.group_obj = group_obj
        self.setWindowTitle("Create Container")
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        layout = QtWidgets.QVBoxLayout(self)
        button_box = QtWidgets.QDialogButtonBox()
        button_box.addButton("Update", QtWidgets.QDialogButtonBox.AcceptRole)
        button_box.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
        button_box.accepted.connect(self.update_app)
        button_box.rejected.connect(self.close_dialogbox)
        button_box.setCenterButtons(True)
        self.checkbox_list = []
        for app_name, app in self.workspace_window.apptype_details.items():
            app_checkbox = QtWidgets.QCheckBox(app_name)
            if app_name in self.group_workspace.group_app_types:
                app_checkbox.setChecked(True)
            self.checkbox_list.append(app_checkbox)
            layout.addWidget(app_checkbox)
        layout.addWidget(button_box)
        if self.group_obj.container:
            self.exec_()
        else:
            self.workspace_window.canvas_logger('No Container assigned to this group...', level=Qgis.Warning)
    
    def update_app(self):
        self.accept()
        selected_apps = []
        for checkbox in self.checkbox_list:
            if checkbox.isChecked():
                selected_apps.append(self.workspace_window.apptype_details[checkbox.text()])
        json = {'app_types':selected_apps}
        headers = {'Authorization':f'Token {self.workspace_window.core_token}'} 
        url = CORE_URL+f'/api/v1/containers/{self.group_obj.container.uid}/?organization={self.workspace_window.org_uid}'
        assign_app_response = requests.patch(url, headers=headers, json=json)
        if assign_app_response.status_code == 200:
            self.group_obj.container.applications = selected_apps
            self.workspace_window.group_workspace.setupUi(self.group_obj, self.workspace_window.home_window.groups_dict)


    def close_dialogbox(self):
        self.reject()

class ReportsDashboard(QtWidgets.QDialog):
    def __init__(self, workspace_window, project_uid, project_name, group_obj):
        super(ReportsDashboard, self).__init__()
        self.project_uid = project_uid
        self.project_name = project_name
        self.group_obj = group_obj
        self.workspace_window = workspace_window
        self.setWindowTitle("Reports Upload")
        # self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        layout = QtWidgets.QVBoxLayout(self)
        self.reports_upload_ui = uic.loadUi(os.path.join(os.path.dirname(__file__),"reports_upload.ui"))
        self.reports_upload_ui.browse_file.clicked.connect(self.select_file)
        button_box = QtWidgets.QDialogButtonBox()
        button_box.addButton("Upload", QtWidgets.QDialogButtonBox.AcceptRole)
        button_box.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
        button_box.accepted.connect(self.upload_reports)
        button_box.rejected.connect(self.close_dialogbox)
        button_box.setCenterButtons(True)
        self.progress_bar = QtWidgets.QProgressBar()
        self.network_manager = QNetworkAccessManager(self)
        self.headers = {'Authorization':f'Token {self.workspace_window.core_token}'} 
        layout.addWidget(self.reports_upload_ui)
        layout.addWidget(self.progress_bar)
        layout.addWidget(button_box)
        self.module_width = None
        self.module_height = None
        self.upload_file_path = None
        self.auto_detect = False
        self.download_file_path = ("", "")
        self.aws_info = {"Asia Pacific (Mumbai)": {"name": "ap-south-1",     "bucket": "sh-inc-ap-south-1"},
                "US East (Ohio)"                : {"name": "us-east-2",      "bucket": "sh-inc-us-east-2"},
                "US West (N. California)"       : {"name": "us-west-1",      "bucket": "sh-inc-us-west-1"},
                "Asia Pacific (Singapore)"      : {"name": "ap-southeast-1", "bucket": "sh-inc-ap-southeast-1"},
                "Asia Pacific (Sydney)"         : {"name": "ap-southeast-2", "bucket": "sh-inc-ap-southeast-2" },
                "EU (Stockholm)"                : {"name": "eu-north-1",     "bucket": "sh-inc-eu-north-1"}}
        self.setup_ui()
        self.exec_()

    def setup_ui(self):
        path = os.path.join(os.path.dirname(__file__), 'report_type_info.json')
        with open(path, "r") as report_json:
            self.report_type_info = json.load(report_json)
        reports = list(self.report_type_info.keys())
        self.reports_upload_ui.report_type.addItems(reports)
        self.reports_upload_ui.aws_bucket.addItems(list(self.aws_info.keys()))
        url = f"https://therm-server.sensehawk.com/projects/{self.project_uid}/data?organization={self.workspace_window.org_uid}"
        response = requests.get(url=url, headers=self.headers)
        available_reports = response.json()
        for report_name, download_url in available_reports.items():
            report_download_widget = uic.loadUi(os.path.join(os.path.dirname(__file__),"report_download.ui"))
            report_download_widget.report_name.setText(report_name)
            report_download_widget.report_download.clicked.connect(partial(self.download_report, report_name, download_url))
            self.reports_upload_ui.download_report_layout.addWidget(report_download_widget)
        #TODO add support to download terra files
            # url = f"https://terra-server.sensehawk.com/container-views/{container_uid}/projects/{project_uid}/?organization={org_uid}"
            # res = requests.get(url, headers=headers).json()["reports"]
            # ortho_url = res.get("ortho", {}).get('url', None)
            # dsm_url = res.get("dsm", {}).get('url', None)


    def select_file(self):
        # Auto detect option while uploading ortho type report
        report_type = self.report_type_info.get(self.reports_upload_ui.report_type.currentText(), {}).get("name", "report")
        if report_type == "ortho":
            self.module_info()

        self.filter = self.report_type_info.get(self.reports_upload_ui.report_type.currentText(), {}).get("supported_formats", "All Files (*)")
        self.upload_file_path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Open", "", self.filter)
        if self.upload_file_path:
            if self.reports_upload_ui.file_name.text():
                self.file_name = self.reports_upload_ui.file_name.text()
            else:
                self.file_name = Path(self.upload_file_path).name
            self.reports_upload_ui.file_label.setText(Path(self.upload_file_path).name)
    
    def module_info(self):
        confirmation_dialog = QtWidgets.QDialog()
        confirmation_dialog.setWindowTitle("Confirmation")
        layout = QtWidgets.QVBoxLayout()
        self.module_info_ui = uic.loadUi(os.path.join(os.path.dirname(__file__),"detection_module_info.ui"))
        button_box = QtWidgets.QDialogButtonBox()
        button_box.addButton("Detect", QtWidgets.QDialogButtonBox.AcceptRole)
        button_box.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
        button_box.accepted.connect(lambda : self.update_moduelSize_info(confirmation_dialog))
        button_box.rejected.connect(lambda : self.close_module_info(confirmation_dialog))
        button_box.setCenterButtons(True)
        layout.addWidget(self.module_info_ui)
        layout.addWidget(button_box)
        confirmation_dialog.setLayout(layout)
        confirmation_dialog.exec_()
    
    def update_moduelSize_info(self, qdialog):
        print(self.module_info_ui.module_height.text(), self.module_info_ui.module_width.text())
        self.module_width, self.module_height = self.module_info_ui.module_width.text(), self.module_info_ui.module_height.text()
        self.auto_detect = True
        qdialog.close()
    
    def close_module_info(self, qdialog):
        self.auto_detect = False
        qdialog.close()

    def upload_reports(self):
        if not self.upload_file_path:
            self.group_obj.canvas_logger("Select the file to Upload...", level=Qgis.Warning)
            return 
        report_type = self.report_type_info.get(self.reports_upload_ui.report_type.currentText(), {}).get("name", "report")
                
        region = self.aws_info.get(self.reports_upload_ui.aws_bucket.currentText(), {}).get("name", "ap-south-1")
        # bucket   = self.aws_info.get(self.reports_upload_ui.aws_bucket.currentText(), {}).get("bucket", "sh-inc-ap-south-1")
        url = f"https://core-server.sensehawk.com/api/v1/projects/{self.project_uid}/reports/generate/post/?&organization={self.workspace_window.org_uid}"
        payload = {"report_type":report_type,"filename":self.file_name, "service": {"name": "aws_s3",
                                                                               "region": region}}
        s3_policy = requests.post(url=url, json=payload, headers=self.headers)

        if s3_policy.status_code == 200:
            self.db_payload = {}
            response = s3_policy.json()
            upload_url = response["url"]
            self.db_payload["name"] = response["filename"]
            self.db_payload["service"] = response["service"]
            self.db_payload["report_type"] = response["report_type"]
            content_type = self.report_type_info.get(self.reports_upload_ui.report_type.currentText(), {}).get("Content-type", "application/octet-stream")
            files = {"file":open(self.upload_file_path,'rb'), "Content-Type":content_type}
            #uploading File Using S3 URL
            self.upload_file(upload_url)

        else:
            self.group_obj.canvas_logger(s3_policy.json()[0], level=Qgis.Warning)

    def upload_file(self, url):
        upload_url = QtCore.QUrl(url)
        with open(self.upload_file_path, "rb") as file:
            file_content = file.read()
            data = QtCore.QByteArray(file_content)
            request = QNetworkRequest(upload_url)
            reply = self.network_manager.put(request, data)
            reply.uploadProgress.connect(self.upload_progress)
            reply.finished.connect(self.upload_complete)


    def upload_progress(self, bytes_sent, bytes_total):
        if bytes_total > 0:
            progress_percentage = int((bytes_sent / bytes_total) * 100)
            self.progress_bar.setValue(progress_percentage)

    def upload_complete(self):
        self.group_obj.canvas_logger("File Uploaded to S3 Bucket.", level=Qgis.Success)
        #Save report in DB
        update_url = f"https://core-server.sensehawk.com/api/v1/projects/{self.project_uid}/reports/?&organization={self.workspace_window.org_uid}"
        update_DB = requests.post(url=update_url, json=self.db_payload, headers=self.headers)
        if update_DB.status_code == 201:
            self.group_obj.canvas_logger("Report File Uploaded Successfully...", level=Qgis.Success)
            if self.auto_detect:
                self.detect_issues()
        else:
            self.group_obj.canvas_logger(f"{update_DB.json()} Unsuccessful...", level=Qgis.Warning)
        self.close()

    def get_ortho_url(self):
        url = f"https://therm-server.sensehawk.com/projects/{self.project_uid}/data?organization={self.workspace_window.org_uid}"
        response = requests.get(url, headers=self.headers).json()
        print(response)
        return response.get("ortho", None)
    
    def detect_issues(self):
        url =  f'https://sid.sensehawk.com/detect-solar-issues'
        headers = self.headers
        headers['email_id'] = self.workspace_window.user_email
        payload = {
                    "details": {
                        "projectUID": self.project_uid,
                        "user_email": self.workspace_window.user_email,
                        "angle" :iface.mapCanvas().rotation(),
                        "width":float(self.module_width),
                        "height":float(self.module_height)
                    },
                    # TODO ask udit to fetch ortho url usig project and org uid
                    "data": {"ortho": ""},
                    "geojson": {
                                "type": "FeatureCollection",
                                "features": []
                                }
                }
        
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 202:
            self.workspace_window.canvas_logger('Report uploaded and Detection Queued Successfully.',level=Qgis.Success)
        else:
            self.workspace_window.canvas_logger(response.json())

    def download_report(self, report_name, url):
        content_type = {"ortho":"TIFF FILES (*.tiff *.tif)", "dsm":"TIFF FILES (*.tiff *.tif)", "reflectance":"TIFF FILES (*.tiff *.tif)","processedImages":"ZIP (*.zip)",
                        "compressedImages":"ZIP (*.zip)", "calibratedParameters":"Text Files (*.txt)", "externalCalibratedParameters":"Text Files (*.txt)", "pdfReport":'application/pdf'}
        self.download_file_path = QtWidgets.QFileDialog.getSaveFileName(None, "Title",  directory=report_name, filter=content_type[report_name])
        if self.download_file_path[0]:
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            block_size = 500000  # 0.5 MB

            with open(self.download_file_path[0], 'wb') as file:
                for data in response.iter_content(block_size):
                    file.write(data)
                    downloaded_size = file.tell()
                    if total_size > 0:
                        percentage = (downloaded_size / total_size) * 100
                        self.progress_bar.setValue(percentage)
                    if percentage == 100:
                        self.group_obj.canvas_logger("Report File Downloaded Successfully")
                        self.close()
    
    def close_dialogbox(self):
        self.close()