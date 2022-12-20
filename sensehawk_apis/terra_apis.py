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
