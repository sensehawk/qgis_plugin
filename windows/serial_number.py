from qgis.PyQt.QtCore import Qt
from qgis.PyQt import QtWidgets, uic
from qgis.core import Qgis

import os
import re

from ..windows.autoNumbering_utils import Table
from qgis.core import  Qgis, QgsApplication, QgsTask
from ..utils import features_to_polygons
from ..utils import combobox_modifier
from ..constants import TERRA_URL
from qgis.utils import iface
from PyQt5 import QtCore
from math import ceil
import requests
import json

class SerialNumberWidget(QtWidgets.QWidget):

    def __init__(self, therm_tools):
        """Constructor."""
        super(SerialNumberWidget, self).__init__()
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'serial_number.ui'), self)
        self.canvas_logger = therm_tools.canvas_logger
        self.logger = therm_tools.logger
        self.thermToolObj = therm_tools
        self.project = therm_tools.project
        self.canvas_logger = therm_tools.canvas_logger
        self.core_token = therm_tools.project.core_token
        self.uid = therm_tools.project_details['uid']
        self.groupuid = therm_tools.project_details["group"]["uid"]
        self.org_uid = therm_tools.project_details["organization"]["uid"]
        self.locate_row_column.clicked.connect(self.locate_row_and_column)
        self.update_serial_number.clicked.connect(self.update_serial_numbers)
        self.assetlevel_projects = AssetLevelProjects(self)
        self.load_barcode_projects.clicked.connect(self.assetlevel_projects.show)

    def closeEvent(self, event):
        self.thermToolObj.uncheck_all_buttons()
        event.accept()

    def locate_row_and_column(self):
        module_width = self.width.value()
        module_height = self.height.value()
        if not module_height and not module_width:
            self.thermToolObj.canvas_logger("Width and Height detail are Empty...", level=Qgis.Warning)
            return None
        
        self.vlayer = iface.activeLayer()
        vfeatures = self.vlayer.getFeatures()
        featureslist = [feature for feature in vfeatures] 
        try:
            self.thermToolObj.featuresobjlist = [Table(feature) for feature in featureslist] 
            #Associate issues Parent table
            associate_issues_parent_table(self.thermToolObj.featuresobjlist)
            #Update Issue Row and Column number with respecte barcode tracker
            update_issue_Row_column(self.thermToolObj.featuresobjlist, self.vlayer, module_height, module_width)
        except Exception as e:
            self.thermToolObj.canvas_logger(str(e), level=Qgis.Warning)
        else:
            self.thermToolObj.canvas_logger("Issue Row and Column Numbers updated w.r.t Barcode Trackers...", level=Qgis.Success)

    def update_serial_numbers(self):
        if not self.thermToolObj.featuresobjlist:
            self.thermToolObj.canvas_logger("Locate Row and Column Before Updating serial number", level=Qgis.Warning)
            return None
        
        tablelist = [table for table in self.thermToolObj.featuresobjlist if table.feature['class_name'] == 'strings' and table.issue_obj]
        try:
            for table in tablelist:
                uid = table.feature["uid"]
                serial_number = self.thermToolObj.project.extraProperties.get(uid, {}).get("_serial_numbers", {})
                parentTableIssueObj = [issue for issue in table.issue_obj]
                for issueObj in parentTableIssueObj:
                    module_number = issueObj.feature['serial_number'] 
                    row, column = module_number.split("-")
                    row = int(re.findall(r'\d+', row)[0])-1
                    column = int(re.findall(r'\d+', column)[0])-1
                    module_num = ":".join([str(row), str(column)])
                    issueObj.feature['serial_number'] = serial_number.get(module_num)
                    self.vlayer.updateFeature(issueObj.feature)
            self.thermToolObj.uncheck_all_buttons()
            self.vlayer.commitChanges()
            self.vlayer.startEditing()
        except Exception as e:
            self.thermToolObj.canvas_logger(str(e), level=Qgis.Warning)
        else:
            self.thermToolObj.canvas_logger("Serial Number Updated...", level=Qgis.Success)

def associate_issues_parent_table(featuresobjlist):
    tablelist = [table for table in featuresobjlist if table.feature['class_name'] == 'strings']
    issuelist = [issue for issue in featuresobjlist if issue.feature['class_name'] != 'strings' and issue.feature['class_name'] != 'table']
    for table in tablelist:
        issueObjlist = []
        for issue in issuelist:
            centriod = issue.feature.geometry().centroid() 
            if table.feature.geometry().contains(centriod):
                issueObjlist.append(issue)
        setattr(table,'issue_obj',issueObjlist)

def update_issue_Row_column(featuresobjlist, vlayer, height, width):
    tablelist = [table for table in featuresobjlist if table.feature['class_name'] == 'strings' and table.issue_obj]
    for table in tablelist:
        parentTableIssueObj = [issue for issue in table.issue_obj]
        abjx = width/2
        abjy = height/2
        leftTop_y = max(table.raw_utm_coords, key=lambda x: x[1])[1]
        leftTop_x = min(table.raw_utm_coords, key=lambda x: x[0])[0]
        for issueObj in parentTableIssueObj:
            x = (issueObj.raw_utm_x-leftTop_x)/width
            y = (leftTop_y-issueObj.raw_utm_y)/height
            column = ceil(x)
            row = ceil(y)
            if row < abjy: row = 1
            if column < abjx: column =1
            issueObj.feature['serial_number'] = f'R{row}-C{column}'
            vlayer.updateFeature(issueObj.feature)


