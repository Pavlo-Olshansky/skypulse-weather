from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Units(str, Enum):
    STANDARD = "standard"
    METRIC = "metric"
    IMPERIAL = "imperial"


@dataclass
class CacheConfig:
    enabled: bool = True
    ttl: int = 300
    max_entries: int = 128


@dataclass
class RetryConfig:
    enabled: bool = True
    max_retries: int = 3
    backoff_factor: float = 0.5
