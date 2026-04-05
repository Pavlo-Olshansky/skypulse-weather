from __future__ import annotations

import asyncio
from datetime import timezone

import pytest
import respx

from skypulse import AsyncSkyPulseClient, SkyPulseClient, UVIndex, UVForecastEntry, RateLimitError, ServiceUnavailableError
from skypulse._constants import UV_INDEX_API_URL
from skypulse._uv import AsyncUVTransport
from tests.conftest import load_fixture


class TestGetUVIndex:
    @respx.mock
    def test_success(self, api_key: str) -> None:
        fixture = load_fixture("uv_current.json")
        respx.get(UV_INDEX_API_URL).respond(json=fixture)

        client = SkyPulseClient(api_key=api_key)
        uv = client.get_uv_index(lat=50.45, lon=30.52)

        assert isinstance(uv, UVIndex)
        assert uv.value == 6.2
        assert uv.risk_level == "high"
        assert uv.risk_label == "High"
        assert uv.measured_at.tzinfo == timezone.utc
        client.close()

    @respx.mock
    def test_risk_levels(self, api_key: str) -> None:
        for uvi, expected_key, expected_label in [
            (1.5, "low", "Low"),
            (4.0, "moderate", "Moderate"),
            (6.5, "high", "High"),
            (9.0, "very_high", "Very High"),
            (12.0, "extreme", "Extreme"),
        ]:
            data = {"ok": True, "latitude": 50, "longitude": 30, "now": {"time": "2026-04-05T12:00:00.000Z", "uvi": uvi}, "forecast": [], "history": []}
            respx.get(UV_INDEX_API_URL).respond(json=data)
            client = SkyPulseClient(api_key=api_key)
            uv = client.get_uv_index(lat=50.0, lon=30.0)
            assert uv.risk_level == expected_key
            assert uv.risk_label == expected_label
            client.close()
            respx.reset()

    @respx.mock
    def test_ukrainian_label(self, api_key: str) -> None:
        fixture = load_fixture("uv_current.json")
        respx.get(UV_INDEX_API_URL).respond(json=fixture)

        client = SkyPulseClient(api_key=api_key, language="uk")
        uv = client.get_uv_index(lat=50.45, lon=30.52)
        assert uv.risk_label == "Високий"
        client.close()

    @respx.mock
    def test_rate_limit(self, api_key: str) -> None:
        respx.get(UV_INDEX_API_URL).respond(status_code=429)
        client = SkyPulseClient(api_key=api_key)
        with pytest.raises(RateLimitError):
            client.get_uv_index(lat=50.0, lon=30.0)
        client.close()

    @respx.mock
    def test_api_error(self, api_key: str) -> None:
        respx.get(UV_INDEX_API_URL).respond(json={"ok": False, "message": "Invalid"})
        client = SkyPulseClient(api_key=api_key)
        with pytest.raises(ServiceUnavailableError):
            client.get_uv_index(lat=50.0, lon=30.0)
        client.close()


class TestGetUVForecast:
    @respx.mock
    def test_success(self, api_key: str) -> None:
        fixture = load_fixture("uv_current.json")
        respx.get(UV_INDEX_API_URL).respond(json=fixture)

        client = SkyPulseClient(api_key=api_key)
        forecast = client.get_uv_forecast(lat=50.45, lon=30.52)

        assert len(forecast) == 4
        assert all(isinstance(e, UVForecastEntry) for e in forecast)
        assert forecast[0].value == 6.5
        client.close()

    @respx.mock
    def test_chronological_order(self, api_key: str) -> None:
        fixture = load_fixture("uv_current.json")
        respx.get(UV_INDEX_API_URL).respond(json=fixture)

        client = SkyPulseClient(api_key=api_key)
        forecast = client.get_uv_forecast(lat=50.45, lon=30.52)

        for i in range(len(forecast) - 1):
            assert forecast[i].forecast_at <= forecast[i + 1].forecast_at
        client.close()


class TestAsyncUVDeduplication:
    @respx.mock
    @pytest.mark.asyncio
    async def test_concurrent_uv_single_request(self, api_key: str) -> None:
        fixture = load_fixture("uv_current.json")
        route = respx.get(UV_INDEX_API_URL).respond(json=fixture)

        async with AsyncSkyPulseClient(api_key=api_key) as client:
            uv_index, uv_forecast = await asyncio.gather(
                client.get_uv_index(lat=50.45, lon=30.52),
                client.get_uv_forecast(lat=50.45, lon=30.52),
            )

        assert isinstance(uv_index, UVIndex)
        assert len(uv_forecast) == 4
        assert route.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_locks_created_per_key(self, api_key: str) -> None:
        fixture = load_fixture("uv_current.json")
        respx.get(UV_INDEX_API_URL).respond(json=fixture)

        async with AsyncSkyPulseClient(api_key=api_key) as client:
            await client.get_uv_index(lat=50.45, lon=30.52)
            await client.get_uv_index(lat=60.00, lon=25.00)
            assert len(client._uv._locks) == 2
