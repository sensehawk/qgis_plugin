import requests
import json
import os


CORE_URL = "https://core-stage-server.sensehawk.com"
MAP_SERVER_URL = "https://mapserver.sensehawk.com/"
TERRA_URL = "https://terra-stage-server.sensehawk.com"
THERM_URL = "https://therm-stage-server.sensehawk.com"


def get_project_details(project_uid, token):
    url = CORE_URL+"/api/v1/projects/{}/?reports=true".format(project_uid)
    headers = {"Authorization": "Token {}".format(token)}
    project_details = requests.get(url, headers=headers).json()
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


def save_project_geojson(geojson_path, project_uid, token, project_type="terra"):
    if not os.path.exists(geojson_path):
        return False
    geojson = json.load(open(geojson_path))
    project_details = get_project_details(project_uid, token)
    headers = {"Authorization": "Token {}".format(token)}
    url = None
    if project_type == "terra":
        url = TERRA_URL + "/qc/project/{}/features/?organization={}".format(project_uid,
                                                                            project_details["organization"]["uid"])
        for f in geojson["features"]:
            f["properties"]["workflowProgress"] = {}
    elif project_type == "therm":
        url = THERM_URL + "/qc/projects/{}?organization={}".format(project_uid,
                                                                   project_details["organization"]["uid"])

    if not url:
        return False
    res = requests.post(url, json={"geojson": geojson}, headers=headers)
    return res.json()


def core_login(username, password):
    url = "https://core-stage-server.sensehawk.com/api/v1/api-basic-auth/"  # stage URI
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
