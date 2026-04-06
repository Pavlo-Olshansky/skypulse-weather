from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from skypulse.models.air_quality import AirQuality, AirQualityEntry
from skypulse.models.circadian import CircadianLight
from skypulse.models.forecast import Forecast
from skypulse.models.location import Location
from skypulse.models.storm import MagneticForecastEntry, MagneticStorm
from skypulse.models.uv import UVForecastEntry, UVIndex
from skypulse.models.weather import Weather


@dataclass
class WeatherSnapshot:
    """Composite weather data for a single location, returned by ``prefetch()``."""

    weather: Optional[Weather]
    forecast: Optional[Forecast]
    air_quality: Optional[AirQuality]
    air_quality_forecast: List[AirQualityEntry]
    uv: Optional[UVIndex]
    uv_forecast: List[UVForecastEntry]
    circadian: Optional[CircadianLight]
    magnetic_storm: Optional[MagneticStorm]
    magnetic_forecast: List[MagneticForecastEntry]
    location: Location
    fetched_at: datetime
    errors: Dict[str, str] = field(default_factory=dict)
