# Changelog

All notable changes to this project will be documented in this file.

## [2.1.0] - 2026-04-06

### Added
- `prefetch()` method on both sync and async clients — fetches all weather data in one parallel batch
- `WeatherSnapshot` composite model with all weather data, partial failure handling, and error tracking
- Adaptive cache TTL that scales with API quota usage (<50%: base TTL, 50-75%: 30min, >75%: 1hr)
- `UsageTracker` for per-provider daily API call counting with midnight UTC reset
- New `CacheConfig` fields: `owm_daily_limit`, `uv_daily_limit`

### Changed
- Cache internals refactored from `TTLCache` to `LRUCache` with manual timestamp tracking to support adaptive TTL
- Individual getters now record API calls for usage tracking

## [2.0.2] - 2026-04-05

- Includes CHANGELOG.md in the published package (missing from 2.0.1)

## [2.0.1] - 2026-04-05

### Added
- Geocode cache with configurable TTL (default 1 hour) and LRU eviction (default 256 entries)
- New `CacheConfig` fields: `geo_cache_ttl`, `geo_cache_max_entries`
- `sunrise` and `sunset` fields on `Weather` dataclass
- Async UV fetch deduplication via per-key `asyncio.Lock`

### Changed
- `get_circadian_light()` now calls `get_current_weather()` internally, reusing cached weather data
- `geocode()` and `reverse_geocode()` results are cached when caching is enabled

### Fixed
- Redundant HTTP requests: repeated `city=` calls no longer trigger duplicate geocode requests
- Concurrent `get_uv_index()` + `get_uv_forecast()` via `asyncio.gather` now makes 1 request instead of 2

## [2.0.0] - 2026-04-05

Initial public release on PyPI. Versioned as 2.0 because the SDK was rewritten
from scratch after v1.x was developed as an internal prototype (never published).

- Sync and async clients with identical API surface
- Current weather, 5-day forecast, geocoding (direct + reverse)
- Air quality index with 8 pollutant concentrations and 4-day forecast
- UV index and 5-day UV forecast via CurrentUVIndex (no extra API key)
- Circadian light quality rating for wellness apps
- Geomagnetic storm monitoring via NOAA SWPC (real-time Kp + 3-day forecast)
- Health impact assessment with latitude-adjusted severity
- Storm alerts with aurora visibility prediction
- IP-based auto-location
- LRU caching with configurable TTL, automatic retries with exponential backoff
- English and Ukrainian translations
- API key redaction in logs and exceptions
