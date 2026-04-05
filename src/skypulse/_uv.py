from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import httpx

from skypulse._constants import UV_INDEX_API_URL
from skypulse._errors import ParseError, RateLimitError, ServiceUnavailableError
from skypulse._translations import get_label
from skypulse.models.uv import UVForecastEntry, UVIndex


def _uv_risk_key(value: float) -> str:
    if value <= 2:
        return "low"
    elif value <= 5:
        return "moderate"
    elif value <= 7:
        return "high"
    elif value <= 10:
        return "very_high"
    else:
        return "extreme"


class _StaleEntry:
    __slots__ = ("data", "fetched_at")

    def __init__(self, data: Any, fetched_at: float) -> None:
        self.data = data
        self.fetched_at = fetched_at

    def is_fresh(self, ttl: int) -> bool:
        return (time.monotonic() - self.fetched_at) < ttl


UV_CACHE_TTL = 300


class UVTransport:
    """Synchronous CurrentUVIndex API transport."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client
        self._cache: dict[str, _StaleEntry] = {}

    def fetch(self, lat: float, lon: float, language: str = "en") -> dict[str, Any]:
        cache_key = f"{lat:.2f},{lon:.2f}"
        cached = self._cache.get(cache_key)
        if cached and cached.is_fresh(UV_CACHE_TTL):
            return cached.data  # type: ignore[return-value]

        try:
            resp = self._client.get(
                UV_INDEX_API_URL,
                params={"latitude": lat, "longitude": lon},
            )
            if resp.status_code == 429:
                raise RateLimitError(status_code=429, message="UV Index API rate limit exceeded (500/day)")
            if resp.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"UV API returned {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
            data = resp.json()
        except (RateLimitError, ParseError):
            raise
        except Exception as exc:
            raise ServiceUnavailableError("CurrentUVIndex", str(exc)) from exc

        if not data.get("ok"):
            raise ServiceUnavailableError("CurrentUVIndex", data.get("message", "Unknown error"))

        self._cache[cache_key] = _StaleEntry(data, time.monotonic())
        return data

    def get_current(self, lat: float, lon: float, language: str = "en") -> UVIndex:
        data = self.fetch(lat, lon, language)
        return _parse_current(data, language)

    def get_forecast(self, lat: float, lon: float, language: str = "en") -> list[UVForecastEntry]:
        data = self.fetch(lat, lon, language)
        return _parse_forecast(data)


class AsyncUVTransport:
    """Asynchronous CurrentUVIndex API transport."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._cache: dict[str, _StaleEntry] = {}

    async def fetch(self, lat: float, lon: float, language: str = "en") -> dict[str, Any]:
        cache_key = f"{lat:.2f},{lon:.2f}"
        cached = self._cache.get(cache_key)
        if cached and cached.is_fresh(UV_CACHE_TTL):
            return cached.data  # type: ignore[return-value]

        try:
            resp = await self._client.get(
                UV_INDEX_API_URL,
                params={"latitude": lat, "longitude": lon},
            )
            if resp.status_code == 429:
                raise RateLimitError(status_code=429, message="UV Index API rate limit exceeded (500/day)")
            if resp.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"UV API returned {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
            data = resp.json()
        except (RateLimitError, ParseError):
            raise
        except Exception as exc:
            raise ServiceUnavailableError("CurrentUVIndex", str(exc)) from exc

        if not data.get("ok"):
            raise ServiceUnavailableError("CurrentUVIndex", data.get("message", "Unknown error"))

        self._cache[cache_key] = _StaleEntry(data, time.monotonic())
        return data

    async def get_current(self, lat: float, lon: float, language: str = "en") -> UVIndex:
        data = await self.fetch(lat, lon, language)
        return _parse_current(data, language)

    async def get_forecast(self, lat: float, lon: float, language: str = "en") -> list[UVForecastEntry]:
        data = await self.fetch(lat, lon, language)
        return _parse_forecast(data)


def _parse_current(data: dict[str, Any], language: str = "en") -> UVIndex:
    try:
        now = data["now"]
        value = float(now["uvi"])
        risk_key = _uv_risk_key(value)
        return UVIndex(
            value=value,
            risk_level=risk_key,
            risk_label=get_label("uv_risk", risk_key, language),
            measured_at=datetime.fromisoformat(now["time"].replace("Z", "+00:00")),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise ParseError(
            raw_body=str(data)[:500],
            message=f"Failed to parse UV index data: {exc}",
        ) from exc


def _parse_forecast(data: dict[str, Any]) -> list[UVForecastEntry]:
    try:
        entries = []
        for item in data.get("forecast", []):
            entries.append(UVForecastEntry(
                value=float(item["uvi"]),
                forecast_at=datetime.fromisoformat(item["time"].replace("Z", "+00:00")),
            ))
        entries.sort(key=lambda e: e.forecast_at)
        return entries
    except (KeyError, ValueError, TypeError) as exc:
        raise ParseError(
            raw_body=str(data)[:500],
            message=f"Failed to parse UV forecast data: {exc}",
        ) from exc
