
from PyQt5.QtWidgets import QPushButton, QWidget

from ..project_management.datatypes import Asset
from qgis.PyQt import QtGui, QtWidgets, uic, QtGui
from qgis.PyQt.QtCore import Qt
from qgis.PyQt import QtCore
from .groups_homepage import GroupSelectionWidget
from .group_workspace import GroupWorkspace
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
        
        self.iface = iface
        self.groups_form = None
        self.org_uid = home_window.org_uid
        self.asset_uid = home_window.asset_uid
        self.user_email = home_window.user_email
        self.core_token = home_window.core_token
       
        # self.container_details = home_window.container_details 
        self.home_window = home_window
        self.set_asset_label()

        self.dock_widget = home_window.dock_widget
        self.pm_workspace_grid.addWidget(self.dashboard_ui, 0, 0)
        self.dock_widget.setWidget(self)
        self.dock_widget.setFixedSize(130, 830)
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dock_widget)
        
        self.dashboard_ui.home_button.clicked.connect(self.load_home)
        self.dashboard_ui.project_management_button.clicked.connect(self.load_project_management)
        self.group_workspace = None
        self.group_selection_widget = None

    def set_asset_label(self):
        # class AssetLabel(QWidget):
        #     def __init__(self, asset_name):
        #         super(AssetLabel, self).__init__()
        #         self.asset_name = asset_name

        #     def paintEvent(self, event):
        #         painter = QtGui.QPainter(self)
        #         painter.setPen(Qt.black)
        #         painter.translate(5, -50)
        #         painter.rotate(90)
        #         painter.drawText(0, 0, self.asset_name)
        #         painter.end()
        
        # asset_label = AssetLabel(self.home_window.asset.name)
        asset_label_scene = QtWidgets.QGraphicsScene()
        self.dashboard_ui.asset_label.setScene(asset_label_scene)
        label = QtWidgets.QGraphicsTextItem(self.home_window.asset.name)
        label.setRotation(-90)
        asset_label_scene.addItem(label)
        label.setPos(0, 0)
        
        # asset_label.setFixedSize(40,500)
        # self.dashboard_ui.asset_label_layout.addWidget(asset_label, Qt.AlignTop)
        # Check if profile photo of the asset exists

        # # Limit length of name to 15 characters
        # if len(self.home_window.asset.name) <= 15:
        #     self.dashboard_ui.asset_label.setText(self.home_window.asset.name)
        # else:
        #     self.dashboard_ui.asset_label.setText(self.home_window.asset.name[:15]+"...")
    
    def load_home(self):
        self.dock_widget.setWidget(self.home_window)
        self.dock_widget.setFixedSize(300, 830)
        self.hide()
    
    def load_project_management(self):
        if not self.group_selection_widget:
            self.group_selection_widget =  GroupSelectionWidget(self)
        else:
            self.group_selection_widget.show()
        if self.group_workspace :
            self.group_workspace.hide()

    def load_group_window(self, group_uid):
        group_obj = self.home_window.groups_dict[group_uid]
        self.group_selection_widget.hide()
        self.group_workspace = GroupWorkspace(self, group_obj)
        self.pm_workspace_grid.addWidget(self.group_workspace, 0, 1, Qt.AlignTop)