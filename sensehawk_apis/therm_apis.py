import json
import os
import requests
from ..constants import THERM_URL

def get_therm_classmaps(core_token, org_uid, container_uid):
    # IDs and class names of all the classes defined in Therm
    headers = {'Authorization':f'Token {core_token}'}
    response = requests.get(THERM_URL + f'/viewer/config?organization={org_uid}', headers=headers)
    therm_classes = response.json()
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

    c_response = requests.get(THERM_URL + f'/viewer/view/{container_uid}/config/?organization={org_uid}', headers=headers)
    c_therm_classes = c_response.json()
    container_class_map = {}
    for c_class_name in c_therm_classes:
        issue_name = c_class_name['class_name']
        org_class_name =  therm_classmaps[issue_name]
        if org_class_name['description'] != c_class_name['description'] or org_class_name['color'] != c_class_name['color']:
            org_class_name['description'] = c_class_name['description']
            container_class_map[issue_name] = c_class_name['description']
            org_class_name['color'] = c_class_name['color']
            therm_classmaps[issue_name] = org_class_name
    
    # print(container_class_map)
    return [therm_classmaps, container_class_map]

def get_project_data(project_details, token):
    project_uid = project_details.get("uid", None)
    organization_uid = project_details.get("organization", {}).get("uid", None)
    url = THERM_URL + f"/projects/{project_uid}/data?organization={organization_uid}"
    headers = {"Authorization": "Token {}".format(token)}
    project_data = requests.get(url, headers=headers).json()
    return project_data

