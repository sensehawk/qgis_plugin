import requests
from ..constants import TERRA_URL


def get_terra_classmaps(project_details, token):
    container_uid = project_details.get("container", {}).get("uid", None)
    organization_uid = project_details.get("organization", {}).get("uid", None)
    url = TERRA_URL + "/feature-type-groups/"
    params = {"container": container_uid,
              "organization": organization_uid}
    headers = {"authorization": "Token {}".format(token)}
    response = requests.request("GET", url, params=params, headers=headers)
    # Gather all featureTypes
    all_features = []
    [all_features.extend(i.get("featureTypes", [])) for i in response.json()]
    class_maps = {i["uid"]: i for i in all_features}
    # Group featureTypes
    class_groups = {i["name"]: [x["uid"] for x in i["featureTypes"]] for i in response.json()}
    return class_maps, class_groups

def get_project_data(project_details, token):
    project_uid = project_details.get("uid", None)
    group_uid = project_details.get("group", {}).get("uid", None)
    container_uid = project_details.get("container", {}).get("uid", None)
    organization_uid = project_details.get("organization", {}).get("uid", None)
    url = TERRA_URL + f"/container-views/{container_uid}/?organization={organization_uid}"
    headers = {"Authorization": "Token {}".format(token)}
    response = requests.get(url, headers=headers).json()

    group = None
    for g in response.get("groups", []):
        if g.get("uid", None) == group_uid:
            group = g
            break
    project = None
    for p in group.get("projects", []):
        if p.get("uid", None) == project_uid:
            project = p
            break
    project_data = project.get("reports", {})
    return project_data



