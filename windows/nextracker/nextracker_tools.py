# -*- coding: utf-8 -*-
# """
# /***************************************************************************
#  Terra Tools
#                                  A QGIS plugin
#  This window has access to Tools for Terra/SCM application.
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

from qgis.PyQt import QtWidgets, uic
import os
from qgis.core import QgsMessageLog, Qgis, QgsApplication, QgsTask, QgsFeatureRequest, QgsPoint, QgsVectorLayer
from .utils import setup_clipped_orthos_group
from ...tasks import clip_request
from ...constants import CORE_URL, THERMAL_TAGGING_URL, NEXTRACKER_URL
import requests
import urllib.request


class NextrackerToolsWidget(QtWidgets.QWidget):

    def __init__(self, project):
        """Constructor."""
        super(NextrackerToolsWidget, self).__init__()
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'nextracker_tools.ui'), self)
        self.project = project
        self.clip_button.clicked.connect(self.start_clip_task)
        self.csv_button.clicked.connect(lambda : self.download_csv(QtWidgets.QFileDialog.getSaveFileName(None, "Title", "", "ZIP (*.zip)")[0]))
        self.points_button.clicked.connect(self.generate_points)
    
    # def logger(self, message, level=Qgis.Info):
    #     QgsMessageLog.logMessage(message, 'SenseHawk QC', level=level)

    def start_clip_task(self):
        def validate_group_callback(task, logger):
            result = task.returned_values
            if result:
                logger(str(result["message"]))
            if result and result["success"]:
                clip_task_inputs = {'project_uid': self.project.project_details["uid"],
                                    'geojson_path': self.project.geojson_path,
                                    'class_maps': self.project.class_maps,
                                    'core_core_token': self.project.core_core_token,
                                    'project_type': 'terra',
                                    'user_email': self.project.user_email,
                                    'convert_to_magma': False,
                                    'group_uid': result["group_uid"],
                                    'logger': self.project.logger}
                self.project.logger("Clip task starting...")
                clip_task = QgsTask.fromFunction("Clip Request", clip_request, clip_task_input=clip_task_inputs)
                clip_task.statusChanged.connect(lambda:clip_callback(clip_task, self.project.canvas_logger))
                QgsApplication.taskManager().addTask(clip_task)
            
        def clip_callback(task, canvas_logger):
            result = task.returned_values
            if result:
                canvas_logger(str(result))
        
        # Check if `Clipped Orthos` group exists or not
        self.project.logger("Validating `Clipped Orthos` group")
        deal_id, asset_uid, container_uid, core_core_token = self.project.group_details.deal_id, self.project.group_details.container.asset.uid, self.project.group_details.container.uid, self.project.core_core_token
        group_validate_task = QgsTask.fromFunction("Clipped Orthos group validate", 
                                                setup_clipped_orthos_group, 
                                                task_inputs=[deal_id, asset_uid, container_uid, core_core_token, self.project.logger])
        group_validate_task.statusChanged.connect(lambda:validate_group_callback(group_validate_task, self.project.logger))
        QgsApplication.taskManager().addTask(group_validate_task)

    def download_csv(self, download_path):
        project_uid = self.project.project_details["uid"]
        # download_path = f"{project_uid}_csvs.zip"
        csvs_service_obj = None
        url = CORE_URL + f"/api/v1/projects/{project_uid}/?reports=true"
        reports = requests.get(url, headers={"Authorization": f"Token {self.project.core_token}"}).json().get("reports", [])
        csvs_service_obj = None
        for r in reports:
            if r.get("name", "") == "Nextracker CSVs":
                csvs_service_obj = r["service"]
                break
        if csvs_service_obj:
            csvs_url = self.get_csv_url(csvs_service_obj)
            urllib.request.urlretrieve(csvs_url, download_path)
            self.project.canvas_logger("CSV download successful.", level=Qgis.Success)
        else:
            self.project.canvas_logger("CSV does not exist. Please generate using `Points` feature first.", level=Qgis.Warning)
    
    def get_csv_url(self, csv_service_obj):
        body = {"project_uid": self.project.project_details["uid"],
                "organization": self.project.project_details.get("organization", {}).get("uid", None),
                "service_objects":[csv_service_obj]}
        object_urls = requests.get(THERMAL_TAGGING_URL+"/get_object_urls", 
                               headers={"Authorization": f"Token {self.project.core_token}"}, 
                               json=body).json()
        return list(object_urls.values())[0]

    def generate_points(self):
        project_uid = self.project.project_details["uid"]
        org_uid = self.project.project_details.get("organization", {}).get("uid", None)
        url = f"{NEXTRACKER_URL}/points?project_uid={project_uid}&organization_uid={org_uid}&user_email={self.project.user_email}"
        headers = {"Authorization": f"Token {self.project.core_token}"}
        resp = requests.post(url, headers=headers).json()
        self.project.canvas_logger(str(resp))