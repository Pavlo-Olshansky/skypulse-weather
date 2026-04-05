"""OpenWeather Python SDK — typed, cached, sync + async."""

from openweather._async_client import AsyncOpenWeatherClient
from openweather._client import OpenWeatherClient
from openweather._errors import (
    APIError,
    AuthenticationError,
    NetworkError,
    NotFoundError,
    OpenWeatherError,
    ParseError,
    RateLimitError,
    ServerError,
    ServiceUnavailableError,
    TimeoutError,
)
from openweather._version import __version__
from openweather.models.common import CacheConfig, RetryConfig, Units
from openweather.models.forecast import Forecast, ForecastEntry
from openweather.models.health import HealthImpact, StormAlert
from openweather.models.location import Location
from openweather.models.storm import MagneticForecastEntry, MagneticStorm
from openweather.models.weather import Condition, Weather, Wind

__all__ = [
    "APIError",
    "AsyncOpenWeatherClient",
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
    "OpenWeatherClient",
    "OpenWeatherError",
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
