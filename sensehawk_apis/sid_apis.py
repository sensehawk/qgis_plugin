import requests
from ..constants import SID_URL
from .core_apis import get_report_url

def detect_solar_issues(project_details, angle, core_token, user_email):
    # Make request to the SID server
    try:
        ortho_report_object = [r for r in project_details["reports"] if r.get("report_type", None) == "ortho"][0]
        ortho_url = get_report_url(ortho_report_object)
    except Exception:
        return None
    project_uid = project_details.get("uid", None)
    if not project_uid:
        return None
    request_body = {"details": {"projectUID": project_uid,
                                "angle": angle,
                                "user_email": user_email},
                    "data": {"ortho": ortho_url}}
    headers = {"Authorization": "Token {}".format(core_token)}
    response = requests.post(SID_URL, headers=headers, json=request_body)
    return response