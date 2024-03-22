import requests
import json
import os
from ..constants import CORE_URL, TERRA_URL, THERM_URL, MAP_SERVER_URL, API_NEW_SENSEHAWK, V2_MAP_SERVER_UTL
from qgis.core import Qgis

def get_project_reports(project_uid, container_uid, org_uid, core_token):
    headers = {'Authorization':f'Token {core_token}'}
    url = f"https://terra-server.sensehawk.com/container-views/{container_uid}/projects/{project_uid}/?organization={org_uid}"
    res = requests.get(url, headers=headers).json()["reports"]
    ortho_url = res.get("ortho", {}).get('url', None)
    dsm_url = res.get("dsm", {}).get('url', None)
    
    return ortho_url, dsm_url

def get_reports_url(bucket: str, key: str, region: str) -> str:
    """
    # https://api-new.sensehawk.com/storage/download?b=<bucket>&k=<key>&r=<region>&f=filename
    # https://api-new.sensehawk.com/storage/download?b=sensehawk-test-data-management&k=core%2FK4W6yJ1zMP%2Fml_models.zip&r=ap-south-1&f=test1.zip
    """
    url = API_NEW_SENSEHAWK + f"/storage/download?b={bucket}&k={key}&r={region}"
    response = requests.head(url, allow_redirects=True)  # to get only final redirect url
    assert response.status_code == 403, response.json()
    return response.url


def get_project_details(project_uid, token):
    url = CORE_URL+"/api/v1/projects/{}/?reports=true".format(project_uid)
    headers = {"Authorization": "Token {}".format(token)}
    project_details = requests.get(url, headers=headers).json()
    if project_details.get("detail", None) == "Not found.":
        return None
    return project_details


def get_ortho_tiles_url(project_uid, token):
    project_details = get_project_details(project_uid, token)
    reports = project_details["reports"]
    orthotiles = [r for r in reports if r["report_type"] == "orthotiles"]
    if not orthotiles:
        return None
    orthotiles_uid = orthotiles[0]["uid"]
    version = orthotiles[0]['properties'].get('version', None)
    if version == 2:
        orthotiles_url = V2_MAP_SERVER_UTL + orthotiles_uid
    else:
        orthotiles_url = MAP_SERVER_URL + orthotiles_uid
    return orthotiles_url, version

def get_ortho_url(project_uid, org, token):
    url  = f'https://therm-server.sensehawk.com/projects/{project_uid}/data?organization={org}'
    headers = {"Authorization": f"Token {token}"}
    reponse = requests.get(url, headers=headers)
    return reponse.json()

def get_project_geojson(project_uid, token, project_type):
    project_details = get_project_details(project_uid, token)
    headers = {"Authorization": "Token {}".format(token)}
    url = None
    if project_type == "terra":
        url = TERRA_URL + "/qc/project/{}/features/?organization={}".format(project_uid,
                                                                            project_details["organization"]["uid"])
    elif project_type == "therm":
        url = THERM_URL + "/qc/projects/{}?organization={}".format(project_uid,
                                                                   project_details["organization"]["uid"])
    if not url:
        return None
    res = requests.get(url, headers=headers)
    return res.json()


def save_project_geojson(geojson, project_uid, token, project_type="terra"):
    project_details = get_project_details(project_uid, token)
    headers = {"Authorization": "Token {}".format(token)}
    if project_type == "terra":
        url = TERRA_URL + "/qc/project/{}/features/?organization={}".format(project_uid,
                                                                            project_details["organization"]["uid"])

    elif project_type == "therm":
        url = THERM_URL + "/qc/projects/{}?organization={}".format(project_uid,
                                                                   project_details["organization"]["uid"])

    res = requests.post(url, json={"geojson": geojson}, headers=headers)
    if project_type == "terra":
        # Return only status code
        if res.status_code == 200:
            return "Successfully saved to SenseHawk Terra.", res.status_code
    return res.json(), res.status_code


def core_login(username, password, logger):
    url = CORE_URL + "/api/v1/api-basic-auth/"
    payload = json.dumps({
        "username": username,
        "password": password
    })
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    try:
        token = response.json()["Authorization"]
    except Exception as e:
        logger(str(e), Qgis.Warning)
        token = None
    return token

