from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from openweather._constants import (
    DEFAULT_FORECAST_STALE_TTL,
    DEFAULT_STORM_CACHE_TTL,
    DEFAULT_STORM_STALE_TTL,
    NOAA_KP_CURRENT_URL,
    NOAA_KP_FORECAST_URL,
)
from openweather._errors import ParseError, ServiceUnavailableError
from openweather._storm_mapping import is_storm, kp_to_g_scale
from openweather.models.storm import MagneticForecastEntry, MagneticStorm


class _StaleEntry:
    __slots__ = ("data", "fetched_at")

    def __init__(self, data: Any, fetched_at: float) -> None:
        self.data = data
        self.fetched_at = fetched_at

    def is_fresh(self, ttl: int) -> bool:
        return (time.monotonic() - self.fetched_at) < ttl

    def is_usable(self, stale_ttl: int) -> bool:
        return (time.monotonic() - self.fetched_at) < stale_ttl


class NOAATransport:
    """Synchronous NOAA SWPC transport with stale-cache fallback."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client
        self._kp_cache: _StaleEntry | None = None
        self._forecast_cache: _StaleEntry | None = None

    def fetch_current_kp(self) -> MagneticStorm:
        cached = self._kp_cache
        if cached and cached.is_fresh(DEFAULT_STORM_CACHE_TTL):
            return cached.data  # type: ignore[return-value]

        try:
            resp = self._client.get(NOAA_KP_CURRENT_URL)
            if resp.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"NOAA returned {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
            data = resp.json()
        except Exception as exc:
            if cached and cached.is_usable(DEFAULT_STORM_STALE_TTL):
                stale = cached.data
                return MagneticStorm(
                    kp_index=stale.kp_index,
                    g_scale=stale.g_scale,
                    is_storm=stale.is_storm,
                    observed_at=stale.observed_at,
                    data_age_seconds=int(time.time() - stale.observed_at.timestamp()),
                    stale=True,
                    station_count=stale.station_count,
                )
            if isinstance(exc, httpx.HTTPStatusError):
                raise ServiceUnavailableError("NOAA SWPC", str(exc)) from exc
            raise ServiceUnavailableError("NOAA SWPC", str(exc)) from exc

        storm = _parse_current_kp(data)
        self._kp_cache = _StaleEntry(storm, time.monotonic())
        return storm

    def fetch_forecast(self) -> list[MagneticForecastEntry]:
        cached = self._forecast_cache
        if cached and cached.is_fresh(DEFAULT_STORM_CACHE_TTL):
            return cached.data  # type: ignore[return-value]

        try:
            resp = self._client.get(NOAA_KP_FORECAST_URL)
            if resp.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"NOAA returned {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
            data = resp.json()
        except Exception as exc:
            if cached and cached.is_usable(DEFAULT_FORECAST_STALE_TTL):
                return cached.data  # type: ignore[return-value]
            if isinstance(exc, httpx.HTTPStatusError):
                raise ServiceUnavailableError("NOAA SWPC", str(exc)) from exc
            raise ServiceUnavailableError("NOAA SWPC", str(exc)) from exc

        entries = _parse_forecast(data)
        self._forecast_cache = _StaleEntry(entries, time.monotonic())
        return entries


class AsyncNOAATransport:
    """Asynchronous NOAA SWPC transport with stale-cache fallback."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._kp_cache: _StaleEntry | None = None
        self._forecast_cache: _StaleEntry | None = None

    async def fetch_current_kp(self) -> MagneticStorm:
        cached = self._kp_cache
        if cached and cached.is_fresh(DEFAULT_STORM_CACHE_TTL):
            return cached.data  # type: ignore[return-value]

        try:
            resp = await self._client.get(NOAA_KP_CURRENT_URL)
            if resp.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"NOAA returned {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
            data = resp.json()
        except Exception as exc:
            if cached and cached.is_usable(DEFAULT_STORM_STALE_TTL):
                stale = cached.data
                return MagneticStorm(
                    kp_index=stale.kp_index,
                    g_scale=stale.g_scale,
                    is_storm=stale.is_storm,
                    observed_at=stale.observed_at,
                    data_age_seconds=int(time.time() - stale.observed_at.timestamp()),
                    stale=True,
                    station_count=stale.station_count,
                )
            if isinstance(exc, httpx.HTTPStatusError):
                raise ServiceUnavailableError("NOAA SWPC", str(exc)) from exc
            raise ServiceUnavailableError("NOAA SWPC", str(exc)) from exc

        storm = _parse_current_kp(data)
        self._kp_cache = _StaleEntry(storm, time.monotonic())
        return storm

    async def fetch_forecast(self) -> list[MagneticForecastEntry]:
        cached = self._forecast_cache
        if cached and cached.is_fresh(DEFAULT_STORM_CACHE_TTL):
            return cached.data  # type: ignore[return-value]

        try:
            resp = await self._client.get(NOAA_KP_FORECAST_URL)
            if resp.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"NOAA returned {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
            data = resp.json()
        except Exception as exc:
            if cached and cached.is_usable(DEFAULT_FORECAST_STALE_TTL):
                return cached.data  # type: ignore[return-value]
            if isinstance(exc, httpx.HTTPStatusError):
                raise ServiceUnavailableError("NOAA SWPC", str(exc)) from exc
            raise ServiceUnavailableError("NOAA SWPC", str(exc)) from exc

        entries = _parse_forecast(data)
        self._forecast_cache = _StaleEntry(entries, time.monotonic())
        return entries


def _parse_current_kp(data: list[list[str]]) -> MagneticStorm:
    try:
        if len(data) < 2:
            raise ValueError("Empty NOAA response")
        row = data[-1]
        kp = float(row[2])  # Kp_fraction
        observed_at = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)
        g_scale = kp_to_g_scale(kp)
        station_count = int(row[4])
        return MagneticStorm(
            kp_index=kp,
            g_scale=g_scale,
            is_storm=is_storm(kp),
            observed_at=observed_at,
            data_age_seconds=int(time.time() - observed_at.timestamp()),
            stale=False,
            station_count=station_count,
        )
    except (IndexError, ValueError, TypeError) as exc:
        raise ParseError(
            raw_body=str(data)[:500],
            message=f"Failed to parse NOAA Kp data: {exc}",
        ) from exc


def _parse_forecast(data: list[list[str]]) -> list[MagneticForecastEntry]:
    try:
        if len(data) < 2:
            raise ValueError("Empty NOAA forecast response")
        entries = []
        for row in data[1:]:
            kp = float(row[1])
            g_scale = row[3] if len(row) > 3 else kp_to_g_scale(kp)
            period_start = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)
            entries.append(MagneticForecastEntry(
                predicted_kp=kp,
                g_scale=g_scale,
                is_storm=is_storm(kp),
                period_start=period_start,
                period_end=period_start + timedelta(hours=3),
                is_observed=row[2] == "observed",
            ))
        entries.sort(key=lambda e: e.period_start)
        return entries
    except (IndexError, ValueError, TypeError) as exc:
        raise ParseError(
            raw_body=str(data)[:500],
            message=f"Failed to parse NOAA forecast data: {exc}",
        ) from exc
