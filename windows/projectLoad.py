from qgis.PyQt.QtCore import Qt, QSize
from PyQt5 import QtCore, QtGui, QtWidgets 
from qgis.utils import iface
from qgis.core import Qgis, QgsApplication, QgsTask, QgsProject, QgsMessageLog
from ..tasks import loadTask
from PyQt5.QtWidgets import QLineEdit, QLabel,QCompleter, QVBoxLayout, QPushButton, QComboBox
from PyQt5.QtCore import QRect
from ..utils import download_file, load_vectors, categorize_layer , group_details, combobox_modifier
from .projectTabs import ProjectTabsWidget, Project
from ..event_filters import KeypressFilter, KeypressEmitter, KeypressShortcut, MousepressFilter

class ProjectForm:
    def __init__(self, project_list, project_selection_layout, project_selection_window):
        project_groupbox = QtWidgets.QGroupBox('Projects:')
        myform = QtWidgets.QFormLayout()
        for project in project_list:
            button = QtWidgets.QPushButton(f'{project}')
            button.clicked.connect(project_selection_window.load_project_layers)
            myform.addRow(button)

        project_groupbox.setLayout(myform)

        self.scroll_widget = QtWidgets.QScrollArea()
        self.scroll_widget.setWidget(project_groupbox)
        self.scroll_widget.setWidgetResizable(True)
        self.scroll_widget.setFixedHeight(400)
        # Replace the scroll widget if it exists
        if project_selection_window.projects_form:
            project_selection_layout.replaceWidget(project_selection_window.projects_form.scroll_widget, self.scroll_widget)
        else:
            project_selection_layout.addWidget(self.scroll_widget, 0, Qt.AlignTop)


