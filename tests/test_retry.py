from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest
import respx

from openweather.client import OpenWeatherClient
from openweather.errors import AuthenticationError, NotFoundError, RateLimitError, ServerError
from openweather.models.common import RetryConfig

FIXTURES = Path(__file__).parent / "fixtures"
API_KEY = "test-key-abc123"
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


def _load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


@respx.mock
@patch("openweather._http.time.sleep")
def test_retry_on_5xx_with_backoff(mock_sleep: Any) -> None:
    route = respx.get(WEATHER_URL).mock(
        side_effect=[
            httpx.Response(500, json=_load("error_responses/500_server_error.json")),
            httpx.Response(500, json=_load("error_responses/500_server_error.json")),
            httpx.Response(200, json=_load("current_weather.json")),
        ]
    )
    client = OpenWeatherClient(
        API_KEY, retry=RetryConfig(enabled=True, max_retries=3, backoff_factor=0.5)
    )
    weather = client.get_current_weather(city="London")

    assert weather.location.name == "London"
    assert route.call_count == 3
    assert mock_sleep.call_count == 2
    # backoff: 0.5 * 2^0 = 0.5, 0.5 * 2^1 = 1.0
    mock_sleep.assert_any_call(0.5)
    mock_sleep.assert_any_call(1.0)
    client.close()


@respx.mock
@patch("openweather._http.time.sleep")
def test_retry_on_429_with_retry_after(mock_sleep: Any) -> None:
    route = respx.get(WEATHER_URL).mock(
        side_effect=[
            httpx.Response(
                429,
                json=_load("error_responses/429_rate_limit.json"),
                headers={"Retry-After": "5"},
            ),
            httpx.Response(200, json=_load("current_weather.json")),
        ]
    )
    client = OpenWeatherClient(
        API_KEY, retry=RetryConfig(enabled=True, max_retries=2, backoff_factor=0.5)
    )
    weather = client.get_current_weather(city="London")

    assert weather.location.name == "London"
    assert route.call_count == 2
    mock_sleep.assert_called_once_with(5)
    client.close()


@respx.mock
@patch("openweather._http.time.sleep")
def test_retry_max_retries_exhausted(mock_sleep: Any) -> None:
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(500, json=_load("error_responses/500_server_error.json"))
    )
    client = OpenWeatherClient(
        API_KEY, retry=RetryConfig(enabled=True, max_retries=2, backoff_factor=0.1)
    )
    with pytest.raises(ServerError):
        client.get_current_weather(city="London")
    client.close()


@respx.mock
def test_no_retry_on_401() -> None:
    route = respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(401, json=_load("error_responses/401_invalid_key.json"))
    )
    client = OpenWeatherClient(
        API_KEY, retry=RetryConfig(enabled=True, max_retries=3)
    )
    with pytest.raises(AuthenticationError):
        client.get_current_weather(city="London")
    assert route.call_count == 1  # no retries
    client.close()


@respx.mock
def test_no_retry_on_404() -> None:
    route = respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(404, json=_load("error_responses/404_not_found.json"))
    )
    client = OpenWeatherClient(
        API_KEY, retry=RetryConfig(enabled=True, max_retries=3)
    )
    with pytest.raises(NotFoundError):
        client.get_current_weather(city="Atlantis")
    assert route.call_count == 1
    client.close()
