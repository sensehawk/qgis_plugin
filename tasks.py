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
from .windows.nextracker.utils import setup_nextracker_features, nextracker_org_uid


def project_loadtask(task, load_inputs):
    try:
        project_uid = load_inputs.get("project_uid", None)
        project_type = load_inputs.get("project_type", None)
        core_token = load_inputs.get("core_token", None)
        logger = load_inputs.get("logger", None)
        org_uid = load_inputs.get("org_uid", None)
        container_uid = load_inputs.get('container_uid', None)
        reload = load_inputs.get('reload', None)
        # Get project details from core
        project_details = get_project_details(project_uid, core_token)
        project_details["project_type"] = project_type
        # Get the class maps for vectors from terra / therm
        if not reload :
            if project_type == "terra":
                if org_uid == nextracker_org_uid:
                    logger("Nextracker project")
                    setup_nextracker_features(container_uid, core_token)
                    logger("Nextracker features setup complete")
                class_maps, class_groups = get_terra_classmaps(project_details, core_token)
                existing_files = None
                container_class_map = {}
            elif project_type == "therm":
                class_maps, container_class_map = get_therm_classmaps(core_token, org_uid, container_uid)
                class_groups = None
                org = project_details['organization']['uid']
                existing_files = file_existent(project_uid,org,core_token)

            # Load orthotiles
            # Get base url for ortho tiles
            base_orthotiles_url = get_ortho_tiles_url(project_uid, core_token)
            print("Ortho tile url", base_orthotiles_url)
            # Get metadata from the base url
            ortho_tiles_details = requests.request("GET", base_orthotiles_url).json()
            ortho_bounds = ortho_tiles_details["bounds"]
           
            zmax = ortho_tiles_details["maxzoom"]
            zmin = 1

            orthotiles_url = "type=xyz&url=" + \
                            base_orthotiles_url + "/{z}/{x}/{y}.png" + \
                            "&zmax={}&zmin={}".format(zmax, zmin)
            print(orthotiles_url)
        else:
            orthotiles_url, class_maps, class_groups, existing_files, container_class_map = None, None, None, None, None
            ortho_bounds = load_inputs['bounds']
            logger('Fetching json from core for the existing project')

        geojson_path = load_vectors(project_details,
                                            project_type,
                                            ortho_bounds,
                                            core_token,
                                            logger)

    except Exception:
        tb = traceback.format_exc()
        logger(str(tb), level=Qgis.Warning)
        return False
    
    return {'rlayer_url': orthotiles_url,
            'project_uid': project_uid,
            'class_maps': class_maps,
            'class_groups': class_groups,
            'project_details': project_details,
            'geojson_path': geojson_path,
            'existing_files':existing_files,
            'container_class_map':container_class_map,
            'bounds':ortho_bounds,
            'container_uid':container_uid,
            'container_name':load_inputs.get("container_name",None),
            'task': task.description()}


def clip_request(task, clip_task_input):
    """
    Sends clip request to the AWS lambda clip function
    """
    project_uid= clip_task_input['project_uid']
    geojson_path = clip_task_input['geojson_path']
    class_maps = clip_task_input['class_maps']
    core_token = clip_task_input['core_token']
    project_type = clip_task_input['project_type'] 
    user_email = clip_task_input['user_email']
    convert_to_magma = clip_task_input['convert_to_magma']
    group_uid = clip_task_input.get('group_uid', None)
    logger = clip_task_input.get("logger", None)
    container_uid = clip_task_input.get("container_uid", None)
    org_uid = clip_task_input.get("org_uid", None)
    
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
            if properties["class_name"] == clip_boundary_class_name or properties["class"] == clip_boundary_class_name:
                name = properties.get("name", None)
                all_clip_feature_names.append(name)
        n_clip_features = len(all_clip_feature_names)
        n_unique_clip_names = len(list(set(all_clip_feature_names)))

        # If there are no unique clip feature names or if any of them has None
        if n_clip_features != n_unique_clip_names or None in all_clip_feature_names:
            return {"task": task.description(), "title": 'Need unique clip boundary names',
                    "description": "Please provide unique name property to all clip_boundary features before clipping..."}

        ortho_url, dsm_url = get_project_reports(project_uid, container_uid, org_uid,  core_token)

        if not ortho_url:
            return {"task": task.description(), "title": "Ortho doesn't exist",
                    "description": "No ortho found for project..."}
        
        if not dsm_url:
            return {"task": task.description(), "title": "DSM doesn't exist",
                    "description": "No DSM found for project..."}

        print(ortho_url, dsm_url)
        request_body = {"project_uid": project_uid,
                        "raster_url": ortho_url,
                        "dsm_url":dsm_url,
                        "geojson": geojson,
                        "clip_boundary_class_name": clip_boundary_class_name,
                        "project_type": project_type,
                        "email_id": user_email,
                        "convert_to_magma": convert_to_magma,
                        "group_uid": group_uid}
        
        
        headers = {"Authorization": f"Token {core_token}"}
        response = requests.post(CLIP_FUNCTION_URL+'/clip-raster', headers=headers, json=request_body)
        res_status = response.status_code
        res_title, res_description = response.json()['title'], response.json()['description']

    except Exception:
        logger(traceback.format_exc())
    return {"task": task.description(), 'title':res_title, 'description':res_description, 'res_status':res_status}

def logintask(task, login_window):
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
    project_details, geojson, model_details, user_email, core_token,logger = detection_task_input
    try:
        return detect(project_details, geojson, model_details, user_email, core_token,logger)
    except Exception as e:
        return {"task": task.description(), "Exception": e, "success": 404}

def approveTask(task, approve_task_input):
    project_details, geojson, user_email, core_token = approve_task_input
    try:
        approve(project_details, geojson, user_email, core_token)
        return {"task": task.description(), "Exception": None, "success": True}
    except Exception as e:
        return {"task": task.description(), "Exception": e, "success": False}


