from __future__ import annotations

import logging
from typing import Any

import httpx
import respx

from skypulse import SkyPulseClient
from skypulse import AuthenticationError, SkyPulseError
from skypulse import RetryConfig

API_KEY = "super-secret-key-xyz"
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


@respx.mock
def test_api_key_not_in_log_output(caplog: Any) -> None:
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(200, json={
            "coord": {"lon": -0.13, "lat": 51.51},
            "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
            "main": {"temp": 15.0, "feels_like": 14.0, "temp_min": 13.0, "temp_max": 17.0,
                      "pressure": 1013, "humidity": 72},
            "visibility": 10000,
            "wind": {"speed": 3.6, "deg": 220},
            "clouds": {"all": 0},
            "dt": 1712179200,
            "sys": {"country": "GB", "sunrise": 1712120000, "sunset": 1712168000},
            "timezone": 3600, "id": 2643743, "name": "London", "cod": 200
        })
    )
    with caplog.at_level(logging.DEBUG, logger="skypulse"):
        client = SkyPulseClient(API_KEY, retry=RetryConfig(enabled=False))
        client.get_current_weather(city="London")
        client.close()

    full_log = caplog.text
    assert API_KEY not in full_log


def test_api_key_not_in_exception_str() -> None:
    err = SkyPulseError(
        message=f"Failed request with key {API_KEY}",
        params={"appid": API_KEY, "q": "London"},
        api_key=API_KEY,
    )
    assert API_KEY not in str(err)
    assert API_KEY not in repr(err)
    assert API_KEY not in err.message
    assert err.params is not None
    assert err.params["appid"] == "***"


def test_api_key_not_in_auth_error() -> None:
    err = AuthenticationError(
        message=f"Invalid API key: {API_KEY}",
        status_code=401,
        api_key=API_KEY,
    )
    assert API_KEY not in str(err)
    assert API_KEY not in repr(err)
    assert "***" in err.message
