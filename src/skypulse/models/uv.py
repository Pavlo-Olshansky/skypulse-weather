from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class UVIndex:
    """Current UV index measurement."""

    value: float
    risk_level: str
    risk_label: str
    measured_at: datetime


@dataclass(frozen=True)
class UVForecastEntry:
    """Single hourly UV forecast entry."""

    value: float
    forecast_at: datetime
