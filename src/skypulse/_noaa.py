from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from skypulse._constants import (
    DEFAULT_FORECAST_STALE_TTL,
    DEFAULT_STORM_CACHE_TTL,
    DEFAULT_STORM_STALE_TTL,
    NOAA_KP_CURRENT_URL,
    NOAA_KP_FORECAST_URL,
)
from skypulse._errors import ParseError, ServiceUnavailableError
from skypulse._storm_mapping import g_scale_to_severity, is_storm, kp_to_g_scale
from skypulse.models.storm import MagneticForecastEntry, MagneticStorm


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

    def fetch_current_kp(self, language: str = "en") -> MagneticStorm:
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
                    severity=stale.severity,
                    is_storm=stale.is_storm,
                    observed_at=stale.observed_at,
                    data_age_seconds=int(time.time() - stale.observed_at.timestamp()),
                    stale=True,
                    station_count=stale.station_count,
                )
            if isinstance(exc, httpx.HTTPStatusError):
                raise ServiceUnavailableError("NOAA SWPC", str(exc)) from exc
            raise ServiceUnavailableError("NOAA SWPC", str(exc)) from exc

        storm = _parse_current_kp(data, language)
        self._kp_cache = _StaleEntry(storm, time.monotonic())
        return storm

    def fetch_forecast(self, language: str = "en") -> list[MagneticForecastEntry]:
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

        entries = _parse_forecast(data, language)
        self._forecast_cache = _StaleEntry(entries, time.monotonic())
        return entries


class AsyncNOAATransport:
    """Asynchronous NOAA SWPC transport with stale-cache fallback."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._kp_cache: _StaleEntry | None = None
        self._forecast_cache: _StaleEntry | None = None

    async def fetch_current_kp(self, language: str = "en") -> MagneticStorm:
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
                    severity=stale.severity,
                    is_storm=stale.is_storm,
                    observed_at=stale.observed_at,
                    data_age_seconds=int(time.time() - stale.observed_at.timestamp()),
                    stale=True,
                    station_count=stale.station_count,
                )
            if isinstance(exc, httpx.HTTPStatusError):
                raise ServiceUnavailableError("NOAA SWPC", str(exc)) from exc
            raise ServiceUnavailableError("NOAA SWPC", str(exc)) from exc

        storm = _parse_current_kp(data, language)
        self._kp_cache = _StaleEntry(storm, time.monotonic())
        return storm

    async def fetch_forecast(self, language: str = "en") -> list[MagneticForecastEntry]:
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

        entries = _parse_forecast(data, language)
        self._forecast_cache = _StaleEntry(entries, time.monotonic())
        return entries


def _parse_time(raw: str) -> datetime:
    """Parse NOAA time strings in both old and new formats."""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Unrecognised time format: {raw}")


def _parse_current_kp(data: list, language: str = "en") -> MagneticStorm:
    try:
        if not data:
            raise ValueError("Empty NOAA response")
        row = data[-1]

        # New format: list of dicts with "time_tag", "Kp", "station_count"
        if isinstance(row, dict):
            kp = float(row["Kp"])
            observed_at = _parse_time(row["time_tag"])
            station_count = int(row.get("station_count", 0))
        # Legacy format: list of lists ["time", ..., "kp_fraction", ..., "station_count"]
        else:
            if len(data) < 2:
                raise ValueError("Empty NOAA response")
            row = data[-1]
            kp = float(row[2])
            observed_at = _parse_time(row[0])
            station_count = int(row[4])

        g_scale = kp_to_g_scale(kp)
        return MagneticStorm(
            kp_index=kp,
            g_scale=g_scale,
            severity=g_scale_to_severity(g_scale, language),
            is_storm=is_storm(kp),
            observed_at=observed_at,
            data_age_seconds=int(time.time() - observed_at.timestamp()),
            stale=False,
            station_count=station_count,
        )
    except (IndexError, KeyError, ValueError, TypeError) as exc:
        raise ParseError(
            raw_body=str(data)[:500],
            message=f"Failed to parse NOAA Kp data: {exc}",
        ) from exc


def _parse_forecast(data: list, language: str = "en") -> list[MagneticForecastEntry]:
    try:
        if not data:
            raise ValueError("Empty NOAA forecast response")
        entries = []

        # New format: list of dicts with "time_tag", "kp", "observed", "noaa_scale"
        if isinstance(data[0], dict):
            for row in data:
                kp = float(row["kp"])
                noaa_scale = row.get("noaa_scale")
                g_scale = noaa_scale if noaa_scale else kp_to_g_scale(kp)
                period_start = _parse_time(row["time_tag"])
                entries.append(MagneticForecastEntry(
                    predicted_kp=kp,
                    g_scale=g_scale,
                    severity=g_scale_to_severity(g_scale, language),
                    is_storm=is_storm(kp),
                    period_start=period_start,
                    period_end=period_start + timedelta(hours=3),
                    is_observed=row.get("observed") == "observed",
                ))
        # Legacy format: list of lists with header row
        else:
            for row in data[1:]:
                kp = float(row[1])
                g_scale = row[3] if len(row) > 3 else kp_to_g_scale(kp)
                period_start = _parse_time(row[0])
                entries.append(MagneticForecastEntry(
                    predicted_kp=kp,
                    g_scale=g_scale,
                    severity=g_scale_to_severity(g_scale, language),
                    is_storm=is_storm(kp),
                    period_start=period_start,
                    period_end=period_start + timedelta(hours=3),
                    is_observed=row[2] == "observed",
                ))

        entries.sort(key=lambda e: e.period_start)
        return entries
    except (IndexError, KeyError, ValueError, TypeError) as exc:
        raise ParseError(
            raw_body=str(data)[:500],
            message=f"Failed to parse NOAA forecast data: {exc}",
        ) from exc
