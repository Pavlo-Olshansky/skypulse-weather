from __future__ import annotations

import httpx

DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.5
DEFAULT_CACHE_TTL = 300
DEFAULT_CACHE_MAX_ENTRIES = 128
DEFAULT_CONNECTION_LIMITS = httpx.Limits(
    max_connections=100, max_keepalive_connections=20
)

API_BASE_WEATHER = "https://api.openweathermap.org/data/2.5"
API_BASE_GEO = "https://api.openweathermap.org/geo/1.0"

ENV_API_KEY = "OPENWEATHER_API_KEY"
