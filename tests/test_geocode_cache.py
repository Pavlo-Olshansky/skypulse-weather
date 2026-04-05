from __future__ import annotations

import time

import respx

from skypulse import SkyPulseClient
from skypulse._constants import API_BASE_GEO
from skypulse.models.common import CacheConfig
from tests.conftest import load_fixture

GEOCODE_URL = f"{API_BASE_GEO}/direct"
REVERSE_URL = f"{API_BASE_GEO}/reverse"


class TestGeocodeCacheHit:
    @respx.mock
    def test_repeated_geocode_single_request(self, api_key: str) -> None:
        fixture = load_fixture("geocoding_direct.json")
        route = respx.get(GEOCODE_URL).respond(json=fixture)

        client = SkyPulseClient(api_key=api_key, cache=CacheConfig(enabled=True))
        result1 = client.geocode("London")
        result2 = client.geocode("London")

        assert result1[0].name == result2[0].name
        assert route.call_count == 1
        client.close()

    @respx.mock
    def test_different_cities_separate_requests(self, api_key: str) -> None:
        fixture = load_fixture("geocoding_direct.json")
        route = respx.get(GEOCODE_URL).respond(json=fixture)

        client = SkyPulseClient(api_key=api_key, cache=CacheConfig(enabled=True))
        client.geocode("London")
        client.geocode("Berlin")

        assert route.call_count == 2
        client.close()

    @respx.mock
    def test_reverse_geocode_cache_hit(self, api_key: str) -> None:
        fixture = load_fixture("geocoding_reverse.json")
        route = respx.get(REVERSE_URL).respond(json=fixture)

        client = SkyPulseClient(api_key=api_key, cache=CacheConfig(enabled=True))
        client.reverse_geocode(51.5085, -0.1257)
        client.reverse_geocode(51.5085, -0.1257)

        assert route.call_count == 1
        client.close()


class TestGeocodeCacheTTL:
    @respx.mock
    def test_ttl_expiry_triggers_new_request(self, api_key: str) -> None:
        fixture = load_fixture("geocoding_direct.json")
        route = respx.get(GEOCODE_URL).respond(json=fixture)

        client = SkyPulseClient(
            api_key=api_key, cache=CacheConfig(enabled=True, geo_cache_ttl=1),
        )
        client.geocode("London")
        assert route.call_count == 1

        time.sleep(1.1)

        client.geocode("London")
        assert route.call_count == 2
        client.close()


class TestGeocodeCacheDisabled:
    @respx.mock
    def test_no_cache_when_disabled(self, api_key: str) -> None:
        fixture = load_fixture("geocoding_direct.json")
        route = respx.get(GEOCODE_URL).respond(json=fixture)

        client = SkyPulseClient(api_key=api_key, cache=CacheConfig(enabled=False))
        client.geocode("London")
        client.geocode("London")

        assert route.call_count == 2
        client.close()
