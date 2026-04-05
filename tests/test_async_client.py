from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from openweather import AsyncOpenWeatherClient
from openweather import CacheConfig, RetryConfig, Units

FIXTURES = Path(__file__).parent / "fixtures"
API_KEY = "test-key-abc123"
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
GEO_DIRECT_URL = "https://api.openweathermap.org/geo/1.0/direct"
GEO_REVERSE_URL = "https://api.openweathermap.org/geo/1.0/reverse"


def _load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.asyncio
@respx.mock
async def test_async_get_current_weather() -> None:
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(200, json=_load("current_weather.json"))
    )
    client = AsyncOpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    weather = await client.get_current_weather(city="London")

    assert weather.location.name == "London"
    assert weather.temperature == 15.2
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_get_forecast() -> None:
    respx.get(FORECAST_URL).mock(
        return_value=httpx.Response(200, json=_load("forecast.json"))
    )
    client = AsyncOpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    forecast = await client.get_forecast(city="London")

    assert forecast.location.name == "London"
    assert len(forecast.entries) == 3
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_geocode() -> None:
    respx.get(GEO_DIRECT_URL).mock(
        return_value=httpx.Response(200, json=_load("geocoding_direct.json"))
    )
    client = AsyncOpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    locations = await client.geocode("London")

    assert len(locations) == 2
    assert locations[0].name == "London"
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_reverse_geocode() -> None:
    respx.get(GEO_REVERSE_URL).mock(
        return_value=httpx.Response(200, json=_load("geocoding_reverse.json"))
    )
    client = AsyncOpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))
    locations = await client.reverse_geocode(lat=51.5085, lon=-0.1257)

    assert len(locations) == 1
    assert locations[0].name == "London"
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_context_manager() -> None:
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(200, json=_load("current_weather.json"))
    )
    async with AsyncOpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False)) as client:
        weather = await client.get_current_weather(city="London")
        assert weather.location.name == "London"


@pytest.mark.asyncio
@respx.mock
async def test_async_concurrent_requests() -> None:
    respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(200, json=_load("current_weather.json"))
    )
    client = AsyncOpenWeatherClient(API_KEY, retry=RetryConfig(enabled=False))

    results = await asyncio.gather(
        client.get_current_weather(city="London"),
        client.get_current_weather(city="Berlin"),
        client.get_current_weather(city="Paris"),
    )

    assert len(results) == 3
    for w in results:
        assert w.location.name == "London"  # all mock same fixture
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_cache_integration() -> None:
    route = respx.get(WEATHER_URL).mock(
        return_value=httpx.Response(200, json=_load("current_weather.json"))
    )
    client = AsyncOpenWeatherClient(
        API_KEY,
        cache=CacheConfig(enabled=True, ttl=300),
        retry=RetryConfig(enabled=False),
    )
    w1 = await client.get_current_weather(city="London")
    w2 = await client.get_current_weather(city="London")

    assert w1.temperature == w2.temperature
    assert route.call_count == 1
    await client.close()
