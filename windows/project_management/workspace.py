
from PyQt5.QtWidgets import QPushButton, QWidget

from ..project_management.datatypes import Asset
from qgis.PyQt import QtGui, QtWidgets, uic, QtGui
from qgis.PyQt.QtCore import Qt
from .groups_homepage import GroupSelectionWidget
import os

class WorkspaceWindow(QtWidgets.QWidget):
    def __init__(self, home_window, iface):
        """Constructor."""
        super(WorkspaceWindow, self).__init__()
        self.pm_workspace_grid = QtWidgets.QGridLayout(self)
        # self.pm_workspace_gird.setContentsMargins(10, 15, 0, 10)
        self.dashboard_ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'workspace.ui'))
        # self.dashboard_ui.setStyleSheet('QWidget {background-color: #dcf7ea; color: #3d3838;}')
    
        self.iface = iface
        self.groups_form = None
        self.org_uid = home_window.org_uid
        self.asset_uid = home_window.asset_uid
        self.user_email = home_window.user_email
        self.core_token = home_window.core_token
       
        # self.container_details = home_window.container_details 
        self.home_window = home_window

        self.dock_widget = home_window.dock_widget
        self.pm_workspace_grid.addWidget(self.dashboard_ui, 0, 0)
        self.dock_widget.setWidget(self)
        self.dock_widget.setFixedSize(100, 830)
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dock_widget)
        
        self.dashboard_ui.home_button.clicked.connect(self.load_home)
        self.dashboard_ui.project_management_button.clicked.connect(self.load_project_management)

    
    def load_home(self):
        self.dock_widget.setWidget(self.home_window)
        self.dock_widget.setFixedSize(300, 830)
        self.hide()
    
    def load_project_management(self):
        GroupSelectionWidget(self)
        # print(self.container_details)
    def load_group_window(self, group_name):
        pass