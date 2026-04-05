from __future__ import annotations

import time
from typing import Any

import httpx

from skypulse._constants import (
    DEFAULT_GEO_CACHE_TTL,
    DEFAULT_GEO_STALE_TTL,
    DEFAULT_GEOLOCATION_FIELDS,
    DEFAULT_GEOLOCATION_URL,
)
from skypulse._errors import ServiceUnavailableError
from skypulse.models.location import Location


class _StaleEntry:
    __slots__ = ("data", "fetched_at")

    def __init__(self, data: Any, fetched_at: float) -> None:
        self.data = data
        self.fetched_at = fetched_at

    def is_fresh(self, ttl: int) -> bool:
        return (time.monotonic() - self.fetched_at) < ttl

    def is_usable(self, stale_ttl: int) -> bool:
        return (time.monotonic() - self.fetched_at) < stale_ttl


class GeoLocationTransport:
    """Synchronous IP geolocation transport with stale-cache fallback."""

    def __init__(self, client: httpx.Client, base_url: str = DEFAULT_GEOLOCATION_URL) -> None:
        self._client = client
        self._base_url = base_url
        self._cache: dict[str, _StaleEntry] = {}

    def locate(self, ip: str | None = None) -> Location:
        cache_key = ip or "auto"
        cached = self._cache.get(cache_key)
        if cached and cached.is_fresh(DEFAULT_GEO_CACHE_TTL):
            return cached.data  # type: ignore[return-value]

        url = f"{self._base_url}{ip}" if ip else self._base_url
        try:
            resp = self._client.get(url, params={"fields": DEFAULT_GEOLOCATION_FIELDS})
            if resp.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"Geolocation returned {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
            data = resp.json()
        except Exception as exc:
            if cached and cached.is_usable(DEFAULT_GEO_STALE_TTL):
                return cached.data  # type: ignore[return-value]
            raise ServiceUnavailableError("IP Geolocation", str(exc)) from exc

        return self._parse_and_cache(data, cache_key)

    def _parse_and_cache(self, data: dict[str, Any], cache_key: str) -> Location:
        if data.get("status") != "success":
            msg = data.get("message", "Unknown error")
            raise ServiceUnavailableError("IP Geolocation", msg)

        location = Location(
            name=data.get("city", "Unknown"),
            latitude=data["lat"],
            longitude=data["lon"],
            country=data.get("countryCode", data.get("country", "")),
            source="ip_geolocation",
        )
        self._cache[cache_key] = _StaleEntry(location, time.monotonic())
        return location


class AsyncGeoLocationTransport:
    """Asynchronous IP geolocation transport with stale-cache fallback."""

    def __init__(self, client: httpx.AsyncClient, base_url: str = DEFAULT_GEOLOCATION_URL) -> None:
        self._client = client
        self._base_url = base_url
        self._cache: dict[str, _StaleEntry] = {}

    async def locate(self, ip: str | None = None) -> Location:
        cache_key = ip or "auto"
        cached = self._cache.get(cache_key)
        if cached and cached.is_fresh(DEFAULT_GEO_CACHE_TTL):
            return cached.data  # type: ignore[return-value]

        url = f"{self._base_url}{ip}" if ip else self._base_url
        try:
            resp = await self._client.get(url, params={"fields": DEFAULT_GEOLOCATION_FIELDS})
            if resp.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"Geolocation returned {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
            data = resp.json()
        except Exception as exc:
            if cached and cached.is_usable(DEFAULT_GEO_STALE_TTL):
                return cached.data  # type: ignore[return-value]
            raise ServiceUnavailableError("IP Geolocation", str(exc)) from exc

        return self._parse_and_cache(data, cache_key)

    def _parse_and_cache(self, data: dict[str, Any], cache_key: str) -> Location:
        if data.get("status") != "success":
            msg = data.get("message", "Unknown error")
            raise ServiceUnavailableError("IP Geolocation", msg)

        location = Location(
            name=data.get("city", "Unknown"),
            latitude=data["lat"],
            longitude=data["lon"],
            country=data.get("countryCode", data.get("country", "")),
            source="ip_geolocation",
        )
        self._cache[cache_key] = _StaleEntry(location, time.monotonic())
        return location
