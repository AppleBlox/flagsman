import aiohttp
import logging
import json
import os
from typing import Dict, Optional
from datetime import datetime
from utils.http_client import HTTPClient

logger = logging.getLogger(__name__)

class FlagFetcher:
    BASE_URL = "https://clientsettings.roblox.com/v2/settings/application"
    GITHUB_URL = "https://raw.githubusercontent.com/MaximumADHD/Roblox-Client-Tracker/refs/heads/roblox/FVariables.txt"

    VALID_CLIENTS = {
        "PCDesktopClient",
        "MacDesktopClient", 
        "AndroidApp",
        "iOSApp",
        "XboxClient",
        "PCStudioApp",
        "MacStudioApp",
        "UWPApp",
        "ALL"
    }

    def __init__(self):
        self._http = HTTPClient()
        self._last_fetch: Optional[datetime] = None

    @property
    def last_fetch(self) -> Optional[datetime]:
        return self._last_fetch

    async def fetch_application_flags(self, app_name: str) -> Optional[dict]:
        if app_name not in self.VALID_CLIENTS:
            logger.warning(f"Skipping fetch for invalid client: {app_name}")
            return None

        url = f"{self.BASE_URL}/{app_name}"

        try:
            response = await self._http.get(url)
            if response:
                logger.info(f"Successfully fetched flags for {app_name}")
            return response

        except Exception as e:
            logger.error(f"Failed to fetch flags for {app_name}: {str(e)}")
            return None

    async def fetch_all_flags(self) -> Dict[str, dict]:
        results = {}

        try:
            # First, fetch GitHub flags
            github_flags = await self.fetch_flags_from_github()
            logger.info(f"Fetched {len(github_flags)} flags from GitHub")

            # Create the ALL application specifically from GitHub flags
            all_app = {"applicationSettings": {}}
            all_app["applicationSettings"] = github_flags.copy()  # Direct assignment
            results["ALL"] = all_app

            # Now fetch regular applications
            regular_clients = [c for c in self.VALID_CLIENTS if c != "ALL"]
            tasks = [self.fetch_application_flags(client) for client in regular_clients]
            responses = await self._http.gather(*tasks)

            # Process regular applications
            for client, response in zip(regular_clients, responses):
                if response:
                    # Ensure applicationSettings exists
                    if 'applicationSettings' not in response:
                        response['applicationSettings'] = {}
                    
                    # Merge GitHub flags into this application's flags
                    for flag_name, flag_value in github_flags.items():
                        if flag_name not in response['applicationSettings']:
                            response['applicationSettings'][flag_name] = flag_value
                    
                    results[client] = response

            self._last_fetch = datetime.now()
            self.save_flags(results)
            return results

        except Exception as e:
            logger.error(f"Failed to fetch flags: {str(e)}")
            return results

    async def fetch_flags_from_github(self) -> Dict[str, str]:
        try:
            response = await self._http.get(self.GITHUB_URL, raw=True)
            if not response:
                logger.error("Failed to fetch flags from GitHub")
                return {}

            flags = {}
            for line in response.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Check for pattern [Type] FlagName
                if '] ' in line and line.startswith('['):
                    type_end = line.find('] ')
                    if type_end > 0:
                        flag_name = line[type_end + 2:].strip()
                        
                        # Only add the flag if it has a recognized prefix
                        if any(flag_name.startswith(prefix) for prefix in [
                            'DFFlag', 'FFlag', 'BFFlag', 'FInt', 'DFInt', 'FString', 'DFString'
                        ]):
                            # Set appropriate default value based on prefix
                            if flag_name.startswith(('DFInt', 'FInt')):
                                flags[flag_name] = "0"
                            elif flag_name.startswith(('DFString', 'FString')):
                                flags[flag_name] = ""
                            else:  # DFFlag, FFlag, etc.
                                flags[flag_name] = "false"
                
            return flags

        except Exception as e:
            logger.error(f"Failed to fetch flags from GitHub: {str(e)}")
            return {}
        
    def save_flags(self, flags_data: Dict[str, dict]) -> bool:
        try:
            os.makedirs('data/cache', exist_ok=True)
            with open('data/cache/flags.json', 'w') as f:
                json.dump(flags_data, f)
            logger.info("Successfully saved flags to disk")
            return True
        except Exception as e:
            logger.error(f"Failed to save flags: {str(e)}")
            return False

    def load_saved_flags(self) -> Optional[Dict[str, dict]]:
        try:
            if os.path.exists('data/cache/flags.json'):
                with open('data/cache/flags.json', 'r') as f:
                    flags_data = json.load(f)
                logger.info("Successfully loaded flags from disk")
                return flags_data
            else:
                logger.info("No saved flags found")
                return None
        except Exception as e:
            logger.error(f"Failed to load saved flags: {str(e)}")
            return None