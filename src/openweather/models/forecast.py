from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from openweather.models.location import Location
from openweather.models.weather import Condition, Wind


@dataclass(frozen=True)
class ForecastEntry:
    """A single 3-hour forecast data point.

    Attributes:
        temperature: Forecasted temperature.
        feels_like: Perceived temperature.
        temp_min: Minimum forecasted temperature for the period.
        temp_max: Maximum forecasted temperature for the period.
        humidity: Humidity percentage (0--100).
        pressure: Atmospheric pressure in hPa.
        visibility: Visibility in metres.
        wind: Wind data.
        clouds: Cloudiness percentage (0--100).
        condition: Weather condition descriptor.
        forecast_at: UTC timestamp this entry is valid for.
    """

    temperature: float
    feels_like: float
    temp_min: float
    temp_max: float
    humidity: int
    pressure: int
    visibility: int
    wind: Wind
    clouds: int
    condition: Condition
    forecast_at: datetime


@dataclass(frozen=True)
class Forecast:
    """5-day / 3-hour weather forecast for a location.

    Attributes:
        location: The location this forecast covers.
        entries: Chronologically ordered list of forecast data points.
    """

    location: Location
    entries: list[ForecastEntry]
