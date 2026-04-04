from __future__ import annotations

from typing import Any

import httpx

from openweather._endpoints import (
    build_weather_params,
    current_weather_url,
    forecast_url,
    geocode_direct_url,
    geocode_reverse_url,
)
from openweather._http import request_async
from openweather._logging import get_logger
from openweather.client import _parse_forecast, _parse_locations, _parse_weather
from openweather.models.common import CacheConfig, RetryConfig, Units
from openweather.models.forecast import Forecast
from openweather.models.location import Location
from openweather.models.weather import Weather


class AsyncOpenWeatherClient:
    """Asynchronous client for the OpenWeather API.

    Provides async methods to fetch current weather, forecasts, and geocoding
    data. Supports optional response caching and automatic retries.
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
        """Initialize the async OpenWeather client.

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
        self._client = httpx.AsyncClient(timeout=timeout)

    async def get_current_weather(
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
        url = current_weather_url()
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

        data = await request_async(
            self._client,
            url,
            params,
            api_key=self._api_key,
            retry=self._retry,
            logger=self._logger,
        )
        result = _parse_weather(data)

        if self._cache:
            from openweather.cache import build_cache_key

            key = cache_key or build_cache_key(
                "weather",
                **{k: v for k, v in params.items() if k != "appid"},
            )
            self._cache.set(key, result)

        return result

    async def get_forecast(
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
        url = forecast_url()
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

        data = await request_async(
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

    async def geocode(self, city: str, *, limit: int = 5) -> list[Location]:
        """Convert a city name to geographic coordinates.

        Args:
            city: City name, optionally with state and country code.
            limit: Maximum number of results to return.

        Returns:
            A list of matching ``Location`` objects.
        """
        url = geocode_direct_url()
        params: dict[str, Any] = {
            "appid": self._api_key,
            "q": city,
            "limit": limit,
        }
        data = await request_async(
            self._client,
            url,
            params,
            api_key=self._api_key,
            retry=self._retry,
            logger=self._logger,
        )
        return _parse_locations(data)

    async def reverse_geocode(
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
        url = geocode_reverse_url()
        params: dict[str, Any] = {
            "appid": self._api_key,
            "lat": lat,
            "lon": lon,
            "limit": limit,
        }
        data = await request_async(
            self._client,
            url,
            params,
            api_key=self._api_key,
            retry=self._retry,
            logger=self._logger,
        )
        return _parse_locations(data)

    async def close(self) -> None:
        """Close the underlying HTTP client and release resources."""
        await self._client.aclose()

    async def __aenter__(self) -> AsyncOpenWeatherClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
