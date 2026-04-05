from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from skypulse._constants import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_CACHE_MAX_ENTRIES,
    DEFAULT_CACHE_TTL,
    DEFAULT_MAX_RETRIES,
)


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
    ttl: int = DEFAULT_CACHE_TTL
    max_entries: int = DEFAULT_CACHE_MAX_ENTRIES


@dataclass
class RetryConfig:
    """Configuration for automatic request retries.

    Attributes:
        enabled: Whether retries are active.
        max_retries: Maximum number of retry attempts.
        backoff_factor: Multiplier for exponential backoff between retries.
    """

    enabled: bool = True
    max_retries: int = DEFAULT_MAX_RETRIES
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR
