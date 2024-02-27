try:
    from .windows.packages.cv2 import cv2
except Exception:
    import cv2

from PyQt5 import QtCore
from qgis.utils import iface
from qgis.PyQt.QtCore import Qt
from qgis.PyQt import QtWidgets
from PyQt5.QtGui import QImage, QColor, QFont
from PyQt5.QtWidgets import QCompleter, QComboBox
from qgis.core import Qgis, QgsField, QgsPalLayerSettings, QgsTextBufferSettings, QgsTextFormat, \
    QgsVectorLayerSimpleLabeling, QgsSimpleFillSymbolLayer, QgsSymbol, QgsGeometry, QgsRectangle, \
    QgsCategorizedSymbolRenderer, QgsRendererCategory
import re
import glob
import json
import random
import os
import requests
import threading
import traceback
import numpy as np
from pathlib import Path
from datetime import datetime
from functools import partial
import matplotlib.pyplot as plt
from urllib.request import urlopen
from .sensehawk_apis.core_apis import get_project_geojson
from .windows.packages.exiftool import ExifToolHelper
from .constants import THERM_URL, THERMAL_TAGGING_URL, CORE_URL
from qgis.PyQt.QtCore import Qt
from shapely.ops import MultiLineString, Polygon, transform
from shapely.geometry import mapping

import yaml


def project_data_existent(task, input):
    projectUid, org, token = input
    url = f'{THERM_URL}/projects/{projectUid}/data?organization={org}'
    headers = {"Authorization": f"Token {token}"}
    projetJson = requests.get(url, headers=headers)
    return {'projectjson': projetJson.json(),
            'task': task.description()}


def sort_images(task, images_dir, logger, reverse=False):
    try:
        logger('Started sorting images using DateTimeOriginal exif tag')
        images = glob.glob(images_dir + "\\*")
        supported_image_formats = ('.jpg', '.JPG', '.tiff', '.tif', '.TIFF', '.TIF')
        images = [i for i in images if i.endswith(supported_image_formats)]
        with ExifToolHelper() as e:
            time_stamps = []
            long_lat = []
            for i in images:
                m = e.get_metadata(i)[0]
                m = {k.split(":")[-1]: m[k] for k in m}
                long = m['GPSLongitude']
                lat = m['GPSLatitude']
                long_lat.append((long, lat))
                t = m["DateTimeOriginal"]
                try:
                    t = datetime.strptime(t, "%Y:%m:%d  %H:%M:%S")
                except Exception:
                    try:
                        t = datetime.strptime(t.split(".")[0], "%Y:%m:%d  %H:%M:%S")
                    except Exception:
                        t = datetime.strptime(t, "%H:%M:%S")
                time_stamps.append(t)
        sorted_tuples = sorted(zip(time_stamps, images, long_lat), reverse=reverse)
        images = [i[1] for i in sorted_tuples]
        timestamps = [i[0] for i in sorted_tuples]
        long_lats = [i[2] for i in sorted_tuples]
    except Exception:
        dt = traceback.format_exc()
        logger(f'Error:{dt}')

    return {'sorted_images': images,
            'sorted_timestamps': timestamps,
            'sorted_long_lat': np.array(long_lats),
            'task': task.description()}


def combobox_modifier(combobox, wordlist):
    """
    args: combobox, list items

    convert combobox into an line-editer with auto-word_suggestion widget and drop-down items of passed list

    return modified combobox widget

    """
    completer = QCompleter(wordlist)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    combobox.addItems(wordlist)
    combobox.setEditable(True)
    combobox.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
    combobox.setCompleter(completer)
    combobox.completer().setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
    return combobox


def download_file(url, logger, output_path=None):
    logger("Downloading {} to {}...".format(url, output_path))
    if not url or url == "None":
        logger("Invalid file url...")
        return None

    # if output_path already exists and is of the same size as the download, skip download
    if os.path.exists(output_path) and os.stat(output_path).st_size == urlopen(url).length:
        return output_path
    response = requests.get(url)
    with open(output_path, "wb") as fi:
        fi.write(response.content)
    return output_path


def random_color():
    # Generating random color for unlisted issue type
    random_color_pick = (["#" + ''.join([random.choice('0123456789ABCDEF') for _ in range(6)])])
    color = ''
    for i in random_color_pick:
        color += i
    return color


