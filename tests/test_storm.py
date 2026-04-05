from __future__ import annotations

import time
from datetime import timezone

import pytest
import respx

from skypulse import (
    MagneticForecastEntry,
    MagneticStorm,
    SkyPulseClient,
    ParseError,
    ServiceUnavailableError,
)
from skypulse._constants import NOAA_KP_CURRENT_URL, NOAA_KP_FORECAST_URL
from tests.conftest import load_fixture


class TestGetMagneticStorm:
    @respx.mock
    def test_success(self, api_key: str) -> None:
        fixture = load_fixture("noaa_kp_current.json")
        respx.get(NOAA_KP_CURRENT_URL).respond(json=fixture)

        client = SkyPulseClient(api_key=api_key)
        storm = client.get_magnetic_storm()

        assert isinstance(storm, MagneticStorm)
        assert storm.kp_index == 7.0
        assert storm.g_scale == "G3"
        assert storm.severity == "Strong storm"
        assert storm.is_storm is True
        assert storm.stale is False
        assert storm.station_count == 8
        assert storm.observed_at.tzinfo == timezone.utc
        client.close()

    @respx.mock
    def test_no_storm(self, api_key: str) -> None:
        data = [
            ["time_tag", "Kp", "Kp_fraction", "a_running", "station_count"],
            ["2026-04-05 00:00:00.000", "2", "2.00", "7", "8"],
        ]
        respx.get(NOAA_KP_CURRENT_URL).respond(json=data)

        client = SkyPulseClient(api_key=api_key)
        storm = client.get_magnetic_storm()

        assert storm.kp_index == 2.0
        assert storm.g_scale == "G0"
        assert storm.severity == "Quiet"
        assert storm.is_storm is False
        client.close()

    @respx.mock
    def test_noaa_down_no_cache(self, api_key: str) -> None:
        respx.get(NOAA_KP_CURRENT_URL).respond(status_code=503)

        client = SkyPulseClient(api_key=api_key)
        with pytest.raises(ServiceUnavailableError, match="NOAA SWPC"):
            client.get_magnetic_storm()
        client.close()

    @respx.mock
    def test_stale_cache_on_failure(self, api_key: str) -> None:
        fixture = load_fixture("noaa_kp_current.json")
        respx.get(NOAA_KP_CURRENT_URL).respond(json=fixture)

        client = SkyPulseClient(api_key=api_key)
        storm1 = client.get_magnetic_storm()
        assert storm1.stale is False

        # Expire fresh cache but keep within stale window
        client._noaa._kp_cache.fetched_at = time.monotonic() - 700

        respx.get(NOAA_KP_CURRENT_URL).respond(status_code=503)
        storm2 = client.get_magnetic_storm()
        assert storm2.stale is True
        assert storm2.kp_index == 7.0
        client.close()

    @respx.mock
    def test_parse_error(self, api_key: str) -> None:
        respx.get(NOAA_KP_CURRENT_URL).respond(json=[["header_only"]])

        client = SkyPulseClient(api_key=api_key)
        with pytest.raises(ParseError):
            client.get_magnetic_storm()
        client.close()

    @respx.mock
    def test_cache_hit(self, api_key: str) -> None:
        fixture = load_fixture("noaa_kp_current.json")
        route = respx.get(NOAA_KP_CURRENT_URL).respond(json=fixture)

        client = SkyPulseClient(api_key=api_key)
        client.get_magnetic_storm()
        client.get_magnetic_storm()
        assert route.call_count == 1
        client.close()


class TestGetMagneticForecast:
    @respx.mock
    def test_success(self, api_key: str) -> None:
        fixture = load_fixture("noaa_kp_forecast.json")
        respx.get(NOAA_KP_FORECAST_URL).respond(json=fixture)

        client = SkyPulseClient(api_key=api_key)
        forecast = client.get_magnetic_forecast()

        assert len(forecast) == 4
        assert all(isinstance(e, MagneticForecastEntry) for e in forecast)
        assert forecast[0].is_observed is True
        assert forecast[0].predicted_kp == 7.0
        assert forecast[0].g_scale == "G3"
        assert forecast[0].severity == "Strong storm"
        assert forecast[0].is_storm is True
        assert forecast[1].is_observed is False
        assert forecast[1].predicted_kp == 5.0
        assert forecast[1].severity == "Minor storm"
        assert forecast[1].is_storm is True
        client.close()

    @respx.mock
    def test_chronological_order(self, api_key: str) -> None:
        fixture = load_fixture("noaa_kp_forecast.json")
        respx.get(NOAA_KP_FORECAST_URL).respond(json=fixture)

        client = SkyPulseClient(api_key=api_key)
        forecast = client.get_magnetic_forecast()

        for i in range(len(forecast) - 1):
            assert forecast[i].period_start < forecast[i + 1].period_start
        client.close()

    @respx.mock
    def test_period_end_is_start_plus_3h(self, api_key: str) -> None:
        fixture = load_fixture("noaa_kp_forecast.json")
        respx.get(NOAA_KP_FORECAST_URL).respond(json=fixture)

        client = SkyPulseClient(api_key=api_key)
        forecast = client.get_magnetic_forecast()

        for entry in forecast:
            diff = (entry.period_end - entry.period_start).total_seconds()
            assert diff == 3 * 3600
        client.close()

    @respx.mock
    def test_noaa_down(self, api_key: str) -> None:
        respx.get(NOAA_KP_FORECAST_URL).respond(status_code=503)

        client = SkyPulseClient(api_key=api_key)
        with pytest.raises(ServiceUnavailableError, match="NOAA SWPC"):
            client.get_magnetic_forecast()
        client.close()
