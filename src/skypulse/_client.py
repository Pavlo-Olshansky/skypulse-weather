from __future__ import annotations

from typing import Any

import httpx

from skypulse._base import _BaseClient, parse_forecast, parse_locations, parse_weather
from skypulse._cache import build_cache_key
from skypulse._circadian import compute_circadian_light
from skypulse._constants import DEFAULT_GEOLOCATION_URL, DEFAULT_TIMEOUT
from skypulse._endpoints import (
    AIR_POLLUTION_FORECAST_URL,
    AIR_POLLUTION_URL,
    CURRENT_WEATHER_URL,
    FORECAST_URL,
    GEOCODE_DIRECT_URL,
    GEOCODE_REVERSE_URL,
    build_weather_params,
)
from skypulse._geolocation import GeoLocationTransport
from skypulse._http import HTTPTransport
from skypulse._noaa import NOAATransport
from skypulse._storm_mapping import (
    G_SCALE_LEVELS,
    adjust_impact_for_latitude,
    classify_latitude_zone,
    get_health_impact,
)
from skypulse._translations import get_label
from skypulse._uv import UVTransport
from skypulse.models.air_quality import AirQuality, AirQualityEntry
from skypulse.models.circadian import CircadianLight
from skypulse.models.common import CacheConfig, RetryConfig, Units
from skypulse.models.forecast import Forecast
from skypulse.models.health import HealthImpact, StormAlert
from skypulse.models.location import Location
from skypulse.models.storm import MagneticForecastEntry, MagneticStorm
from skypulse.models.uv import UVForecastEntry, UVIndex
from skypulse.models.weather import Weather


