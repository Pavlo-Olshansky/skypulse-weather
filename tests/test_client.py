from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from openweather.client import OpenWeatherClient
from openweather.errors import AuthenticationError, NotFoundError
from openweather.models.common import RetryConfig, Units

FIXTURES = Path(__file__).parent / "fixtures"
API_KEY = "test-key-abc123"
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
GEO_DIRECT_URL = "https://api.openweathermap.org/geo/1.0/direct"
GEO_REVERSE_URL = "https://api.openweathermap.org/geo/1.0/reverse"


def _load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())




@respx.mock
def test_get_current_weather_by_city() -> None:
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(200, json=_load("current_weather.json"))
    )
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    weather = client.get_current_weather(city="London")

    assert weather.location.name == "London"
    assert weather.temperature == 15.2
    assert weather.condition.main == "Clear"
    client.close()


@respx.mock
def test_get_current_weather_by_coords() -> None:
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(200, json=_load("current_weather.json"))
    )
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    weather = client.get_current_weather(lat=51.5085, lon=-0.1257)

    assert weather.location.name == "London"
    client.close()


@respx.mock
def test_get_current_weather_by_zip() -> None:
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(200, json=_load("current_weather.json"))
    )
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    weather = client.get_current_weather(zip_code="SW1A 1AA,GB")

    assert weather.location.name == "London"
    client.close()


@respx.mock
def test_get_current_weather_by_city_id() -> None:
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(200, json=_load("current_weather.json"))
    )
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    weather = client.get_current_weather(city_id=2643743)

    assert weather.location.name == "London"
    client.close()


@respx.mock
def test_get_current_weather_unit_override() -> None:
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(200, json=_load("current_weather.json"))
    )
    client = OpenWeatherClient(API_KEY, units=Units.METRIC, retry=RetryConfig(enabled=False))
    weather = client.get_current_weather(city="London", units=Units.IMPERIAL)

    assert weather is not None
    req = respx.calls[0].request
    assert "units=imperial" in str(req.url)
    client.close()


@respx.mock
def test_get_current_weather_invalid_key() -> None:
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(401, json=_load("error_responses/401_invalid_key.json"))
    )
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    with pytest.raises(AuthenticationError) as exc_info:
        client.get_current_weather(city="London")
    assert exc_info.value.status_code == 401
    client.close()


@respx.mock
def test_get_current_weather_not_found() -> None:
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(404, json=_load("error_responses/404_not_found.json"))
    )
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    with pytest.raises(NotFoundError) as exc_info:
        client.get_current_weather(city="Atlantis")
    assert exc_info.value.status_code == 404
    client.close()


def test_get_current_weather_no_location_raises() -> None:
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    with pytest.raises(ValueError, match="Exactly one location"):
        client.get_current_weather()
    client.close()


def test_get_current_weather_multiple_locations_raises() -> None:
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    with pytest.raises(ValueError, match="Exactly one location"):
        client.get_current_weather(city="London", lat=51.5, lon=-0.1)
    client.close()


@respx.mock
def test_client_context_manager() -> None:
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(200, json=_load("current_weather.json"))
    )
    with OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False)) as client:
        weather = client.get_current_weather(city="London")
        assert weather.location.name == "London"
