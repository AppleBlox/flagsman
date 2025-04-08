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
        "UWPApp"
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

            tasks = [self.fetch_application_flags(client) for client in self.VALID_CLIENTS]
            responses = await self._http.gather(*tasks)

            for client, response in zip(self.VALID_CLIENTS, responses):
                if response:
                    results[client] = response

            github_flags = await self.fetch_flags_from_github()

            if github_flags:
                for client in self.VALID_CLIENTS:
                    if client in results:

                        if 'applicationSettings' not in results[client]:
                            results[client]['applicationSettings'] = {}

                        results[client]['applicationSettings'].update(github_flags)

            self._last_fetch = datetime.now()
            logger.info(f"Completed flag fetch for {len(results)} clients")

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

                if '[C++]' in line:
                    flag_name = line.split('[C++]')[1].strip()
                elif '[Lua]' in line:
                    flag_name = line.split('[Lua]')[1].strip()
                else:
                    flag_name = line

                if not flag_name:
                    continue

                if flag_name.startswith('DFFlag') or flag_name.startswith('FFlag') or flag_name.startswith('BFFlag'):
                    flags[flag_name] = "false"
                elif flag_name.startswith('FInt'):
                    flags[flag_name] = "0"
                elif flag_name.startswith('FString'):
                    flags[flag_name] = ""
                else:
                    flags[flag_name] = "false"

            logger.info(f"Successfully fetched {len(flags)} flags from GitHub")
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