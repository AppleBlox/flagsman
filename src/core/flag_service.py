import json
import logging
from typing import List, Set, Dict
from threading import Lock
from datetime import datetime
from models import Flag, FlagCheckResult, CacheStats
from .flag_fetcher import FlagFetcher

logger = logging.getLogger(__name__)

class FlagService:
    _instance = None
    _lock = Lock()

    def __init__(self):
        if FlagService._instance is not None:
            raise RuntimeError("Use FlagService.instance() to get singleton")
            
        self._fetcher = FlagFetcher()
        self._cache: Dict[str, List[Flag]] = {}
        self._whitelist: Set[str] = set()
        self._risk_list: Set[str] = set()
        self._start_time = datetime.now()
        
        self._load_lists()

    @classmethod
    def instance(cls) -> 'FlagService':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _load_lists(self) -> None:
        try:
            with open('data/whitelist.json', 'r') as f:
                self._whitelist = set(json.load(f))
            with open('data/risklist.json', 'r') as f:
                self._risk_list = set(json.load(f))
            logger.info("Loaded special flag lists successfully")
        except Exception as e:
            logger.error(f"Error loading special lists: {str(e)}")
            self._whitelist = set()
            self._risk_list = set()

    def _parse_flag(self, name: str, value: str, timestamp: datetime) -> Flag:
        return Flag(
            name=name,
            enabled=str(value).lower() == "true",
            last_updated=timestamp
        )

    async def update_cache(self) -> None:
        try:
            flag_data = await self._fetcher.fetch_all_flags()
            timestamp = datetime.now()

            with self._lock:
                self._cache.clear()
                for app_name, app_data in flag_data.items():
                    if not app_data:
                        continue
                        
                    flags = []
                    for key, value in app_data.get("applicationSettings", {}).items():
                        if key.startswith("DFFlag"):
                            flags.append(self._parse_flag(key, value, timestamp))
                    
                    if flags:
                        self._cache[app_name] = flags
                        logger.info(f"Updated {len(flags)} flags for {app_name}")

            logger.info(f"Cache update completed. Total apps: {len(self._cache)}")

        except Exception as e:
            logger.error(f"Cache update failed: {str(e)}")
            raise

    async def get_application_flags(self, app_id: str) -> List[Flag]:
        if app_id not in FlagFetcher.VALID_CLIENTS:
            raise ValueError(f"Invalid application ID: {app_id}")
        return self._cache.get(app_id, [])

    async def check_flags(self, flags: List[str], applications: List[str]) -> FlagCheckResult:
        valid_flags: Set[str] = set()
        risk_flags = self._risk_list.intersection(flags)
        
        remaining = set(flags) - risk_flags
        
        for app_id in applications:
            if app_id not in FlagFetcher.VALID_CLIENTS:
                raise ValueError(f"Invalid application ID: {app_id}")
                
            app_flags = await self.get_application_flags(app_id)
            flag_names = {f.name for f in app_flags}
            valid_flags.update(flag_names.intersection(remaining))
            remaining -= flag_names

        return FlagCheckResult(
            valid=list(valid_flags),
            invalid=list(remaining),
            risk=list(risk_flags)
        )

    @property
    def stats(self) -> CacheStats:
        return CacheStats(
            uptime=(datetime.now() - self._start_time).total_seconds(),
            last_fetch=self._fetcher.last_fetch,
            cache_size=sum(len(flags) for flags in self._cache.values())
        )