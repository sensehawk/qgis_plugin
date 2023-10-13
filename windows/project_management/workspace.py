from qgis.PyQt import QtGui, QtWidgets, uic, QtGui
from qgis.PyQt.QtCore import Qt 
from qgis.core import QgsProject, Qgis
from .groups_homepage import GroupSelectionWidget
from .group_workspace import GroupWorkspace
from ...utils import download_asset_logo
import os



class WorkspaceWindow(QtWidgets.QWidget):
    def __init__(self, home_window, iface):
        """Constructor."""
        super(WorkspaceWindow, self).__init__()
        self.pm_workspace_grid = QtWidgets.QGridLayout(self)
        # self.pm_workspace_gird.setContentsMargins(10, 15, 0, 10)
        self.dashboard_ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'workspace.ui'))
        # self.dashboard_ui.setStyleSheet('Qlabel {background-color: #dcf7ea; color: #3d3838;}')
        logo = QtGui.QPixmap(QtGui.QPixmap(os.path.join(os.path.dirname(__file__), 'logo.png')))
        logo = logo.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatioByExpanding)
        self.dashboard_ui.logo_label.setPixmap(logo)
        self.dashboard_ui.logo_label.setAlignment(Qt.AlignCenter)
        self.dashboard_ui.logo_label.show()
        self.dashboard_ui.home_button.setStyleSheet('QPushButton {background-color: #dcf7ea; color: #3d3838;}')
        self.dashboard_ui.logout_button.setStyleSheet('QPushButton {background-color: #f7b7ce; color: #3d3838;}')
        self.dashboard_ui.home_button.clicked.connect(lambda: self.clear_loaded_projects(next_window=self.home_window, message="All loaded projects will be closed. Are you sure?"))
        home_window.dock_widget.closeEvent = lambda x: self.clear_loaded_projects(event=x, message="Closing Sensehawk Plugin. Are you sure?")

        self.iface = iface
        self.user_id = home_window.user_id
        self.groups_form = None
        self.org_uid = home_window.org_uid
        self.asset_uid = home_window.asset_uid
        self.user_email = home_window.user_email
        self.core_token = home_window.core_token
        self.logger = home_window.logger
        self.canvas_logger = home_window.canvas_logger
        self.asset = home_window.asset
        self.org_info = home_window.org_info
        self.apptype_details = home_window.apptype_details
        # self.container_details = home_window.container_details 
        self.home_window = home_window
        self.qgis_project = QgsProject.instance()
        self.set_asset_label()

        self.dock_widget = home_window.dock_widget
        self.pm_workspace_grid.addWidget(self.dashboard_ui, 0, 0)
        self.dock_widget.setWidget(self)
        self.dock_widget.setFixedSize(130, 830)
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dock_widget)
        
        # self.dashboard_ui.home_button.clicked.connect(self.load_home)
        self.dashboard_ui.project_management_button.clicked.connect(self.load_project_management)
        self.group_workspace = None
        self.group_selection_widget = None
        self.therm_project_tabs_widget = None
        self.terra_project_tabs_widget = None
        self.active_widget = None
        self.therm_tab_button = None
        self.terra_tab_button = None
        print(self.dashboard_ui.module_layout)

    def set_asset_label(self):
        # Limit length of name to 15 characters
        if len(self.home_window.asset.name) <= 9:
            self.dashboard_ui.asset_label.setText(self.home_window.asset.name)
        else:
            self.dashboard_ui.asset_label.setText(self.home_window.asset.name[:8]+"..")
        self.dashboard_ui.asset_label.setAlignment(Qt.AlignCenter)
        # self.dashboard_ui.asset_label.setStyleSheet("background-color: #d7e1f5;  color: #35373b;")

        if self.home_window.asset.profile_image:
            asset_logo_path = download_asset_logo(self.home_window.asset.name, self.home_window.asset.profile_image)
            logo = QtGui.QPixmap(asset_logo_path)
            self.dashboard_ui.asset_logo.setScaledContents(True)
            self.dashboard_ui.asset_logo.setPixmap(logo.scaled(self.dashboard_ui.asset_logo.size(), aspectRatioMode=Qt.KeepAspectRatio))

            print(asset_logo_path)
        else:
            self.dashboard_ui.asset_logo.setText(self.home_window.asset.name[:1])
            self.dashboard_ui.asset_logo.setStyleSheet("background-color: #d7e1f5;  color: #35373b;")

    def load_home(self):
        self.dock_widget.setWidget(self.home_window)
        self.dock_widget.setFixedSize(300, 830)
        self.hide()
    
    def load_project_management(self):
        #uncheck therm_tab_button
        if self.therm_tab_button:
            self.therm_tab_button.setChecked(False)
        if self.terra_tab_button:
            self.terra_tab_button.setChecked(False)
        if self.dashboard_ui.project_management_button.isChecked():
            print('checked')
            if not self.group_selection_widget:
                self.group_selection_widget =  GroupSelectionWidget(self)
                self.active_widget = self.group_selection_widget
                self.pm_workspace_grid.addWidget(self.group_selection_widget, 0, 1, Qt.AlignTop)
                self.dock_widget.setFixedSize(520, 830)
            else:
                if self.active_widget is self.group_selection_widget:
                    pass
                else:
                    self.group_selection_widget.setup_ui(self)
                    self.group_selection_widget.show()
                    if self.active_widget:
                        self.active_widget.hide()
                    else:
                        self.dock_widget.setFixedSize(520,830)
                    self.active_widget = self.group_selection_widget
        else:
            self.active_widget.hide()
            self.active_widget = None
            self.dock_widget.setFixedSize(130, 830)

    def load_group_window(self, group_uid):
        #uncheck project management button
        self.dashboard_ui.project_management_button.setChecked(False)
        group_obj = self.home_window.groups_dict[group_uid]
        if not self.group_workspace:
            self.group_workspace = GroupWorkspace(self, group_obj, self.home_window.groups_dict)
            self.dock_widget.setFixedSize(520, 830)
            self.active_widget.hide()
            self.active_widget = self.group_workspace
            self.pm_workspace_grid.addWidget(self.group_workspace, 0, 1, Qt.AlignTop)
        else:
            self.group_workspace.setupUi(group_obj, self.home_window.groups_dict)
            self.group_workspace.show()
            self.active_widget.hide()
            self.active_widget = self.group_workspace

    def load_therm_tab_widget(self):
        #uncheck project management button
        if self.terra_tab_button:
            self.terra_tab_button.setChecked(False)
        self.dashboard_ui.project_management_button.setChecked(False)
        if self.therm_tab_button.isChecked():
            if self.active_widget is self.therm_project_tabs_widget:
                pass
            else:
                self.therm_project_tabs_widget.show()
                if self.active_widget:
                    self.active_widget.hide()
                else:
                    self.dock_widget.setFixedSize(520,830)
                self.active_widget = self.therm_project_tabs_widget
        else:
            self.active_widget.hide()
            self.active_widget = None
            self.dock_widget.setFixedSize(130,830)
    
    def load_terra_tab_widget(self):#uncheck project management button
        if self.therm_tab_button:
            self.therm_tab_button.setChecked(False)
        self.dashboard_ui.project_management_button.setChecked(False)
        if self.terra_tab_button.isChecked():
            if self.active_widget is self.terra_project_tabs_widget:
                pass
            else:
                self.terra_project_tabs_widget.show()
                if self.active_widget:
                    self.active_widget.hide()
                else:
                    self.dock_widget.setFixedSize(520,830)
                self.active_widget = self.terra_project_tabs_widget
        else:
            self.active_widget.hide()
            self.active_widget = None
            self.dock_widget.setFixedSize(130,830)
    

    def clear_loaded_projects(self, event=None, next_window=None, message=""):
        # Ignore the event for now until the confimation message is replied to
        message_box = QtWidgets.QMessageBox()
        message_box.setIcon(QtWidgets.QMessageBox.Warning)
        message_box.setWindowTitle('Sensehawk Plugin')
        message_box.setText(message)
        message_box.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        ret = message_box.exec()
        try:
            active_layers = [i for i in self.group_workspace.therm_project_tabs_widget.projects_loaded.values()]
            active_layers += [i for i in self.group_workspace.terra_project_tabs_widget.projects_loaded.values()]
            self.layers_id = []
            for i in active_layers:
                self.layers_id.append(i.vlayer.id())
                self.layers_id.append(i.rlayer.id())
        except AttributeError as e:
            pass
        
        if event:
            if ret == QtWidgets.QMessageBox.Ok:
                event.accept()
                self.change_window(window=None)
            else:
                event.ignore()
        else:
            if ret == QtWidgets.QMessageBox.Ok:
                print('pressed')
                self.change_window(window=next_window)
            elif ret == QtWidgets.QMessageBox.Cancel:
                print('canceled')
                return None

    def change_window(self, window=None):
        #remove loaded projects
        try:
            self.qgis_project.removeMapLayers(self.layers_id)
            #close active tool widget 
            self.group_workspace.therm_project_tabs_widget.docktool_widget.close()
            self.group_workspace.terra_project_tabs_widget.docktool_widget.close()
            del self.group_workspace.therm_project_tabs_widget.docktool_widget
            del self.group_workspace.terra_project_tabs_widget.docktool_widget
        except Exception as e:
            self.logger(str(e), level=Qgis.Warning)
        if window:
            self.dock_widget.setWidget(self.home_window)
            self.dock_widget.setFixedSize(300, 830)
            self.hide()
        else:
            del self.home_window.login_obj
            del self.dock_widget
            del self.home_window
            del self