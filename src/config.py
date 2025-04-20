import os
from typing import List


HOST = os.getenv('APPLEBLOX_HOST', '0.0.0.0')
PORT = int(os.getenv('APPLEBLOX_PORT', '8000'))
DEBUG = os.getenv('APPLEBLOX_DEBUG', '0').lower() in ('1', 'true')

RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_REQUESTS = 100  


CACHE_UPDATE_INTERVAL = 3600  
REQUEST_TIMEOUT = 30 

DATA_DIR = 'data'
WHITELIST_PATH = os.path.join(DATA_DIR, 'whitelist.json')
RISK_LIST_PATH = os.path.join(DATA_DIR, 'risklist.json')


VALID_APPLICATIONS: List[str] = [
    "PCDesktopClient",
    "MacDesktopClient", 
    "AndroidApp",
    "iOSApp",
    "XboxClient",
    "PCStudioApp",
    "MacStudioApp",
    "UWPApp",
    "ALL"
]


USER_AGENT = "AppleBlox/1.0"
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json"
}