def categorize_layer(project):
    renderer = categorized_renderer(project)
    active_layer = iface.activeLayer()
    active_layer.setRenderer(renderer)
    active_layer.triggerRepaint()
    return renderer


def categorized_renderer(project):
    color_code = project.color_code
    # Add black color for NULL class names (any newly added feature before reclassification)
    color_code[None] = "#000000"
    # Applying color based on feature 'class_name' for therm and 'class' for terra
    categories = []
    for class_name, color in color_code.items():
        # initialize the default symbol for this geometry type
        # PolygonGeometry has value 2
        symbol = QgsSymbol.defaultSymbol(2)

        # configure a symbol layer
        layer_style = {}
        layer_style['color'] = 'transparent'
        layer_style['line_width'] = '0.660000'

        #  Applying colour to features based on class name
        layer_style['line_color'] = color_code.get(class_name)

        # initialize the default symbol for this geometry type
        symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)

        # replace default symbol layer with the configured one
        if symbol_layer is not None:
            symbol.changeSymbolLayer(0, symbol_layer)

        # create renderer object
        category = QgsRendererCategory(class_name, symbol, str(class_name))
        # entry for the list of category items
        categories.append(category)

    # create renderer object
    renderer = None
    if project.project_details["project_type"] == "terra":
        renderer = QgsCategorizedSymbolRenderer('class', categories)
    elif project.project_details["project_type"] == "therm":
        renderer = QgsCategorizedSymbolRenderer('class_name', categories)

    return renderer


def load_vectors(project_details, project_type, raster_bounds, core_token, logger):
    project_uid = project_details["uid"]

    # Download vectors
    geojson = get_project_geojson(project_uid, core_token, project_type=project_type)

    # To make qgis support temperature_difference field as decimal Qvariant type
    if geojson.get('features', None) and project_type == 'therm':
        try:
            loop = True
            count = 0
            while loop:
                feature = geojson['features'][count]
                if feature['properties']['class_name'] == 'table':
                    # Assigning one of the table temp_difference with decimal value so that qgis ready this type field as decimal tyep
                    feature['properties']['temperature_difference'] = 0.67
                    loop = False
                else:
                    count += 1
        except IndexError:
            geojson['features'][0]['properties']['temperature_min'] = 44.45

    if "features" not in geojson:
        logger(str(geojson), level=Qgis.Warning)

    if not geojson.get('features', None):
        # Create an extent feature if no feature exists
        extent_geometry = json.loads(QgsGeometry.fromRect(QgsRectangle(raster_bounds[0],
                                                                       raster_bounds[1],
                                                                       raster_bounds[2],
                                                                       raster_bounds[3])).asJson())
        extent_feature = {"type": "Feature",
                          "properties": {"name": "Ortho Extent", "class_name": None, "class_id": None, "class": None,
                                         "uid": None},
                          "geometry": extent_geometry, "workflow": {}}
        geojson["features"] += [extent_feature]

    # Save geojson
    d_path = str(Path.home() / "Downloads")
    rpath = os.path.join(
        d_path + '\\' + 'Sensehawk_plugin' + '\\' + project_details['asset']['name'] + '\\' + project_details['group'][
            'name'])
    geojson_path = os.path.join(rpath + '\\' + project_details['name'] + '.geojson').replace("/", "_")
    if not os.path.exists(rpath):
        os.makedirs(rpath)
        with open(geojson_path, "w") as fi:
            json.dump(geojson, fi)

    logger("Saving project geojson...")

    return geojson_path


def projects_details(group, org, token):
    url = CORE_URL + f'/api/v1/groups/{group}/projects/?reports=true&page=1&page_size=1000&organization={org}'
    headers = {"Authorization": f"Token {token}"}
    response = requests.get(url, headers=headers)
    projects_details = response.json()['results']
    projects_dict = {}
    for project in projects_details:
        projects_dict[project['uid']] = project['name']

    return projects_dict


def groups_details(asset, org, token):
    url = CORE_URL + f'/api/v1/groups/?asset={asset}&projects=true&page=1&page_size=1000&organization={org}'
    headers = {"Authorization": f"Token {token}"}
    response = requests.get(url, headers=headers)
    groups_details = response.json()['results']
    groups_dict = {}
    for group in groups_details:
        project_details = {}
        for projects in group['projects']:
            project_details[projects['uid']] = projects['name']
        groups_dict[group['uid']] = (group['name'], project_details, group['container'], group['deal_id'])
    return groups_dict


