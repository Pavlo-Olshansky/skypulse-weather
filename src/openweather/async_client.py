from __future__ import annotations

from typing import Any

import httpx

from openweather._base import _BaseClient, parse_forecast, parse_locations, parse_weather
from openweather._constants import DEFAULT_TIMEOUT
from openweather._endpoints import (
    CURRENT_WEATHER_URL,
    FORECAST_URL,
    GEOCODE_DIRECT_URL,
    GEOCODE_REVERSE_URL,
    build_weather_params,
)
from openweather._http import AsyncHTTPTransport
from openweather.models.common import CacheConfig, RetryConfig, Units
from openweather.models.forecast import Forecast
from openweather.models.location import Location
from openweather.models.weather import Weather


class AsyncOpenWeatherClient(_BaseClient):
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
        timeout: float = DEFAULT_TIMEOUT,
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
        super().__init__(api_key, units=units, language=language, cache=cache, retry=retry)
        self._client = httpx.AsyncClient(timeout=timeout)
        self._transport = AsyncHTTPTransport(self._client, api_key=self._api_key, retry=self._retry, logger=self._logger)

    async def _request(self, url: str, params: dict[str, Any]) -> Any:
        return await self._transport.request(url, params)

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
        params = build_weather_params(
            self._api_key, units=(units or self._units).value, lang=language or self._language,
            city=city, city_id=city_id, lat=lat, lon=lon, zip_code=zip_code,
        )
        key, cached = self._check_cache("weather", params, skip_cache)
        if cached is not None:
            return cached  # type: ignore[return-value]
        result = parse_weather(await self._request(CURRENT_WEATHER_URL, params))
        self._store_cache(key, result)
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
        params = build_weather_params(
            self._api_key, units=(units or self._units).value, lang=language or self._language,
            city=city, city_id=city_id, lat=lat, lon=lon, zip_code=zip_code, cnt=count,
        )
        key, cached = self._check_cache("forecast", params, skip_cache)
        if cached is not None:
            return cached  # type: ignore[return-value]
        result = parse_forecast(await self._request(FORECAST_URL, params))
        self._store_cache(key, result)
        return result

    async def geocode(self, city: str, *, limit: int = 5) -> list[Location]:
        """Convert a city name to geographic coordinates.

        Args:
            city: City name, optionally with state and country code.
            limit: Maximum number of results to return.

        Returns:
            A list of matching ``Location`` objects.
        """
        params: dict[str, Any] = {"appid": self._api_key, "q": city, "limit": limit}
        return parse_locations(await self._request(GEOCODE_DIRECT_URL, params))

    async def reverse_geocode(self, lat: float, lon: float, *, limit: int = 5) -> list[Location]:
        """Convert geographic coordinates to location names.

        Args:
            lat: Latitude.
            lon: Longitude.
            limit: Maximum number of results to return.

        Returns:
            A list of matching ``Location`` objects.
        """
        params: dict[str, Any] = {"appid": self._api_key, "lat": lat, "lon": lon, "limit": limit}
        return parse_locations(await self._request(GEOCODE_REVERSE_URL, params))

    async def close(self) -> None:
        """Close the underlying HTTP client and release resources."""
        await self._client.aclose()

    async def __aenter__(self) -> AsyncOpenWeatherClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
