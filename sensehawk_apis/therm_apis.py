import json
import os
import requests
from ..constants import THERM_URL

def get_therm_classmaps():
    # IDs and class names of all the classes defined in Therm
    class_maps_path = os.path.join(os.path.dirname(__file__), "therm_classmaps.json")
    therm_classes = json.load(open(class_maps_path))
    therm_classmaps = {}
    for i in range(len(therm_classes)):
        therm_class = therm_classes[i]
        class_name = therm_class["class_name"]
        therm_classmaps[class_name] = therm_class
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
    header = {"Authorization": "Token {}".format(token)}
    project_data = requests.get(url, header=header)
    return project_data

