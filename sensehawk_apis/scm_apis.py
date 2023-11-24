from ..constants import SCM_INFERENCE_URL,SCMAPP_URL
import requests

def get_models_list(project_uid, core_token):
    url = SCM_INFERENCE_URL + "/list-models"
    params = {"project_uid": project_uid}
    headers = {"Authorization": f"Token {core_token}"}
    response = requests.request("GET", url, headers=headers, params=params)
    return response.json()


def train(task, train_inputs):
    project_details, geojson, ml_service_map, class_maps, user_email, core_token = train_inputs
    project_uid = project_details.get("uid", None)
    request_body = {
        'project_uids': [project_uid],
        'val_project_uids': [project_uid],
        'email': user_email,

        'ml_service_map': ml_service_map,
        'class_maps': class_maps,
    }

    headers = {"Authorization": f"Token {core_token}"}
    response = requests.post(SCMAPP_URL + '/train', json=request_body, headers=headers)
    # assert response.status_code == 202
    return {"task": task.description(), "status": response.status_code}


def detect(project_details, geojson, model_details, user_email, core_token):
    model_name, models_url = model_details
    project_uid = project_details.get("uid", None)
    if not project_uid or not models_url:
        return None

    request_body = {
        'project_uid': project_uid,
        'email': user_email,
        'inference': {'models_zip_url': models_url}
    }
    headers = {"Authorization": f"Token {core_token}"}
    response = requests.post(SCMAPP_URL + '/predict', json=request_body, headers=headers)
    return response


def approve(project_details, geojson, user_email, core_token):
    project_uid = project_details.get("uid")
    headers = {"Authorization": f"Token {core_token}"}
    response = requests.post(SCMAPP_URL + '/approve', params={"project_uid": project_uid}, headers=headers)
    return response.json()