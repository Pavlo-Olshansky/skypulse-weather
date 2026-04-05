from __future__ import annotations

import pytest
import respx

from openweather import Location, OpenWeatherClient, ServiceUnavailableError
from openweather._constants import DEFAULT_GEOLOCATION_URL


class TestGetLocation:
    @respx.mock
    def test_success_auto_detect(self, api_key: str) -> None:
        geo_data = {
            "status": "success",
            "city": "London",
            "countryCode": "GB",
            "lat": 51.5085,
            "lon": -0.1257,
        }
        respx.get(DEFAULT_GEOLOCATION_URL).respond(json=geo_data)

        client = OpenWeatherClient(api_key=api_key)
        loc = client.get_location()

        assert isinstance(loc, Location)
        assert loc.name == "London"
        assert loc.country == "GB"
        assert loc.latitude == 51.5085
        assert loc.longitude == -0.1257
        assert loc.source == "ip_geolocation"
        client.close()

    @respx.mock
    def test_explicit_ip(self, api_key: str) -> None:
        geo_data = {
            "status": "success",
            "city": "Berlin",
            "countryCode": "DE",
            "lat": 52.52,
            "lon": 13.405,
        }
        respx.get(f"{DEFAULT_GEOLOCATION_URL}8.8.8.8").respond(json=geo_data)

        client = OpenWeatherClient(api_key=api_key)
        loc = client.get_location(ip="8.8.8.8")

        assert loc.name == "Berlin"
        assert loc.country == "DE"
        client.close()

    @respx.mock
    def test_provider_down(self, api_key: str) -> None:
        respx.get(DEFAULT_GEOLOCATION_URL).respond(status_code=503)

        client = OpenWeatherClient(api_key=api_key)
        with pytest.raises(ServiceUnavailableError, match="IP Geolocation"):
            client.get_location()
        client.close()

    @respx.mock
    def test_provider_fail_status(self, api_key: str) -> None:
        respx.get(DEFAULT_GEOLOCATION_URL).respond(json={
            "status": "fail",
            "message": "reserved range",
            "query": "127.0.0.1",
        })

        client = OpenWeatherClient(api_key=api_key)
        with pytest.raises(ServiceUnavailableError, match="reserved range"):
            client.get_location()
        client.close()

    @respx.mock
    def test_cache_hit(self, api_key: str) -> None:
        geo_data = {
            "status": "success",
            "city": "London",
            "countryCode": "GB",
            "lat": 51.5085,
            "lon": -0.1257,
        }
        route = respx.get(DEFAULT_GEOLOCATION_URL).respond(json=geo_data)

        client = OpenWeatherClient(api_key=api_key)
        client.get_location()
        client.get_location()
        assert route.call_count == 1
        client.close()


class TestAutoLocateOptIn:
    @respx.mock
    def test_no_location_no_auto_locate_raises(self, api_key: str) -> None:
        client = OpenWeatherClient(api_key=api_key)
        with pytest.raises(ValueError, match="No location provided"):
            client.get_current_weather()
        client.close()

    @respx.mock
    def test_explicit_location_takes_precedence(self, api_key: str, current_weather_data: dict) -> None:
        respx.get("https://api.openweathermap.org/data/2.5/weather").respond(json=current_weather_data)

        client = OpenWeatherClient(api_key=api_key, auto_locate=True)
        weather = client.get_current_weather(city="Berlin")
        assert weather is not None
        client.close()

    @respx.mock
    def test_auto_locate_per_call(self, api_key: str, current_weather_data: dict) -> None:
        geo_data = {
            "status": "success",
            "city": "London",
            "countryCode": "GB",
            "lat": 51.5085,
            "lon": -0.1257,
        }
        respx.get(DEFAULT_GEOLOCATION_URL).respond(json=geo_data)
        respx.get("https://api.openweathermap.org/data/2.5/weather").respond(json=current_weather_data)

        client = OpenWeatherClient(api_key=api_key)
        weather = client.get_current_weather(auto_locate=True)
        assert weather is not None
        client.close()
