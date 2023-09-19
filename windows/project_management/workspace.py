
from PyQt5.QtWidgets import QPushButton, QWidget

from ...utils import container_details, group_details
from ..project_management.datatypes import Asset
from qgis.PyQt import QtGui, QtWidgets, uic, QtGui
from qgis.PyQt.QtCore import Qt
import os

class WorkspaceWindow(QtWidgets.QWidget):
    def __init__(self, home_window, iface):
        """Constructor."""
        super(WorkspaceWindow, self).__init__()
        widget = QWidget()
        self.pm_workspace_grid = QtWidgets.QGridLayout(widget)
        # self.pm_workspace_gird.setContentsMargins(10, 15, 0, 10)
        self.dashboard_ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'workspace.ui'))
        # self.dashboard_ui.setStyleSheet('QWidget {background-color: #dcf7ea; color: #3d3838;}')
    
        self.iface = iface
        self.org_uid = home_window.org_uid
        self.asset_uid = home_window.asset_uid
        self.user_email = home_window.user_email
        self.core_token = home_window.core_token
        # container details reference {'container_name':{'uid':'container_uid','groups':[], 'application_info':[{'uid': 2, 'name': 'therm', 'label': 'Thermal'},{}]} , 
                                     # 'container_name':{}}
        self.container_details = home_window.container_details 
        self.home_window = home_window

        self.dock_widget = home_window.dock_widget
        self.pm_workspace_grid.addWidget(self.dashboard_ui, 0, 0)
        self.dock_widget.setWidget(widget)
        self.dock_widget.setFixedSize(100, 830)
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dock_widget)
        
        self.get_project_details()
        self.dashboard_ui.home_button.clicked.connect(self.load_home)
        self.dashboard_ui.project_management_button.clicked.connect(self.load_project_management)

    def get_project_details(self):
        # list of all the groups in the asset and there respective projects  | {'group_name':('group_uid', {'project_name':'project_uid'})}
        self.groups_details = group_details(self.asset_uid, self.org_uid, self.core_token)
    
    def load_home(self):
        self.dock_widget.setWidget(self.home_window)
        self.dock_widget.setFixedSize(300, 830)
        self.hide()
    
    def load_project_management(self):
        self.project_management_ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'project_management.ui')) 
        self.pm_workspace_grid.addWidget(self.project_management_ui, 0, 1, Qt.AlignTop)
        self.dock_widget.setFixedSize(450, 830)


    
    def init_project_management(self):
        pass