def asset_details(task, org_uid, token):  # fetching asset and org_container details
    url = CORE_URL + f'/api/v1/asset-lists/?page_size=1000&page_number=1&organization={org_uid}'
    headers = {"Authorization": f"Token {token}"}
    asset_response = requests.get(url, headers=headers)
    asset_details = asset_response.json()['results']
    asset_dict = {}
    for asset in asset_details:
        asset_dict[asset['uid']] = {"uid": asset["uid"], "name": asset['name'],
                                    "profile_image": asset['properties'].get("cover_image", None)}

    user_id_url = CORE_URL + f'/api/v1/organizations/{org_uid}/?organization={org_uid}'
    org_user_response = requests.get(user_id_url, headers=headers)
    user_id = org_user_response.json()['owner'].get('uid', None)

    apptype_url = CORE_URL + f'/api/v1/apptypes/?organization={org_uid}'
    apptype_response = requests.get(apptype_url, headers=headers)
    apptype_details = apptype_response.json()['results']
    apptype_dict = {}
    if apptype_details:
        for apptype in apptype_details:
            apptype_dict[apptype['name']] = {'uid': apptype['uid'], 'name': apptype['name'],
            'acitve': apptype['active'], 'application': apptype['application']}


    return {'asset_dict': asset_dict,
            'user_id': user_id,
            'apptype_dict': apptype_dict,
            'task': task.description()}
    # 'org_container_details':org_container_details,


def organization_details(token):
    url = CORE_URL + '/api/v1/organizations/?page_size=99999&page=1'
    headers = {"Authorization": f"Token {token}"}
    response = requests.get(url, headers=headers)
    org_details = response.json()['results']
    org_list = {}
    for org in org_details:
        org_list[org['uid']] = org['name']
    return org_list


def file_existent(project_uid, org, token):
    url = f'{THERM_URL}/projects/{project_uid}/data?organization={org}'
    headers = {"Authorization": f"Token {token}"}
    project_json = requests.get(url, headers=headers)
    if project_json.status_code == 404:
        return project_json.status_code
    else:
        existing_file = ['None']
        json = project_json.json()
        files = list(json.keys())
        if 'reflectance' in files:
            existing_file = ['reflectance'] + existing_file

        return existing_file


def convert_and_upload(path, image_path, projectUid, post_urls_data, logger):
    image_name = image_path.split('\\')[-1]
    image_key = f"hawkai/{projectUid}/IR_rawimage/{image_name}"
    dpath = os.path.join(f'{path}', image_name)
    image = cv2.imread(image_path, 0)
    colormap = plt.get_cmap('inferno')
    heatmap = (colormap(image) * 2 ** 16)[:, :, :3].astype(np.uint16)
    heatmap = cv2.convertScaleAbs(heatmap, alpha=(255.0 / 65535.0))
    heatmap = cv2.cvtColor(heatmap, cv2.COLOR_RGB2BGR)
    if cv2.imwrite(dpath, heatmap):
        post_url = post_urls_data[image_key]["url"]
        post_data = post_urls_data[image_key]["fields"]
        files = {'file': open(dpath, 'rb')}
        requests.post(post_url, data=post_data, files=files)
        logger(f'Uploading Tagged Image {image_name}')
    else:
        logger("Unable to write inferno image ")


def upload(task, inputs):
    images = inputs['imageslist']
    image_path = inputs['img_dir']
    projectUid = inputs['projectUid']
    post_urls_data = inputs['post_urls_data']
    logger = inputs['logger']
    path = os.path.join(f'{image_path}', 'inferno_scale')

    if not os.path.exists(path):
        os.mkdir(path)

    for image in images:
        t = threading.Thread(target=convert_and_upload, args=(path, image, projectUid, post_urls_data, logger))
        t.start()

    if images:
        t.join()

    return {'num_images': len(images),
            'task': task.description()}


def get_presigned_post_urls(task, inputs):
    upload_image_list = inputs["imageslist"]
    # print(f"Upload images list: {upload_image_list}")
    org_uid = inputs["orgUid"]
    project_uid = inputs["projectUid"]
    core_token = inputs["core_token"]
    upload_keys = [f"hawkai/{project_uid}/IR_rawimage/{os.path.split(i)[-1]}" for i in upload_image_list]
    data = {"project_uid": project_uid, "organization": org_uid, "object_keys": upload_keys}
    # print(f"Data for presigned post urls: {data}")
    url = THERMAL_TAGGING_URL + "/presigned_post_urls"
    headers = {"Authorization": f"Token {core_token}"}
    response = requests.get(url, json=data, headers=headers).json()
    # print(f"Presigned post url response: {response}")
    return {'task': task.description(),
            'response': response}


