import requests
from qgis.core import Qgis
from PyQt5 import QtWidgets
from qgis.PyQt import QtCore
from functools import partial
from qgis.PyQt.QtCore import Qt
from ...constants import CORE_URL
from qgis.PyQt import QtWidgets, uic
import os
from .datatypes import Group

class GroupsForm:
    def __init__(self, groups_dict, group_selection_layout, workspace_window):
        self.groups_groupbox = QtWidgets.QGroupBox('Groups:')
        self.myform = QtWidgets.QFormLayout()
        for group_uid, group_obj in groups_dict.items():
            group_button = QtWidgets.QPushButton(f'{group_obj.name}')
            group_button.clicked.connect(partial(workspace_window.load_group_window, group_uid))
            self.myform.addRow(group_button)

        self.new_group_button = QtWidgets.QPushButton('+')
        self.new_group_button.clicked.connect(lambda : GroupCreate(workspace_window))
        self.myform.addRow(self.new_group_button)
        self.groups_groupbox.setLayout(self.myform) 

        self.scroll_widget = QtWidgets.QScrollArea()
        self.scroll_widget.setWidget(self.groups_groupbox)
        self.scroll_widget.setWidgetResizable(True)
        self.scroll_widget.setFixedHeight(400)
        # Replace the scroll widget if it exists
        if workspace_window.groups_form:
            group_selection_layout.replaceWidget(workspace_window.groups_form.scroll_widget, self.scroll_widget)
        else:
            group_selection_layout.addWidget(self.scroll_widget, 0, Qt.AlignTop)


class GroupSelectionWidget(QtWidgets.QWidget):
    def __init__(self, workspace_window):
        super().__init__()
        group_selection_layout = QtWidgets.QVBoxLayout(self)
        workspace_window.group_selection_layout = group_selection_layout
        self.setup_ui(workspace_window) 
        
    def setup_ui(self, workspace_window):
        workspace_window.groups_form = GroupsForm(workspace_window.home_window.groups_dict, workspace_window.group_selection_layout, workspace_window)
        # workspace_window.pm_workspace_grid.addWidget(self, 0, 1, Qt.AlignTop)
        # workspace_window.dock_widget.setFixedSize(520, 830)




class GroupCreate(QtWidgets.QDialog):
    def __init__(self, workspace_window):
        super(GroupCreate, self).__init__()
        self.workspace_window = workspace_window
        # self.container_details  = workspace_window
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Group Create")
        layout = QtWidgets.QVBoxLayout(self)
        self.group_create_ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'create_group.ui'))
        self.containers_detail = { container.name:[container_uid, container.group_info] for container_uid, container in self.workspace_window.home_window.containers_dict.items()}
        self.group_create_ui.container_list.addItems(list(self.containers_detail.keys()))
        button_box = QtWidgets.QDialogButtonBox()
        button_box.addButton("Create", QtWidgets.QDialogButtonBox.AcceptRole)
        button_box.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
        button_box.accepted.connect(self.create_group)
        button_box.rejected.connect(self.close_dialogbox)
        button_box.setCenterButtons(True)
        layout.addWidget(self.group_create_ui)
        layout.addWidget(button_box)
        self.exec_()
        
    def create_group(self):
        if self.group_create_ui.deal_id.text() and self.group_create_ui.group_name.text():
            self.accept()
            print(self.workspace_window.user_id)
            url = CORE_URL+f'/api/v1/groups/?organization={self.workspace_window.org_uid}'
            headers = {'Authorization':f'Token {self.workspace_window.core_token}'}
            json = {'name':self.group_create_ui.group_name.text(),'organization':{'uid':self.workspace_window.org_uid},
                                                                  'deal_id':self.group_create_ui.deal_id.text(),
                                                                  'asset':{'uid':self.workspace_window.asset.uid},
                                                                  'owner':{'uid':self.workspace_window.user_id}}
            group_create_response = requests.post(url, headers=headers, json=json)
            create_group_response = group_create_response.json()
            new_group_uid = create_group_response.get("uid", None)
            new_group_name = create_group_response.get("name",None)
           
            if group_create_response.status_code == 201:
                new_group_obj = Group(new_group_uid, new_group_name, None, {}, self.workspace_window.org_info, self.group_create_ui.deal_id.text(), {})
                self.workspace_window.home_window.groups_dict[new_group_uid] = new_group_obj
                self.workspace_window.canvas_logger(f'{self.group_create_ui.group_name.text()} Group is Sucessfully created...')
                # Re-initialize the Group Selection widget
                self.workspace_window.group_selection_widget.setup_ui(self.workspace_window)         
            else:
                self.workspace_window.logger(group_create_response.json(), level=Qgis.Warning)

            if self.group_create_ui.container_list.currentText() != "Optional":
                container_name = self.group_create_ui.container_list.currentText()
                container_uid = self.containers_detail[container_name][0]
                container_group_info = self.containers_detail[container_name][1]
                if group_create_response.status_code != 201:
                    self.workspace_window.canvas_logger(f'Failed to created {self.group_create_ui.group_name.text()} group...')
                else:
                    print(container_group_info)
                    json = {'groups':container_group_info}
                    url = CORE_URL + f'/api/v1/containers/{container_uid}/?organization={self.workspace_window.org_uid}'
                    json['groups'].append({'uid':new_group_uid})
                    add_group_response = requests.patch(url, headers=headers, json=json)
                    if add_group_response.status_code == 200:
                        container_obj = self.workspace_window.home_window.containers_dict[container_uid]
                        container_obj.groups_dict[new_group_uid] = new_group_obj
                        new_group_obj.container = container_obj
                        self.workspace_window.canvas_logger(f'{self.group_create_ui.group_name.text()} Group added to {container_name} Container....')
                    else:
                        self.workspace_window.logger(add_group_response.json())
        else:
            if not self.group_create_ui.group_name.text():
                self.workspace_window.canvas_logger('Group Name Field is Empty...', level=Qgis.Warning)
            elif not self.group_create_ui.deal_id.text():
                self.workspace_window.canvas_logger('Deal ID Field is Empty..', level=Qgis.Warning)

    def close_dialogbox(self):
        self.reject()