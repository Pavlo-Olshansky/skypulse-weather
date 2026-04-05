from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from openweather import OpenWeatherClient
from openweather import (
    APIError,
    AuthenticationError,
    NetworkError,
    NotFoundError,
    OpenWeatherError,
    ParseError,
    RateLimitError,
    ServerError,
    TimeoutError,
)
from openweather import CacheConfig, RetryConfig, Units

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




@respx.mock
def test_get_forecast_by_city() -> None:
    respx.get(FORECAST_URL).mock(
        return_value=httpx.Response(200, json=_load("forecast.json"))
    )
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    forecast = client.get_forecast(city="London")

    assert forecast.location.name == "London"
    assert len(forecast.entries) == 3
    assert forecast.entries[0].temperature == 14.5
    client.close()


@respx.mock
def test_get_forecast_count_parameter() -> None:
    respx.get(FORECAST_URL).mock(
        return_value=httpx.Response(200, json=_load("forecast.json"))
    )
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    forecast = client.get_forecast(city="London", count=3)

    req = respx.calls[0].request
    assert "cnt=3" in str(req.url)
    assert len(forecast.entries) == 3
    client.close()


@respx.mock
def test_get_forecast_imperial_units() -> None:
    respx.get(FORECAST_URL).mock(
        return_value=httpx.Response(200, json=_load("forecast.json"))
    )
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    client.get_forecast(city="London", units=Units.IMPERIAL)

    req = respx.calls[0].request
    assert "units=imperial" in str(req.url)
    client.close()


@respx.mock
def test_get_forecast_entries_ordered() -> None:
    respx.get(FORECAST_URL).mock(
        return_value=httpx.Response(200, json=_load("forecast.json"))
    )
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    forecast = client.get_forecast(city="London")

    timestamps = [e.forecast_at for e in forecast.entries]
    assert timestamps == sorted(timestamps)
    assert len(set(timestamps)) == len(timestamps)
    client.close()




@respx.mock
def test_geocode_direct() -> None:
    respx.get(GEO_DIRECT_URL).mock(
        return_value=httpx.Response(200, json=_load("geocoding_direct.json"))
    )
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    locations = client.geocode("London")

    assert len(locations) == 2
    assert locations[0].name == "London"
    assert locations[0].country == "GB"
    assert locations[0].latitude == 51.5085
    assert locations[0].state == "England"
    client.close()


@respx.mock
def test_geocode_reverse() -> None:
    respx.get(GEO_REVERSE_URL).mock(
        return_value=httpx.Response(200, json=_load("geocoding_reverse.json"))
    )
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    locations = client.reverse_geocode(lat=51.5085, lon=-0.1257)

    assert len(locations) == 1
    assert locations[0].name == "London"
    client.close()


@respx.mock
def test_geocode_multiple_results() -> None:
    respx.get(GEO_DIRECT_URL).mock(
        return_value=httpx.Response(200, json=_load("geocoding_direct.json"))
    )
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    locations = client.geocode("London")

    assert len(locations) == 2
    countries = {loc.country for loc in locations}
    assert "GB" in countries
    assert "CA" in countries
    client.close()


@respx.mock
def test_geocode_limit_parameter() -> None:
    respx.get(GEO_DIRECT_URL).mock(
        return_value=httpx.Response(200, json=_load("geocoding_direct.json"))
    )
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    client.geocode("London", limit=1)

    req = respx.calls[0].request
    assert "limit=1" in str(req.url)
    client.close()




@respx.mock
def test_cache_hit_skips_network() -> None:
    route = respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(200, json=_load("current_weather.json"))
    )
    client = OpenWeatherClient(
        API_KEY,
        cache=CacheConfig(enabled=True, ttl=300),
        retry=RetryConfig(enabled=False),
    )
    w1 = client.get_current_weather(city="London")
    w2 = client.get_current_weather(city="London")

    assert w1.temperature == w2.temperature
    assert route.call_count == 1  # only one network call
    client.close()


@respx.mock
def test_cache_disabled_always_fetches() -> None:
    route = respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(200, json=_load("current_weather.json"))
    )
    client = OpenWeatherClient(
        API_KEY,
        cache=CacheConfig(enabled=False),
        retry=RetryConfig(enabled=False),
    )
    client.get_current_weather(city="London")
    client.get_current_weather(city="London")

    assert route.call_count == 2
    client.close()


@respx.mock
def test_cache_skip_cache_flag() -> None:
    route = respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(200, json=_load("current_weather.json"))
    )
    client = OpenWeatherClient(
        API_KEY,
        cache=CacheConfig(enabled=True, ttl=300),
        retry=RetryConfig(enabled=False),
    )
    client.get_current_weather(city="London")
    client.get_current_weather(city="London", skip_cache=True)

    assert route.call_count == 2
    client.close()


