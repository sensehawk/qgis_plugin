import requests
import json
import os
from ..constants import CORE_URL, TERRA_URL, THERM_URL, MAP_SERVER_URL
from qgis.core import Qgis

def get_project_reports(project_uid, token):
    PROJECT_REPORT_URL = CORE_URL + "/api/v1/projects/%s/reports/"
    REPORT_DOWNLOAD_URL = CORE_URL + "/api/v1/projects/%s/reports/%s/download/"
    HOST_TOKEN = f'Token {token}'

    all_reports = {}
    reports = requests.get(PROJECT_REPORT_URL %project_uid, headers = {'Authorization': HOST_TOKEN}).json()['results']

    for report in reports:
        if report['report_type'] != 'processed':
            url = requests.get(REPORT_DOWNLOAD_URL %(project_uid, report['uid']), headers = {'Authorization':HOST_TOKEN}).json()['url']
            all_reports[report['report_type']] = url
    return all_reports


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
    orthotiles_url = MAP_SERVER_URL + orthotiles_uid
    return orthotiles_url

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
            return "Successfully saved to SenseHawk Terra."
    return res.json()


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

