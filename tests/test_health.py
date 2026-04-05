from __future__ import annotations

import respx

from skypulse import HealthImpact, SkyPulseClient
from skypulse._constants import HEALTH_DISCLAIMER, NOAA_KP_CURRENT_URL


def _make_noaa_response(kp: float, kp_int: str = "7") -> list:
    return [
        ["time_tag", "Kp", "Kp_fraction", "a_running", "station_count"],
        ["2026-04-05 06:00:00.000", kp_int, str(kp), "48", "8"],
    ]


class TestGetStormHealthImpact:
    @respx.mock
    def test_no_storm_g0(self, api_key: str) -> None:
        respx.get(NOAA_KP_CURRENT_URL).respond(json=_make_noaa_response(2.0, "2"))

        client = SkyPulseClient(api_key=api_key)
        impact = client.get_storm_health_impact()

        assert isinstance(impact, HealthImpact)
        assert impact.level == "none"
        assert impact.g_scale == "G0"
        assert impact.affected_systems == []
        assert impact.disclaimer == HEALTH_DISCLAIMER
        client.close()

    @respx.mock
    def test_g1_low(self, api_key: str) -> None:
        respx.get(NOAA_KP_CURRENT_URL).respond(json=_make_noaa_response(5.0, "5"))

        client = SkyPulseClient(api_key=api_key)
        impact = client.get_storm_health_impact()

        assert impact.level == "low"
        assert impact.g_scale == "G1"
        assert "nervous" in impact.affected_systems
        client.close()

    @respx.mock
    def test_g2_moderate(self, api_key: str) -> None:
        respx.get(NOAA_KP_CURRENT_URL).respond(json=_make_noaa_response(6.0, "6"))

        client = SkyPulseClient(api_key=api_key)
        impact = client.get_storm_health_impact()

        assert impact.level == "moderate"
        assert impact.g_scale == "G2"
        assert "cardiovascular" in impact.affected_systems
        assert "nervous" in impact.affected_systems
        client.close()

    @respx.mock
    def test_g3_high(self, api_key: str) -> None:
        respx.get(NOAA_KP_CURRENT_URL).respond(json=_make_noaa_response(7.0, "7"))

        client = SkyPulseClient(api_key=api_key)
        impact = client.get_storm_health_impact()

        assert impact.level == "high"
        assert impact.g_scale == "G3"
        assert "general" in impact.affected_systems
        client.close()

    @respx.mock
    def test_g4_severe(self, api_key: str) -> None:
        respx.get(NOAA_KP_CURRENT_URL).respond(json=_make_noaa_response(8.0, "8"))

        client = SkyPulseClient(api_key=api_key)
        impact = client.get_storm_health_impact()

        assert impact.level == "severe"
        assert impact.g_scale == "G4"
        client.close()

    @respx.mock
    def test_g5_severe(self, api_key: str) -> None:
        respx.get(NOAA_KP_CURRENT_URL).respond(json=_make_noaa_response(9.0, "9"))

        client = SkyPulseClient(api_key=api_key)
        impact = client.get_storm_health_impact()

        assert impact.level == "severe"
        assert impact.g_scale == "G5"
        client.close()

    @respx.mock
    def test_disclaimer_always_present(self, api_key: str) -> None:
        respx.get(NOAA_KP_CURRENT_URL).respond(json=_make_noaa_response(3.0, "3"))

        client = SkyPulseClient(api_key=api_key)
        impact = client.get_storm_health_impact()

        assert impact.disclaimer
        assert "not medical advice" in impact.disclaimer
        client.close()

    @respx.mock
    def test_kp_and_g_scale_preserved(self, api_key: str) -> None:
        respx.get(NOAA_KP_CURRENT_URL).respond(json=_make_noaa_response(7.0, "7"))

        client = SkyPulseClient(api_key=api_key)
        impact = client.get_storm_health_impact()

        assert impact.kp_index == 7.0
        assert impact.g_scale == "G3"
        client.close()
