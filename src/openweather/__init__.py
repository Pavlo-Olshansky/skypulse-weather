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
    TimeoutError,
)
from openweather._version import __version__
from openweather.models.common import CacheConfig, RetryConfig, Units
from openweather.models.forecast import Forecast, ForecastEntry
from openweather.models.location import Location
from openweather.models.weather import Condition, Weather, Wind

__all__ = [
    "APIError",
    "AsyncOpenWeatherClient",
    "AuthenticationError",
    "CacheConfig",
    "Condition",
    "Forecast",
    "ForecastEntry",
    "Location",
    "NetworkError",
    "NotFoundError",
    "OpenWeatherClient",
    "OpenWeatherError",
    "ParseError",
    "RateLimitError",
    "RetryConfig",
    "ServerError",
    "TimeoutError",
    "Units",
    "Weather",
    "Wind",
    "__version__",
]
