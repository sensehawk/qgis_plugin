import os


CORE_URL = "https://core-stage-server.sensehawk.com"
MAP_SERVER_URL = "https://mapserver.sensehawk.com/"
TERRA_URL = "https://terra-stage-server.sensehawk.com"
THERM_URL = "https://therm-stage-server.sensehawk.com"
SCM_URL = "https://scm-inference-stage.sensehawk.com"

CLIP_FUNCTION_URL = "https://848rwfqtw0.execute-api.us-west-2.amazonaws.com/default/clipRaster"

STORAGE_URL="https://storage-stage-server.sensehawk.com/get-url/?payload=%s"
try:
    STORAGE_PRIVATE_KEY = open("SECRET_KEY.txt").read().strip()
except Exception:
    STORAGE_PRIVATE_KEY = None
