import json
import os
import requests
from ..constants import THERM_URL

def get_therm_classmaps(core_token, org_uid):
    # IDs and class names of all the classes defined in Therm
    headers = {'Authorization':f'Token {core_token}'}
    respones = requests.get(THERM_URL + f'/viewer/config?organization={org_uid}', headers=headers)
    therm_classes = respones.json()
    therm_classmaps = {}
    for i in range(len(therm_classes)):
        therm_class = therm_classes[i]
        class_name = therm_class["class_name"]
        therm_classmaps[class_name] = therm_class  # {hotspot = {}}
        therm_classmaps[class_name]["name"] = class_name 
        # We will use the same order for keyboard shortcuts later
        therm_classmaps[class_name]["key"] = str(i)
        # Color is moved into properties key
        therm_classmaps[class_name]["properties"] = {"color": therm_class["color"]}
    # # Add a clip boundary class
    # therm_classmaps["clip_boundary"] = {"name": "clip_boundary",
    #                                     "key": "C",
    #                                     "properties": {"color": "rgb(150, 195, 235)"},
    #                                     "class_name": "clip_boundary"}
    return therm_classmaps

def get_project_data(project_details, token):
    project_uid = project_details.get("uid", None)
    organization_uid = project_details.get("organization", {}).get("uid", None)
    url = THERM_URL + f"/projects/{project_uid}/data?organization={organization_uid}"
    headers = {"Authorization": "Token {}".format(token)}
    project_data = requests.get(url, headers=headers).json()
    return project_data

