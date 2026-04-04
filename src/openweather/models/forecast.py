from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from openweather.models.location import Location
from openweather.models.weather import Condition, Wind


@dataclass(frozen=True)
class ForecastEntry:
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
    location: Location
    entries: list[ForecastEntry]
