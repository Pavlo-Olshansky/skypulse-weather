from __future__ import annotations

import pytest
import respx

from openweather import OpenWeatherClient, StormAlert
from openweather._constants import DEFAULT_GEOLOCATION_URL, NOAA_KP_CURRENT_URL


def _noaa_response(kp: float, kp_int: str) -> list:
    return [
        ["time_tag", "Kp", "Kp_fraction", "a_running", "station_count"],
        ["2026-04-05 06:00:00.000", kp_int, str(kp), "48", "8"],
    ]


class TestGetStormAlert:
    @respx.mock
    def test_high_latitude_full_impact(self, api_key: str) -> None:
        respx.get(NOAA_KP_CURRENT_URL).respond(json=_noaa_response(7.0, "7"))

        client = OpenWeatherClient(api_key=api_key)
        alert = client.get_storm_alert(lat=65.0, lon=25.0)

        assert isinstance(alert, StormAlert)
        assert alert.latitude_zone == "high"
        assert alert.health_impact.level == "high"
        assert alert.aurora_visible is True
        assert alert.latitude == 65.0
        client.close()

    @respx.mock
    def test_mid_latitude_reduced_impact(self, api_key: str) -> None:
        respx.get(NOAA_KP_CURRENT_URL).respond(json=_noaa_response(7.0, "7"))

        client = OpenWeatherClient(api_key=api_key)
        alert = client.get_storm_alert(lat=50.0, lon=10.0)

        assert alert.latitude_zone == "mid"
        assert alert.health_impact.level == "moderate"
        assert alert.aurora_visible is False
        client.close()

    @respx.mock
    def test_low_latitude_minimal_impact(self, api_key: str) -> None:
        respx.get(NOAA_KP_CURRENT_URL).respond(json=_noaa_response(7.0, "7"))

        client = OpenWeatherClient(api_key=api_key)
        alert = client.get_storm_alert(lat=20.0, lon=0.0)

        assert alert.latitude_zone == "low"
        assert alert.health_impact.level == "low"
        assert alert.aurora_visible is False
        client.close()

    @respx.mock
    def test_no_storm_all_zones_none(self, api_key: str) -> None:
        respx.get(NOAA_KP_CURRENT_URL).respond(json=_noaa_response(3.0, "3"))

        client = OpenWeatherClient(api_key=api_key)
        alert = client.get_storm_alert(lat=65.0, lon=25.0)

        assert alert.latitude_zone == "low"
        assert alert.health_impact.level == "none"
        assert alert.aurora_visible is False
        client.close()

    @respx.mock
    def test_auto_locate_integration(self, api_key: str) -> None:
        respx.get(NOAA_KP_CURRENT_URL).respond(json=_noaa_response(7.0, "7"))
        respx.get(DEFAULT_GEOLOCATION_URL).respond(json={
            "status": "success",
            "city": "Helsinki",
            "countryCode": "FI",
            "lat": 60.17,
            "lon": 24.94,
        })

        client = OpenWeatherClient(api_key=api_key)
        alert = client.get_storm_alert(auto_locate=True)

        assert alert.location_name == "Helsinki"
        assert alert.latitude == 60.17
        client.close()

    @respx.mock
    def test_no_location_no_auto_raises(self, api_key: str) -> None:
        client = OpenWeatherClient(api_key=api_key)
        with pytest.raises(ValueError, match="No location provided"):
            client.get_storm_alert()
        client.close()

    @respx.mock
    def test_southern_hemisphere(self, api_key: str) -> None:
        respx.get(NOAA_KP_CURRENT_URL).respond(json=_noaa_response(7.0, "7"))

        client = OpenWeatherClient(api_key=api_key)
        alert = client.get_storm_alert(lat=-65.0, lon=-60.0)

        assert alert.latitude_zone == "high"
        assert alert.health_impact.level == "high"
        assert alert.aurora_visible is True
        client.close()

    @respx.mock
    def test_g5_extreme(self, api_key: str) -> None:
        respx.get(NOAA_KP_CURRENT_URL).respond(json=_noaa_response(9.0, "9"))

        client = OpenWeatherClient(api_key=api_key)
        alert = client.get_storm_alert(lat=50.0, lon=10.0)

        assert alert.latitude_zone == "high"
        assert alert.health_impact.level == "severe"
        assert alert.aurora_visible is True
        client.close()
