# -*- coding: utf-8 -*-
# """
# /***************************************************************************
#  Therm Tools
#                                  A QGIS plugin
#  This window has access to Tools for Therm application.
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

from qgis.core import Qgis, QgsTask, QgsApplication
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import Qt
from PyQt5 import QtCore
from ..constants import THERMAL_TAGGING_URL
from ..utils import project_data_existent, AssetLevelProjects

import os
import requests


class ThermImageTaggingWidget(QtWidgets.QWidget):
    
    def __init__(self, thermtool_obj, iface):
        """Constructor."""
        super(ThermImageTaggingWidget, self).__init__()
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'ImageTagging.ui'), self)
        self.canvas_logger = thermtool_obj.canvas_logger
        self.logger = thermtool_obj.logger
        self.thermToolobj = thermtool_obj
        self.iface = iface
        self.canvas =self.iface.mapCanvas()
        self.existing_files = self.thermToolobj.existing_files
        self.project = thermtool_obj.project
        self.project_details = self.project.project_details
        self.email_id = self.project.user_email
        self.core_token = self.project.core_token
        self.project_uid = self.project.project_details["uid"]
        self.canvas =self.iface.mapCanvas()
        self.tables_module_info = {}
        self.stringnum_type = ''
        self.stringnum_updated = False
        self.string_number_prefix = ''
        self.string_number_suffix = ''
        self.addl_uid = None # additional Project uid

        self.central_stringnumber_widget = thermtool_obj.project.stringnumber_widget
        self.project_details_button.clicked.connect(self.get_project_details)
        self.tag_button.clicked.connect(self.image_tagging)
        self.imagetaggingType.currentTextChanged.connect(self.current_type)
        self.MagmaConversion.setChecked(True)
        self.assetlevel_projects = AssetLevelProjects(self)
        self.addl_projectuid_button.clicked.connect(self.assetlevel_projects.show)
        # self.existing_files = self.thermToolobj.existing_files
        # self.temp_option.addItems(self.existing_files)
        self.temp_option.addItems(self.existing_files)
        self.No_images.setValue(4)
        self.No_images.setMaximum(4)
        self.No_images.setMinimum(1)

   
    def get_project_details_callback(self, get_project_detials_task_status, get_details):
        if get_project_detials_task_status != 3:
            return None
        result = get_details.returned_values
        dsm = result['projectjson'].get('dsm', None)
        ortho = result['projectjson'].get('ortho', None)
        rawimage = self.project_details.get('no_of_images', None)
        reflectance = result['projectjson'].get('reflectance', None)
        calibratedParameters = result['projectjson'].get('calibratedParameters', None)
        externalCalibratedParameters = result['projectjson'].get('externalCalibratedParameters', None)
        green = "QCheckBox::indicator"+"{"+"background-color : lightgreen;"+"}"
        red = "QCheckBox::indicator"+"{"+"background-color : red;"+"}"
        if dsm : 
            self.get_dsm.setChecked(True)
            self.get_dsm.setStyleSheet(green)
        else:self.get_dsm.setStyleSheet(red)
        if ortho : 
            self.get_ortho.setChecked(True)
            self.get_ortho.setStyleSheet(green)
        else: self.get_ortho.setStyleSheet(red)
        if reflectance : 
            self.get_reflectance.setChecked(True)
            self.get_reflectance.setStyleSheet(green)
        else:self.get_reflectance.setStyleSheet(red)
        if rawimage : 
            self.get_rawimage.setChecked(True)
            self.get_rawimage.setStyleSheet(green)
        else : self.get_rawimage.setStyleSheet(red)
        if calibratedParameters : 
            self.get_calibration.setChecked(True)
            self.get_calibration.setStyleSheet(green)
        else : self.get_calibration.setStyleSheet(red)
        if externalCalibratedParameters : 
            self.get_externalcalibration.setChecked(True)
            self.get_externalcalibration.setStyleSheet(green)
        else: self.get_externalcalibration.setStyleSheet(red)

    def get_project_details(self):
        org = self.project_details['organization']['uid']
        project_info = [self.project_uid, org, self.core_token]
        get_details = QgsTask.fromFunction("Get image urls", project_data_existent, project_info)
        QgsApplication.taskManager().addTask(get_details)
        get_details.statusChanged.connect(lambda get_project_detials_task_status: self.get_project_details_callback(get_project_detials_task_status, get_details))

    def current_type(self, value):
        three_gsd = '3.5GSD UID'
        if value == 'ThermLite Tagging' or value == 'Thermal Tagging':
            self.MagmaConversion.setChecked(True)
            self.rotate_image.setEnabled(True)
            self.rotate_image.setChecked(True)
            self.IssueCropImage.setChecked(False)
            self.opt_uid_txt.setText(three_gsd)
            self.addl_projectuid_button.setEnabled(True)
            self.addl_projectuid.setEnabled(True)
            self.IssueCropImage.setEnabled(False)
            self.MagmaConversion.setEnabled(True)
            self.temp_option.setEnabled(True)
            self.No_images.setEnabled(True)
            self.No_images.setValue(4)
            self.stringNumCheckbox.setChecked(False)
            if value == "Thermal Tagging":
                self.markerlocation.setEnabled(True)
                self.markerlocation.setChecked(True)
            else:
                self.markerlocation.setEnabled(False)
                self.markerlocation.setChecked(False)

        elif value == 'Visual Tagging':
            self.MagmaConversion.setChecked(False)
            self.rotate_image.setEnabled(True)
            self.rotate_image.setChecked(True)
            self.IssueCropImage.setChecked(False)
            self.opt_uid_txt.setText('VProj UID')
            self.addl_projectuid_button.setEnabled(True)
            self.addl_projectuid.setEnabled(True)
            self.IssueCropImage.setEnabled(False)
            self.MagmaConversion.setEnabled(False)
            self.temp_option.setEnabled(False)
            self.No_images.setEnabled(True)
            self.No_images.setValue(2)
            self.stringNumCheckbox.setChecked(False)
            self.markerlocation.setEnabled(False)
            self.markerlocation.setChecked(False)
        elif value == 'SiteMap Tagging':
            self.MagmaConversion.setChecked(True)
            self.rotate_image.setEnabled(False)
            self.rotate_image.setChecked(False)
            self.IssueCropImage.setChecked(True)
            self.opt_uid_txt.setText(three_gsd)
            self.addl_projectuid_button.setEnabled(False)
            self.addl_projectuid.setEnabled(False)
            self.IssueCropImage.setEnabled(True)
            self.MagmaConversion.setEnabled(True)
            self.temp_option.setEnabled(False)
            self.No_images.setEnabled(False)
            self.stringNumCheckbox.setChecked(False)
            self.markerlocation.setEnabled(False)
            self.markerlocation.setChecked(False)
        elif value == 'Temp Extraction':
            self.MagmaConversion.setChecked(False)
            self.rotate_image.setEnabled(False)
            self.rotate_image.setChecked(False)
            self.IssueCropImage.setChecked(False)
            self.opt_uid_txt.setText(three_gsd)
            self.addl_projectuid_button.setEnabled(False)
            self.addl_projectuid.setEnabled(False)
            self.IssueCropImage.setEnabled(False)
            self.MagmaConversion.setEnabled(False)
            self.temp_option.setEnabled(True)
            self.No_images.setEnabled(False)
            self.stringNumCheckbox.setChecked(False)
            self.markerlocation.setEnabled(False)
            self.markerlocation.setChecked(False)
        elif value == '3.5 GSD Tagging':
            self.MagmaConversion.setChecked(True)
            self.rotate_image.setEnabled(True)
            self.rotate_image.setChecked(True)
            self.IssueCropImage.setChecked(False)
            self.opt_uid_txt.setText(three_gsd)
            self.addl_projectuid_button.setEnabled(True)
            self.addl_projectuid.setEnabled(True)
            self.IssueCropImage.setEnabled(False)
            self.MagmaConversion.setEnabled(True)
            self.temp_option.setEnabled(False)
            self.No_images.setEnabled(True)
            self.No_images.setValue(2)
            self.No_images.setEnabled(False)
            self.stringNumCheckbox.setChecked(False)
            self.markerlocation.setEnabled(False)
            self.markerlocation.setChecked(False)
        elif value == "String Number":
            self.MagmaConversion.setChecked(False)
            self.rotate_image.setEnabled(False)
            self.rotate_image.setChecked(False)
            self.IssueCropImage.setChecked(False)
            self.opt_uid_txt.setText(three_gsd)
            self.addl_projectuid_button.setEnabled(False)
            self.addl_projectuid.setEnabled(False)
            self.IssueCropImage.setEnabled(False)
            self.MagmaConversion.setEnabled(False)
            self.temp_option.setEnabled(False)
            self.No_images.setEnabled(False)
            self.No_images.setValue(2)
            self.No_images.setEnabled(False)
            self.stringNumCheckbox.setChecked(True)
            self.markerlocation.setEnabled(False)
            self.markerlocation.setChecked(False)   

    def imgTagCallback(self, approve_status, approveTaggingTask):
            if approve_status != 3:
                return None
            result = approveTaggingTask.returned_values
            if result:
                response = result['response']
                if response.status_code == 200:
                    self.tag_button.setChecked(False)
                    self.canvas_logger('Thermal tagging Approval Queued Successfully.',level=Qgis.Success)
                else:
                    self.tag_button.setChecked(False)
                    self.canvas_logger(f'Failed to Queue {response.status_code}, {response.json()}',level=Qgis.Warning)

    def thermalTaggingApprove(self, task, json):
        url =  THERMAL_TAGGING_URL + "/tag" 
        headers = {'Authorization': f'Token {self.core_token}'}
        imgtag_response = requests.post(url, json=json, headers=headers)
        print(imgtag_response.json(), imgtag_response.status_code)

        return  {'task':task.description(),'response':imgtag_response}
    
    def api(self, json):
        canvas  = self.canvas
        rotation = canvas.rotation()
        json['angle'] = rotation
        json['email_id'] = self.email_id
        json['stringNumber_info'] = {'numbering_type':self.stringnum_type,'table-module_info':self.tables_module_info, 
                                     'prefix':self.string_number_prefix, 'suffix':self.string_number_suffix}
        print(json)
        
        approveTaggingTask = QgsTask.fromFunction("Thermal Approval", self.thermalTaggingApprove, json)
        QgsApplication.taskManager().addTask(approveTaggingTask)
        approveTaggingTask.statusChanged.connect(lambda approve_status: self.imgTagCallback(approve_status, approveTaggingTask))
        
        #clear additional Projectuid let user select it again
        self.addl_uid = None
        self.addl_projectuid.setText('N/A')

    def image_tagging(self): 
        self.tag_button.setChecked(True)
        if self.MagmaConversion.isChecked():magma_image = True
        else : magma_image = False
        if self.IssueCropImage.isChecked():crop_image = True
        else: crop_image = False
        if self.rotate_image.isChecked():rotate = True
        else : rotate = False
        if self.markerlocation.isChecked(): markerlocation = True
        else : markerlocation = False
        no_images = self.No_images.value()
        temp_file = self.temp_option.currentText()

        #clear String number related details
        self.tables_module_info.clear()
        self.stringnum_updated = False
        self.stringnum_type = ""
        self.string_number_prefix = ""
        self.string_number_suffix = ""
        if self.stringNumCheckbox.isChecked():
            self.central_stringnumber_widget.stringNumObj = self
            self.central_stringnumber_widget.exec_()
            if not self.stringnum_updated:
                self.canvas_logger('Approval request Cancelled',level=Qgis.Warning)
                return None


        org = self.project_details['organization']['uid']
        if self.imagetaggingType.currentText() == 'Visual Tagging':
            if not self.addl_uid :
                self.canvas_logger('Select the Project to tag Visual images....',level=Qgis.Warning)
            else:
                json = {'projectUid': self.project_uid, 'method':5, 'VprojectUid': self.addl_uid, 'org':org, 'Addl_ProjUid':None,
                        'magma_image':magma_image, 'crop_image':crop_image, 'No_images':no_images, 'temp_file':'None', 'rotate_image':rotate, 'markerlocation':markerlocation}
                self.api(json)
         
        elif self.imagetaggingType.currentText() == 'Thermal Tagging':
            json = {'projectUid': self.project_uid, 'method':1, 'Addl_ProjUid':self.addl_uid,'org':org,
                    'magma_image':magma_image,'crop_image':crop_image, 'No_images':no_images, 'temp_file':temp_file, 'rotate_image':rotate, 'markerlocation':markerlocation}
            self.api(json)
           
        elif self.imagetaggingType.currentText() == 'ThermLite Tagging':
            json ={'projectUid': self.project_uid, 'method':2, 'Addl_ProjUid':self.addl_uid,'org':org,
                   'magma_image':magma_image, 'crop_image':crop_image,'No_images':no_images,'temp_file':temp_file, 'rotate_image':rotate, 'markerlocation':markerlocation}
            self.api(json)
            
        elif self.imagetaggingType.currentText() == 'SiteMap Tagging':
            json ={'projectUid': self.project_uid, 'method':3, 'Addl_ProjUid': None,'org':org,
                   'magma_image':magma_image, 'crop_image':crop_image, 'No_images':no_images, 'temp_file':'None','markerlocation':markerlocation}
            self.api(json) 
        
        elif self.imagetaggingType.currentText() == 'Temp Extraction':
            json ={'projectUid': self.project_uid, 'method':4, 'Addl_ProjUid': None,'org':org,
                   'magma_image':magma_image, 'crop_image':crop_image, 'No_images':0, 'temp_file':temp_file, 'markerlocation':markerlocation}
            self.api(json) 

        elif self.imagetaggingType.currentText() == '3.5 GSD Tagging':
            if not self.addl_uid :
                self.canvas_logger('Select the Project to tag 3.5GSD images....',level=Qgis.Warning)
            else:
                json = {'projectUid': self.project_uid, 'method':6, 'Addl_ProjUid': self.addl_uid, 'org':org,
                        'magma_image':magma_image, 'crop_image':crop_image, 'No_images':no_images, 'temp_file':'None', 'rotate_image':rotate, 'markerlocation':markerlocation}
                self.api(json)
        elif self.imagetaggingType.currentText() == "String Number":
            json ={'projectUid': self.project_uid, 'method':7, 'Addl_ProjUid': None,'org':org,
                   'magma_image':magma_image, 'crop_image':crop_image, 'No_images':0, 'temp_file':temp_file, 'markerlocation':markerlocation}
            self.api(json) 


