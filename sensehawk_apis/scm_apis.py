from ..constants import SCM_URL
import requests
from .core_apis import get_project_details, get_project_geojson
from .terra_apis import get_terra_classmaps, get_project_data


def get_models_list(project_uid):
    url = SCM_URL + "/list-models"
    params = {"project_uid": project_uid}
    response = requests.request("GET", url, params=params)
    return response.json()


def detect(project_details, geojson, models_url, user_email, core_token):
    url = SCM_URL + "/predict"
    project_uid = project_details.get("uid", None)
    ortho_url = get_project_data(project_details, core_token).get("ortho", {}).get("url", None)
    if not project_uid or not ortho_url:
        return None
    request_body = {"data": {"ortho": ortho_url, "ml_models": models_url},
                    "details": {"project_uid": project_uid, "user_email": user_email},
                    "geojson": geojson
                    }
    response = requests.request("POST", url, json=request_body).json()
    return response


def approve(project_details, geojson, user_email):
    url = SCM_URL + "/approve"
    request_body = {"details": {"user_email": user_email, "project_uid": project_details.get("uid", None)},
                    "geojson": geojson
                    }
    response = requests.request("POST", url, json=request_body)
    return response.json()

