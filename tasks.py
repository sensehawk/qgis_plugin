from qgis.core import QgsTask, QgsApplication, Qgis, QgsRasterLayer, QgsField
from .sensehawk_apis.terra_apis import get_terra_classmaps, get_project_data
from.sensehawk_apis.therm_apis import get_therm_classmaps
from .sensehawk_apis.core_apis import get_ortho_tiles_url, get_ortho_url, core_login, get_project_geojson, get_project_reports, get_project_details
from .sensehawk_apis.scm_apis import detect, approve
from .utils import load_vectors, file_existent, organization_details, download_ortho
import requests
from pathlib import Path
from .constants import CLIP_FUNCTION_URL
import json
import traceback
import os
import tempfile
import urllib

def loadTask(task, load_inputs):
    try:
        project_uid = load_inputs.get("project_uid", None)
        project_type = load_inputs.get("project_type", None)
        core_token = load_inputs.get("core_token", None)
        logger = load_inputs.get("logger", None)
        org_uid = load_inputs.get("org_uid", None)
        container_uid = load_inputs.get('container_uid', None)
        # Get project details from core
        project_details = get_project_details(project_uid, core_token)
        project_details["project_type"] = project_type
        # Get the class maps for vectors from terra / therm
        if project_type == "terra":
            class_maps, class_groups = get_terra_classmaps(project_details, core_token)
            existing_files = None
        elif project_type == "therm":
            class_maps, class_groups = get_therm_classmaps(core_token, org_uid, container_uid), None
            org = project_details['organization']['uid']
            existing_files = file_existent(project_uid,org,core_token)

####################################
        # Load orthotiles
        # Get base url for ortho tiles
        base_orthotiles_url = get_ortho_tiles_url(project_uid, core_token)

        # Get metadata from the base url
        ortho_tiles_details = requests.request("GET", base_orthotiles_url).json()
        ortho_bounds = ortho_tiles_details["bounds"]
        bounds = ortho_bounds

        # zmax = ortho_tiles_details["maxzoom"]
        # zmin = 1

        # orthotiles_url = "type=xyz&url=" + \
        #                  base_orthotiles_url + "/{z}/{x}/{y}.png" + \
        #                  "&zmax={}&zmin={}".format(zmax, zmin)
        # print(orthotiles_url)
        # # Load ortho tiles from url
        # rlayer = QgsRasterLayer(orthotiles_url, project_uid + "_ortho", 'wms')
########################################   

        # Load Rasters
        ortho_url = get_ortho_url(project_uid, org, core_token)["ortho"]
        ortho_size = urllib.request.urlopen(ortho_url)
        dpath = str(Path.home() / "Downloads")
        rpath = os.path.join(dpath+'\\'+'Sensehawk_plugin'+'\\'+project_details['asset']['name']+'\\'+project_details['group']['name'])
        number_of_threads = 20
        # check for folder existent
        if not os.path.exists(rpath):
            os.makedirs(rpath)
        ortho_path = os.path.join(rpath+'\\'+project_details['name']+'.tiff')

        if not os.path.exists(ortho_path) or os.path.getsize(ortho_path) != ortho_size.length:
            logger(f"Downloading {project_details['name']} ortho ...")
            download_ortho(ortho_size.length, number_of_threads, ortho_path, ortho_url)

        rlayer = QgsRasterLayer(ortho_path, project_details['name'] + "_ortho")

        # Load vectors
    
        geojson_path = load_vectors(project_details,
                                            project_type,
                                            bounds,
                                            core_token,
                                            logger)

    except Exception as e:
        tb = traceback.format_exc()
        logger(str(tb), level=Qgis.Warning)
        return False

    return {'rlayer': rlayer,
            'project_uid': project_uid,
            'class_maps': class_maps,
            'class_groups': class_groups,
            'project_details': project_details,
            'geojson_path': geojson_path,
            'existing_files':existing_files,
            'task': task.description()}


