import requests
from ..constants import SID_URL
from .therm_apis import get_project_data
import traceback

def detect_solar_issues(project_details, angle, core_token, user_email, width, height):
    # Make request to the SID server
    try:
        project_data = get_project_data(project_details, core_token)
        ortho_url = project_data.get("ortho", None)
    except Exception:
        return str(traceback.format_exc())
    project_uid = project_details.get("uid", None)
    if not project_uid or not ortho_url:
        return "Invalid project_uid or ortho_url"
    request_body = {"details": {"projectUID": project_uid,
                                "user_email":user_email,
                                "angle": angle,
                                "width":width,
                                "height":height,},
                                "data": {"ortho": ortho_url},
                                "geojson": {
                                     "type": "FeatureCollection",
                                     "features": []}}
    headers = {"Authorization": "Token {}".format(core_token), 'email_id':user_email}
    response = requests.post(SID_URL, headers=headers, json=request_body)
    return response