class SkyPulseClient(_BaseClient):
    """Synchronous client for the SkyPulse API.

    Provides methods to fetch current weather, forecasts, and geocoding data.
    Supports optional response caching and automatic retries.
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
        self._client = httpx.Client(timeout=timeout)
        self._transport = HTTPTransport(self._client, api_key=self._api_key, retry=self._retry, logger=self._logger)
        self._noaa = NOAATransport(self._client)
        self._geo = GeoLocationTransport(self._client, base_url=geolocation_url)
        self._uv = UVTransport(self._client)

    def _request(self, url: str, params: dict[str, Any]) -> Any:
        return self._transport.request(url, params)

    def _resolve_auto_locate(
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
            loc = self.get_location()
            return None, None, loc.latitude, loc.longitude, None
        raise ValueError(
            "No location provided. Pass a location parameter or set auto_locate=True."
        )

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
        auto_locate: bool | None = None,
    ) -> Weather:
        city, city_id, lat, lon, zip_code = self._resolve_auto_locate(
            auto_locate, city, city_id, lat, lon, zip_code,
        )
        params = build_weather_params(
            self._api_key, units=(units or self._units).value, lang=language or self._language,
            city=city, city_id=city_id, lat=lat, lon=lon, zip_code=zip_code,
        )
        key, cached = self._check_cache("weather", params, skip_cache)
        if cached is not None:
            return cached  # type: ignore[return-value]
        result = parse_weather(self._request(CURRENT_WEATHER_URL, params))
        self._store_cache(key, result)
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
        auto_locate: bool | None = None,
    ) -> Forecast:
        city, city_id, lat, lon, zip_code = self._resolve_auto_locate(
            auto_locate, city, city_id, lat, lon, zip_code,
        )
        params = build_weather_params(
            self._api_key, units=(units or self._units).value, lang=language or self._language,
            city=city, city_id=city_id, lat=lat, lon=lon, zip_code=zip_code, cnt=count,
        )
        key, cached = self._check_cache("forecast", params, skip_cache)
        if cached is not None:
            return cached  # type: ignore[return-value]
        result = parse_forecast(self._request(FORECAST_URL, params))
        self._store_cache(key, result)
        return result

    def geocode(self, city: str, *, limit: int = 5) -> list[Location]:
        """Convert a city name to geographic coordinates.

        Args:
            city: City name, optionally with state and country code.
            limit: Maximum number of results to return.

        Returns:
            A list of matching ``Location`` objects.
        """
        key = build_cache_key("geocode", q=city, limit=limit)
        cached = self._check_geo_cache(key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        params: dict[str, Any] = {"appid": self._api_key, "q": city, "limit": limit}
        result = parse_locations(self._request(GEOCODE_DIRECT_URL, params))
        self._store_geo_cache(key, result)
        return result

    def reverse_geocode(self, lat: float, lon: float, *, limit: int = 5) -> list[Location]:
        """Convert geographic coordinates to location names.

        Args:
            lat: Latitude.
            lon: Longitude.
            limit: Maximum number of results to return.

        Returns:
            A list of matching ``Location`` objects.
        """
        key = build_cache_key("reverse", lat=f"{lat:.4f}", lon=f"{lon:.4f}", limit=limit)
        cached = self._check_geo_cache(key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        params: dict[str, Any] = {"appid": self._api_key, "lat": lat, "lon": lon, "limit": limit}
        result = parse_locations(self._request(GEOCODE_REVERSE_URL, params))
        self._store_geo_cache(key, result)
        return result

    def get_magnetic_storm(self) -> MagneticStorm:
        return self._noaa.fetch_current_kp(self._language)

    def get_magnetic_forecast(self) -> list[MagneticForecastEntry]:
        return self._noaa.fetch_forecast(self._language)

    def get_storm_health_impact(self) -> HealthImpact:
        storm = self.get_magnetic_storm()
        return get_health_impact(storm.kp_index, storm.g_scale, self._language)

    def get_location(self, ip: str | None = None) -> Location:
        return self._geo.locate(ip)

    def get_storm_alert(
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
            location = self.get_location()

        storm = self.get_magnetic_storm()
        kp_int = min(int(storm.kp_index), 9)
        zone = classify_latitude_zone(abs(location.latitude), kp_int)
        raw_level = G_SCALE_LEVELS.get(storm.g_scale, "none")
        adjusted_raw = adjust_impact_for_latitude(raw_level, zone)
        base_impact = get_health_impact(storm.kp_index, storm.g_scale, self._language)
        adjusted_impact = HealthImpact(
            level=get_label("health_level", adjusted_raw, self._language),
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

    def _resolve_coords(
        self,
        city: str | None,
        lat: float | None,
        lon: float | None,
        auto_locate: bool | None,
    ) -> tuple[float, float]:
        if lat is not None and lon is not None:
            return lat, lon
        if city is not None:
            locations = self.geocode(city, limit=1)
            if not locations:
                from skypulse._errors import NotFoundError
                raise NotFoundError(status_code=404, message=f"City not found: {city}")
            return locations[0].latitude, locations[0].longitude
        should_auto = auto_locate if auto_locate is not None else self._auto_locate
        if should_auto:
            loc = self.get_location()
            return loc.latitude, loc.longitude
        raise ValueError("No location provided. Pass city, lat+lon, or auto_locate=True.")

    def get_air_quality(
        self,
        *,
        city: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        auto_locate: bool | None = None,
        skip_cache: bool = False,
    ) -> AirQuality:
        rlat, rlon = self._resolve_coords(city, lat, lon, auto_locate)
        params: dict[str, Any] = {"appid": self._api_key, "lat": rlat, "lon": rlon}
        key, cached = self._check_cache("aq", params, skip_cache)
        if cached is not None:
            return cached  # type: ignore[return-value]
        data = self._request(AIR_POLLUTION_URL, params)
        result = _parse_air_quality(data, self._language)
        self._store_cache(key, result)
        return result

    def get_air_quality_forecast(
        self,
        *,
        city: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        auto_locate: bool | None = None,
        skip_cache: bool = False,
    ) -> list[AirQualityEntry]:
        rlat, rlon = self._resolve_coords(city, lat, lon, auto_locate)
        params: dict[str, Any] = {"appid": self._api_key, "lat": rlat, "lon": rlon}
        key, cached = self._check_cache("aq_forecast", params, skip_cache)
        if cached is not None:
            return cached  # type: ignore[return-value]
        data = self._request(AIR_POLLUTION_FORECAST_URL, params)
        result = _parse_air_quality_forecast(data, self._language)
        self._store_cache(key, result)
        return result

    def get_uv_index(
        self,
        *,
        city: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        auto_locate: bool | None = None,
    ) -> UVIndex:
        rlat, rlon = self._resolve_coords(city, lat, lon, auto_locate)
        return self._uv.get_current(rlat, rlon, self._language)

    def get_uv_forecast(
        self,
        *,
        city: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        auto_locate: bool | None = None,
    ) -> list[UVForecastEntry]:
        rlat, rlon = self._resolve_coords(city, lat, lon, auto_locate)
        return self._uv.get_forecast(rlat, rlon, self._language)

    def get_circadian_light(
        self,
        *,
        city: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        auto_locate: bool | None = None,
    ) -> CircadianLight:
        rlat, rlon = self._resolve_coords(city, lat, lon, auto_locate)
        weather = self.get_current_weather(lat=rlat, lon=rlon)
        from datetime import datetime, timezone
        return compute_circadian_light(
            sunrise_ts=int(weather.sunrise.timestamp()) if weather.sunrise else 0,
            sunset_ts=int(weather.sunset.timestamp()) if weather.sunset else 0,
            cloud_cover=weather.clouds,
            latitude=rlat,
            now=datetime.now(tz=timezone.utc),
            language=self._language,
        )

    def close(self) -> None:
        """Close the underlying HTTP client and release resources."""
        self._client.close()

    def __enter__(self) -> SkyPulseClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


def _parse_aq_entry(item: dict[str, Any], language: str) -> dict[str, Any]:
    from datetime import datetime, timezone
    aqi = item["main"]["aqi"]
    c = item["components"]
    return {
        "aqi": aqi,
        "label": get_label("aqi_label", str(aqi), language),
        "co": c["co"],
        "no": c["no"],
        "no2": c["no2"],
        "o3": c["o3"],
        "so2": c["so2"],
        "pm2_5": c["pm2_5"],
        "pm10": c["pm10"],
        "nh3": c["nh3"],
        "measured_at": datetime.fromtimestamp(item["dt"], tz=timezone.utc),
    }


def _parse_air_quality(data: dict[str, Any], language: str) -> AirQuality:
    from skypulse._errors import NotFoundError
    items = data.get("list", [])
    if not items:
        raise NotFoundError(status_code=404, message="No air quality data for this location")
    return AirQuality(**_parse_aq_entry(items[0], language))


def _parse_air_quality_forecast(data: dict[str, Any], language: str) -> list[AirQualityEntry]:
    entries = [AirQualityEntry(**_parse_aq_entry(item, language)) for item in data.get("list", [])]
    entries.sort(key=lambda e: e.measured_at)
    return entries
