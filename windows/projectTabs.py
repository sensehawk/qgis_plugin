from qgis.PyQt.QtCore import Qt
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from qgis.core import QgsProject, Qgis
from qgis.utils import iface
from .terra_tools import TerraToolsWindow
from .therm_tools import ThermToolsWindow
from ..event_filters import KeypressFilter, KeypressEmitter, KeypressShortcut
import pandas as pd


class Project:
    def __init__(self, load_task_result):
        self.project_details = load_task_result['project_details']
        self.vlayer = load_task_result['vlayer']
        self.rlayer = load_task_result['rlayer']
        self.feature_counts = load_task_result['feature_counts']
        self.class_maps = load_task_result['class_maps']
        self.class_groups = load_task_result['class_groups']
        self.project_tab_index = None
        self.project_tab = QtWidgets.QWidget()
        # Create a layout that contains project details
        self.project_tab_layout = QtWidgets.QVBoxLayout(self.project_tab)
        self.tools_window = None
        self.project_tabs_window = None
        self.feature_shortcuts = {}
        self.setup_feature_shortcuts()
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

    def connect_tools(self):
        if self.project_details["project_type"] == "terra":
            # Connect terra tools
            self.tools_window = TerraToolsWindow(self)
        elif self.project_details["project_type"] == "therm":
            # Connect therm tools
            self.tools_window = ThermToolsWindow(self)
        # Hide window for now
        self.tools_window.hide()

    def show_tools_window(self):
        self.tools_window.show()

    def create_features_table(self):
        # Create a table of feature counts
        features_table = QtWidgets.QTableWidget(self.project_tab)

        # Hide headers
        features_table.verticalHeader().setVisible(False)
        features_table.horizontalHeader().setVisible(False)

        # Disable editing
        features_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.project_tab_layout.addWidget(features_table)

        # Populate feature counts
        features_table.setRowCount(len(self.feature_counts))
        features_table.setColumnCount(2)
        for i, (feature_type, feature_count) in enumerate(self.feature_counts):
            feature_type_item = QtWidgets.QTableWidgetItem(feature_type)
            feature_type_item.setBackground(QtGui.QColor(self.color_code[feature_type]))
            feature_count_item = QtWidgets.QTableWidgetItem(str(feature_count))
            features_table.setItem(i, 0, feature_type_item)
            features_table.setItem(i, 1, feature_count_item)
        features_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)

    def populate_project_tab(self):
        project_details = self.project_details
        # Create project UID label
        project_uid_label = QtWidgets.QLabel(self.project_tab)
        project_uid_label.setText(f"UID: {project_details['uid']}")
        self.project_tab_layout.addWidget(project_uid_label)
        # Create project type label
        project_type_label = QtWidgets.QLabel(self.project_tab)
        project_type_label.setText(f"Project type: {project_details['project_type'].capitalize()}")
        self.project_tab_layout.addWidget(project_type_label)
        # Create features table
        self.create_features_table()
        # Create a tools button
        tools_button = QtWidgets.QPushButton(self.project_tab)
        tools_button.setText("Tools")
        self.project_tab_layout.addWidget(tools_button)
        # Connect this button to tools
        tools_button.clicked.connect(self.show_tools_window)

    def setup_feature_shortcuts(self):
        # Feature types are defined at the container level in case of Terra and is fixed in case of Therm
        # Check if the container csv exists in case of terra or therm shortcuts in case of therm
        if self.project_details["project_type"] == "therm":
            self.shortcuts_csv_path = os.path.join(os.path.dirname(__file__), 'keyboard_shortcuts', 'therm_keyboard_shortcuts.csv')
        elif self.project_details["project_type"] == "terra":
            self.shortcuts_csv_path = os.path.join(os.path.dirname(__file__), 'keyboard_shortcuts', f'{self.project_details["group"]["name"]}.csv')
        # If shortcuts exist, load from there
        if os.path.exists(self.shortcuts_csv_path):
            df = pd.read_csv(self.shortcuts_csv_path)
            for i in range(len(df)):
                key, feature_type = df["Key"][i], df["Feature Type"][i].strip()
                self.feature_shortcuts[key] = feature_type
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
        self.vlayer.triggerRepaint()