class ProjectLoadWindow(QtWidgets.QWidget):
    def __init__(self, homeobj, iface):
        super().__init__()
        self.canvas_logger = homeobj.canvas_logger
        self.logger = homeobj.logger
        self.projects_form = None
        self.iface = iface
        self.home = homeobj
        self.core_token = self.home.core_token
        self.asset_uid = self.home.asset_uid
        self.user_email = self.home.user_email
        self.layers_id = []
            
        self.org_uid = self.home.org_uid
        self.org_contianer_details = self.home.org_contianer_details
        self.group_details = group_details(self.asset_uid, self.org_uid, self.core_token) # list of all groups in asset and there respective projects are loaded all at once 

        group_list = list(self.group_details.keys())
        self.group_combobox = QComboBox(self) 
        self.group = combobox_modifier(self.group_combobox, group_list)
        self.group_uid = self.group_details[self.group.currentText()][0]
        self.associated_group_app = next((item['app_types'][0]['name'] for item in self.org_contianer_details if list(filter(lambda group: group['uid'] == self.group_uid, item['groups']))), None)
        self.container_uid = next((item['uid'] for item in self.org_contianer_details if list(filter(lambda group: group['uid'] == self.group_uid, item['groups']))), None)
        self.group.currentIndexChanged.connect(self.group_tree)
        self.project_details = self.group_details[self.group.currentText()][1]
        project_list = list(self.project_details.keys())

        self.project_tabs_widget = ProjectTabsWidget(self)

        self.home_button = QPushButton(self)
        self.home_button.setText('🏡 Home')
        self.home_button.clicked.connect(self.back_to_home)

        # self.group_text = QLabel(self)
        # self.group_text.setText('Groups:')
        # self.group_text.setStyleSheet("background-color: white;") 
        
        self.project_selection_layout = QtWidgets.QVBoxLayout(self)
        self.project_selection_layout.setContentsMargins(10, 15, 0, 10)
        # self.project_selection_layout.addWidget(self.group_text,0, Qt.AlignTop)
        self.project_selection_layout.addWidget(self.home_button, 0, Qt.AlignTop)
        # self.project_selection_layout.addWidget(self.group_text, 0, Qt.AlignTop)
        # Simple line widget separator
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        self.project_selection_layout.addWidget(line)
        self.project_selection_layout.addWidget(self.group, 0)
        self.projects_form = ProjectForm(project_list, self.project_selection_layout, self)
        self.project_selection_layout.addWidget(line)
        projects_loaded_button = QPushButton(self)
        projects_loaded_button.setText('Projects loaded')
        projects_loaded_button.clicked.connect(self.show_projects_loaded)
        self.project_selection_layout.addStretch()
        self.project_selection_layout.addWidget(projects_loaded_button, 0, Qt.AlignBottom)

        self.dock_widget = homeobj.dock_widget
        # self.dock_widget.setFixedSize(330, 830)
        self.dock_widget.setMinimumSize(QSize(200, 380))
        self.dock_widget.setMaximumSize(QSize(500,800))
        self.dock_widget.setWidget(self)
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dock_widget)

    def show_projects_loaded(self):
        self.dock_widget.setWidget(self.project_tabs_widget)


    def group_tree(self):
        self.group_uid = self.group_details[self.group.currentText()][0]
        self.associated_group_app = next((item['app_types'][0]['name'] for item in self.org_contianer_details if list(filter(lambda group: group['uid'] == self.group_uid, item['groups']))), None)
        
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
        self.start_project_load(project_uid, project_type, clicked_button.text())

    def load_callback(self, load_task_status, load_task):
        new_project_index = len(self.project_tabs_widget.project_uids)
        if load_task_status != 3:
            return None
        result = load_task.returned_values
        if not result:
            self.logger("Load failed...", level=Qgis.Warning)
            return None
        # Create a project object from the callback result
        project = Project(result)
        project.user_email = self.user_email
        project.canvas_logger = self.canvas_logger
        project.logger = self.logger
        
        # Add project to project tab
        project.project_tab_index = new_project_index
        self.project_tabs_widget.add_project(project)
        self.project_tabs_widget.project_tabs_widget.setCurrentIndex(new_project_index)

        # Apply styling
        self.categorized_renderer = categorize_layer(project)
        self.project_tabs_widget.show()
        self.show_projects_loaded()
        # collect loaded project layers id's
        self.layers_id_collect()
        
    def layers_id_collect(self):
        self.layers_id.append(self.project_tabs_widget.rlayer_id)
        self.layers_id.append(self.project_tabs_widget.vlayer_id)
        print(self.layers_id)

    def start_project_load(self, project_uid, project_type, project_name):
        if not project_uid:
            self.logger("No project uid given", level=Qgis.Warning)
            return None
        # Load only if it is not already present in project tabs
        if project_uid in self.project_tabs_widget.projects_loaded:
            self.logger("Project loaded already!")
            project_index = self.project_tabs_widget.project_uids.index(project_uid)
            self.project_tabs_widget.project_tabs_widget.setCurrentIndex(project_index)
            self.project_tabs_widget.activate_project()
            self.show_projects_loaded()
            return None

        load_task_inputs = {"project_uid": project_uid,
                            "project_type": project_type,
                            "core_token": self.core_token,
                            "org_uid":self.org_uid,
                            'container_uid':self.container_uid,
                            "logger": self.logger}
        load_task = QgsTask.fromFunction(f"{project_name} Project Load", loadTask, load_task_inputs)
        QgsApplication.taskManager().addTask(load_task)
        load_task.statusChanged.connect(lambda load_task_status: self.load_callback(load_task_status, load_task))

    def back_to_home(self):
        confirmation_widget = iface.messageBar().createMessage("Are u sure? one or more projects loaded!")
        yes_button = QtWidgets.QPushButton(confirmation_widget)
        yes_button.setText("Yes")
        yes_button.clicked.connect(self.to_home)
        no_button = QtWidgets.QPushButton(confirmation_widget)
        no_button.setText("No")
        no_button.clicked.connect(iface.messageBar().clearWidgets)
        confirmation_widget.layout().addWidget(yes_button)
        confirmation_widget.layout().addWidget(no_button)
        iface.messageBar().pushWidget(confirmation_widget, Qgis.Warning)
        

    def to_home(self):
        iface.messageBar().clearWidgets()
        print(self.layers_id)
        try:
            self.project_tabs_widget.qgis_project.removeMapLayers(self.layers_id)
        except Exception as e:
            self.logger(str(e), level=Qgis.Warning)
        self.dock_widget.setWidget(self.home)