from __future__ import annotations

import pytest
import respx

from skypulse import AsyncSkyPulseClient, SkyPulseClient, WeatherSnapshot
from skypulse._constants import (
    API_BASE_AIR_POLLUTION,
    API_BASE_WEATHER,
    NOAA_KP_CURRENT_URL,
    NOAA_KP_FORECAST_URL,
    UV_INDEX_API_URL,
)
from skypulse.models.common import CacheConfig
from tests.conftest import load_fixture

WEATHER_URL = f"{API_BASE_WEATHER}/weather"
FORECAST_URL = f"{API_BASE_WEATHER}/forecast"
AQ_URL = API_BASE_AIR_POLLUTION
AQ_FORECAST_URL = f"{API_BASE_AIR_POLLUTION}/forecast"


def _setup_all_mocks() -> dict[str, respx.Route]:
    weather = {
        "coord": {"lat": 50.45, "lon": 30.52},
        "sys": {"sunrise": 1712293200, "sunset": 1712340000, "country": "UA"},
        "clouds": {"all": 30},
        "main": {"temp": 15, "feels_like": 13, "temp_min": 12, "temp_max": 17, "humidity": 60, "pressure": 1013},
        "wind": {"speed": 3, "deg": 200},
        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
        "visibility": 10000, "dt": 1712316000, "name": "Kyiv", "timezone": 7200, "id": 703448, "cod": 200,
    }
    forecast = load_fixture("forecast.json")
    aq = load_fixture("air_pollution_current.json")
    aq_fc = load_fixture("air_pollution_forecast.json")
    uv = load_fixture("uv_current.json")
    noaa_kp = load_fixture("noaa_kp_current.json")
    noaa_fc = load_fixture("noaa_kp_forecast.json")

    return {
        "weather": respx.get(WEATHER_URL).respond(json=weather),
        "forecast": respx.get(FORECAST_URL).respond(json=forecast),
        "aq": respx.get(AQ_URL).respond(json=aq),
        "aq_forecast": respx.get(AQ_FORECAST_URL).respond(json=aq_fc),
        "uv": respx.get(UV_INDEX_API_URL).respond(json=uv),
        "noaa_kp": respx.get(NOAA_KP_CURRENT_URL).respond(json=noaa_kp),
        "noaa_fc": respx.get(NOAA_KP_FORECAST_URL).respond(json=noaa_fc),
    }


class TestAsyncPrefetch:
    @respx.mock
    @pytest.mark.asyncio
    async def test_all_fields_populated(self, api_key: str) -> None:
        _setup_all_mocks()

        async with AsyncSkyPulseClient(api_key=api_key, cache=CacheConfig(enabled=True)) as client:
            snapshot = await client.prefetch(lat=50.45, lon=30.52)

        assert isinstance(snapshot, WeatherSnapshot)
        assert snapshot.weather is not None
        assert snapshot.forecast is not None
        assert snapshot.air_quality is not None
        assert len(snapshot.air_quality_forecast) > 0
        assert snapshot.uv is not None
        assert len(snapshot.uv_forecast) > 0
        assert snapshot.circadian is not None
        assert snapshot.magnetic_storm is not None
        assert len(snapshot.magnetic_forecast) > 0
        assert snapshot.location.name == "Kyiv"
        assert snapshot.errors == {}

    @respx.mock
    @pytest.mark.asyncio
    async def test_exactly_7_http_calls(self, api_key: str) -> None:
        routes = _setup_all_mocks()

        async with AsyncSkyPulseClient(api_key=api_key, cache=CacheConfig(enabled=True)) as client:
            await client.prefetch(lat=50.45, lon=30.52)

        total = sum(r.call_count for r in routes.values())
        assert total == 7, f"Expected 7 HTTP calls, got {total}"
        assert routes["uv"].call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_partial_failure_uv_down(self, api_key: str) -> None:
        _setup_all_mocks()
        respx.pop("GET", UV_INDEX_API_URL)
        respx.get(UV_INDEX_API_URL).respond(status_code=429)

        async with AsyncSkyPulseClient(api_key=api_key, cache=CacheConfig(enabled=True)) as client:
            snapshot = await client.prefetch(lat=50.45, lon=30.52)

        assert snapshot.weather is not None
        assert snapshot.uv is None
        assert "uv" in snapshot.errors

    @respx.mock
    @pytest.mark.asyncio
    async def test_cache_hit_after_prefetch(self, api_key: str) -> None:
        routes = _setup_all_mocks()

        async with AsyncSkyPulseClient(api_key=api_key, cache=CacheConfig(enabled=True)) as client:
            await client.prefetch(lat=50.45, lon=30.52)
            weather_calls_before = routes["weather"].call_count

            weather = await client.get_current_weather(lat=50.45, lon=30.52)

        assert weather is not None
        assert routes["weather"].call_count == weather_calls_before

    @respx.mock
    @pytest.mark.asyncio
    async def test_circadian_none_when_weather_fails(self, api_key: str) -> None:
        _setup_all_mocks()
        respx.pop("GET", WEATHER_URL)
        respx.get(WEATHER_URL).respond(status_code=500)

        async with AsyncSkyPulseClient(api_key=api_key, cache=CacheConfig(enabled=True)) as client:
            snapshot = await client.prefetch(lat=50.45, lon=30.52)

        assert snapshot.weather is None
        assert snapshot.circadian is None


class TestSyncPrefetch:
    @respx.mock
    def test_all_fields_populated(self, api_key: str) -> None:
        _setup_all_mocks()

        client = SkyPulseClient(api_key=api_key, cache=CacheConfig(enabled=True))
        snapshot = client.prefetch(lat=50.45, lon=30.52)

        assert isinstance(snapshot, WeatherSnapshot)
        assert snapshot.weather is not None
        assert snapshot.forecast is not None
        assert snapshot.circadian is not None
        assert snapshot.errors == {}
        client.close()

    @respx.mock
    def test_cache_hit_after_prefetch(self, api_key: str) -> None:
        routes = _setup_all_mocks()

        client = SkyPulseClient(api_key=api_key, cache=CacheConfig(enabled=True))
        client.prefetch(lat=50.45, lon=30.52)
        weather_calls_before = routes["weather"].call_count

        client.get_current_weather(lat=50.45, lon=30.52)
        assert routes["weather"].call_count == weather_calls_before
        client.close()
