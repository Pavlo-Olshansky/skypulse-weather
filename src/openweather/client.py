from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from openweather._endpoints import (
    CURRENT_WEATHER_URL,
    FORECAST_URL,
    GEOCODE_DIRECT_URL,
    GEOCODE_REVERSE_URL,
    build_weather_params,
)
from openweather._http import request_sync
from openweather._logging import get_logger
from openweather.models.common import CacheConfig, RetryConfig, Units
from openweather.models.forecast import Forecast, ForecastEntry
from openweather.models.location import Location
from openweather.models.weather import Condition, Weather, Wind


def _parse_location_from_weather(data: dict[str, Any]) -> Location:
    return Location(
        name=data["name"],
        latitude=data["coord"]["lat"],
        longitude=data["coord"]["lon"],
        country=data["sys"]["country"],
    )


def _parse_condition(data: dict[str, Any]) -> Condition:
    w = data["weather"][0]
    return Condition(id=w["id"], main=w["main"], description=w["description"], icon=w["icon"])


def _parse_wind(data: dict[str, Any]) -> Wind:
    return Wind(
        speed=data["wind"]["speed"],
        direction=data["wind"]["deg"],
        gust=data["wind"].get("gust"),
    )


def _parse_weather(data: dict[str, Any]) -> Weather:
    return Weather(
        location=_parse_location_from_weather(data),
        temperature=data["main"]["temp"],
        feels_like=data["main"]["feels_like"],
        temp_min=data["main"]["temp_min"],
        temp_max=data["main"]["temp_max"],
        humidity=data["main"]["humidity"],
        pressure=data["main"]["pressure"],
        visibility=data.get("visibility", 0),
        wind=_parse_wind(data),
        clouds=data["clouds"]["all"],
        condition=_parse_condition(data),
        observed_at=datetime.fromtimestamp(data["dt"], tz=timezone.utc),
    )


def _parse_forecast(data: dict[str, Any]) -> Forecast:
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


def _parse_locations(data: list[dict[str, Any]]) -> list[Location]:
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


