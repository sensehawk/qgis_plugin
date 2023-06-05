import requests
from urllib.request import urlopen
import os
import math
from .sensehawk_apis.core_apis import get_project_geojson, save_project_geojson, get_project_details
import json
from qgis.core import QgsMessageLog, Qgis, QgsProject, QgsMapLayer, QgsRasterLayer, QgsVectorLayer
import qgis
from qgis.utils import iface
from qgis.core import *
import qgis.utils
import tempfile
import random
import tempfile
from .constants import THERM_URL
from PyQt5.QtWidgets import  QCompleter
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import Qt




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


def download_file(url, logger, output_path=None, directory_path=None):
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
    random_color_pick = (["#" + ''.join([random.choice('0123456789ABCDEF') for j in range(6)])])
    color = ''
    for i in random_color_pick:
        color += i
    return color


def categorize_layer(project_type=None, class_maps=None):
    renderer = categorized_renderer(project_type=project_type, class_maps=class_maps)
    active_layer = iface.activeLayer()
    active_layer.setRenderer(renderer)
    active_layer.triggerRepaint()
    return renderer

def categorized_renderer(project_type=None, class_maps=None):
    # color classifying based on class_name for therm / class_name and class_maps for terra
    if not class_maps:
        color_code = {'hotspot': '#001c63', 'diode_failure': '#42e9de', 'module_failure': '#2ecc71',
                      'string_failure': '#3ded2d', 'module_reverse_polarity': '#ff84dc',
                      'potential_induced_degradation': '#550487', 'vegetation': '#076e0a',
                      'tracker_malfunction': '#c50000', 'string_reverse_polarity': '#f531bd',
                      'dirt': '#b5b0b0', 'cracked_modules': '#9b9e33', 'table': '#ffff00'}
    else:
        color_code = {
            i: class_maps[i]["properties"]["color"].replace("rgb(", "").replace(")", "").replace(" ", "").split(",") for
            i in class_maps}
        color_code = {i: "#%02x%02x%02x" % tuple(int(x) for x in color_code[i]) for i in color_code}

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
    if project_type == "terra":
        renderer = QgsCategorizedSymbolRenderer('class', categories)
    elif project_type == "therm":
        renderer = QgsCategorizedSymbolRenderer('class_name', categories)

    return renderer


def load_vectors(project_details, project_type, raster_bounds, core_token, logger):
    project_uid = project_details["uid"]

    # Download vectors
    geojson = get_project_geojson(project_uid, core_token, project_type=project_type)
    if "features" not in geojson:
        logger(str(geojson), level=Qgis.Warning)

    if not geojson["features"]:
        # Create an extent feature if no feature exists
        extent_geometry = json.loads(QgsGeometry.fromRect(QgsRectangle(raster_bounds[0],
                                                                       raster_bounds[1],
                                                                       raster_bounds[2],
                                                                       raster_bounds[3])).asJson())
        extent_feature = {"type": "Feature",
                          "properties": {"name": "Ortho Extent", "class_name": None, "class_id": None, "class": None},
                          "geometry": extent_geometry, "workflow": {}}
        geojson["features"] += [extent_feature]

    # Save geojson
    geojson_path = os.path.join(tempfile.gettempdir(), "{}.geojson".format(project_uid))
    with open(geojson_path, "w") as fi:
        json.dump(geojson, fi)

    logger("Saving project geojson...")

    # Load vectors
    vlayer = QgsVectorLayer(geojson_path, geojson_path, "ogr")

    # Get feature count by class_name
    feature_count_dict = {}
    class_name_keyword = {"terra": "class", "therm": "class_name"}[project_type]
    for f in geojson["features"]:
        feature_class = f["properties"].get(class_name_keyword, None)
        if not feature_class:
            continue
        class_count = feature_count_dict.get(feature_class, 0)
        class_count += 1
        feature_count_dict[feature_class] = class_count

    feature_count_list = [(k, v) for k, v in feature_count_dict.items()]

    return vlayer, geojson_path, feature_count_list

def project_details( group, org, token):
    url = f'https://core-server.sensehawk.com/api/v1/groups/{group}/projects/?reports=true&page=1&page_size=10&organization={org}'
    headers = {"Authorization": f"Token {token}"}
    response = requests.get(url, headers=headers)
    project_details = response.json()['results']
    project_list = {}
    for project in project_details:
        project_list[project['name']] = project['uid']

    return project_list    
    # return {'project_list':project_list,
            # 'task':task.description()}


def group_details(asset, org, token):
    url = f'https://core-server.sensehawk.com/api/v1/groups/?asset={asset}&projects=true&page=1&page_size=10&organization={org}'
    headers = {"Authorization": f"Token {token}"}
    response = requests.get(url, headers=headers)
    group_details = response.json()['results']
    group_list = {}
    for group in group_details:
        project_details = {}
        for projects in group['projects']:
            project_details[projects['name']] = projects['uid']
        group_list[group['name']] = (group['uid'], project_details)
    return group_list


def asset_details(task ,org, token): # fetching asset and org_container details 
    url = f'https://api.sensehawk.com/v1/assets/?organization={org}'
    headers = {"Authorization": f"Token {token}"}
    response = requests.get(url, headers=headers)
    asset_details = response.json()['assets']
    asset_list = {}
    for asset in asset_details:
        asset_list[asset['name']] = asset['uid']
    
    container_url =f'https://core-server.sensehawk.com/api/v1/containers/?groups=true&page=1&page_size=10&organization={org}'
    container_response = requests.get(container_url, headers=headers)
    org_contianer_details = container_response.json()['results']

    return {'asset_list': asset_list,
            'org_contianer_details':org_contianer_details,
            'task': task.description()}


def organization_details(token):
    url = 'https://api.sensehawk.com/v1/organizations/?limit=9007199254740991&page=1'
    headers = {"Authorization": f"Token {token}"}
    response = requests.get(url, headers=headers)
    org_details = response.json()['organizations']
    org_list = {}
    for org in org_details:
        org_list[org['name']] = org['uid']

    return org_list

def file_existent(project_uid, org, token):
    url  = f'{THERM_URL}/projects/{project_uid}/data?organization={org}'
    headers = {"Authorization": f"Token {token}"}
    project_json = requests.get(url, headers=headers)
    if project_json.status_code == 404:
        return project_json.status_code
    else:
        existing_file = ['None']
        json = project_json.json()
        files = list(json.keys())
        if 'ortho' in files:
            existing_file =  ['ortho'] + existing_file
        if 'reflectance' in files:
           existing_file =  ['reflectance'] + existing_file

        return existing_file