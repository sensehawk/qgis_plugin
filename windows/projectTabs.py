from qgis.PyQt.QtCore import Qt, QVariant, QSize
import os
from PyQt5 import QtGui, QtWidgets, uic
from qgis.core import QgsProject, Qgis, QgsTask, QgsApplication, QgsVectorLayer, QgsField, NULL, QgsRasterLayer
from qgis.utils import iface
from .terra_tools import TerraToolsWidget
from ..event_filters import KeypressFilter, KeypressEmitter
from .therm_tools import ThermToolsWidget
from datetime import datetime
from ..sensehawk_apis.core_apis import save_project_geojson
from ..utils import fields_validator, categorize_layer, save_edits
import pandas as pd
import qgis
import json
from .keyboard_settings import ShortcutSettings
import random 
import string
import re
import tempfile
import shutil
import pprint

class Project:
    def __init__(self, load_task_result):

        self.project_details = load_task_result['project_details']
        self.geojson_path = load_task_result['geojson_path']
        self.vlayer = QgsVectorLayer(self.geojson_path+ "|geometrytype=Polygon", self.geojson_path, "ogr")
        self.vlayer.featureAdded.connect(lambda x: self.updateUid_and_sync_featurecount(new_feature_id=x))
        self.vlayer.featureDeleted.connect(lambda x: self.load_feature_count(feature_id=x))

        #validate fields and create if not there
        self.required_fields = {'temperature_min':QVariant.Double,'temperature_max':QVariant.Double,
                           'temperature_difference':QVariant.Double,'uid':QVariant.String,
                           'projectUid':QVariant.String,'groupUid':QVariant.String,
                           'num_images_tagged':QVariant.Double,'string_number':QVariant.String, 
                           'table_row':QVariant.Double,'table_column':QVariant.Double, 
                           'row':QVariant.Double,'idx':QVariant.Double,
                           'total_num_modules':QVariant.Double,'column':QVariant.Double, 
                           'num_modules_horizontal':QVariant.Double,'timestamp':QVariant.String, 
                           'num_modules_vertical':QVariant.Double,'center':QVariant.String, 
                           'raw_images':QVariant.String,'attachments':QVariant.String,
                           'parent_uid':QVariant.String}

        fields_validator(self.required_fields, self.vlayer)
        #initialize and update parent_uid field 
        self.initialize_parentUid()
        self.collect_list_Type_dataFields()
        self.rlayer_url = load_task_result['rlayer_url']
        self.rlayer = QgsRasterLayer(self.rlayer_url, self.project_details['name'] + "_ortho", "wms")
        self.class_maps = load_task_result['class_maps']
        self.class_groups = load_task_result['class_groups']
        self.existing_files = load_task_result['existing_files']
        self.iface = iface
        self.project_tab = QtWidgets.QWidget()
        # Create a layout that contains project details
        self.project_tab_layout = QtWidgets.QVBoxLayout(self.project_tab)
        self.project_tab_layout.setContentsMargins(5, 5, 5, 5)
        self.setup_tool_widget()
        self.setup_docktool_widget()
        self.project_tabs_widget = None
        self.feature_shortcuts = {}
        self.setup_feature_shortcuts()
        self.setup_feature_uid()

        # Time stamp of last saved
        self.last_saved = str(datetime.now())
        # color classifying based on class_name for therm / class_name and class_maps for terra
        if not self.class_maps:
            self.color_code = {'hotspot': '#001c63', 'diode_failure': '#42e9de', 'module_failure': '#2ecc71',
                          'string_failure': '#3ded2d', 'module_reverse_polarity': '#ff84dc',
                          'potential_induced_degradation': '#550487', 'vegetation': '#076e0a',
                          'tracker_malfunction': '#c50000', 'string_reverse_polarity': '#f531bd',
                          'dirt': '#b5b0b0', 'cracked_modules': '#9b9e33', 'table': '#ffff00'}
        else:
            self.color_code = {
                i: self.class_maps[i]["properties"]["color"].replace("rgb(", "").replace(")", "").replace(" ", "").split(",")
                for i in self.class_maps}
            self.color_code = {i: "#%02x%02x%02x" % tuple(int(x) for x in self.color_code[i]) for i in self.color_code}
    
    # parsing collected list type data to copy_pasted issue and validting list_type fields for newly added ones
    def save_and_parse_listType_dataFields(self):
        self.vlayer.commitChanges()
        #disconnect any single added to existing vlayer
        self.vlayer.selectionChanged.disconnect()
        # remove existing json 
        self.qgis_project.removeMapLayers([self.vlayer.id()])

        save_edits_task = QgsTask.fromFunction("Save_Edits", save_edits, save_inputs={'json_path':self.geojson_path,
                                                                                      'listType_dataFields':self.listType_dataFields})
        QgsApplication.taskManager().addTask(save_edits_task)
        save_edits_task.statusChanged.connect(lambda save_edits_status : self.save_edits_callback(save_edits_status, save_edits_task))
    
    def save_edits_callback(self, save_edits_status, save_edits_task):
        if save_edits_status != 3:
            return None
        result = save_edits_task.returned_values
        if result:
            #Add and Initializing Vlayer features
            self.initialize_vlayer()
            self.canvas_logger(f'{self.project_details.get("name", None)} Geojson Saved...', level=Qgis.Success)
            
    # Initialize Vlayer 
    def initialize_vlayer(self):
        #loaded updated layer
        updated_vlayer = QgsVectorLayer(self.geojson_path, self.geojson_path, "ogr")
        self.qgis_project.addMapLayer(updated_vlayer)
        self.vlayer = updated_vlayer
        categorize_layer(self)
        self.load_feature_count()   
        self.vlayer.startEditing()
        #validate and create fields if not exits
        fields_validator(self.required_fields, self.vlayer)
        #connect pre-defined singles 
        self.vlayer.featureAdded.connect(lambda x: self.updateUid_and_sync_featurecount(new_feature_id=x))
        self.vlayer.featureDeleted.connect(lambda x: self.load_feature_count(feature_id=x))

    # Since Qgis won't support list type fields data in copy-pasted issues, 
    # collecting list type data with Parentuid as key and list type data as value 
    def collect_list_Type_dataFields(self):
        self.listType_dataFields = {}
        features = json.load(open(self.geojson_path))['features']
        for feature in features:
            if feature['properties']['class_name'] != 'table':
                center = feature['properties'].get('center', None)
                raw_images = feature['properties'].get('raw_images', None)
                parentUid = feature['properties'].get('parent_uid', None)
                if type(center) == list :
                    center_value = self.listType_dataFields.get(parentUid, {})
                    center_value['center'] = center
                    self.listType_dataFields[parentUid] = center_value

                if type(raw_images) == list :
                    rawimage_value = self.listType_dataFields.get(parentUid, {})
                    rawimage_value['raw_images'] = raw_images
                    self.listType_dataFields[parentUid] = rawimage_value


    def initialize_parentUid(self):
        self.vlayer.startEditing()
        for feature in self.vlayer.getFeatures():
            feature['parent_uid'] = feature['uid']
            feature['num_images_tagged'] = 0
            self.vlayer.updateFeature(feature)
        self.vlayer.commitChanges()

    def clean_fields(self):
        print('cleaning the fields')
        # Clean wrongly formatted fields (center, raw_images, attachments) in case they exist
        self.vlayer.startEditing()
        default_values = {"raw_images": NULL, "attachments": NULL, "center": NULL, "temperature_max": NULL, "temperature_min": NULL, "temperature_difference": NULL}
        for f in self.vlayer.getFeatures():
            for attr in default_values.keys():
                try:   
                    attr_value = f[attr]
                except KeyError:
                    continue
                if type(attr_value) in [str, dict]:
                    f[attr] = re.sub('[{}\n]', '', str(f[attr]))
                    if not f[attr]:
                        f[attr] = default_values[attr]
            self.vlayer.updateFeature(f)
        self.vlayer.commitChanges()

    def setup_tool_widget(self):
        # Dummy active tool widget and tool dock widget
        self.tools_widget = QtWidgets.QWidget(self.project_tab)
        self.active_tool_widget = self.tools_widget

    def setup_docktool_widget(self):
        self.docktool_widget = QtWidgets.QDockWidget()
        # Dummy placeholder widget
        self.active_docktool_widget = QtWidgets.QWidget()
        self.docktool_widget.setWidget(self.active_docktool_widget)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.docktool_widget)
        self.docktool_widget.hide()

    def import_geojson(self, geojson_path):
        # Merge with existing geojson and reload from there
        if geojson_path:
            self.vlayer.commitChanges()
            with open(geojson_path, 'r') as g:
                imported_geojson = json.load(g)['features']
            with open(self.geojson_path , 'r') as g:
                existing_geojson = json.load(g)
            existing_geojson['features'] += imported_geojson
            #disconnect any single added to existing vlayer
            self.vlayer.selectionChanged.disconnect()
            # Remove existing Vlayer  
            self.qgis_project.removeMapLayers([self.vlayer.id()])
            #save merged_geojson 
            with open(self.geojson_path, "w") as fi:
                json.dump(existing_geojson, fi)
            #Initialize Vlayer features
            self.initialize_vlayer()
            self.canvas_logger('Selected Geojson Imported...', level=Qgis.Success)

    def export_geojson(self, save_path):
        if save_path:
            self.save_and_parse_listType_dataFields()
            real_path = os.path.realpath(save_path)
            current_layer = json.load(open(self.geojson_path))
            json.dump(current_layer, open(real_path, "w"))
            self.canvas_logger(f'{self.project_details.get("name", None)} Geojson exported...', level=Qgis.Success)
            del current_layer # to aviod ram overload

    def add_tools(self):
        if self.project_details["project_type"] == "terra":
            # get terra tools
            self.tools_widget = TerraToolsWidget(self)
        elif self.project_details["project_type"] == "therm":
            # get therm tools
            self.tools_widget = ThermToolsWidget(self)
        self.project_tab_layout.addWidget(self.tools_widget)
        self.tools_widget.show()
    
    # update uid to newly added feature and synch feature count in project table tab widget
    def updateUid_and_sync_featurecount(self, new_feature_id=None):
        # Update uid field 
        feature = list(self.vlayer.getFeatures([new_feature_id]))[0]
        self.load_feature_count()
        feature['uid'] = self.create_uid()
        feature['projectUid'] = self.project_details["uid"]
        feature['groupUid'] = self.project_details["group"]["uid"]
        self.vlayer.updateFeature(feature)

    # synch  feature count in project table
    def load_feature_count(self, feature_id=None):
        # Get feature count by class_name
        feature_count_dict = {}
        class_name_keyword = {"terra": "class", "therm": "class_name"}[self.project_details["project_type"]]
        for f in self.vlayer.getFeatures():
            feature_class = f[class_name_keyword]
            class_count = feature_count_dict.get(feature_class, 0)
            class_count += 1
            feature_count_dict[feature_class] = class_count

        self.feature_counts = [(k, v) for k, v in feature_count_dict.items()]
        # Populate feature counts
        self.features_table.setRowCount(len(self.feature_counts))
        for i, (feature_type, feature_count) in enumerate(self.feature_counts):
            feature_type_item = QtWidgets.QTableWidgetItem(str(feature_type))
            feature_type_item.setBackground(QtGui.QColor(self.color_code.get(str(feature_type), "#000000")))
            feature_count_item = QtWidgets.QTableWidgetItem(str(feature_count))
            self.features_table.setItem(i, 0, feature_type_item)
            self.features_table.setItem(i, 1, feature_count_item)

    def create_features_table(self):
        # Create a table of feature counts
        self.features_table = QtWidgets.QTableWidget(self.project_tab)

        # Hide headers
        self.features_table.verticalHeader().setVisible(False)
        self.features_table.verticalHeader().resizeSection(0, 100)
        self.features_table.verticalHeader().resizeSection(1, 100)
        self.features_table.horizontalHeader().setVisible(False)
        self.features_table.horizontalHeader().resizeSection(0, 100)
        self.features_table.horizontalHeader().resizeSection(1, 100)
        # 2 columns
        self.features_table.setColumnCount(2)

        # Disable editing
        self.features_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.project_tab_layout.addWidget(self.features_table)

    def create_project_details_widget(self):
        self.project_details_widget = QtWidgets.QWidget(self.project_tab)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'project_details.ui'), self.project_details_widget)
        self.project_details_widget.project_uid.setText(f"UID: {self.project_details['uid']}")
        self.project_details_widget.group.setText(f"Group: {self.project_details['group']['name']}")
        # self.project_details_widget.project_type.setText(
        #     f"Project Type: {self.project_details['project_type'].capitalize()}")
        self.project_details_widget.show()
        self.project_tab_layout.addWidget(self.project_details_widget)
        self.feature_shortcut_settings_widget = ShortcutSettings(self)
        self.project_details_widget.toolButton.clicked.connect(self.feature_shortcut_settings_widget.show)
        self.project_details_widget.toolButton.setStyleSheet("background-color:#dcf7ea;")
        self.project_details_widget.save_edits.clicked.connect(self.save_and_parse_listType_dataFields)
        self.project_details_widget.save_edits.setStyleSheet("background-color:#dcf7ea;")
        self.project_details_widget.importButton.clicked.connect(lambda: self.import_geojson(QtWidgets.QFileDialog.getOpenFileName(None, "Title", "", "JSON (*.json)")[0]))
        self.project_details_widget.importButton.setStyleSheet("background-color:#dce4f7; color: #3d3838;")
        self.project_details_widget.exportButton.clicked.connect(lambda: self.export_geojson(QtWidgets.QFileDialog.getSaveFileName(None, "Title", "", "JSON (*.json)")[0]))
        self.project_details_widget.exportButton.setStyleSheet("background-color:#dce4f7; color: #3d3838;")
        self.project_details_widget.project_uid.setTextInteractionFlags(Qt.TextSelectableByMouse)

    def populate_project_tab(self):
        # Simple line widget separator
        line1 = QtWidgets.QFrame()
        line1.setFrameShape(QtWidgets.QFrame.HLine)
        self.project_tab_layout.addWidget(line1)
        # Create the project details widget
        self.create_project_details_widget()
        line2 = QtWidgets.QFrame()
        line2.setFrameShape(QtWidgets.QFrame.HLine)
        self.project_tab_layout.addWidget(line2)
        # Create features table
        self.create_features_table()
        self.load_feature_count()
        line3 = QtWidgets.QFrame()
        line3.setFrameShape(QtWidgets.QFrame.HLine)
        self.project_tab_layout.addWidget(line3)
        # Add project tools
        self.add_tools()
        # Add the dummy active tool widget
        self.project_tab_layout.addWidget(self.active_tool_widget)
        line4 = QtWidgets.QFrame()
        line4.setFrameShape(QtWidgets.QFrame.HLine)
        self.project_tab_layout.addWidget(line4)
        

    def setup_feature_shortcuts(self):
        keyboard_shorcuts_dir = os.path.join(os.path.dirname(__file__), 'keyboard_shortcuts')
        if not os.path.exists(keyboard_shorcuts_dir):
            os.mkdir(keyboard_shorcuts_dir)
        # Feature types are defined at the container level in case of Terra and is fixed in case of Therm
        # Check if the container csv exists in case of terra or therm shortcuts in case of therm
        if self.project_details["project_type"] == "therm":
            self.shortcuts_csv_path = os.path.join(keyboard_shorcuts_dir, 'therm_keyboard_shortcuts.csv')
        elif self.project_details["project_type"] == "terra":
            self.shortcuts_csv_path = os.path.join(keyboard_shorcuts_dir, f'{self.project_details["group"]["name"]}.csv')
        # If shortcuts exist, load from there
        if os.path.exists(self.shortcuts_csv_path):
            df = pd.read_csv(self.shortcuts_csv_path)
            for i in range(len(df)):
                key, feature_type = df["Key"][i], df["Feature Type"][i].strip()
                self.feature_shortcuts[str(key)] = feature_type
        else:
            # Create default mapping and write to file
            default_maps = {"clip_boundary": "C", "train_boundary": "T"}
            shortcut = 0
            for c in self.class_maps:
                feature_name = self.class_maps[c]["name"]
                if feature_name in self.feature_shortcuts.values():
                    continue
                if feature_name.lower() in default_maps:
                    self.feature_shortcuts[default_maps[feature_name.lower()]] = feature_name
                    continue
                self.feature_shortcuts[str(shortcut)] = feature_name
                shortcut += 1
            with open(self.shortcuts_csv_path, "w") as fi:
                fi.write("Key,Feature Type\n")
                for k, v in self.feature_shortcuts.items():
                    fi.write(f"{k},{v}\n")

    def change_feature_type(self, class_name):
        # If there are selected items, change feature type for those or else change feature type of last added feature
        self.vlayer.startEditing()
        selected_features = list(self.vlayer.selectedFeatures())
        if selected_features:
            self.logger("Changing class_name of selected features to {}".format(class_name))
            for feature in selected_features:
                if self.project_details["project_type"] == "therm":
                    feature.setAttribute("class_name", class_name)
                    feature.setAttribute("class_id", self.class_maps[class_name]["class_id"])
                elif self.project_details["project_type"] == "terra":
                    name = self.class_maps.get(class_name, {}).get("name", None)
                    feature.setAttribute("class", name)
                    feature.setAttribute("class_name", class_name)
                    class_id = self.class_maps.get(class_name, {}).get("id", None)
                    feature.setAttribute("class_id", int(class_id))
                self.vlayer.updateFeature(feature)
        else:
            self.vlayer.commitChanges()
            self.vlayer.startEditing()
            # Change last added feature
            features = list(self.vlayer.getFeatures())
            last_feature_index = -1
            try:
                last_feature = features[last_feature_index]
            except IndexError:
                self.logger("No feature selected or new feature added...")
                return None
            self.logger("Changing class_name of last added feature to {}".format(class_name))
            if self.project_details["project_type"] == "therm":
                last_feature.setAttribute("class_name", class_name)
                last_feature.setAttribute("class_id", self.class_maps[class_name]["class_id"])
            elif self.project_details["project_type"] == "terra":
                name = self.class_maps.get(class_name, {}).get("name", None)
                last_feature.setAttribute("class", name)
                last_feature.setAttribute("class_name", class_name)
                class_id = self.class_maps.get(class_name, {}).get("id", None)
                last_feature.setAttribute("class_id", int(class_id))
            self.vlayer.updateFeature(last_feature)
        self.load_feature_count()

    def create_uid(self):
        unique_string = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase) for _ in range(9))
        uid = f"{self.project_details['uid']}-{unique_string[:3]}:{unique_string[3:6]}~{unique_string[6:]}"
        print(f"UID of newly added feature: {uid}")
        return uid

    def setup_feature_uid(self):
        if self.vlayer.fields().indexFromName("uid") == -1:
                uid_field = QgsField("uid", QVariant.String)
                self.vlayer.dataProvider().addAttributes([uid_field])
                self.vlayer.updateFields() # update layer fields after creating new one
        self.vlayer.commitChanges()
        self.vlayer.startEditing()



