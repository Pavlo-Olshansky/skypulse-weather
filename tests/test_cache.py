from __future__ import annotations

import threading
import time

from openweather.cache import Cache, build_cache_key


def test_cache_get_set() -> None:
    cache = Cache(max_entries=10, default_ttl=60)
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"


def test_cache_get_missing() -> None:
    cache = Cache()
    assert cache.get("missing") is None


def test_cache_ttl_expiry() -> None:
    cache = Cache(max_entries=10, default_ttl=1)
    cache.set("key1", "value1")
    time.sleep(1.1)
    assert cache.get("key1") is None


def test_cache_lru_eviction() -> None:
    cache = Cache(max_entries=3, default_ttl=60)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    cache.set("d", 4)  # evicts "a"

    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("d") == 4


def test_cache_invalidate() -> None:
    cache = Cache(max_entries=10, default_ttl=60)
    cache.set("key1", "value1")
    assert cache.invalidate("key1") is True
    assert cache.get("key1") is None
    assert cache.invalidate("missing") is False


def test_cache_clear() -> None:
    cache = Cache(max_entries=10, default_ttl=60)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert cache.size == 0
    assert cache.get("a") is None


def test_cache_size() -> None:
    cache = Cache(max_entries=10, default_ttl=60)
    assert cache.size == 0
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.size == 2


def test_cache_overwrite_key() -> None:
    cache = Cache(max_entries=10, default_ttl=60)
    cache.set("key", "old")
    cache.set("key", "new")
    assert cache.get("key") == "new"
    assert cache.size == 1


def test_build_cache_key_sorted() -> None:
    key1 = build_cache_key("weather", city="London", units="metric", lang="en")
    key2 = build_cache_key("weather", lang="en", units="metric", city="London")
    assert key1 == key2
    assert key1 == "weather:city=London:lang=en:units=metric"


def test_build_cache_key_different_params() -> None:
    key1 = build_cache_key("weather", city="London", units="metric")
    key2 = build_cache_key("weather", city="London", units="imperial")
    assert key1 != key2


def test_build_cache_key_skips_none() -> None:
    key = build_cache_key("weather", city="London", units="metric", cnt=None)
    assert "cnt" not in key


def test_cache_thread_safety() -> None:
    cache = Cache(max_entries=1000, default_ttl=60)
    errors: list[Exception] = []

    def writer(prefix: str) -> None:
        try:
            for i in range(100):
                cache.set(f"{prefix}_{i}", i)
        except Exception as e:
            errors.append(e)

    def reader(prefix: str) -> None:
        try:
            for i in range(100):
                cache.get(f"{prefix}_{i}")
        except Exception as e:
            errors.append(e)

    threads = []
    for p in ["a", "b", "c"]:
        threads.append(threading.Thread(target=writer, args=(p,)))
        threads.append(threading.Thread(target=reader, args=(p,)))

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0


def test_cache_performance_10x() -> None:
    cache = Cache(max_entries=128, default_ttl=60)
    cache.set("perf_key", {"temp": 15.2, "city": "London"})

    # Warm up
    for _ in range(100):
        cache.get("perf_key")

    # Measure cached access time
    start = time.perf_counter()
    iterations = 10000
    for _ in range(iterations):
        cache.get("perf_key")
    cached_time = time.perf_counter() - start

    # Cached access should be extremely fast (< 1ms per call on average)
    avg_cached_us = (cached_time / iterations) * 1_000_000
    assert avg_cached_us < 100, f"Cached access too slow: {avg_cached_us:.1f}µs per call"
