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

# NOAA SWPC endpoints
NOAA_KP_CURRENT_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
NOAA_KP_FORECAST_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json"

# IP Geolocation
DEFAULT_GEOLOCATION_URL = "http://ip-api.com/json/"
DEFAULT_GEOLOCATION_FIELDS = "status,lat,lon,city,country,countryCode,message"

# Storm cache TTL (seconds)
DEFAULT_STORM_CACHE_TTL = 600
DEFAULT_STORM_STALE_TTL = 1800
DEFAULT_FORECAST_STALE_TTL = 21600
DEFAULT_GEO_CACHE_TTL = 3600
DEFAULT_GEO_STALE_TTL = 86400

# Storm threshold
STORM_KP_THRESHOLD = 5.0

# Health impact disclaimer
HEALTH_DISCLAIMER = (
    "Health impact assessments are informational only, based on published research "
    "correlating geomagnetic activity with human health effects. This is not medical "
    "advice. Consult a healthcare professional for personal health concerns."
)