def get_image_urls(task, inputs):
    token = inputs['token']
    data = inputs['data']
    image_urls = requests.get(THERMAL_TAGGING_URL + "/get_object_urls", headers={"Authorization": f"Token {token}"},
                              json=data).json()
    return {'task': task.description(),
            'image_urls': image_urls}


def fields_validator(required_fields, layer, application_type):
    required_fields = required_fields.get(application_type, {})
    layer.startEditing()
    fname = list(required_fields.keys())
    for field in fname:
        variant = required_fields[field]
        if layer.fields().indexFromName(field) == -1:
            if field == 'temperature_min' or field == 'temperature_max' or field == 'temperature_difference':  # creating decimal supporting fields type
                fieldz = QgsField(field, variant, "double", 10, 2)
            else:
                fieldz = QgsField(field, variant)
            layer.dataProvider().addAttributes([fieldz])
            layer.updateFields()  # update layer fields after creating new one
    layer.commitChanges()
    layer.startEditing()


def download_images(task, inputs):
    threads = []
    viewerobj, raw_images = inputs
    if not os.path.exists(viewerobj.images_dir):
        os.makedirs(viewerobj.images_dir)
    for r in raw_images:
        key = r["service"]["key"]
        viewerobj.marker_location.append(r['location'])
        url = viewerobj.image_urls.get(key, None)
        raw_image_name = re.sub(":", "_", key.split("/")[-1])
        save_path = os.path.join(viewerobj.images_dir, raw_image_name)
        viewerobj.image_paths.append(save_path)
        t = threading.Thread(target=viewerobj.download_image, args=(url, save_path))
        threads.append(t)

    # Start all threads
    for x in threads:
        x.start()

    # Wait for all of them to finish
    for x in threads:
        x.join()

    return {'task': task.description(),
            'status': 'Downloaded'}


def create_custom_label(vlayer, field_name):
    num_images_label = QgsPalLayerSettings()
    num_images_label.fieldName = field_name
    num_images_label.enabled = True
    num_images_label.centroidInside = True

    buffer = QgsTextBufferSettings()
    buffer.setColor(QColor('white'))
    buffer.setEnabled(True)
    buffer.setSize(1)

    textformat = QgsTextFormat()
    textformat.setFont(QFont("Arial", 12))
    textformat.setColor(QColor(0, 0, 255))
    textformat.setBuffer(buffer)

    num_images_label.setFormat(textformat)

    labeler = QgsVectorLayerSimpleLabeling(num_images_label)
    labeler.requiresAdvancedEffects()
    vlayer.setLabelsEnabled(True)
    vlayer.setLabeling(labeler)
    vlayer.triggerRepaint()


def save_edits(task, save_inputs):
    json_path = save_inputs['json_path']
    listType_dataFields = save_inputs['listType_dataFields']
    logger = save_inputs['logger']
    features = json.load(open(json_path))['features']
    cleaned_json = {"type": "FeatureCollection", "features": []}
    for feature in features:
        raw_image = feature['properties'].get('raw_images', None)
        parentUid = feature['properties'].get('parent_uid', None)
        attachment = feature['properties'].get('attachments', None)
        if feature['properties']['class_name'] != 'table':
            try:
                if parentUid:
                    parent_item = listType_dataFields.get(parentUid, None)
                    if parent_item:
                        parent_rawimages = parent_item.get('raw_images', [])
                else:
                    parent_rawimages = []

                if parentUid in listType_dataFields:
                    feature['properties']['raw_images'] = parent_rawimages
                    feature['properties']['attachments'] = parent_rawimages
                else:
                    if isinstance(raw_image, str) or not raw_image:
                        feature['properties']['raw_images'] = []
                    elif isinstance(raw_image, str) or not attachment:
                        feature['properties']['attachments'] = []

            except Exception:
                tb = traceback.format_exc()
                logger(str(tb), level=Qgis.Warning)

        if feature['geometry']['coordinates'][0]:
            cleaned_json["features"].append(feature)

    with open(json_path, "w") as fi:
        json.dump(cleaned_json, fi)

    return {'json_path': json_path, 'task': task.description()}