# from functools import partial

# class StringNumberTableWidget(QtWidgets.QDialog):
#     def __init__(self, group_obj):
#         super(StringNumberTableWidget, self).__init__()
#         layout = QtWidgets.QVBoxLayout(self)
#         self.string_ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'AutoNumbering_V2.ui'))
#         self.stringNumObj = None
#         self.group_obj = group_obj
#         self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
#         self.setWindowTitle("String Number")
#         self.table_info_ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'table_info_V2.ui'))
#         self.tables = [self.table_info_ui]
#         button_box = QtWidgets.QDialogButtonBox()
#         button_box.addButton("Collect", QtWidgets.QDialogButtonBox.AcceptRole)
#         button_box.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
#         button_box.accepted.connect(self.tables_info)
#         button_box.rejected.connect(self.close_dialogbox)
#         button_box.setCenterButtons(True)
#         self.add_btn = QtWidgets.QPushButton("➕")
#         self.add_btn.setFixedSize(40, 24)
#         self.add_remove_buttons = [self.add_btn]
#         self.add_btn.clicked.connect(self.add_table_widget)
#         layout.addWidget(self.string_ui)
#         layout.addWidget(button_box)
#         self.add_btn_poistion = 3
#         self.table_and_module_info = {}
#         self.setup_ui()

