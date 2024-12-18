from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Set, Optional

@dataclass
class Flag:
    name: str
    enabled: bool
    last_updated: datetime
    places: Set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "last_updated": self.last_updated.isoformat(),
            "places": list(self.places) if self.places else []
        }

@dataclass
class FlagCheckResult:
    valid: List[str]
    invalid: List[str]
    risk: List[str]

@dataclass
class CacheStats:
    uptime: float
    last_fetch: Optional[datetime]
    cache_size: int