# asset level projects
class ProjectForm:
    def __init__(self, projects_dict, project_selection_layout, project_selection_window):
        self.project_groupbox = QtWidgets.QGroupBox('Projects:')
        self.myform = QtWidgets.QFormLayout()
        for project_uid, project_name in sorted(projects_dict.items(), key=lambda x: x[1]):
            button = QtWidgets.QPushButton(f'{project_name}')
            button.clicked.connect(partial(project_selection_window.update_selected_project, project_uid))
            self.myform.addRow(button)

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


class AssetLevelProjects(QtWidgets.QWidget):
    def __init__(self, img_tag_obj):
        super().__init__()
        self.img_tag_obj = img_tag_obj
        self.projects_form = None
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.project_selection_layout = QtWidgets.QVBoxLayout(self)
        self.setWindowTitle('Groups...')
        self.setupUi(self.img_tag_obj.project.group_dict)

    def setupUi(self, group_dict):
        self.group_details = {}
        for group_uid, group_obj in group_dict.items():
            self.group_details[group_obj.name] = (group_uid, group_obj.projects_details)
        group_list = list(self.group_details.keys())
        self.group_combobox = QComboBox(self)
        self.group = combobox_modifier(self.group_combobox, group_list)
        self.project_selection_layout.addWidget(self.group, 0, Qt.AlignTop)
        self.group.currentIndexChanged.connect(self.group_tree)
        self.project_details = self.group_details[self.group.currentText()][1]
        self.projects_form = ProjectForm(self.project_details, self.project_selection_layout, self)

    def group_tree(self):
        self.group_uid = self.group_details[self.group.currentText()][0]
        self.project_details = self.group_details[self.group.currentText()][1]
        self.projects_form = ProjectForm(self.project_details, self.project_selection_layout, self)

    def update_selected_project(self, project_uid):
        clicked_button = self.sender()
        self.img_tag_obj.addl_uid = project_uid
        self.img_tag_obj.addl_projectuid.setText(f'{clicked_button.text()}')
        self.img_tag_obj.addl_projectuid.setReadOnly(True)
        self.hide()


def containers_details(task, asset_uid, org_uid, core_token):
    url = CORE_URL + f'/api/v1/containers/?asset={asset_uid}&groups=true&labels=true&page=1&page_size=1000&search=&users=true&organization={org_uid}'
    headers = {"Authorization": f"Token {core_token}"}
    response = requests.get(url, headers=headers)
    containers = response.json()['results']
    containers_dict = {}
    for container in containers:
        groups = container['groups']
        container_name = container['name']
        container_level_groups = [group['name'] for group in
                                  groups]  # app_type [{'uid':1,'name':'Thermal analaysis','application':{'uid': 2, 'name': 'therm', 'label': 'Thermal'},{}]
        containers_dict[container['uid']] = {'name': container_name, 'groups': container_level_groups,
                                             'applications_info': container['app_types']}

    return {'containers_dict': containers_dict, 'task': task.description()}


def download_asset_logo(asset_name, url):
    d_path = str(Path.home() / "Downloads")
    path = os.path.join(d_path + '\\' + 'Sensehawk_plugin' + '\\' + asset_name)
    if not os.path.exists(path):
        os.makedirs(path)
    logo_name = asset_name + '.png'
    asset_logo_path = os.path.join(path, logo_name)
    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(asset_logo_path, 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)

    return asset_logo_path


def features_to_polygons(features):
    polygon_features = []
    for f in features:
        if "class" not in f["properties"].keys():
            f["properties"]["class"] = None
        if f["geometry"]["type"] in ["MultiPolygon", "Polygon"]:
            polygon_features.append(f)
        elif f["geometry"]["type"] in ["MultiLineString"]:
            coords = f["geometry"]["coordinates"]
            ml = MultiLineString(coords)
            # Remove
            ml = transform(lambda x, y, z=None: (x, y), ml)
            p = mapping(Polygon(ml.convex_hull))
            f = {
                "type": "Feature",
                "properties": {},
                "geometry": p
            }
            polygon_features.append(f)
    return polygon_features


def load_yaml_file(yaml_path: str):
    assert os.path.exists(yaml_path), f'{yaml_path} not exists'
    # Read YAML file
    with open(yaml_path, 'r') as stream:
        data_loaded = yaml.safe_load(stream)
    return data_loaded
