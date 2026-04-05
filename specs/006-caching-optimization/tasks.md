# Implementation Tasks: Caching & Request Optimization

**Branch**: `006-caching-optimization` | **Date**: 2026-04-05
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Geocode Cache

- [x] [T001] Add `geo_cache_ttl` (default 3600) and `geo_cache_max_entries` (default 256) fields to `CacheConfig` in `src/skypulse/models/common.py`
- [x] [T002] Add `self._geo_cache: TTLCache | None` to `_BaseClient.__init__` in `src/skypulse/_base.py`, initialized when caching is enabled
- [x] [T003] Add `_check_geo_cache(key)` and `_store_geo_cache(key, value)` helper methods to `_BaseClient`
- [x] [T004] Route `geocode()` in `src/skypulse/_client.py` through geo cache: build key `geocode:q={city}:limit={limit}`, check cache before HTTP, store result after
- [x] [T005] [P] Route `geocode()` in `src/skypulse/_async_client.py` through geo cache (mirror of T004)
- [x] [T006] Route `reverse_geocode()` in `src/skypulse/_client.py` through geo cache: use `build_cache_key("reverse", lat=f"{lat:.4f}", lon=f"{lon:.4f}", limit=limit)` for 4-decimal precision
- [x] [T007] [P] Route `reverse_geocode()` in `src/skypulse/_async_client.py` through geo cache (mirror of T006)
- [x] [T008] Create `tests/test_geocode_cache.py` with tests: cache hit on repeated call, TTL expiry, different cities get different cache entries

## Phase 2: Circadian Weather Cache

- [x] [T009] Add `sunrise: datetime | None` and `sunset: datetime | None` fields to `Weather` dataclass in `src/skypulse/models/weather.py`
- [x] [T010] Update `parse_weather()` in `src/skypulse/_base.py` to populate `sunrise`/`sunset` from `data["sys"]["sunrise"]` and `data["sys"]["sunset"]`
- [x] [T011] Refactor `get_circadian_light()` in `src/skypulse/_client.py` to call `get_current_weather()` internally and extract sunrise/sunset/clouds from the `Weather` object, instead of making a raw `_request()` call
- [x] [T012] [P] Refactor `get_circadian_light()` in `src/skypulse/_async_client.py` (mirror of T011)
- [x] [T013] Update `tests/test_circadian.py` to verify: calling `get_current_weather()` then `get_circadian_light()` sequentially produces exactly 1 HTTP request to `/data/2.5/weather`
- [x] [T014] Update `tests/test_models.py` to cover new `sunrise`/`sunset` fields on `Weather`

## Phase 3: UV Fetch Deduplication

- [ ] [T015] Add `self._locks: dict[str, asyncio.Lock]` to `AsyncUVTransport.__init__` in `src/skypulse/_uv.py`
- [ ] [T016] Wrap the HTTP-fetch section of `AsyncUVTransport.fetch()` with a per-cache-key `asyncio.Lock` — check cache again after acquiring lock (double-check pattern)
- [ ] [T017] Add test to `tests/test_uv_index.py`: launch `get_uv_index()` + `get_uv_forecast()` concurrently via `asyncio.gather`, assert exactly 1 HTTP request to `currentuvindex.com` (via `respx` call count)
- [ ] [T018] Add test for lock cleanup: verify that locks for expired cache keys don't accumulate unboundedly (optional: clean locks when cache entry expires)

## Phase 4: Polish

- [ ] [T019] Run full test suite (`pytest`) — all existing + new tests pass
- [ ] [T020] Run `ruff check src/` and fix any linting issues
- [ ] [T021] Run `mypy src/skypulse` and fix any type errors
- [ ] [T022] Update `README.md` caching section to document geocode cache behavior and new `CacheConfig` fields

## Dependency Graph

```
T001 ──> T002 ──> T003 ──> T004, T005, T006, T007 ──> T008
                                                         │
T009 ──> T010 ──> T011, T012 ──> T013, T014              │
                                     │                    │
T015 ──> T016 ──> T017, T018        │                    │
                       │             │                    │
                       └─────────────┴────────────────────┘
                                     │
                                T019, T020, T021, T022
```

## Parallel Opportunities

| Group | Tasks | Reason |
|-------|-------|--------|
| Sync + Async geocode | T004 + T005, T006 + T007 | Mirror methods on both clients |
| Sync + Async circadian | T011 + T012 | Mirror refactor on both clients |
| All three phases | Phase 1, Phase 2, Phase 3 | Independent cache domains — can be developed and tested in parallel |
| Tests | T008, T013 + T014, T017 + T018 | Independent test files |

## Summary

- **Total tasks**: 22
- **Per story**: S1 (geocode cache)=8, S2 (circadian cache)=6, S3 (UV dedup)=4, Polish=4
- **Parallel opportunities**: 4 groups
- **Expected HTTP savings**: 30% reduction on cold cache, 100% on warm cache
- **Risk**: Low — all changes are internal caching; no public API changes, no new dependencies
