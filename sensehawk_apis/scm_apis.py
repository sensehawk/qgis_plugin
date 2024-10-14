import os
import requests

from ..utils import load_yaml_file
from .core_apis import get_project_details, get_project_geojson, get_project_reports, get_reports_url
from .terra_apis import get_terra_classmaps, get_project_data



def detect(project_details, geojson, model_registry_name, user_email, core_token, logger):
    project_uid = project_details.get("uid", None)
    logger(f'Detect {project_uid} called ...')

    ortho_report = {}
    for report in project_details.get('reports'):
        if report.get('report_type') == 'ortho':
            ortho_report = report.get('service')
    ortho_url = get_reports_url(ortho_report.get('bucket'),
                                ortho_report.get('key'),
                                ortho_report.get('region'))
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
    response = requests.post('test' + '/predict', json=infer_config_payload, headers=headers)
    return {"task": "Detect",
            "Exception": "",
            "status": response.status_code}

