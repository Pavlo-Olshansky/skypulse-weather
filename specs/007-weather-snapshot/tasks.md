# Implementation Tasks: Weather Snapshot & Adaptive Cache

**Branch**: `007-weather-snapshot` | **Date**: 2026-04-05
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Usage Tracker

- [x] [T001] Create `src/skypulse/_usage.py` with `UsageTracker` class: `record(provider)`, `usage_ratio(provider)`, `effective_ttl(provider, base_ttl)`, daily reset at midnight UTC using `datetime.now(timezone.utc).date()`, thread-safe with `threading.Lock`
- [x] [T002] Add `DEFAULT_OWM_DAILY_LIMIT = 1000` and `DEFAULT_UV_DAILY_LIMIT = 500` to `src/skypulse/_constants.py`
- [x] [T003] Add `owm_daily_limit` (default 1000) and `uv_daily_limit` (default 500) to `CacheConfig` in `src/skypulse/models/common.py`
- [x] [T004] Create `tests/test_usage_tracker.py` — test TTL tiers (<50%, 50-75%, >=75%), daily reset using mocked UTC date boundary, multiple providers, zero-limit edge case

## Phase 2: Adaptive Cache TTL

- [ ] [T005] Refactor `Cache` in `src/skypulse/_cache.py`: replace `TTLCache` with `LRUCache` + manual timestamps, add optional `ttl` parameter to `get()` method
- [ ] [T006] Update `tests/test_cache.py` for adaptive TTL parameter in `Cache.get()`, add test for `size` behavior after entries expire
- [ ] [T007] Create `UsageTracker` in `_BaseClient.__init__` in `src/skypulse/_base.py` with limits from `CacheConfig`
- [ ] [T008] Add `CACHE_PREFIX_TO_PROVIDER` mapping (`{"weather": "owm", "forecast": "owm", "aq": "owm", "aq_forecast": "owm"}`) to `_BaseClient`, modify `_check_cache()` to look up provider and pass adaptive TTL to `Cache.get()`
- [ ] [T009] Add `_record_api_call(provider)` helper to `_BaseClient` that delegates to `UsageTracker`; wire into OWM getter methods (`get_current_weather`, `get_forecast`, `get_air_quality`, `get_air_quality_forecast`) after successful HTTP fetch
- [ ] [T010] Create integration test in `tests/test_adaptive_cache.py` — simulate crossing 50% and 75% usage thresholds, verify cache entries live longer under adaptive TTL

## Phase 3: `WeatherSnapshot` Model

- [ ] [T011] Create `src/skypulse/models/snapshot.py` with `WeatherSnapshot` dataclass (fields: weather, forecast, air_quality, air_quality_forecast, uv, uv_forecast, circadian, magnetic_storm, magnetic_forecast, location, fetched_at, errors)
- [ ] [T012] Export `WeatherSnapshot` from `src/skypulse/models/__init__.py` and `src/skypulse/__init__.py`

## Phase 4: Async `prefetch()` Method

- [ ] [T013] Add module-level `_safe_fetch()` async function in `src/skypulse/_async_client.py` — returns `tuple[Any, Exception | None]`
- [ ] [T014] Add `prefetch()` to `AsyncSkyPulseClient` in `src/skypulse/_async_client.py` — resolve coords, fire all getters via `asyncio.gather` with `_safe_fetch`, compute circadian from weather result (None if weather fails), record API calls at client level, build `WeatherSnapshot`
- [ ] [T015] Create `tests/test_prefetch.py` — test: exactly 7 HTTP calls (4 OWM + 1 UV via dedup lock + 2 NOAA), snapshot fields populated, partial failure (UV down) returns None + error in errors dict, individual OWM getter after prefetch is cache hit, circadian is None when weather fails

## Phase 5: Sync `prefetch()` Method

- [ ] [T016] Add module-level `_safe_fetch_sync()` function in `src/skypulse/_client.py`
- [ ] [T017] Add `prefetch()` to `SkyPulseClient` in `src/skypulse/_client.py` — sequential calls, same circadian computation, same error handling, same API call recording
- [ ] [T018] Add sync prefetch tests to `tests/test_prefetch.py`

## Phase 6: Polish

- [ ] [T019] Run full test suite (`pytest`) — all existing + new tests pass
- [ ] [T020] Run `ruff check src/` and fix any linting issues
- [ ] [T021] Run `mypy src/skypulse` and fix any type errors
- [ ] [T022] Update `README.md` with `prefetch()` usage example and adaptive cache docs
- [ ] [T023] Update `CHANGELOG.md` with new version entry
- [ ] [T024] Bump version in `pyproject.toml`

## Dependency Graph

```
T001 ──> T002, T003 ──> T004
                │
T005 ──> T006   │
    │           │
    └──> T007 ──> T008 ──> T009 ──> T010
                                     │
T011 ──> T012                        │
    │                                │
    └────────────> T013 ──> T014 ──> T015
                                │
                           T016 ──> T017 ──> T018
                                              │
                                T019, T020, T021, T022, T023, T024
```

## Parallel Opportunities

| Group | Tasks | Reason |
|-------|-------|--------|
| Cache refactor + Constants | T002 + T003 + T005 | Independent: constants vs cache internals |
| Model + Cache integration | T011-T012 + T007-T010 | Model and cache are independent until prefetch |
| Polish | T019 + T020 + T021 | Independent lint/test/type checks |

## Summary

- **Total tasks**: 24
- **Per phase**: Usage Tracker=4, Adaptive Cache=4, Model=2, Async Prefetch=3, Sync Prefetch=3, Polish=6
- **Key architectural change**: Single cache with adaptive TTL (no snapshot cache layer)
- **Key fixes from analysis**: Thread-safe UsageTracker, UTC date reset, module-level _safe_fetch, API recording at client level, provider-to-prefix mapping, integration test for adaptive TTL thresholds
- **Expected result**: ~45-67% reduction in paid API calls per user per day
- **Risk**: Medium — Cache refactor (T005) touches core caching, requires careful test coverage
