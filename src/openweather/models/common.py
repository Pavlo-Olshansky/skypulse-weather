from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Units(str, Enum):
    """Measurement unit system for API responses.

    STANDARD uses Kelvin / m/s, METRIC uses Celsius / m/s, IMPERIAL uses
    Fahrenheit / mph.
    """

    STANDARD = "standard"
    METRIC = "metric"
    IMPERIAL = "imperial"


@dataclass
class CacheConfig:
    """Configuration for the response cache.

    Attributes:
        enabled: Whether caching is active.
        ttl: Default time-to-live for cache entries, in seconds.
        max_entries: Maximum number of entries the cache will hold.
    """

    enabled: bool = True
    ttl: int = 300
    max_entries: int = 128


@dataclass
class RetryConfig:
    """Configuration for automatic request retries.

    Attributes:
        enabled: Whether retries are active.
        max_retries: Maximum number of retry attempts.
        backoff_factor: Multiplier for exponential backoff between retries.
    """

    enabled: bool = True
    max_retries: int = 3
    backoff_factor: float = 0.5
