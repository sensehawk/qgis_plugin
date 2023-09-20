from PyQt5.QtWidgets import QPushButton, QWidget

from ...utils import container_details, group_details
from ..project_management.datatypes import Asset
from qgis.PyQt import QtGui, QtWidgets, uic, QtGui
from qgis.PyQt.QtCore import Qt
from .groups_homepage import GroupsForm
import os

# class GroupWindow(QtWidgets.QWidget):
#     def __init__(self, workspace_window, iface):
#         """Constructor."""
#         super(GroupWindow, self).__init__()
#         widget = QWidget()