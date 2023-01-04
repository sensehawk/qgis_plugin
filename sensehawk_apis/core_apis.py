import requests
import json
import os
from ..constants import CORE_URL, TERRA_URL, THERM_URL, MAP_SERVER_URL, STORAGE_URL, STORAGE_PRIVATE_KEY
import jwt
import base64


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
    url = None
    if project_type == "terra":
        url = TERRA_URL + "/qc/project/{}/features/?organization={}".format(project_uid,
                                                                            project_details["organization"]["uid"])
        properties_to_remove = ["element", "uid"]
        for f in geojson["features"]:
            for p in properties_to_remove:
                try:
                    del f["properties"][p]
                except KeyError:
                    continue

    elif project_type == "therm":
        url = THERM_URL + "/qc/projects/{}?organization={}".format(project_uid,
                                                                   project_details["organization"]["uid"])

    if not url:
        return False
    res = requests.post(url, json={"geojson": geojson}, headers=headers)
    with open("/home/kiranhegde/Downloads/new_test_test.json.geojson", "w") as fi:
        json.dump(geojson, fi)
    return res.json()


def core_login(username, password):
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
        print(e)
        token = None
    return token


def get_report_url(report_object):
    """
    Takes the sensehawk report object and returns the project name and the object url
    """
    service_object = report_object.get("service", None)
    if not service_object:
        return None
    data = {
        "service": service_object,
    }
    private_key = base64.b64decode(STORAGE_PRIVATE_KEY).decode('utf-8')
    payload = jwt.encode(data, private_key, algorithm='RS256')
    return STORAGE_URL % payload
