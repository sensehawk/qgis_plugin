from ..constants import SCM_URL
import requests
from .core_apis import get_project_details, get_report_url, get_project_geojson
from .terra_apis import get_terra_classmaps


def get_models_list(project_uid):
    url = SCM_URL + "/list-models"
    params = {"project_uid": project_uid}
    response = requests.request("GET", url, params=params)
    return response.json()


def detect(project_details, geojson, models_url, user_email):
    url = SCM_URL + "/predict"
    try:
        ortho_report_object = [r for r in project_details["reports"] if r.get("report_type", None) == "ortho"][0]
    except Exception:
        return None
    project_uid = project_details.get("uid", None)
    if not project_uid:
        return None
    ortho_url = get_report_url(ortho_report_object)
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

