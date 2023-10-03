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
from ...constants import CORE_URL
import os
import time
import requests

therm_logo_png = QtGui.QPixmap(os.path.join(os.path.dirname(__file__), 'therm_logo.svg'))
terra_logo_png = QtGui.QPixmap(os.path.join(os.path.dirname(__file__), 'terra_logo.svg'))


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
        self.project_form = None
        self.group_delete_button.clicked.connect(self.delete_group)
        self.back_button.clicked.connect(self.load_group_workspace)
        self.group_edit_button.clicked.connect(lambda : GroupEdit(self, workspace_window, self.group_obj))
        self.therm_project_tabs_widget = ProjectTabsWidget(self)
        self.terra_project_tabs_widget = ProjectTabsWidget(self)
        self.setupUi(group_obj, group_dict)
    
    def setupUi(self, group_obj, group_dict):
        self.group_obj = group_obj
        self.group_dict = group_dict
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
            opt_button = QtWidgets.QPushButton()
            opt_button.setFixedSize(38, 26)
            edit_btn = QtWidgets.QAction("Edit", self)
            move_btn = QtWidgets.QAction('Move', self)
            delete_btn = QtWidgets.QAction("Delete", self)
            duplicate_btn = QtWidgets.QAction("Duplicate", self)
            menu = QtWidgets.QMenu()
            menu.addActions([edit_btn, move_btn, delete_btn, duplicate_btn])
            opt_button.setMenu(menu)
            hlayout.addWidget(project_button)
            hlayout.addWidget(opt_button)
            project_button.clicked.connect(partial(self.checkapp_and_loadproject, project_uid, project_name))
            edit_btn.triggered.connect(partial( ProjectCreateAndEdit, self.workspace_window, self.group_obj, 'Edit', project_uid, project_name))
            move_btn.triggered.connect(partial ( MoveProject, self.workspace_window, self.group_dict, project_uid, self.group_obj, project_name))
            delete_btn.triggered.connect(partial(self.delete_project, project_uid, project_name))
            duplicate_btn.triggered.connect(lambda : print('Duplicate Clicked'))
            self.projects_form.addRow(hlayout)

        self.new_project_btn = QtWidgets.QPushButton('+')
        self.new_project_btn.setFixedSize(290, 26)
        self.new_project_btn.clicked.connect(lambda : ProjectCreateAndEdit(self.workspace_window, self.group_obj, 'Create'))
        self.projects_form.addRow(self.new_project_btn)

        self.project_groupbox.setLayout(self.projects_form)
        self.project_selection_scrollarea.setWidget(self.project_groupbox)
    
    def remove_applications(self):
        logo_spaces = [self.app1, self.app2, self.app3]
        for i in range(3):
            logo_spaces[i].clear()

    def show_applications(self):
        # Show application logos which are associated to the container to which this group belongs
        logo_map = {"therm": therm_logo_png, "terra": terra_logo_png}
        logo_spaces = [self.app1, self.app2, self.app3]
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
        # Each project button when clicked will be opened in the associated application if only one is associated, 
        # or user is notified to choose if multiple applications are associated or if no app is associated 
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
                self.workspace_window.pm_workspace_grid.addWidget(self.therm_project_tabs_widget, 0,1, Qt.AlignTop)
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
                self.workspace_window.pm_workspace_grid.addWidget(self.terra_project_tabs_widget, 0,1, Qt.AlignTop)
                self.workspace_window.load_terra_tab_widget()
            else:
                self.workspace_window.terra_tab_button.setChecked(True)
                self.workspace_window.load_terra_tab_widget()

    def project_load_callback(self, load_task_status, load_task, application_type, group_obj, group_dict):
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
        project.group_dict = group_dict
        project.group_obj = group_obj
        
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
        
        load_task_inputs = {"project_uid": project_uid,
                            "project_type": application_type,
                            "core_token": self.core_token,
                            "org_uid":self.group_obj.org_info.get('uid', None),
                            'container_uid':self.group_obj.container.uid,
                            "logger": self.logger}
        project_load_task = QgsTask.fromFunction(f"{project_name} Project Load", Project_loadTask, load_task_inputs)
        QgsApplication.taskManager().addTask(project_load_task)
        project_load_task.statusChanged.connect(lambda load_task_status: self.project_load_callback(load_task_status, project_load_task, application_type, group_obj, group_dict))

        clicked_button.setEnabled(True)

    def edit_project(self, project_uid):
        print('Edit project', project_uid)
    
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

class MoveProject(QtWidgets.QDialog):
    def __init__(self, workspace_window, group_dict, project_uid, group_obj, project_name):
        super(MoveProject, self).__init__()
        self.workspace_window = workspace_window 
        self.group_dict = group_dict
        self.project_uid = project_uid
        self.group_obj = group_obj
        self.project_name = project_name
        layout = QtWidgets.QVBoxLayout(self)
        self.group_details = {group_obj.name:group_uid for group_uid, group_obj in self.group_dict.items()}
        self.move_project_ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'move_project.ui'))
        self.move_project_ui.group_list.addItems(list(self.group_details.keys()))
        button_box = QtWidgets.QDialogButtonBox()
        button_box.addButton("Move", QtWidgets.QDialogButtonBox.AcceptRole)
        button_box.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
        button_box.accepted.connect(self.move_project)
        button_box.rejected.connect(self.close_dialogbox)
        # button_box.setCenterButtons(True)
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
                self.workspace_window.canvas_logger(f'{self.project_name} Project moved to {selected_group_name} Group....')
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
                self.workspace_window.canvas_logger('Project Name updated Sucessfully...')
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
                self.workspace_window.canvas_logger(f'{self.project_create_ui.project_name.text()} Project is created Sucessfully...')
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
            print(group_create_response.json())
            print(group_create_response.status_code)
            if group_create_response.status_code == 200 :
                self.group_workspace.group_label.setText(self.group_edit_ui.group_name.text())
                self.group_obj.name = self.group_edit_ui.group_name.text()
                self.group_obj.deal_id = self.group_edit_ui.deal_id.text()
                if self.group_obj.container:
                    for dict in self.group_obj.container.group_info:
                        if dict['uid'] == self.group_obj.uid:
                            dict['name'] = self.group_edit_ui.group_name.text()
                    print(self.group_obj.container.group_info)

                self.workspace_window.canvas_logger('Group Name updated Sucessfully...')
        else:
            if not self.group_edit_ui.group_name.text():
                self.workspace_window.canvas_logger('Group Name Field is Empty...', level=Qgis.Warning)
            elif not self.group_edit_ui.deal_id.text():
                self.workspace_window.canvas_logger('Deal ID Field is Empty..', level=Qgis.Warning)

    def close_dialogbox(self):
        self.reject()