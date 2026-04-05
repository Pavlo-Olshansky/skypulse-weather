from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from skypulse._constants import DEFAULT_GEOLOCATION_URL, ENV_API_KEY, ENV_SKYPULSE_API_KEY
from skypulse._logging import get_logger
from cachetools import TTLCache

from skypulse._cache import Cache, build_cache_key
from skypulse._errors import SkyPulseError
from skypulse.models.common import CacheConfig, RetryConfig, Units
from skypulse.models.forecast import Forecast, ForecastEntry
from skypulse.models.location import Location
from skypulse.models.weather import Condition, Weather, Wind


def parse_weather(data: dict[str, Any]) -> Weather:
    sys = data.get("sys", {})
    sunrise_ts = sys.get("sunrise")
    sunset_ts = sys.get("sunset")
    return Weather(
        location=Location(
            name=data["name"],
            latitude=data["coord"]["lat"],
            longitude=data["coord"]["lon"],
            country=sys.get("country", ""),
        ),
        temperature=data["main"]["temp"],
        feels_like=data["main"]["feels_like"],
        temp_min=data["main"]["temp_min"],
        temp_max=data["main"]["temp_max"],
        humidity=data["main"]["humidity"],
        pressure=data["main"]["pressure"],
        visibility=data.get("visibility", 0),
        wind=Wind(
            speed=data["wind"]["speed"],
            direction=data["wind"]["deg"],
            gust=data["wind"].get("gust"),
        ),
        clouds=data["clouds"]["all"],
        condition=Condition(
            id=data["weather"][0]["id"],
            main=data["weather"][0]["main"],
            description=data["weather"][0]["description"],
            icon=data["weather"][0]["icon"],
        ),
        observed_at=datetime.fromtimestamp(data["dt"], tz=timezone.utc),
        sunrise=datetime.fromtimestamp(sunrise_ts, tz=timezone.utc) if sunrise_ts else None,
        sunset=datetime.fromtimestamp(sunset_ts, tz=timezone.utc) if sunset_ts else None,
    )


def parse_forecast(data: dict[str, Any]) -> Forecast:
    city = data["city"]
    location = Location(
        name=city["name"],
        latitude=city["coord"]["lat"],
        longitude=city["coord"]["lon"],
        country=city["country"],
    )
    entries = []
    for item in data["list"]:
        entries.append(
            ForecastEntry(
                temperature=item["main"]["temp"],
                feels_like=item["main"]["feels_like"],
                temp_min=item["main"]["temp_min"],
                temp_max=item["main"]["temp_max"],
                humidity=item["main"]["humidity"],
                pressure=item["main"]["pressure"],
                visibility=item.get("visibility", 0),
                wind=Wind(
                    speed=item["wind"]["speed"],
                    direction=item["wind"]["deg"],
                    gust=item["wind"].get("gust"),
                ),
                clouds=item["clouds"]["all"],
                condition=Condition(
                    id=item["weather"][0]["id"],
                    main=item["weather"][0]["main"],
                    description=item["weather"][0]["description"],
                    icon=item["weather"][0]["icon"],
                ),
                forecast_at=datetime.fromtimestamp(item["dt"], tz=timezone.utc),
            )
        )
    return Forecast(location=location, entries=entries)


def parse_locations(data: list[dict[str, Any]]) -> list[Location]:
    return [
        Location(
            name=item["name"],
            latitude=item["lat"],
            longitude=item["lon"],
            country=item["country"],
            state=item.get("state"),
        )
        for item in data
    ]


class _BaseClient:
    """Shared configuration, cache, and parsing for sync/async clients."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        units: Units = Units.METRIC,
        language: str = "en",
        cache: CacheConfig | None = None,
        retry: RetryConfig | None = None,
        auto_locate: bool = False,
        geolocation_url: str = DEFAULT_GEOLOCATION_URL,
    ) -> None:
        resolved_key = (
            api_key
            or os.environ.get(ENV_SKYPULSE_API_KEY, "").strip()
            or os.environ.get(ENV_API_KEY, "").strip()
        )
        if not resolved_key:
            raise SkyPulseError(
                message=f"No API key provided. Pass api_key= or set {ENV_SKYPULSE_API_KEY} environment variable."
            )
        self._api_key = resolved_key
        self._units = units
        self._language = language
        self._cache: Cache | None = None
        self._geo_cache: TTLCache[str, Any] | None = None
        if cache and cache.enabled:
            self._cache = Cache(max_entries=cache.max_entries, default_ttl=cache.ttl)
            self._geo_cache = TTLCache(
                maxsize=cache.geo_cache_max_entries, ttl=cache.geo_cache_ttl,
            )
        self._retry = retry or RetryConfig()
        self._logger = get_logger(api_key)
        self._auto_locate = auto_locate
        self._geolocation_url = geolocation_url

    def _check_cache(self, cache_prefix: str, params: dict[str, Any], skip_cache: bool) -> tuple[str, Any | None]:
        """Build cache key and check for a hit. Returns (key, cached_value_or_None)."""
        key = build_cache_key(cache_prefix, **{k: v for k, v in params.items() if k != "appid"})
        if self._cache and not skip_cache:
            cached = self._cache.get(key)
            if cached is not None:
                self._logger.debug("Cache hit: %s", key)
                return key, cached
        return key, None

    def _store_cache(self, key: str, result: Any) -> None:
        if self._cache:
            self._cache.set(key, result)

    def _check_geo_cache(self, key: str) -> Any | None:
        if self._geo_cache is not None:
            return self._geo_cache.get(key)
        return None

    def _store_geo_cache(self, key: str, value: Any) -> None:
        if self._geo_cache is not None:
            self._geo_cache[key] = value
