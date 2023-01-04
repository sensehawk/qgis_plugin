import os

CORE_URL = "https://core-server.sensehawk.com"
MAP_SERVER_URL = "https://mapserver.sensehawk.com/"
TERRA_URL = "https://terra-server.sensehawk.com"
THERM_URL = "https://therm-server.sensehawk.com"
SCM_URL = "https://scm-inference.sensehawk.com"

SID_URL = "https://sid.sensehawk.com/detect-solar-issues"

CLIP_FUNCTION_URL = "https://848rwfqtw0.execute-api.us-west-2.amazonaws.com/default/clipRaster"

STORAGE_URL="https://storage-server.sensehawk.com/get-url/?payload=%s"
STORAGE_PRIVATE_KEY = os.getenv("SENSEHAWK_PRIVATE_KEY")



