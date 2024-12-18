import logging
from typing import Dict, List, Set, Any  # Added Any for type hinting
from threading import Lock
from datetime import datetime
import asyncio
from models import Flag, CacheStats
from .flag_fetcher import RobloxFlagFetcher

logger = logging.getLogger(__name__)

class FlagCacheManager:
    
    _instance = None
    _lock = Lock()
    UPDATE_INTERVAL = 3600

    def __init__(self):
        if FlagCacheManager._instance is not None:
            raise RuntimeError("Use FlagCacheManager.instance() to get singleton")
            
        self._cache: Dict[str, List[Flag]] = {}
        self._start_time = datetime.now()
        self._fetcher = RobloxFlagFetcher()
        self._update_task = None
        self._whitelist: Set[str] = set()
        self._risk_list: Set[str] = set()

    @classmethod
    def instance(cls) -> 'FlagCacheManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _parse_flag_value(self, value: str) -> bool:
        return str(value).lower() == "true"

    async def _process_flags(self, flags_data: Dict[str, Any]) -> Dict[str, List[Flag]]:
        processed = {}
        now = datetime.now()

        for app_name, app_data in flags_data.items():
            flags = []
            settings = app_data.get("applicationSettings", {})
            
            for key, value in settings.items():
                if key.startswith("DFFlag"):
                    base_name = key[:-12] if key.endswith("_PlaceFilter") else key
                    
                    if not key.endswith("_PlaceFilter"):
                        flag = Flag(
                            name=key,
                            enabled=self._parse_flag_value(value),
                            last_updated=now
                        )
                        flags.append(flag)
            
            processed[app_name] = flags

        return processed

    async def _update_cache(self):
        while True:
            try:
                logger.info("Starting flag update from Roblox")
                flags_data = await self._fetcher.fetch_flags()
                
                if flags_data:
                    self._cache = await self._process_flags(flags_data)
                    logger.info(f"Updated {sum(len(flags) for flags in self._cache.values())} flags")
                
                await asyncio.sleep(self.UPDATE_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error updating cache: {str(e)}")
                await asyncio.sleep(60)

    async def init_cache(self):
        try:
            saved_flags = self._fetcher.load_saved_flags()
            if saved_flags:
                self._cache = await self._process_flags(saved_flags)
                logger.info("Loaded flags from storage")
            
            flags_data = await self._fetcher.fetch_flags()
            if flags_data:
                self._cache = await self._process_flags(flags_data)
            
            self._update_task = asyncio.create_task(self._update_cache())
            
            logger.info("Cache initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize cache: {str(e)}")
            raise

    async def get_flags(self, app_id: str) -> List[Flag]:
        if app_id not in self._fetcher.ROBLOX_ENDPOINTS:
            raise ValueError(f"Invalid application ID: {app_id}")
        return self._cache.get(app_id, [])

    @property
    def stats(self) -> CacheStats:
        return CacheStats(
            uptime=(datetime.now() - self._start_time).total_seconds(),
            last_fetch=self._fetcher.last_fetch or self._start_time,
            cache_size=sum(len(flags) for flags in self._cache.values())
        )