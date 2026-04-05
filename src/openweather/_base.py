from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from openweather._constants import ENV_API_KEY
from openweather._logging import get_logger
from openweather.cache import Cache, build_cache_key
from openweather.errors import OpenWeatherError
from openweather.models.common import CacheConfig, RetryConfig, Units
from openweather.models.forecast import Forecast, ForecastEntry
from openweather.models.location import Location
from openweather.models.weather import Condition, Weather, Wind


def parse_weather(data: dict[str, Any]) -> Weather:
    return Weather(
        location=Location(
            name=data["name"],
            latitude=data["coord"]["lat"],
            longitude=data["coord"]["lon"],
            country=data["sys"]["country"],
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
    ) -> None:
        resolved_key = api_key or os.environ.get(ENV_API_KEY, "").strip()
        if not resolved_key:
            raise OpenWeatherError(
                message=f"No API key provided. Pass api_key= or set {ENV_API_KEY} environment variable."
            )
        self._api_key = resolved_key
        self._units = units
        self._language = language
        self._cache: Cache | None = None
        if cache and cache.enabled:
            self._cache = Cache(max_entries=cache.max_entries, default_ttl=cache.ttl)
        self._retry = retry or RetryConfig()
        self._logger = get_logger(api_key)

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
