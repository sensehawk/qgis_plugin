# from ..data_model import ConfigModel, InferenceConfigModel
import os

from ..utils import load_yaml_file
from ..constants import SCM_INFERENCE_URL, SCM_TRAIN_URL, SCMAPP_URL
import requests
from .core_apis import get_project_details, get_project_geojson, get_project_reports, get_reports_url
from .terra_apis import get_terra_classmaps, get_project_data


def get_models_list(project_uid:str,core_token:str):
    params = {"project_uid": project_uid}
    headers = {"Authorization": f"Token {core_token}"}
    response = requests.get(SCMAPP_URL + "/list-models", headers=headers, params=params)
    return response.json()


def train(task, train_inputs):
    project_details, geojson, ml_service_map, class_maps, user_email, core_token, logger = train_inputs

    project_uid = project_details.get("uid", None)
    ortho_url = get_project_reports(project_uid, core_token).get("ortho", None)

    if not ortho_url:
        return {"task": task.description(), "status": f"ortho_url: {ortho_url} invalid"}

    request_body = {
        'project_uids': [project_uid],
        'val_project_uids': [project_uid],
        'email': user_email,
        'ml_service_map': ml_service_map,
        'class_maps': class_maps
    }
    try:
        yaml_path = os.path.join(os.path.dirname(__file__), '../config/service_map_training.yaml')
        config_json = load_yaml_file(yaml_path=yaml_path)
        logger('Loaded Yaml to JSON')

        # update target
        for index in range(len(config_json["detection"])):
            config_json["detection"][index]["target"] = list(ml_service_map["detection"])
        seg_ml_service_map = sorted(ml_service_map["segmentation"])
        for index in range(len(config_json["segmentation"])):
            if index < len(seg_ml_service_map):
                config_json["segmentation"][index]["target"] = seg_ml_service_map[index]
            else:
                config_json["segmentation"][index]["target"] = ""

        logger("Added MLService")

        config_json.update(**request_body)
        logger('Updated config')

        train_config_payload = config_json # ConfigModel(**config_json).model_dump_json()
        logger("Got the Config as per Payload")
    except AssertionError as ae:
        logger(f'Path not exists: {ae}')
        return {"task": task.description(), "status": 'Path not exists'}

    headers = {"Authorization": f"Token {core_token}"}
    response = requests.request("POST", SCMAPP_URL + "/train", json=train_config_payload, headers=headers)
    return {"task": task.description(), "status": response.status_code}

def detect(project_details, geojson, model_registry_name, user_email, core_token, logger):
    project_uid = project_details.get("uid", None)
    logger(f'Detect {project_uid} called ...')

    ortho_report = {}
    for report in project_details.get('reports'):
        if report.get('report_type') == 'ortho':
            ortho_report = report.get('service')
    ortho_url = get_reports_url(ortho_report.get('bucket'),
                                ortho_report.get('key'),
                                ortho_report.get('region'),
                                core_token)
    if not ortho_url:
        return {"task": "get ortho-url detect() failed",
                "Exception": f"ortho_url: {ortho_url} invalid",
                "status": 404}


    yaml_path = os.path.join(os.path.dirname(__file__), '../config/inference.yaml')
    config_json = load_yaml_file(yaml_path=yaml_path)
    logger('Config YAML to JSON')

    new_data = {
        "project_uid": project_uid,
        "email": user_email,
        "geo_json": geojson,
        "ortho_url": ortho_url
    }
    config_json.update(**new_data)
    config_json["inference"]["detection"]["model_registry_name"] = model_registry_name
    logger('Updated Config')

    infer_config_payload = config_json  # InferenceConfigModel(**config_json).model_dump_json()
    logger("Got the Config as per Payload")

    headers = {"Authorization": f"Token {core_token}"}
    response = requests.post(SCMAPP_URL + '/predict', json=infer_config_payload, headers=headers)
    return {"task": "Detect",
            "Exception": "",
            "status": response.status_code}


def approve(project_details, geojson, user_email, core_token):
    project_uid = project_details.get("uid")
    headers = {"Authorization": f"Token {core_token}"}
    response = requests.post(SCMAPP_URL + '/approve', params={"project_uid": project_uid}, headers=headers)
    return response.json()
