from __future__ import annotations

import respx

from skypulse import SkyPulseClient, CircadianLight
from skypulse._circadian import compute_circadian_light, _cloud_reduction_factor, _quality_key
from skypulse._constants import API_BASE_WEATHER
from datetime import datetime, timezone

WEATHER_URL = f"{API_BASE_WEATHER}/weather"


class TestCircadianComputation:
    def test_quality_excellent(self) -> None:
        result = compute_circadian_light(
            sunrise_ts=1712293200, sunset_ts=1712343600,  # ~14h day
            cloud_cover=20, latitude=50.0,
            now=datetime(2026, 7, 1, tzinfo=timezone.utc),
        )
        assert result.quality == "excellent"
        assert result.quality_label == "Excellent"
        assert result.day_length_hours == 14.0
        assert result.effective_light_hours == 12.6

    def test_quality_poor(self) -> None:
        result = compute_circadian_light(
            sunrise_ts=1712300400, sunset_ts=1712325600,  # 7h day
            cloud_cover=80, latitude=50.0,
            now=datetime(2026, 12, 1, tzinfo=timezone.utc),
        )
        assert result.quality == "poor"
        assert result.quality_label == "Poor"

    def test_quality_good(self) -> None:
        result = compute_circadian_light(
            sunrise_ts=1712293200, sunset_ts=1712336400,  # 12h day
            cloud_cover=40, latitude=50.0,
            now=datetime(2026, 4, 5, tzinfo=timezone.utc),
        )
        assert result.quality == "good"

    def test_polar_summer(self) -> None:
        result = compute_circadian_light(
            sunrise_ts=0, sunset_ts=0, cloud_cover=10, latitude=70.0,
            now=datetime(2026, 6, 21, tzinfo=timezone.utc),
        )
        assert result.quality == "extreme_light"
        assert result.quality_label == "Extreme Light"
        assert result.day_length_hours == 24.0
        assert result.sunrise is None
        assert result.sunset is None

    def test_polar_winter(self) -> None:
        result = compute_circadian_light(
            sunrise_ts=0, sunset_ts=0, cloud_cover=50, latitude=70.0,
            now=datetime(2026, 12, 21, tzinfo=timezone.utc),
        )
        assert result.quality == "extreme_dark"
        assert result.quality_label == "Extreme Dark"
        assert result.day_length_hours == 0.0

    def test_ukrainian_labels(self) -> None:
        result = compute_circadian_light(
            sunrise_ts=0, sunset_ts=0, cloud_cover=10, latitude=70.0,
            now=datetime(2026, 6, 21, tzinfo=timezone.utc),
            language="uk",
        )
        assert result.quality_label == "Полярний день"

    def test_cloud_reduction_brackets(self) -> None:
        assert _cloud_reduction_factor(10) == 0.10
        assert _cloud_reduction_factor(30) == 0.25
        assert _cloud_reduction_factor(60) == 0.45
        assert _cloud_reduction_factor(90) == 0.65

    def test_quality_keys(self) -> None:
        assert _quality_key(13, 14) == "excellent"
        assert _quality_key(10, 14) == "good"
        assert _quality_key(7, 14) == "moderate"
        assert _quality_key(4, 14) == "poor"
        assert _quality_key(0, 0) == "extreme_dark"
        assert _quality_key(24, 24) == "extreme_light"


class TestGetCircadianLight:
    @respx.mock
    def test_success(self, api_key: str) -> None:
        weather = {
            "coord": {"lat": 50.45, "lon": 30.52},
            "sys": {"sunrise": 1712293200, "sunset": 1712340000, "country": "UA"},
            "clouds": {"all": 45},
            "main": {"temp": 15, "feels_like": 13, "temp_min": 12, "temp_max": 17, "humidity": 60, "pressure": 1013},
            "wind": {"speed": 3, "deg": 200},
            "weather": [{"id": 802, "main": "Clouds", "description": "scattered clouds", "icon": "03d"}],
            "visibility": 10000, "dt": 1712316000, "name": "Kyiv", "timezone": 7200, "id": 703448, "cod": 200,
        }
        respx.get(WEATHER_URL).respond(json=weather)

        client = SkyPulseClient(api_key=api_key)
        light = client.get_circadian_light(lat=50.45, lon=30.52)

        assert isinstance(light, CircadianLight)
        assert light.cloud_cover_percent == 45
        assert light.quality in ("excellent", "good", "moderate", "poor")
        assert light.sunrise is not None
        assert light.sunset is not None
        assert light.effective_light_hours > 0
        client.close()