class AssetLevelProjects(QtWidgets.QWidget):
    def __init__(self, img_tag_obj):
        super().__init__()
        self.img_tag_obj = img_tag_obj
        self.projects_form = None
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.project_selection_layout = QtWidgets.QVBoxLayout(self)
        self.setWindowTitle('Groups...')
        self.current_group_projects = {}
        self.canvas_logger = img_tag_obj.canvas_logger
        self.org_uid = img_tag_obj.org_uid
        self.core_token = img_tag_obj.core_token
        self.setupUi(self.img_tag_obj.project.group_dict)

    def setupUi(self, group_dict):
        self.group_details = {}
        for group_uid, group_obj in group_dict.items():
            self.group_details[group_uid] = (group_obj.name, group_obj.projects_details)
        group_list = [value[0] for value in self.group_details.values()]
        self.group_combobox = QtWidgets.QComboBox(self)
        self.group = combobox_modifier(self.group_combobox, group_list)
        self.project_selection_layout.addWidget(self.group, 0, Qt.AlignTop)
        self.group.currentIndexChanged.connect(self.group_tree)
        _, self.project_details = [[uid, project_details] for uid, (group_name, project_details) in self.group_details.items() if group_name == self.group.currentText()][0]
        self.projects_form = ProjectForm(self.project_details, self.project_selection_layout, self)
        self.load_projects = QtWidgets.QPushButton('Load Project')
        self.project_selection_layout.addWidget(self.load_projects, 1, Qt.AlignBottom)
        self.load_projects.clicked.connect(self.load_barcode_projects)

    def group_tree(self):
        _, self.project_details = [[uid, project_details] for uid, (group_name, project_details) in self.group_details.items() if group_name == self.group.currentText()][0]
        self.projects_form = ProjectForm(self.project_details, self.project_selection_layout, self)


    def load_barcode_projects(self):
        selected_projects = []
        for project_uid, checkbox in self.current_group_projects.items():
            if checkbox[0].isChecked():
                print(project_uid, checkbox[0], checkbox[1])
                selected_projects.append(project_uid)
        
        print(selected_projects, self.org_uid)

        if not selected_projects:
            self.canvas_logger("No Project Selected to load Barcode Scanning..")
            return None
        inputs = [selected_projects, self.org_uid, self.core_token]

        load_task = QgsTask.fromFunction("Load Barcode Projects", load_barcode_json, inputs)
        QgsApplication.taskManager().addTask(load_task)
        load_task.statusChanged.connect(lambda load_status : self.load_barcode_callback(load_status, load_task))

    def load_barcode_callback(self, load_task_status, load_task):
        if load_task_status != 3:
            return None
        result = load_task.returned_values
        
        if not result:
            self.logger("Load failed...", level=Qgis.Warning)
            return None

        def string_classmap_update(features):
                for feat in features:
                    feat['properties']['class_name'] = "strings"
                    feat['properties']['class_id'] = 202
            
        if result :
            features = result["features"]
            barcode_features = features_to_polygons(features, self.img_tag_obj.uid, self.img_tag_obj.groupuid, self.img_tag_obj.project)

            with open(self.img_tag_obj.project.geojson_path , 'r') as g:
                existing_geojson = json.load(g)
            # Assigning String classmap to Barcode trackers 
            string_classmap_update(barcode_features)

            existing_geojson['features'] += barcode_features

            self.img_tag_obj.project.vlayer.commitChanges()
            self.img_tag_obj.project.vlayer.startEditing()
            #disconnect any single added to existing vlayer
            self.img_tag_obj.project.vlayer.selectionChanged.disconnect()
            # Remove existing Vlayer  
            self.img_tag_obj.project.qgis_project.removeMapLayers([self.img_tag_obj.project.vlayer.id()])
            #save merged_geojson 
            with open(self.img_tag_obj.project.geojson_path, "w") as fi:
                json.dump(existing_geojson, fi)
            #Initialize Vlayer features
            self.img_tag_obj.project.initialize_vlayer()
            self.img_tag_obj.project.canvas_logger('Barcode Trackers imported', level=Qgis.Success)
            self.close()

        self.canvas_logger('Json reloaded from the Core Successfully...', level=Qgis.Success)

def load_barcode_json(task, inputs):
    try:
        project_uids, org_uid, core_token = inputs
        headers = {"Authorization": f"Token {core_token}"}
        all_features = []
        for project_uid in project_uids:
            url = TERRA_URL + "/qc/project/{}/features/?organization={}".format(project_uid,
                                                                                org_uid) 
            
            response = requests.get(url=url, headers=headers)
            features = response.json()['features']
            all_features += features
            print(len(all_features), project_uid)
    except Exception as e:
        print(e)
    return { "features":all_features, "task":task.description()}

class ProjectForm:
    def __init__(self, projects_dict, project_selection_layout, project_selection_window):
        self.project_groupbox = QtWidgets.QGroupBox('Projects:')
        self.checkbox_list = []
        self.myform = QtWidgets.QFormLayout()
        project_selection_window.current_group_projects.clear()
        for project_uid, project_name in sorted(projects_dict.items(), key=lambda x: x[1]):
            project_checkbox = QtWidgets.QCheckBox(f'{project_name}')
            self.myform.addRow(project_checkbox)
            project_selection_window.current_group_projects[project_uid] = [project_checkbox, project_name]

        self.project_groupbox.setLayout(self.myform)

        self.scroll_widget = QtWidgets.QScrollArea()
        self.scroll_widget.setWidget(self.project_groupbox)
        self.scroll_widget.setWidgetResizable(True)
        self.scroll_widget.setFixedSize(250, 300)
        # Replace the scroll widget if it exists
        if project_selection_window.projects_form:
            project_selection_layout.replaceWidget(project_selection_window.projects_form.scroll_widget,
                                                   self.scroll_widget)
        else:
            project_selection_layout.addWidget(self.scroll_widget, 1, Qt.AlignTop)