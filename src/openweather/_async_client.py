from __future__ import annotations

from typing import Any

import httpx

from openweather._base import _BaseClient, parse_forecast, parse_locations, parse_weather
from openweather._constants import DEFAULT_GEOLOCATION_URL, DEFAULT_TIMEOUT
from openweather._endpoints import (
    CURRENT_WEATHER_URL,
    FORECAST_URL,
    GEOCODE_DIRECT_URL,
    GEOCODE_REVERSE_URL,
    build_weather_params,
)
from openweather._geolocation import AsyncGeoLocationTransport
from openweather._http import AsyncHTTPTransport
from openweather._noaa import AsyncNOAATransport
from openweather._storm_mapping import (
    adjust_impact_for_latitude,
    classify_latitude_zone,
    get_health_impact,
)
from openweather.models.common import CacheConfig, RetryConfig, Units
from openweather.models.forecast import Forecast
from openweather.models.health import HealthImpact, StormAlert
from openweather.models.location import Location
from openweather.models.storm import MagneticForecastEntry, MagneticStorm
from openweather.models.weather import Weather


class AsyncOpenWeatherClient(_BaseClient):
    """Asynchronous client for the OpenWeather API.

    Provides async methods to fetch current weather, forecasts, and geocoding
    data. Supports optional response caching and automatic retries.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        units: Units = Units.METRIC,
        language: str = "en",
        cache: CacheConfig | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        retry: RetryConfig | None = None,
        auto_locate: bool = False,
        geolocation_url: str = DEFAULT_GEOLOCATION_URL,
    ) -> None:
        super().__init__(
            api_key, units=units, language=language, cache=cache, retry=retry,
            auto_locate=auto_locate, geolocation_url=geolocation_url,
        )
        self._client = httpx.AsyncClient(timeout=timeout)
        self._transport = AsyncHTTPTransport(self._client, api_key=self._api_key, retry=self._retry, logger=self._logger)
        self._noaa = AsyncNOAATransport(self._client)
        self._geo = AsyncGeoLocationTransport(self._client, base_url=geolocation_url)

    async def _request(self, url: str, params: dict[str, Any]) -> Any:
        return await self._transport.request(url, params)

    async def _resolve_auto_locate(
        self,
        auto_locate: bool | None,
        city: str | None,
        city_id: int | None,
        lat: float | None,
        lon: float | None,
        zip_code: str | None,
    ) -> tuple[str | None, int | None, float | None, float | None, str | None]:
        has_location = any(v is not None for v in [city, city_id, lat, lon, zip_code])
        if has_location:
            return city, city_id, lat, lon, zip_code
        should_auto = auto_locate if auto_locate is not None else self._auto_locate
        if should_auto:
            loc = await self.get_location()
            return None, None, loc.latitude, loc.longitude, None
        raise ValueError(
            "No location provided. Pass a location parameter or set auto_locate=True."
        )

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
        auto_locate: bool | None = None,
    ) -> Weather:
        city, city_id, lat, lon, zip_code = await self._resolve_auto_locate(
            auto_locate, city, city_id, lat, lon, zip_code,
        )
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
        auto_locate: bool | None = None,
    ) -> Forecast:
        city, city_id, lat, lon, zip_code = await self._resolve_auto_locate(
            auto_locate, city, city_id, lat, lon, zip_code,
        )
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

    async def get_magnetic_storm(self) -> MagneticStorm:
        return await self._noaa.fetch_current_kp()

    async def get_magnetic_forecast(self) -> list[MagneticForecastEntry]:
        return await self._noaa.fetch_forecast()

    async def get_storm_health_impact(self) -> HealthImpact:
        storm = await self.get_magnetic_storm()
        return get_health_impact(storm.kp_index, storm.g_scale)

    async def get_location(self, ip: str | None = None) -> Location:
        return await self._geo.locate(ip)

    async def get_storm_alert(
        self,
        *,
        lat: float | None = None,
        lon: float | None = None,
        auto_locate: bool | None = None,
    ) -> StormAlert:
        if lat is not None and lon is not None:
            location = Location(
                name="", latitude=lat, longitude=lon, country="", source="explicit",
            )
        else:
            should_auto = auto_locate if auto_locate is not None else self._auto_locate
            if not should_auto:
                raise ValueError(
                    "No location provided. Pass lat/lon or set auto_locate=True."
                )
            location = await self.get_location()

        storm = await self.get_magnetic_storm()
        kp_int = min(int(storm.kp_index), 9)
        zone = classify_latitude_zone(abs(location.latitude), kp_int)
        base_impact = get_health_impact(storm.kp_index, storm.g_scale)
        adjusted_level = adjust_impact_for_latitude(base_impact.level, zone)
        adjusted_impact = HealthImpact(
            level=adjusted_level,
            kp_index=base_impact.kp_index,
            g_scale=base_impact.g_scale,
            affected_systems=base_impact.affected_systems,
            recommendations=base_impact.recommendations,
            disclaimer=base_impact.disclaimer,
        )
        aurora_visible = zone == "high" and storm.is_storm
        return StormAlert(
            storm=storm,
            health_impact=adjusted_impact,
            latitude=location.latitude,
            longitude=location.longitude,
            location_name=location.name or None,
            aurora_visible=aurora_visible,
            latitude_zone=zone,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client and release resources."""
        await self._client.aclose()

    async def __aenter__(self) -> AsyncOpenWeatherClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
