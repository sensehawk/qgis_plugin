from PyQt5.QtWidgets import QPushButton, QWidget
from PyQt5 import QtCore

from ...utils import combobox_modifier
from PyQt5.QtWidgets import  QComboBox
from ..project_management.datatypes import Asset
from qgis.PyQt import QtGui, QtWidgets, uic, QtGui
from qgis.PyQt.QtCore import Qt
from .groups_homepage import GroupsForm
import os
from functools import partial


therm_logo_png = QtGui.QPixmap(os.path.join(os.path.dirname(__file__), 'therm_logo.svg'))
# therm_logo_png.scaled(10, 10, Qt.AspectRatioMode.KeepAspectRatioByExpanding)
terra_logo_png = QtGui.QPixmap(os.path.join(os.path.dirname(__file__), 'terra_logo.svg'))
# terra_logo_png.scaled(10, 10, Qt.AspectRatioMode.KeepAspectRatioByExpanding)


class GroupWorkspace(QtWidgets.QWidget):
    def __init__(self, workspace, group_obj):
        """Constructor."""
        super(GroupWorkspace, self).__init__()
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'group_workspace.ui'), self)
        self.workspace_window = workspace
        self.group_obj = group_obj
        self.projects_dict = group_obj.projects_details
        self.projects_form = QtWidgets.QFormLayout()
        self.project_groupbox = QtWidgets.QGroupBox('Projects:')
        if group_obj.container:
            self.app_list = [a.get("name", None) for a in group_obj.container.applications]
            self.container_label.setText(f"Container: {group_obj.container.name}")
        else:
            self.app_list = []
            self.container_label.setText("Container: N/A")
        self.show_applications()
        self.create_projects_buttons()
        self.project_count_label.setText(f"Project Count: {len(self.projects_dict)}")
        self.group_label.setText(f"Group: {group_obj.name}")

    def create_projects_buttons(self):
        # Create a lit of buttons for all projects in the group
        for project_uid, project_name in sorted(self.projects_dict.items(), key=lambda x: x[1]):
            button = QtWidgets.QPushButton(f'{project_name}')
            button.clicked.connect(partial(self.load_application, project_uid))
            self.projects_form.addRow(button)

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

    def load_application(self, project_uid):
        # Each project button when clicked will be opened in the associated application if only one is associated, 
        # or user is notified to choose if multiple applications are associated or if no app is associated 
        if not self.group_obj.container:
            #TODO Show message saying container not associated
            pass
        if not self.app_list:
            #TODO: Show message saying no applications associated
            pass
        elif len(self.app_list) > 1:
            app_selection_window = ApplicationSelection(project_uid, self.app_list, self)
            app_selection_window.show()
        elif len(self.app_list) == 1:
            # application_info = [{'uid': 2, 'name': 'therm', 'label': 'Thermal'},{}]
            if self.app_list[0] == "therm":
                #TODO Load in therm
                print("Loading therm project")
                self.load_therm_project(project_uid)
            elif self.app_list[0] == "terra":
                print("Loading terra project")
                self.load_terra_project(project_uid)
    
    def load_therm_project(self, project_uid):
        print("Loading therm project")
        pass

    def load_terra_project(self, project_uid):
        print("Loading terra project")
        pass


class ApplicationSelection(QtWidgets.QWidget):
    def __init__(self, project_uid, app_list, group_workspace):
        super().__init__()
        self.project_uid = project_uid
        self.group_workspace = group_workspace
        self.app_combobox = QComboBox(self) 
        self.app = combobox_modifier(self.app_combobox, app_list)  
        self.app.currentIndexChanged.connect(self.app_selection)
    
    def app_selection(self):
        app = self.app.currentText()
        if app == "therm":
            self.group_workspace.load_therm_project(self.project_uid)
        elif app == "terra":
            self.group_workspace.load_terra_project(self.project_uid)
            