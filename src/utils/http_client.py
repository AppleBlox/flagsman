import aiohttp
import asyncio
import logging
from typing import Optional, Any, List

logger = logging.getLogger(__name__)

class HTTPClient:
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._headers = {
            "User-Agent": "AppleBlox/1.0",
            "Accept": "application/json"
        }
        
    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session
        
    async def get(self, url: str, raw: bool = False) -> Optional[Any]:
        session = await self._get_session()
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    if raw:
                        return await response.text()
                    return await response.json()
                    
                if response.status != 404:
                    logger.error(f"HTTP {response.status} from {url}")
                return None
                
        except asyncio.TimeoutError:
            logger.error(f"Request timeout for {url}")
            return None
            
        except Exception as e:
            logger.error(f"Request failed for {url}: {str(e)}")
            return None

    async def gather(self, *tasks) -> List[Any]:
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            processed_results = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Task failed: {str(result)}")
                    processed_results.append(None)
                else:
                    processed_results.append(result)
                    
            return processed_results
            
        except Exception as e:
            logger.error(f"Parallel request failed: {str(e)}")
            return [None] * len(tasks)