class OpenWeatherClient:
    """Synchronous client for the OpenWeather API.

    Provides methods to fetch current weather, forecasts, and geocoding data.
    Supports optional response caching and automatic retries.
    """

    def __init__(
        self,
        api_key: str,
        *,
        units: Units = Units.METRIC,
        language: str = "en",
        cache: CacheConfig | None = None,
        timeout: float = 30.0,
        retry: RetryConfig | None = None,
    ) -> None:
        """Initialize the OpenWeather client.

        Args:
            api_key: OpenWeather API key.
            units: Measurement units for temperature and wind speed.
            language: Language code for weather descriptions (e.g. ``"en"``).
            cache: Optional cache configuration. ``None`` disables caching.
            timeout: HTTP request timeout in seconds.
            retry: Optional retry configuration. Uses defaults if ``None``.
        """
        self._api_key = api_key
        self._units = units
        self._language = language
        self._cache_config = cache
        self._cache: Any = None
        if cache and cache.enabled:
            from openweather.cache import Cache

            self._cache = Cache(
                max_entries=cache.max_entries, default_ttl=cache.ttl
            )
        self._retry = retry or RetryConfig()
        self._logger = get_logger(api_key)
        self._client = httpx.Client(timeout=timeout)

    def get_current_weather(
        self,
        *,
        city: str | None = None,
        city_id: int | None = None,
        lat: float | None = None,
        lon: float | None = None,
        zip_code: str | None = None,
        units: Units | None = None,
        language: str | None = None,
        skip_cache: bool = False,
    ) -> Weather:
        """Fetch current weather for a location.

        Provide exactly one location identifier (city name, city ID,
        coordinates, or zip code).

        Args:
            city: City name, optionally with country code (e.g. ``"London,GB"``).
            city_id: OpenWeather city ID.
            lat: Latitude for coordinate-based lookup.
            lon: Longitude for coordinate-based lookup.
            zip_code: Zip/postal code, optionally with country (e.g. ``"10001,US"``).
            units: Override the client-level measurement units for this request.
            language: Override the client-level language for this request.
            skip_cache: If ``True``, bypass the read cache (result is still stored).

        Returns:
            A ``Weather`` object with current conditions.
        """
        effective_units = units or self._units
        effective_lang = language or self._language
        url = CURRENT_WEATHER_URL
        params = build_weather_params(
            self._api_key,
            units=effective_units.value,
            lang=effective_lang,
            city=city,
            city_id=city_id,
            lat=lat,
            lon=lon,
            zip_code=zip_code,
        )

        cache_key = None
        if self._cache and not skip_cache:
            from openweather.cache import build_cache_key

            cache_key = build_cache_key(
                "weather",
                **{k: v for k, v in params.items() if k != "appid"},
            )
            cached = self._cache.get(cache_key)
            if cached is not None:
                self._logger.debug("Cache hit: %s", cache_key)
                return cached  # type: ignore[return-value]

        data = request_sync(
            self._client,
            url,
            params,
            api_key=self._api_key,
            retry=self._retry,
            logger=self._logger,
        )
        result = _parse_weather(data)

        if self._cache and cache_key:
            self._cache.set(cache_key, result)
        elif self._cache and skip_cache:
            from openweather.cache import build_cache_key

            key = build_cache_key(
                "weather",
                **{k: v for k, v in params.items() if k != "appid"},
            )
            self._cache.set(key, result)

        return result

    def get_forecast(
        self,
        *,
        city: str | None = None,
        city_id: int | None = None,
        lat: float | None = None,
        lon: float | None = None,
        zip_code: str | None = None,
        units: Units | None = None,
        language: str | None = None,
        count: int | None = None,
        skip_cache: bool = False,
    ) -> Forecast:
        """Fetch a 5-day / 3-hour forecast for a location.

        Provide exactly one location identifier (city name, city ID,
        coordinates, or zip code).

        Args:
            city: City name, optionally with country code.
            city_id: OpenWeather city ID.
            lat: Latitude for coordinate-based lookup.
            lon: Longitude for coordinate-based lookup.
            zip_code: Zip/postal code, optionally with country.
            units: Override the client-level measurement units for this request.
            language: Override the client-level language for this request.
            count: Maximum number of forecast entries to return.
            skip_cache: If ``True``, bypass the read cache (result is still stored).

        Returns:
            A ``Forecast`` containing the location and a list of forecast entries.
        """
        effective_units = units or self._units
        effective_lang = language or self._language
        url = FORECAST_URL
        params = build_weather_params(
            self._api_key,
            units=effective_units.value,
            lang=effective_lang,
            city=city,
            city_id=city_id,
            lat=lat,
            lon=lon,
            zip_code=zip_code,
            cnt=count,
        )

        cache_key = None
        if self._cache and not skip_cache:
            from openweather.cache import build_cache_key

            cache_key = build_cache_key(
                "forecast",
                **{k: v for k, v in params.items() if k != "appid"},
            )
            cached = self._cache.get(cache_key)
            if cached is not None:
                self._logger.debug("Cache hit: %s", cache_key)
                return cached  # type: ignore[return-value]

        data = request_sync(
            self._client,
            url,
            params,
            api_key=self._api_key,
            retry=self._retry,
            logger=self._logger,
        )
        result = _parse_forecast(data)

        if self._cache:
            from openweather.cache import build_cache_key

            key = cache_key or build_cache_key(
                "forecast",
                **{k: v for k, v in params.items() if k != "appid"},
            )
            self._cache.set(key, result)

        return result

    def geocode(self, city: str, *, limit: int = 5) -> list[Location]:
        """Convert a city name to geographic coordinates.

        Args:
            city: City name, optionally with state and country code.
            limit: Maximum number of results to return.

        Returns:
            A list of matching ``Location`` objects.
        """
        url = GEOCODE_DIRECT_URL
        params: dict[str, Any] = {
            "appid": self._api_key,
            "q": city,
            "limit": limit,
        }
        data = request_sync(
            self._client,
            url,
            params,
            api_key=self._api_key,
            retry=self._retry,
            logger=self._logger,
        )
        return _parse_locations(data)

    def reverse_geocode(
        self, lat: float, lon: float, *, limit: int = 5
    ) -> list[Location]:
        """Convert geographic coordinates to location names.

        Args:
            lat: Latitude.
            lon: Longitude.
            limit: Maximum number of results to return.

        Returns:
            A list of matching ``Location`` objects.
        """
        url = GEOCODE_REVERSE_URL
        params: dict[str, Any] = {
            "appid": self._api_key,
            "lat": lat,
            "lon": lon,
            "limit": limit,
        }
        data = request_sync(
            self._client,
            url,
            params,
            api_key=self._api_key,
            retry=self._retry,
            logger=self._logger,
        )
        return _parse_locations(data)

    def close(self) -> None:
        """Close the underlying HTTP client and release resources."""
        self._client.close()

    def __enter__(self) -> OpenWeatherClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