@respx.mock
def test_cache_different_params_different_keys() -> None:
    route = respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(200, json=_load("current_weather.json"))
    )
    client = OpenWeatherClient(
        API_KEY,
        cache=CacheConfig(enabled=True, ttl=300),
        retry=RetryConfig(enabled=False),
    )
    client.get_current_weather(city="London", units=Units.METRIC)
    client.get_current_weather(city="London", units=Units.IMPERIAL)

    assert route.call_count == 2  # different cache keys
    client.close()




@respx.mock
def test_rate_limit_error_with_retry_after() -> None:
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(
            429,
            json=_load("error_responses/429_rate_limit.json"),
            headers={"Retry-After": "30"},
        )
    )
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    with pytest.raises(RateLimitError) as exc_info:
        client.get_current_weather(city="London")
    assert exc_info.value.retry_after == 30
    assert exc_info.value.status_code == 429
    client.close()


@respx.mock
def test_server_error_5xx() -> None:
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(500, json=_load("error_responses/500_server_error.json"))
    )
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    with pytest.raises(ServerError) as exc_info:
        client.get_current_weather(city="London")
    assert exc_info.value.status_code == 500
    client.close()


@respx.mock
def test_parse_error_malformed_json() -> None:
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(200, text="<html>not json</html>")
    )
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    with pytest.raises(ParseError):
        client.get_current_weather(city="London")
    client.close()


@respx.mock
def test_error_carries_context_fields() -> None:
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(404, json=_load("error_responses/404_not_found.json"))
    )
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    with pytest.raises(NotFoundError) as exc_info:
        client.get_current_weather(city="Atlantis")
    err = exc_info.value
    assert err.endpoint is not None
    assert err.params is not None
    assert "appid" not in err.params  # redacted from safe_params
    assert err.status_code == 404
    client.close()


@respx.mock
def test_generic_api_error() -> None:
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(403, json={"cod": 403, "message": "Forbidden"})
    )
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    with pytest.raises(APIError) as exc_info:
        client.get_current_weather(city="London")
    assert exc_info.value.status_code == 403
    client.close()


@respx.mock
def test_network_error() -> None:
    respx.get(WEATHER_URL).mock(side_effect=httpx.ConnectError("Connection refused"))
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    with pytest.raises(NetworkError):
        client.get_current_weather(city="London")
    client.close()


@respx.mock
def test_timeout_error() -> None:
    respx.get(WEATHER_URL).mock(side_effect=httpx.ReadTimeout("Timed out"))
    client = OpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    with pytest.raises(TimeoutError):
        client.get_current_weather(city="London")
    client.close()


@respx.mock
def test_forecast_cache_hit() -> None:
    route = respx.get(FORECAST_URL).mock(
        return_value=httpx.Response(200, json=_load("forecast.json"))
    )
    client = OpenWeatherClient(
        API_KEY,
        cache=CacheConfig(enabled=True, ttl=300),
        retry=RetryConfig(enabled=False),
    )
    f1 = client.get_forecast(city="London")
    f2 = client.get_forecast(city="London")
    assert len(f1.entries) == len(f2.entries)
    assert route.call_count == 1
    client.close()


@respx.mock
def test_forecast_skip_cache() -> None:
    route = respx.get(FORECAST_URL).mock(
        return_value=httpx.Response(200, json=_load("forecast.json"))
    )
    client = OpenWeatherClient(
        API_KEY,
        cache=CacheConfig(enabled=True, ttl=300),
        retry=RetryConfig(enabled=False),
    )
    client.get_forecast(city="London")
    client.get_forecast(city="London", skip_cache=True)
    assert route.call_count == 2
    client.close()


@respx.mock
def test_env_var_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENWEATHER_API_KEY", "env-key-123")
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(200, json=_load("current_weather.json"))
    )
    client = OpenWeatherClient(retry=RetryConfig(enabled=False))
    weather = client.get_current_weather(city="London")
    assert weather.location.name == "London"
    client.close()


@respx.mock
def test_explicit_key_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENWEATHER_API_KEY", "env-key")
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(200, json=_load("current_weather.json"))
    )
    client = OpenWeatherClient("explicit-key", retry=RetryConfig(enabled=False))
    client.get_current_weather(city="London")
    req = respx.calls[0].request
    assert "explicit-key" in str(req.url)
    assert "env-key" not in str(req.url)
    client.close()


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    with pytest.raises(OpenWeatherError, match="No API key provided"):
        OpenWeatherClient()
