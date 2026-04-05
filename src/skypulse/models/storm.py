from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MagneticStorm:
    """Current geomagnetic conditions from NOAA SWPC."""

    kp_index: float
    g_scale: str
    severity: str
    is_storm: bool
    observed_at: datetime
    data_age_seconds: int
    stale: bool
    station_count: int


@dataclass(frozen=True)
class MagneticForecastEntry:
    """A single entry in the 3-day geomagnetic forecast."""

    predicted_kp: float
    g_scale: str
    severity: str
    is_storm: bool
    period_start: datetime
    period_end: datetime
    is_observed: bool
