# -*- coding: utf-8 -*-
# """
# /***************************************************************************
#  Load
#                                  A QGIS plugin
#  This window can be used to load SenseHawk projects needing quality check.
#  Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
#                              -------------------
#         begin                : 2022-08-25
#         git sha              : $Format:%H$
#         copyright            : (C) 2022 by SenseHawk
#         email                : kiranh@sensehawk.com
#  ***************************************************************************/
#
# /***************************************************************************
#  *                                                                         *
#  *   This program is free software; you can redistribute it and/or modify  *
#  *   it under the terms of the GNU General Public License as published by  *
#  *   the Free Software Foundation; either version 2 of the License, or     *
#  *   (at your option) any later version.                                   *
#  *                                                                         *
#  ***************************************************************************/
# """

from ..sensehawk_apis.core_apis import get_ortho_tiles_url, get_project_geojson, get_project_details
from ..sensehawk_apis.terra_apis import get_terra_classmaps

from ..utils import download_file, load_vectors, categorize_layer , organization_details, combobox_modifier, asset_details

from ..tasks import loadTask

from ..windows.project import ProjectWindow
from ..windows.therm_tools import ThermToolsWindow

import os
import json
import tempfile
import json

from qgis.PyQt import QtGui, QtWidgets, uic
from qgis.core import QgsMessageLog, Qgis, QgsProject, QgsRasterLayer, QgsVectorLayer, QgsRectangle, QgsFeature, \
    QgsGeometry, QgsField, QgsCategorizedSymbolRenderer, QgsApplication, QgsTask
from qgis.PyQt.QtCore import Qt, QVariant
from qgis.gui import QgsMessageBar
from PyQt5.QtWidgets import QLineEdit, QCompleter
import qgis
from qgis.utils import iface
import time
import requests


HOME_UI, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'home.ui'))


class HomeWindow(QtWidgets.QDockWidget, HOME_UI):
    def __init__(self, user_email, core_token, org_details ,iface):
        """Constructor."""
        super(HomeWindow, self).__init__()
        self.setupUi(self)
        self.core_token = core_token
        self.user_email = user_email
        self.iface = iface
        self.org_details = org_details
        org_list = list(self.org_details.keys())
        org_combobox = self.organization
        self.asset_combobox = self.asset
        self.org = combobox_modifier(org_combobox, org_list)
        self.org.currentIndexChanged.connect(self.org_tree)
        self.projectbutton.clicked.connect(self.show_tools_window)

        # self.loadProject.clicked.connect(self.start_project_load)
        # self.project_type = None
        # self.project_uid = None
        # self.geojson_path = None
        # self.project_details = None
        # self.tools_window = None
        # # Add to the left docking area by default
        # self.iface.addDockWidget(Qt.LeftDockWidgetArea, self)
        # self.terra_tools_window = None
        # self.therm_tools_window = None
        # self.qgis_project = QgsProject.instance()
        # self.bounds = None
        # self.class_maps = None
        # self.class_groups = None
        # self.load_successful = False
        # self.loaded_feature_count = 0

    def org_tree(self, value):
        self.asset_combobox.clear()
        org = self.org_details[self.org.currentText()]
        self.asset_details = asset_details(org, self.core_token)
        asset_list = list(self.asset_details.keys())
        self.asset_combobox.setEnabled(True)
        self.Asset = combobox_modifier(self.asset_combobox, asset_list)
        self.iface.messageBar().pushMessage(self.tr(f'{self.org.currentText()} assets loaded'),Qgis.Success)
        print('selected_org', self.org.currentText())


    def show_tools_window(self):
            self.tools_window = ProjectWindow(self, self.iface)
            self.tools_window.show()
            self.hide()


    # def logger(self, message, level=Qgis.Info):
    #     QgsMessageLog.logMessage(message, 'SenseHawk QC', level=level)

    # def load_callback(self, load_task_status, load_task):
    #     if load_task_status != 3:
    #         return None
    #     result = load_task.returned_values
    #     if not result:
    #         self.logger("Load failed...", level=Qgis.Warning)
    #         return None
    #     rlayer = result['rlayer']
    #     vlayer = result['vlayer']
    #     # Add layers to the qgis project
    #     self.qgis_project.addMapLayer(rlayer)
    #     self.qgis_project.addMapLayer(vlayer)
    #     # Apply styling
    #     self.categorized_renderer = categorize_layer(project_type=self.project_type, class_maps=self.class_maps)
    #     # Show tools window
    #     self.show_tools_window()

    # def start_project_load(self):
    #     # Reset the tools window to None in case of reload of a different project
    #     self.terra_tools_window = None
    #     self.therm_tools_window = None
    #     load_task = QgsTask.fromFunction("Load", loadTask, load_window=self)
    #     QgsApplication.taskManager().addTask(load_task)
    #     load_task.statusChanged.connect(lambda load_task_status: self.load_callback(load_task_status, load_task))


    # def closeEvent(self, event):
    #     event.accept()
    #     # Delete project geojsons
    #     os.remove(self.geojson_path)

