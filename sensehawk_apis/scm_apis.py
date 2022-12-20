from ..constants import SCM_URL, CLIP_FUNCTION_URL
import requests
from .core_apis import get_project_details, get_report_url, get_project_geojson
from .terra_apis import get_terra_classmaps


def get_models_list(project_uid):
    url = SCM_URL + "/list-models"
    params = {"project_uid": project_uid}
    response = requests.request("GET", url, params=params)
    return response.json()


def detect(logger, project_uid, models_url, user_email, token):
    url = SCM_URL + "/predict"
    project_details = get_project_details(project_uid, token)
    try:
        ortho_report_object = [r for r in project_details["reports"] if r.get("report_type", None) == "ortho"][0]
    except Exception:
        logger("No ortho found for project...", level=Qgis.Warning)
        return None
    ortho_url = get_report_url(ortho_report_object)
    tables_geojson = get_project_geojson(project_uid, token, "terra")
    request_body = {"data": {"ortho": ortho_url, "ml_models": models_url},
                    "details": {"project_uid": project_uid, "user_email": user_email},
                    "geojson": tables_geojson
                    }
    response = requests.request("POST", url, json=request_body)
    return response.json()


def approve(project_uid, user_email, token):
    url = SCM_URL + "/approve"
    project_geojson = get_project_geojson(project_uid, token, "terra")
    request_body = {"details": {"user_email": user_email, "project_uid": project_uid},
                    "geojson": project_geojson
                    }
    response = requests.request("POST", url, json=request_body)
    return response.json()


def clip_request(logger, project_details, geojson, clip_boundary_class_name):
    try:
        ortho_report_object = [r for r in project_details["reports"] if r.get("report_type", None) == "ortho"][0]
    except Exception:
        logger("No ortho found for project...", level=Qgis.Warning)
        return None
    ortho_url = get_report_url(ortho_report_object)
    request_body = {"project_uid": project_details.get("uid", None),
                    "raster_url": ortho_url,
                    "geojson": geojson,
                    "clip_boundary_class_name": clip_boundary_class_name}

    response = requests.post(CLIP_FUNCTION_URL, json=request_body)
    logger("Clipping request sent...")
    return response.json()