def clipRequest(task, clip_task_input):
    """
    Sends clip request to the AWS lambda clip function
    """
    project_details = clip_task_input['project_details']
    geojson_path = clip_task_input['geojson_path']
    class_maps = clip_task_input['class_maps']
    core_token = clip_task_input['core_token']
    project_type = clip_task_input['project_type'] 
    user_email = clip_task_input['user_email']
    convert_to_magma = clip_task_input['convert_to_magma']

    clip_boundary_class_name = None
    # Get the class_name for clip_boundary
    if project_type == 'therm':
        clip_boundary_class_name = 'clip_boundary'
    else:
        for i in class_maps.keys():
            if i.lower() == "clip_boundary":
                clip_boundary_class_name = class_maps[i]["uid"]
   
    if not clip_boundary_class_name:
        return {"task": task.description(), "success": False,
                "message": "Please add clip_boundary feature type in class maps..."}
    # Updated geojson
    with open(geojson_path, "r") as fi:
        geojson = json.load(fi)
    try:

        all_clip_feature_names = []

        for f in geojson["features"]:
            properties = f["properties"]
            if properties["class_name"] == clip_boundary_class_name:
                name = properties.get("name", None)
                all_clip_feature_names.append(name)
        n_clip_features = len(all_clip_feature_names)
        n_unique_clip_names = len(list(set(all_clip_feature_names)))

        # If there are no unique clip feature names or if any of them has None
        if n_clip_features != n_unique_clip_names or None in all_clip_feature_names:
            return {"task": task.description(), "title": 'Need unique clip boundary names',
                    "description": "Please provide unique name property to all clip_boundary features before clipping...", 'level':Qgis.Warning}

        ortho_url = get_project_reports(project_details.get("uid", None), core_token).get("ortho", None)
        if not ortho_url:
            return {"task": task.description(), "title": "Ortho doesn't exist",
                    "description": "No ortho found for project...", 'level':Qgis.Warning}
        
        request_body = {"project_uid": project_details.get("uid", None),
                        "raster_url": ortho_url,
                        "geojson": geojson,
                        "clip_boundary_class_name": clip_boundary_class_name,
                        "project_type": project_type,
                        "email_id": user_email,
                        "convert_to_magma": convert_to_magma}

        headers = {"Authorization": f"Token {core_token}"}
        response = requests.post(CLIP_FUNCTION_URL+'/clip-raster', headers=headers, json=request_body)
        res_status = response.status_code
        res_title, res_description = response.json()['title'], response.json()['description']
    except Exception:
        print(traceback.format_exc())
    return {"task": task.description(), 'title':res_title, 'description':res_description, 'res_status':res_status}

def loginTask(task, login_window):
    login_window.user_email = login_window.userName.text()
    login_window.user_password = login_window.userPassword.text()

    login_window.logger('Logging in SenseHawk user {}...'.format(login_window.user_email))

    if not login_window.user_email or not login_window.user_password:
        login_window.logger('User email or Password empty...',level=Qgis.Warning)
        return None
    
    login_window.core_token = core_login(login_window.user_email, login_window.user_password, login_window.logger)
    login_window.org_details = organization_details(login_window.core_token)
    if login_window.core_token:
        login_window.logger("Successfully logged in...")
        return {"login_window": login_window, "task": task.description()}
    else:
        login_window.logger("incorrect user email or password...", level=Qgis.Warning)
        return None

def detectionTask(task, detection_task_input):
    project_details, geojson, model_details, user_email, core_token = detection_task_input
    try:
        detect(project_details, geojson, model_details, user_email, core_token)
        return {"task": task.description(), "Exception": None, "success": True}
    except Exception as e:
        return {"task": task.description(), "Exception": e, "success": False}

def approveTask(task, approve_task_input):
    project_details, geojson, user_email, core_token = approve_task_input
    try:
        approve(project_details, geojson, user_email, core_token)
        return {"task": task.description(), "Exception": None, "success": True}
    except Exception as e:
        return {"task": task.description(), "Exception": e, "success": False}


