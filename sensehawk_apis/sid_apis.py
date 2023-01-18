import requests
from ..constants import SID_URL
from .therm_apis import get_project_data

def detect_solar_issues(project_details, angle, core_token, user_email):
    # Make request to the SID server
    try:
        project_data = get_project_data(project_details, core_token)
        ortho_url = project_data.get("ortho", None)
    except Exception:
        return None
    project_uid = project_details.get("uid", None)
    if not project_uid or not ortho_url:
        return None
    request_body = {"details": {"projectUID": project_uid,
                                "angle": angle,
                                "user_email": user_email},
                    "data": {"ortho": ortho_url}}
    headers = {"Authorization": "Token {}".format(core_token)}
    response = requests.post(SID_URL, headers=headers, json=request_body)
    return response