class ProjectTabsWidget(QtWidgets.QWidget):
    def __init__(self, load_window):
        super().__init__()
        self.canvas_logger = load_window.canvas_logger
        self.logger = load_window.logger
        self.load_window = load_window
        # Save projects loaded dict mapping uid to project object
        self.projects_loaded = {}
        # Track index through uid list - index in list is the index of its tab
        self.project_uids = []
        self.setupUi()
        self.qgis_project = QgsProject.instance()
        self.layer_tree = self.qgis_project.layerTreeRoot()
        self.active_project = None
        self.iface = iface
        self.setupKeyboardShortcuts() 
        # self.constrain_canvas_zoom()

    def setupUi(self):

        # Create a group of widgets and define layout
        projects_group = QtWidgets.QGroupBox('Projects loaded:', self)
        projects_group_layout = QtWidgets.QVBoxLayout(projects_group)

        # Create base widget for the group
        projects_group_widget = QtWidgets.QWidget(projects_group)

        # Create a tabs widget and add it to the group layout
        self.project_tabs_widget = QtWidgets.QTabWidget(projects_group_widget)
        # Connect tab change event to activate project layers
        self.project_tabs_widget.currentChanged.connect(self.activate_project)
        projects_group_layout.addWidget(self.project_tabs_widget)

        # Create main layout for the main widget and add the widgets group
        Vmain_layout = QtWidgets.QVBoxLayout(self)
        Vmain_layout.addWidget(projects_group)

        Hmain_layout = QtWidgets.QHBoxLayout(self)
        # Back to project load button
        back_button = QtWidgets.QPushButton(self)
        back_button.setText("👈🏼 Back")
        back_button.setStyleSheet('QPushButton {background-color: #f6f7b7; color: #3d3838;}')
        back_button.clicked.connect(self.back_to_load)
        Hmain_layout.addWidget(back_button)

        # Close project button
        close_project_button = QtWidgets.QPushButton(self)
        close_project_button.setText("❌ Close")
        close_project_button.setStyleSheet('QPushButton {background-color: #f7b7ce; color: #3d3838;}')
        close_project_button.clicked.connect(self.close_project)
        Hmain_layout.addWidget(close_project_button)

        # Save project button
        save_project_button = QtWidgets.QPushButton(self)
        save_project_button.setText("✔️ Save")
        save_project_button.setStyleSheet('QPushButton {background-color: #b9f7b7; color: #3d3838;}')
        save_project_button.clicked.connect(self.save_project)
        Hmain_layout.addWidget(save_project_button)

        Vmain_layout.addLayout(Hmain_layout)
        Vmain_layout.setContentsMargins(10, 15, 0, 10)

    def setupKeyboardShortcuts(self):
        # Create gis shortcuts generic to all projects
        self.qgis_shortcuts = {
            "E": "self.active_project.vlayer.startEditing()",
            "A": "self.active_project.vlayer.removeSelection()\n"
                      "self.active_project.vlayer.commitChanges()",
            "F": "self.active_project.vlayer.startEditing()\n"
                 "iface.actionAddFeature().trigger()",
            "S": "iface.actionSelect().trigger()",
            "Z": "iface.actionZoomToLayer().trigger()",
            "O": "iface.showAttributeTable(self.active_project.vlayer)",
            "D": "iface.actionCopyFeatures().trigger()"
        }
        # Create a key emitter that sends the key presses
        self.key_emitter = KeypressEmitter()
        # Connect the key emitter to the key eater that performs required shortcuts
        self.key_emitter.signal.connect(lambda x: self.key_eater(x))
        # Create keypress event filter to consume the key presses from iface and send it to key_emitter
        self.keypress_filter = KeypressFilter(self.key_emitter)
        # Install key press filter to iface's map canvas
        self.iface.mapCanvas().installEventFilter(self.keypress_filter)
    
    def key_eater(self, x):
        # Connect to active projects feature shortcuts and qgis shortcuts
        key = QtGui.QKeySequence(x).toString()
        if not self.active_project:
            return None
        if key in self.active_project.feature_shortcuts:
            self.active_project.vlayer.startEditing()
            feature_change_name = self.active_project.feature_shortcuts.get(key, None)
            self.active_project.change_feature_type(feature_change_name)
            self.iface.actionAddFeature().trigger()
        elif key in self.qgis_shortcuts:
            qgis_shortcut_function = self.qgis_shortcuts[key]
            exec(compile(qgis_shortcut_function, "<string>", "exec"))
            
            
    def back_to_load(self):
        self.load_window.dock_widget.setWidget(self.load_window)
        if self.active_project:
            self.active_project.docktool_widget.hide()

    def add_project(self, project):
        self.rlayer_id = project.rlayer.id()
        self.vlayer_id = project.vlayer.id()
        # Add project tab to the tabs widget
        self.project_tabs_widget.addTab(project.project_tab, project.project_details["name"])
        # Add project layers to the project
        self.qgis_project.addMapLayer(project.rlayer)
        self.qgis_project.addMapLayer(project.vlayer)
        # Set active layer and zoom to layer
        iface.setActiveLayer(project.vlayer)
        iface.actionZoomToLayer().trigger()
        project.project_tabs_widget = self.project_tabs_widget
        project.project_tabs_window = self
        project.core_token = self.load_window.core_token
        project.iface = self.iface
        project.logger = self.logger
        project.qgis_project = self.qgis_project
        # Show all project details in the project tab
        project.populate_project_tab()
        # Add uid to a list to track tab index
        self.project_uids.append(project.project_details["uid"])
        self.projects_loaded[project.project_details["uid"]] = project
        #get docktool_widget
        self.docktool_widget = project.docktool_widget
        # Activate project
        self.activate_project()

    def save_project(self):
        if not self.active_project:
            return None
        self.active_project.last_saved = str(datetime.now())
        self.logger(f"Saving {self.active_project.project_details['uid']} to core...")

        def save_task(task, save_task_input):
            geojson_path, core_token, project_uid, project_type = save_task_input
            with open(geojson_path, 'r') as fi:
                geojson = json.load(fi)

            features = []
            for feature in geojson['features']:
                feature['properties'].pop('parent_uid', None)
                feature['properties'].pop('num_images_tagged', None)
                features.append(feature)
            
            geojson['features'] = features
            #Upload vectors
            print("Uploading")
            saved = save_project_geojson(geojson, project_uid, core_token,
                                         project_type=project_type)
            return {'status': str(saved), 'task': task.description()}
        
        def callback(task, logger):
            result = task.returned_values
            if result:
                self.logger(result["status"])
                self.canvas_logger(result['status'])
                
        st = QgsTask.fromFunction("Save", save_task,
                                  save_task_input=[self.active_project.geojson_path,
                                                   self.load_window.core_token,
                                                   self.active_project.project_details["uid"],
                                                   self.active_project.project_details["project_type"]])
        QgsApplication.taskManager().addTask(st)
        st.statusChanged.connect(lambda: callback(st, self.logger))

    def activate_project(self):
        """
        Make only the selected project layers visible and zoom to layer
        """
        if self.active_project:
            self.active_project.docktool_widget.hide()
        # Get the project_uid and project object
        try:
            project_uid = self.project_uids[self.project_tabs_widget.currentIndex()]
        except IndexError:
            self.active_project = None
            return None
        project = self.projects_loaded[project_uid]
        self.active_project = project
        for layer in self.layer_tree.layerOrder():
            if layer.id() in [project.rlayer.id(), project.vlayer.id()]:
                self.layer_tree.findLayer(layer.id()).setItemVisibilityChecked(True)
                if layer.id() == project.vlayer.id():
                    iface.setActiveLayer(layer)
                    iface.actionZoomToLayer().trigger()
            else:
                self.layer_tree.findLayer(layer.id()).setItemVisibilityChecked(False)
        

    def close_project(self):
        if not self.active_project:
            return None
        # First check if the project is saved to core or not and ask for confirmation
        confirmation_widget = iface.messageBar().createMessage("Are you sure?", f"Last saved: {self.active_project.last_saved}")
        yes_button = QtWidgets.QPushButton(confirmation_widget)
        yes_button.setText("Yes")
        yes_button.clicked.connect(self.remove_project)
        no_button = QtWidgets.QPushButton(confirmation_widget)
        no_button.setText("No")
        no_button.clicked.connect(iface.messageBar().clearWidgets)
        confirmation_widget.layout().addWidget(yes_button)
        confirmation_widget.layout().addWidget(no_button)
        iface.messageBar().pushWidget(confirmation_widget, Qgis.Warning)

    def remove_project(self):
        iface.messageBar().clearWidgets()
        self.logger(f"Removing project: {self.active_project.project_details['name']}")
        project = self.active_project
        try:
            self.qgis_project.removeMapLayers([project.rlayer.id(), project.vlayer.id()])
        except Exception as e:
            self.logger(str(e), level=Qgis.Warning)
        # Remove Project related data
        project_data_path = os.path.join(tempfile.gettempdir(), self.active_project.project_details["uid"])
        if os.path.exists(project_data_path):
            shutil.rmtree(project_data_path)
        # Remove item from projects loaded and project uids list
        self.project_uids.remove(self.active_project.project_details["uid"])
        del self.projects_loaded[self.active_project.project_details["uid"]]
        # Remove project tab
        self.project_tabs_widget.removeTab(self.project_tabs_widget.currentIndex())
        self.docktool_widget.close()
    
    def constrain_canvas_zoom(self):
        # Set max zoom and min zoom 
        canvas = self.iface.mapCanvas()

        # Disable mousewheel if you want
        # QSettings().setValue("/qgis/zoom_factor", 1)

        minScale = 10
        maxScale = 5000

        def renderStart():
            scale = canvas.scale()
            if scale < minScale:
                canvas.zoomScale(minScale)
            if scale > maxScale:
                canvas.zoomScale(maxScale)
            if scale < minScale or scale > maxScale:
                self.iface.actionPan().trigger() # Disable zoom in favor of pan

        canvas.renderStarting.connect(renderStart)

        # canvas.renderStarting.disconnect(renderStart)
