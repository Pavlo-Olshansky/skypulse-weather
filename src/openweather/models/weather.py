from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from openweather.models.location import Location


@dataclass(frozen=True)
class Condition:
    id: int
    main: str
    description: str
    icon: str


@dataclass(frozen=True)
class Wind:
    speed: float
    direction: int
    gust: float | None = None


@dataclass(frozen=True)
class Weather:
    location: Location
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
    observed_at: datetime
