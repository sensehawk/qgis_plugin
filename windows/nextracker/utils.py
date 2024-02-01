import requests
import traceback
from ...constants import NEXTRACKER_URL, CORE_URL

nextracker_org_uid = "00g305uhwb3ULo6Em0i7" #"00g7uy87cofqS3X380i7"
nextracker_owner_uid = "7cqq3r8475" #NMHuEVAxXz
nextracker_featuretype_groups = ["WcePT5wZkJQs","1Ngg3bHRXe5v"] #["BudsBapby0N0", "tM2NCKQSPW0g"] 

# Works only for projects in NEXTracker organization
def setup_nextracker_features(container_uid, core_token):
    url = f"https://terra-server.sensehawk.com/container-views/{container_uid}/ftg/add/"
    headers = {"Authorization": f"Token {core_token}"}
    params = {"organization": nextracker_org_uid}#"00g305uhwb3ULo6Em0i7"}
    # Pre-existing feature type groups
    body = {"featureTypeGroups": nextracker_featuretype_groups}
    requests.post(url, json=body, headers=headers, params=params)
    return True

def setup_clipped_orthos_group(task, task_inputs):
    try:
        deal_id, asset_uid, container_uid, core_token, logger, home_obj, container_name = task_inputs
        container_details = { container.name:[container_uid, container.group_info] for container_uid, container in home_obj.containers_dict.items()}
        # First check if `Clipped Orthos` group already exists in the container or not, and create if not
        url = "https://core-server.sensehawk.com/api/v1/groups/"
        params = {"organization": nextracker_org_uid, "container": container_uid}
        headers = {"Authorization": f"Token {core_token}"}
        groups = requests.get(url, headers=headers, params=params).json()["results"]
        group_names = [i["name"] for i in groups]
        logger(f"Existing groups: {group_names}")
        group_uids = [i["uid"] for i in groups]
        clipped_ortho = "Clipped Orthos"
        if clipped_ortho in group_names:
            group_uid = group_uids[group_names.index(clipped_ortho)]
            return {"task": task.description(), "success": True,
                    "message": "Clipped Orthos group already exists",
                    "group_uid": group_uid}
        else:
            # New group will be the first one in the list, return its uid
            logger("Creating new group - Clipped Orthos")
            url = CORE_URL+f'/api/v1/groups/?organization={nextracker_org_uid}'
            headers = {'Authorization':f'Token {core_token}'}
            json = {'name':clipped_ortho,'organization':{'uid':nextracker_org_uid},
                                                                  'deal_id':deal_id,
                                                                  'asset':{'uid':asset_uid},
                                                                  'owner':{'uid':nextracker_owner_uid}}
            
            resp = requests.post(url, headers=headers, json=json).json()
            group_uid = resp["uid"]
            logger("Successfully created new group - Clipped Orthos")
            container_group_info = container_details[container_name][1]
            json = {'groups':container_group_info}
            url = CORE_URL + f'/api/v1/containers/{container_uid}/?organization={nextracker_org_uid}'
            json['groups'].append({'uid':group_uid})
            add_group_response = requests.patch(url, headers=headers, json=json)
            logger(f'Group added to {container_name} container... ')
            return {"task": task.description(), "success": True,
                    "message": "Clipped Orthos group validated",
                    "group_uid": group_uid}
    except Exception as e:
        tb = traceback.format_exc()
        return {"task": task.description(), "success": False,
                "message": str(tb),
                "group_uid": None}
    
def generate_group_points(group_obj, org_uid, user_email, token, logger):
    group_uid, group_name = group_obj.uid, group_obj.name
    url = f"{NEXTRACKER_URL}/group_points?group_uid={group_uid}&organization_uid={org_uid}&user_email={user_email}&group_name={group_name}"
    headers = {"Authorization": f"Token {token}"}
    resp = requests.post(url, headers=headers)
    logger(str(resp.json()))
