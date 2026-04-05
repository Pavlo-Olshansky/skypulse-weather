from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AirQuality:
    """Current air pollution measurement."""

    aqi: int
    label: str
    co: float
    no: float
    no2: float
    o3: float
    so2: float
    pm2_5: float
    pm10: float
    nh3: float
    measured_at: datetime


@dataclass(frozen=True)
class AirQualityEntry:
    """Single entry in the air quality forecast."""

    aqi: int
    label: str
    co: float
    no: float
    no2: float
    o3: float
    so2: float
    pm2_5: float
    pm10: float
    nh3: float
    measured_at: datetime
