from ..constants import SCM_INFERENCE_URL, SCM_TRAIN_URL
import requests
from .core_apis import get_project_details, get_project_geojson, get_project_reports
from .terra_apis import get_terra_classmaps, get_project_data


def get_models_list(project_uid, core_token):
    url = SCM_INFERENCE_URL + "/list-models"
    params = {"project_uid": project_uid}
    headers = {"Authorization": f"Token {core_token}"}
    response = requests.request("GET", url, headers=headers, params=params)
    return response.json()

def train(task, train_inputs):
    project_details, geojson, ml_service_map, class_maps, user_email, core_token = train_inputs
    url = SCM_TRAIN_URL + "/train"
    project_uid = project_details.get("uid", None)
    ortho_url = get_project_reports(project_details, core_token).get("ortho", None)
    if not project_uid or not ortho_url:
        return {"task": task.description(), "status": "project_uid or ortho_url invalid"}
    request_body = {"data": {"ortho": ortho_url}, "train_geojson": geojson,
                    "details": {"projectUID": project_uid, "user_email": user_email, "class_maps": class_maps},
                    "ml_service_map": ml_service_map}
    headers = {"Authorization": f"Token {core_token}"}
    response = requests.request("POST", url, json=request_body, headers=headers)
    return {"task": task.description(), "status": response.status_code}


def detect(project_details, geojson, model_details, user_email, core_token):
    url = SCM_INFERENCE_URL + "/predict"
    model_name, models_url = model_details
    project_uid = project_details.get("uid", None)
    ortho_url = get_project_reports(project_details, core_token).get("ortho", None)
    if not project_uid or not ortho_url:
        return None
    request_body = {"data": {"ortho": ortho_url, "ml_models": models_url, "model_name": model_name},
                    "details": {"project_uid": project_uid, "user_email": user_email},
                    "geojson": geojson
                    }
    headers = {"Authorization": f"Token {core_token}"}
    response = requests.request("POST", url, json=request_body, headers=headers).json()
    return response


def approve(project_details, geojson, user_email, core_token):
    url = SCM_INFERENCE_URL + "/approve"
    request_body = {"details": {"user_email": user_email, "project_uid": project_details.get("uid", None)},
                    "geojson": geojson
                    }
    headers = {"Authorization": f"Token {core_token}"}
    response = requests.request("POST", url, headers=headers, json=request_body)
    return response.json()