#     def setup_ui(self):
#         self.string_ui.string_grid_layout.addWidget(self.add_btn, self.add_btn_poistion, 0, Qt.AlignLeft)
#         self.string_ui.string_grid_layout.addWidget(self.table_info_ui, self.add_btn_poistion, 1)
    
#     def add_table_widget(self):
#         remove_btn = QtWidgets.QPushButton("❌")
#         remove_btn.setFixedSize(40, 24)
#         remove_btn.clicked.connect(partial (self.remove_table_widget, self.tables[-1], remove_btn))
#         self.add_btn_poistion += 1
#         table_ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'table_info_V2.ui'))
#         self.string_ui.string_grid_layout.addWidget(self.add_btn, self.add_btn_poistion, 0, Qt.AlignLeft)
#         self.string_ui.string_grid_layout.addWidget(remove_btn, self.add_btn_poistion-1, 0, Qt.AlignLeft)
#         self.string_ui.string_grid_layout.addWidget(table_ui, self.add_btn_poistion, 1)
#         self.tables.append(table_ui)
#         self.add_remove_buttons.append(remove_btn)
    
#     def remove_table_widget(self, table_ui, remove_btn):
#         self.string_ui.string_grid_layout.removeWidget(table_ui)
#         self.string_ui.string_grid_layout.removeWidget(remove_btn)
#         self.tables.remove(table_ui)
#         self.add_remove_buttons.remove(remove_btn)
#         table_ui.deleteLater()
#         remove_btn.deleteLater()
        
