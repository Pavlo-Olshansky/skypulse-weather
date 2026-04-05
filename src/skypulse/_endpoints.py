from __future__ import annotations

from typing import Any

from skypulse._constants import API_BASE_GEO, API_BASE_WEATHER


def _build_params(api_key: str, **kwargs: Any) -> dict[str, Any]:
    params: dict[str, Any] = {"appid": api_key}
    for k, v in kwargs.items():
        if v is not None:
            params[k] = v
    return params


CURRENT_WEATHER_URL = f"{API_BASE_WEATHER}/weather"
FORECAST_URL = f"{API_BASE_WEATHER}/forecast"
GEOCODE_DIRECT_URL = f"{API_BASE_GEO}/direct"
GEOCODE_REVERSE_URL = f"{API_BASE_GEO}/reverse"


def build_location_params(
    *,
    city: str | None = None,
    city_id: int | None = None,
    lat: float | None = None,
    lon: float | None = None,
    zip_code: str | None = None,
) -> dict[str, Any]:
    provided = sum(
        x is not None
        for x in [city, city_id, zip_code, (lat if lon is not None else None)]
    )
    if lat is not None and lon is None or lon is not None and lat is None:
        raise ValueError("Both lat and lon must be provided together.")
    if provided == 0:
        raise ValueError(
            "Exactly one location parameter required: city, city_id, lat+lon, or zip_code."
        )
    if provided > 1:
        raise ValueError(
            "Exactly one location parameter required: city, city_id, lat+lon, or zip_code."
        )
    params: dict[str, Any] = {}
    if city is not None:
        params["q"] = city
    elif city_id is not None:
        params["id"] = city_id
    elif lat is not None and lon is not None:
        params["lat"] = lat
        params["lon"] = lon
    elif zip_code is not None:
        params["zip"] = zip_code
    return params


def build_weather_params(
    api_key: str,
    *,
    units: str,
    lang: str,
    city: str | None = None,
    city_id: int | None = None,
    lat: float | None = None,
    lon: float | None = None,
    zip_code: str | None = None,
    cnt: int | None = None,
) -> dict[str, Any]:
    location = build_location_params(
        city=city, city_id=city_id, lat=lat, lon=lon, zip_code=zip_code
    )
    return _build_params(api_key, units=units, lang=lang, cnt=cnt, **location)
