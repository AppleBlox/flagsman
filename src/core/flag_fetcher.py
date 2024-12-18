import aiohttp
import logging
from typing import Dict, Optional
from datetime import datetime
from utils.http_client import HTTPClient

logger = logging.getLogger(__name__)

class FlagFetcher:
    BASE_URL = "https://clientsettings.roblox.com/v2/settings/application"
    
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
                    
            self._last_fetch = datetime.now()
            logger.info(f"Completed flag fetch for {len(results)} clients")
            return results
            
        except Exception as e:
            logger.error(f"Failed to fetch flags: {str(e)}")
            return results