from __future__ import annotations

from datetime import datetime

from skypulse._translations import get_label
from skypulse.models.circadian import CircadianLight

CLOUD_REDUCTION: list[tuple[int, float]] = [
    (25, 0.10),
    (50, 0.25),
    (75, 0.45),
    (100, 0.65),
]


def _cloud_reduction_factor(cloud_percent: int) -> float:
    for threshold, factor in CLOUD_REDUCTION:
        if cloud_percent <= threshold:
            return factor
    return 0.65


def _quality_key(effective_hours: float, day_length: float) -> str:
    if day_length <= 0:
        return "extreme_dark"
    if day_length >= 24:
        return "extreme_light"
    if effective_hours >= 12:
        return "excellent"
    if effective_hours >= 9:
        return "good"
    if effective_hours >= 6:
        return "moderate"
    return "poor"


def _is_polar_summer(latitude: float, month: int) -> bool:
    if latitude > 0:
        return month in (4, 5, 6, 7, 8, 9)
    else:
        return month in (10, 11, 12, 1, 2, 3)


def compute_circadian_light(
    sunrise_ts: int,
    sunset_ts: int,
    cloud_cover: int,
    latitude: float,
    now: datetime,
    language: str = "en",
) -> CircadianLight:
    if sunrise_ts == 0 and sunset_ts == 0 and abs(latitude) > 60:
        if _is_polar_summer(latitude, now.month):
            day_length = 24.0
        else:
            day_length = 0.0
        quality = _quality_key(day_length, day_length)
        return CircadianLight(
            sunrise=None,
            sunset=None,
            day_length_hours=day_length,
            cloud_cover_percent=cloud_cover,
            effective_light_hours=day_length * (1 - _cloud_reduction_factor(cloud_cover)),
            quality=quality,
            quality_label=get_label("circadian_quality", quality, language),
        )

    from datetime import timezone
    sunrise = datetime.fromtimestamp(sunrise_ts, tz=timezone.utc) if sunrise_ts else None
    sunset = datetime.fromtimestamp(sunset_ts, tz=timezone.utc) if sunset_ts else None

    if sunrise and sunset:
        day_length = (sunset_ts - sunrise_ts) / 3600.0
    else:
        day_length = 12.0

    reduction = _cloud_reduction_factor(cloud_cover)
    effective = day_length * (1 - reduction)
    quality = _quality_key(effective, day_length)

    return CircadianLight(
        sunrise=sunrise,
        sunset=sunset,
        day_length_hours=round(day_length, 2),
        cloud_cover_percent=cloud_cover,
        effective_light_hours=round(effective, 2),
        quality=quality,
        quality_label=get_label("circadian_quality", quality, language),
    )
