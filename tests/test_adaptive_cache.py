from __future__ import annotations

import time

import respx

from skypulse import SkyPulseClient
from skypulse._constants import API_BASE_WEATHER
from skypulse.models.common import CacheConfig
from tests.conftest import load_fixture

WEATHER_URL = f"{API_BASE_WEATHER}/weather"


class TestAdaptiveCacheTTL:
    @respx.mock
    def test_high_usage_extends_cache_ttl(self, api_key: str) -> None:
        """When OWM usage crosses 50%, cache entries should live 1800s instead of 1s."""
        fixture = load_fixture("current_weather.json")
        route = respx.get(WEATHER_URL).respond(json=fixture)

        client = SkyPulseClient(
            api_key=api_key,
            cache=CacheConfig(enabled=True, ttl=1, owm_daily_limit=10),
        )

        # Make 5 calls to reach 50% usage (5/10)
        for _ in range(5):
            client.get_current_weather(city="London", skip_cache=True)

        # Now make a cached call
        client.get_current_weather(city="London")
        calls_before = route.call_count

        # Wait for base TTL to expire
        time.sleep(1.1)

        # With adaptive TTL (50% usage → 1800s), cache should still be valid
        client.get_current_weather(city="London")
        assert route.call_count == calls_before, "Should have been a cache hit under adaptive TTL"

        client.close()

    @respx.mock
    def test_low_usage_uses_base_ttl(self, api_key: str) -> None:
        """When OWM usage is below 50%, base TTL applies."""
        fixture = load_fixture("current_weather.json")
        route = respx.get(WEATHER_URL).respond(json=fixture)

        client = SkyPulseClient(
            api_key=api_key,
            cache=CacheConfig(enabled=True, ttl=1, owm_daily_limit=1000),
        )

        client.get_current_weather(city="London")
        assert route.call_count == 1

        time.sleep(1.1)

        # Base TTL expired, low usage → no extension
        client.get_current_weather(city="London")
        assert route.call_count == 2

        client.close()
