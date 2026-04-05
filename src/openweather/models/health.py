from __future__ import annotations

from dataclasses import dataclass

from openweather.models.storm import MagneticStorm


@dataclass(frozen=True)
class HealthImpact:
    """Human health impact assessment based on geomagnetic conditions."""

    level: str
    kp_index: float
    g_scale: str
    affected_systems: list[str]
    recommendations: list[str]
    disclaimer: str


@dataclass(frozen=True)
class StormAlert:
    """Location-aware storm notification with latitude-adjusted health impact."""

    storm: MagneticStorm
    health_impact: HealthImpact
    latitude: float
    longitude: float
    location_name: str | None
    aurora_visible: bool
    latitude_zone: str