#     def tables_info(self):
#         self.table_and_module_info.clear()
#         for table in self.tables:
#             if not table.table_length.text() or not table.table_height.text() or not table.table_row.text() or not table.table_column.text() or not table.module_width.text() or not table.module_height.text():
#                     self.group_obj.canvas_logger('Table length | row | column info is missing...', level=Qgis.Warning)
#                     self.stringNumObj.tables_module_info.clear()
#                     return None 
#             else:
#                 table_half_perimeter =  float(table.table_length.text()) + float(table.table_height.text())
#                 print(table_half_perimeter, type(table_half_perimeter))
#                 self.table_and_module_info[float(table_half_perimeter)] = [float(table.table_length.text()),float(table.table_height.text()), int(table.table_column.text()), int(table.table_row.text()),float(table.module_width.text()),float(table.module_height.text())]
#                 self.stringNumObj.tables_module_info = self.table_and_module_info
#                 self.stringNumObj.stringnum_type = self.string_ui.stringnum_type.currentText()
#                 self.stringNumObj.string_number_prefix = self.string_ui.Prefix.text()
#                 self.stringNumObj.string_number_suffix = self.string_ui.Suffix.text()

#         self.stringNumObj.stringnum_updated = True
#         self.accept()
        
#     def closeEvent(self, event):
#         self.stringNumObj.tag_button.setChecked(False)
        
#     def close_dialogbox(self):
#         self.stringNumObj.tag_button.setChecked(False)
#         self.reject()