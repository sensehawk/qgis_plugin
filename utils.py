try :
    from .windows.packages.cv2 import cv2
except Exception:
    import cv2
import requests
from urllib.request import urlopen
import os
from .sensehawk_apis.core_apis import get_project_geojson
import json
from qgis.core import Qgis, QgsVectorLayer, QgsField
from qgis.utils import iface
from qgis.core import *
import tempfile
import random
import tempfile
from .constants import THERM_URL, THERMAL_TAGGING_URL, CORE_URL, API_SENSEHAWK
from PyQt5.QtWidgets import  QCompleter
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import Qt
from .windows.packages.exiftool.exiftool import ExifTool
from datetime import datetime
import glob
import threading
import matplotlib.pyplot as plt 
import numpy as np
import traceback

exiftool_path = os.path.join(os.path.dirname(__file__), "windows\exiftool.exe")

def sort_images(task, images_dir, logger, reverse=False):
    try:
        logger('Strated sorting images datataken wise')
        images = glob.glob(images_dir+"\*")
        supported_image_formats = ('.jpg','.JPG','.tiff','.tif','.TIFF','.TIF')
        images = [i for i in images if i.endswith(supported_image_formats)]
        with ExifTool(exiftool_path) as e:
            time_stamps = []
            for i in images:
                m = e.get_metadata(i)
                m = {k.split(":")[1]: m[k] for k in m if ":" in k}
                t = m["DateTimeOriginal"]
                try:
                    t = datetime.strptime(t, "%Y:%m:%d  %H:%M:%S")
                except Exception:
                    try:
                        t = datetime.strptime(t.split(".")[0], "%Y:%m:%d  %H:%M:%S")
                    except Exception:
                        t = datetime.strptime(t, "%H:%M:%S")
                time_stamps.append(t)
        sorted_tuples = sorted(zip(time_stamps, images), reverse=reverse)
        images = [i[1] for i in sorted_tuples]
        timestamps = [i[0] for i in sorted_tuples]
    except Exception as e:
        dt = traceback.format_exc()
        logger(f'Error:{e}', extra={"traceback": dt})

    return {'sorted_images':images,
            'sorted_timestamps':timestamps,
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
    if "features" not in geojson:
        logger(str(geojson), level=Qgis.Warning)

    if not geojson["features"]:
        # Create an extent feature if no feature exists
        extent_geometry = json.loads(QgsGeometry.fromRect(QgsRectangle(raster_bounds[0],
                                                                       raster_bounds[1],
                                                                       raster_bounds[2],
                                                                       raster_bounds[3])).asJson())
        extent_feature = {"type": "Feature",
                          "properties": {"name": "Ortho Extent", "class_name": None, "class_id": None, "class": None, "uid": None},
                          "geometry": extent_geometry, "workflow": {}}
        geojson["features"] += [extent_feature]

    # Save geojson
    geojson_path = os.path.join(tempfile.gettempdir(), "{}.geojson".format(project_uid))
    with open(geojson_path, "w") as fi:
        json.dump(geojson, fi)

    logger("Saving project geojson...")

    return geojson_path

def project_details( group, org, token):
    url = CORE_URL + f'/api/v1/groups/{group}/projects/?reports=true&page=1&page_size=10&organization={org}'
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
    url = CORE_URL + f'/api/v1/groups/?asset={asset}&projects=true&page=1&page_size=10&organization={org}'
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
    url = API_SENSEHAWK + f'/v1/assets/?organization={org}'
    headers = {"Authorization": f"Token {token}"}
    response = requests.get(url, headers=headers)
    asset_details = response.json()['assets']
    asset_list = {}
    for asset in asset_details:
        asset_list[asset['name']] = asset['uid']
    
    container_url = CORE_URL + f'/api/v1/containers/?groups=true&page=1&page_size=10&organization={org}'
    container_response = requests.get(container_url, headers=headers)
    org_contianer_details = container_response.json()['results']

    return {'asset_list': asset_list,
            'org_contianer_details':org_contianer_details,
            'task': task.description()}


def organization_details(token):
    url = API_SENSEHAWK + '/v1/organizations/?limit=9007199254740991&page=1'
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

def convert_and_upload(path, image_path, projectUid, post_urls_data):
    image_name = image_path.split('/')[-1]
    image_key = f"hawkai/{projectUid}/IR_rawimage/{image_name}"
    dpath = os.path.join(f'{path}', image_name)
    image = cv2.imread(image_path, 0)
    colormap = plt.get_cmap('inferno')
    heatmap = (colormap(image) * 2**16)[:,:,:3].astype(np.uint16)
    heatmap = cv2.convertScaleAbs(heatmap, alpha=(255.0/65535.0))
    heatmap = cv2.cvtColor(heatmap, cv2.COLOR_RGB2BGR)
    if cv2.imwrite(dpath, heatmap):
        post_url = post_urls_data[image_key]["url"]
        post_data = post_urls_data[image_key]["fields"]
        files = {'file': open(dpath, 'rb')}
        requests.post(post_url, data=post_data, files=files)
    else:
        print("Unable to write inferno image")

def upload(task ,inputs):
    images = inputs['imageslist']
    image_path = inputs['img_dir']
    projectUid = inputs['projectUid']
    post_urls_data = inputs['post_urls_data']
    path = os.path.join(f'{image_path}', 'inferno_scale')

    if not os.path.exists(path):
        os.mkdir(path)

    for image in images:
        print(image)
        t = threading.Thread(target=convert_and_upload, args=(path, image, projectUid, post_urls_data))
        t.start()
    
    if images:
        t.join()

    return {'num_images':len(images),
            'task': task.description()}

def get_presigned_post_urls(task, inputs):
    upload_image_list = inputs["imageslist"]
    org_uid = inputs["orgUid"]
    project_uid = inputs["projectUid"]
    core_token = inputs["core_token"]
    upload_keys = [f"hawkai/{project_uid}/IR_rawimage/{i.split('/')[-1]}" for i in upload_image_list]
    data = {"project_uid": project_uid, "organization": org_uid, "object_keys": upload_keys}
    url = THERMAL_TAGGING_URL + "/presigned_post_urls"
    headers = {"Authorization": f"Token {core_token}"}
    response = requests.get(url, json=data, headers=headers).json()
    return {'task': task.description(),
            'response': response}

def get_image_urls(task , inputs):
    token  = inputs['token']
    data = inputs['data']
    image_urls = requests.get(THERMAL_TAGGING_URL+"/get_object_urls", headers={"Authorization": f"Token {token}"}, json=data).json()
    return {'task':task.description(),
            'image_urls':image_urls}

def fields_validator(required_fields, layer):
        layer.startEditing()
        fname = list(required_fields.keys())
        for field in fname:
            variant = required_fields[field]
            if layer.fields().indexFromName(field) == -1:
                fieldz = QgsField(field , variant)
                layer.dataProvider().addAttributes([fieldz])
                layer.updateFields() # update layer fields after creating new one
        layer.commitChanges()
        layer.startEditing()