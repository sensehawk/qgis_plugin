from qgis.PyQt.QtCore import Qt, QSize
from PyQt5 import QtCore, QtGui, QtWidgets 
from qgis.utils import iface
from qgis.core import Qgis, QgsApplication, QgsTask, QgsProject, QgsMessageLog
from ..tasks import loadTask
from PyQt5.QtWidgets import QLineEdit, QLabel,QCompleter, QVBoxLayout, QPushButton, QComboBox
from PyQt5.QtCore import QRect
from ..utils import download_file, load_vectors, categorize_layer , group_details, combobox_modifier, container_details
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


class ProjectLoadWindow(QtWidgets.QWidget):
    def __init__(self, homeobj, iface):
        super().__init__()
        self.projects_form = None
        self.iface = iface
        self.home = homeobj
        self.logger = homeobj.logger
        self.org_uid = self.home.org_uid
        self.asset_uid = self.home.asset_uid
        self.user_email = self.home.user_email
        self.core_token = self.home.core_token
        self.canvas_logger = homeobj.canvas_logger
        self.org_contianer_details = self.home.org_contianer_details
        self.layers_id = []

        self.container_details = container_details(self.asset_uid, self.org_uid, self.core_token)    
        container_list = list(self.container_details.keys())
        self.container_combobox = QComboBox(self)
        self.container = combobox_modifier(self.container_combobox, container_list)
        self.container.currentIndexChanged.connect(self.container_tree)
        print(self.container_details)

        self.group_details = group_details(self.asset_uid, self.org_uid, self.core_token) # list of all groups in asset and there respective projects 
        group_list = self.container_details[self.container.currentText()]
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
        self.home_button.setStyleSheet('QPushButton {background-color: #dcf7ea; color: #3d3838;}')
        self.home_button.clicked.connect(lambda: self.clear_loaded_projects(next_window=self.home, message="All loaded projects will be closed. Are you sure?"))
        
        homeobj.dock_widget.closeEvent = lambda x: self.clear_loaded_projects(event=x, message="Closing Sensehawk Plugin. Are you sure?")

        self.group_text = QLabel(self)
        self.group_text.setText('<b>Groups &nbsp;&nbsp;&nbsp;&nbsp;:</b>')
        self.group_text.setFixedWidth(70)
        self.container_text = QLabel(self)
        self.container_text.setText('<b>Container :</b>')
        self.container_text.setFixedWidth(70)
        # self.group_text.setStyleSheet("background-color: white;") 
        
        self.project_selection_layout = QtWidgets.QVBoxLayout(self)
        self.project_selection_layout.setContentsMargins(10, 15, 0, 10)
        self.project_selection_layout.addWidget(self.home_button, 0, Qt.AlignTop)

        self.Hlayout_1 = QtWidgets.QHBoxLayout(self)
        self.Hlayout_2 = QtWidgets.QHBoxLayout(self)
        self.Hlayout_1.addWidget(self.group_text, 0)
        self.Hlayout_1.addWidget(self.group, 1)
        self.Hlayout_2.addWidget(self.container_text, 0)
        self.Hlayout_2.addWidget(self.container, 1)

        line1 = QtWidgets.QFrame()
        line1.setFrameShape(QtWidgets.QFrame.HLine)
        line2 = QtWidgets.QFrame()
        line2.setFrameShape(QtWidgets.QFrame.HLine)
        # self.project_selection_layout.addWidget(line1)
        self.project_selection_layout.addSpacing(20)
        self.project_selection_layout.addLayout(self.Hlayout_2, 0)
        self.project_selection_layout.addLayout(self.Hlayout_1, 1)
        self.project_selection_layout.addSpacing(10)
        self.projects_form = ProjectForm(project_list, self.project_selection_layout, self)
        self.project_selection_layout.addWidget(line2)
        projects_loaded_button = QPushButton(self)
        projects_loaded_button.setText('Projects loaded')
        projects_loaded_button.clicked.connect(self.show_projects_loaded)
        self.project_selection_layout.addStretch()
        self.project_selection_layout.addWidget(projects_loaded_button, 0, Qt.AlignBottom)

        self.dock_widget = homeobj.dock_widget
        self.dock_widget.setMinimumSize(QSize(200, 380))
        self.dock_widget.setMaximumSize(QSize(350,800))
        self.dock_widget.setWidget(self)
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dock_widget)

    def show_projects_loaded(self):
        self.dock_widget.setWidget(self.project_tabs_widget)

    def container_tree(self):
        self.group.clear()
        group_list = self.container_details[self.container.currentText()]
        self.group.addItems(group_list)

    def group_tree(self):
        print(self.container_uid)
        if not self.group.currentText():
            return None
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
        self.start_project_load(project_uid, project_type, clicked_button)

    def load_callback(self, load_task_status, load_task, clicked_button):
        new_project_index = len(self.project_tabs_widget.project_uids)
        if load_task_status != 3:
            return None
        result = load_task.returned_values
        if not result:
            self.logger("Load failed...", level=Qgis.Warning)
            clicked_button.setEnabled(True)
            return None
        # Create a project object from the callback result
        clicked_button.setEnabled(True)
        project = Project(result)
        project.user_email = self.user_email
        project.canvas_logger = self.canvas_logger
        project.logger = self.logger
        project.group_details = self.group_details
        
        # Add project to project tab
        project.project_tab_index = new_project_index
        self.project_tabs_widget.add_project(project)
        self.project_tabs_widget.project_tabs_widget.setCurrentIndex(new_project_index)

        # Apply styling
        self.categorized_renderer = categorize_layer(project)
        self.project_tabs_widget.show()
        self.show_projects_loaded()
        # collect loaded project layers id's


    def start_project_load(self, project_uid, project_type, clicked_button):
        project_name = clicked_button.text()
        clicked_button.setEnabled(False)
        if not project_uid:
            self.logger("No project uid given", level=Qgis.Warning)
            return None
        # Load only if it is not already present in project tabs
        if project_uid in self.project_tabs_widget.projects_loaded:
            self.logger("Project loaded already!")
            clicked_button.setEnabled(True)
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
        load_task.statusChanged.connect(lambda load_task_status: self.load_callback(load_task_status, load_task, clicked_button))

    def clear_loaded_projects(self, event=None, next_window=None, message=""):
        active_layers = [i for i in self.project_tabs_widget.projects_loaded.values()]
        self.layers_id = []
        for i in active_layers:
            self.layers_id.append(i.vlayer.id())
            self.layers_id.append(i.rlayer.id())
        # Ignore the event for now until the confimation message is replied to
        message_box = QtWidgets.QMessageBox()
        message_box.setIcon(QtWidgets.QMessageBox.Warning)
        message_box.setWindowTitle('Sensehawk Plugin')
        message_box.setText(message)
        message_box.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        ret = message_box.exec_()
        if event:
            if ret == QtWidgets.QMessageBox.Ok:
                event.accept()
                self.change_window(window=None)
            else:
                event.ignore()

        if ret == QtWidgets.QMessageBox.Ok:
            self.change_window(window=next_window)

    def change_window(self, window=None):
        #remove loaded projects
        try:
            self.project_tabs_widget.qgis_project.removeMapLayers(self.layers_id)
            #close active tool widget 
            self.project_tabs_widget.docktool_widget.close()
        except Exception as e:
            self.logger(str(e), level=Qgis.Warning)
        if window:
            self.dock_widget.setWidget(window)
