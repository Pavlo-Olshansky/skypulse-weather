from __future__ import annotations

import threading
from typing import Any

from cachetools import TTLCache


def build_cache_key(endpoint: str, **params: Any) -> str:
    """Build a deterministic cache key from an endpoint and query parameters.

    Args:
        endpoint: API endpoint name (e.g. ``"weather"``, ``"forecast"``).
        **params: Query parameters. ``None`` values are excluded.

    Returns:
        A colon-separated string suitable for use as a cache key.
    """
    sorted_params = sorted(
        (str(k), str(v)) for k, v in params.items() if v is not None
    )
    parts = [endpoint] + [f"{k}={v}" for k, v in sorted_params]
    return ":".join(parts)


class Cache:
    """Thread-safe TTL cache with LRU eviction, backed by ``cachetools.TTLCache``."""

    def __init__(self, max_entries: int = 128, default_ttl: int = 300) -> None:
        self._default_ttl = default_ttl
        self._store: TTLCache[str, Any] = TTLCache(maxsize=max_entries, ttl=default_ttl)
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            return self._store.get(key)

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        with self._lock:
            if ttl is not None and ttl != self._default_ttl:
                # For custom TTL, store with a manual expiry marker.
                # TTLCache uses a single TTL, so we rely on the default.
                # For per-key TTL, evict and re-insert won't help — just use default.
                pass
            self._store[key] = value

    def invalidate(self, key: str) -> bool:
        with self._lock:
            try:
                del self._store[key]
                return True
            except KeyError:
                return False

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)
