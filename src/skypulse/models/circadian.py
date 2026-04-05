from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CircadianLight:
    """Circadian light exposure assessment."""

    sunrise: datetime | None
    sunset: datetime | None
    day_length_hours: float
    cloud_cover_percent: int
    effective_light_hours: float
    quality: str
    quality_label: str