class ProjectTabsWindow(QtWidgets.QWidget):
    def __init__(self, load_window):
        super().__init__()
        self.load_window = load_window
        self.logger = self.load_window.logger
        # Save projects loaded dict mapping uid to project object
        self.projects_loaded = {}
        # Track index through uid list - index in list is the index of its tab
        self.project_uids = []
        self.setupUi()
        self.qgis_project = QgsProject.instance()
        self.layer_tree = self.qgis_project.layerTreeRoot()
        self.active_project = None
        self.setupKeyboardShortcuts()

    def setupKeyboardShortcuts(self):
        # Create gis shortcuts generic to all projects
        self.qgis_shortcuts = {
            "E": "self.active_project.vlayer.startEditing()",
            "Return": "self.active_project.vlayer.removeSelection()\n"
                      "self.active_project.vlayer.commitChanges()",
            "F": "self.active_project.vlayer.startEditing()\n"
                 "iface.actionAddFeature().trigger()",
            "S": "iface.actionSelect().trigger()",
            "Z": "iface.actionZoomToLayer().trigger()",
            "P": "iface.showAttributeTable(self.active_project.vlayer())"
        }
        # Create a key emitter that sends the key presses
        self.key_emitter = KeypressEmitter()
        # Connect the key emitter to the key eater that performs required shortcuts
        self.key_emitter.signal.connect(lambda x: self.key_eater(x))
        # Create keypress event filter to consume the key presses from iface and send it to key_emitter
        self.keypress_filter = KeypressFilter(self.key_emitter)
        # Install key press filter to iface's map canvas
        iface.mapCanvas().installEventFilter(self.keypress_filter)

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
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(projects_group)

        # Close project button
        close_project_button = QtWidgets.QPushButton(self)
        close_project_button.setText("Close Project")
        close_project_button.clicked.connect(self.remove_project)
        main_layout.addWidget(close_project_button)

    def add_project(self, project):
        # Add uid to a list to track tab index
        self.project_uids.append(project.project_details["uid"])
        self.projects_loaded[project.project_details["uid"]] = project
        # Add project tab to the tabs widget
        self.project_tabs_widget.addTab(project.project_tab, project.project_details["name"])
        # Show all project details in the project tab
        project.populate_project_tab()
        # Add project layers to the project
        self.qgis_project.addMapLayer(project.rlayer)
        self.qgis_project.addMapLayer(project.vlayer)
        # Set active layer and zoom to layer
        iface.setActiveLayer(project.vlayer)
        iface.actionZoomToLayer().trigger()
        project.project_tabs_window = self
        project.logger = self.logger
        # Connect project tools
        # project.connect_tools()
        # Activate project
        self.activate_project()

    def activate_project(self):
        """
        Make only the selected project layers visible and zoom to layer
        """
        # Get the project_uid and project object
        try:
            project_uid = self.project_uids[self.project_tabs_widget.currentIndex()]
        except IndexError:
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

    def remove_project(self):
        # Get current project
        try:
            project_uid = self.project_uids[self.project_tabs_widget.currentIndex()]
            project = self.projects_loaded[project_uid]
        except Exception as e:
            return None
        try:
            self.qgis_project.removeMapLayers([project.rlayer.id(), project.vlayer.id()])
        except Exception as e:
            self.logger(str(e), level=Qgis.Warning)
        # Remove item from projects loaded and project uids list
        self.project_uids.remove(project_uid)
        del self.projects_loaded[project_uid]
        # Remove project tab
        self.project_tabs_widget.removeTab(self.project_tabs_widget.currentIndex())

    def key_eater(self, x):
        # Connect to active projects feature shortcuts and qgis shortcuts
        key = QtGui.QKeySequence(x).toString()
        if key in self.active_project.feature_shortcuts:
            feature_change_name = self.active_project.feature_shortcuts.get(key, None)
            self.active_project.change_feature_type(feature_change_name)
        elif key in self.qgis_shortcuts:
            qgis_shortcut_function = self.qgis_shortcuts[key]
            exec(compile(qgis_shortcut_function, "<string>", "exec"))
