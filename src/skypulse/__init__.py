"""SkyPulse Python SDK — typed, cached, sync + async."""

from skypulse._async_client import AsyncSkyPulseClient
from skypulse._client import SkyPulseClient
from skypulse._errors import (
    APIError,
    AuthenticationError,
    NetworkError,
    NotFoundError,
    SkyPulseError,
    ParseError,
    RateLimitError,
    ServerError,
    ServiceUnavailableError,
    TimeoutError,
)
from skypulse._version import __version__
from skypulse.models.common import CacheConfig, RetryConfig, Units
from skypulse.models.forecast import Forecast, ForecastEntry
from skypulse.models.health import HealthImpact, StormAlert
from skypulse.models.location import Location
from skypulse.models.storm import MagneticForecastEntry, MagneticStorm
from skypulse.models.weather import Condition, Weather, Wind

__all__ = [
    "APIError",
    "AsyncSkyPulseClient",
    "AuthenticationError",
    "CacheConfig",
    "Condition",
    "Forecast",
    "ForecastEntry",
    "HealthImpact",
    "Location",
    "MagneticForecastEntry",
    "MagneticStorm",
    "NetworkError",
    "NotFoundError",
    "SkyPulseClient",
    "SkyPulseError",
    "ParseError",
    "RateLimitError",
    "RetryConfig",
    "ServerError",
    "ServiceUnavailableError",
    "StormAlert",
    "TimeoutError",
    "Units",
    "Weather",
    "Wind",
    "__version__",
]
