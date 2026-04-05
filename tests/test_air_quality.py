from __future__ import annotations

from datetime import timezone

import respx

from skypulse import AirQuality, AirQualityEntry, SkyPulseClient
from skypulse._constants import API_BASE_AIR_POLLUTION
from tests.conftest import load_fixture

AQ_URL = API_BASE_AIR_POLLUTION
AQ_FORECAST_URL = f"{API_BASE_AIR_POLLUTION}/forecast"


class TestGetAirQuality:
    @respx.mock
    def test_success(self, api_key: str) -> None:
        fixture = load_fixture("air_pollution_current.json")
        respx.get(AQ_URL).respond(json=fixture)

        client = SkyPulseClient(api_key=api_key)
        aq = client.get_air_quality(lat=50.45, lon=30.52)

        assert isinstance(aq, AirQuality)
        assert aq.aqi == 3
        assert aq.label == "Moderate"
        assert aq.co == 230.31
        assert aq.pm2_5 == 12.3
        assert aq.o3 == 62.44
        assert aq.measured_at.tzinfo == timezone.utc
        client.close()

    @respx.mock
    def test_aqi_labels(self, api_key: str) -> None:
        for aqi_val, expected_label in [(1, "Good"), (2, "Fair"), (3, "Moderate"), (4, "Poor"), (5, "Very Poor")]:
            data = {"list": [{"dt": 1712300400, "main": {"aqi": aqi_val}, "components": {"co": 0, "no": 0, "no2": 0, "o3": 0, "so2": 0, "pm2_5": 0, "pm10": 0, "nh3": 0}}]}
            respx.get(AQ_URL).respond(json=data)
            client = SkyPulseClient(api_key=api_key)
            aq = client.get_air_quality(lat=50.45, lon=30.52)
            assert aq.label == expected_label
            client.close()
            respx.reset()

    @respx.mock
    def test_ukrainian_labels(self, api_key: str) -> None:
        data = {"list": [{"dt": 1712300400, "main": {"aqi": 3}, "components": {"co": 0, "no": 0, "no2": 0, "o3": 0, "so2": 0, "pm2_5": 0, "pm10": 0, "nh3": 0}}]}
        respx.get(AQ_URL).respond(json=data)
        client = SkyPulseClient(api_key=api_key, language="uk")
        aq = client.get_air_quality(lat=50.45, lon=30.52)
        assert aq.label == "Помірно"
        client.close()

    @respx.mock
    def test_empty_list_raises_not_found(self, api_key: str) -> None:
        import pytest
        from skypulse import NotFoundError
        respx.get(AQ_URL).respond(json={"list": []})
        client = SkyPulseClient(api_key=api_key)
        with pytest.raises(NotFoundError):
            client.get_air_quality(lat=0.0, lon=0.0)
        client.close()


class TestGetAirQualityForecast:
    @respx.mock
    def test_success(self, api_key: str) -> None:
        fixture = load_fixture("air_pollution_forecast.json")
        respx.get(AQ_FORECAST_URL).respond(json=fixture)

        client = SkyPulseClient(api_key=api_key)
        forecast = client.get_air_quality_forecast(lat=50.45, lon=30.52)

        assert len(forecast) == 3
        assert all(isinstance(e, AirQualityEntry) for e in forecast)
        assert forecast[0].aqi == 2
        assert forecast[0].label == "Fair"
        client.close()

    @respx.mock
    def test_chronological_order(self, api_key: str) -> None:
        fixture = load_fixture("air_pollution_forecast.json")
        respx.get(AQ_FORECAST_URL).respond(json=fixture)

        client = SkyPulseClient(api_key=api_key)
        forecast = client.get_air_quality_forecast(lat=50.45, lon=30.52)

        for i in range(len(forecast) - 1):
            assert forecast[i].measured_at <= forecast[i + 1].measured_at
        client.close()
