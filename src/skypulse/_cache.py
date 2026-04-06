from __future__ import annotations

import threading
import time
from typing import Any

from cachetools import LRUCache


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
    """Thread-safe LRU cache with adaptive TTL support, backed by ``cachetools.LRUCache``."""

    def __init__(self, max_entries: int = 128, default_ttl: int = 300) -> None:
        self._default_ttl = default_ttl
        self._store: LRUCache[str, tuple[float, Any]] = LRUCache(maxsize=max_entries)
        self._lock = threading.Lock()

    def get(self, key: str, ttl: int | None = None) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            stored_at, value = entry
            effective = ttl if ttl is not None else self._default_ttl
            if (time.monotonic() - stored_at) >= effective:
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        """Store a value, evicting the least-recently-used entry if full."""
        with self._lock:
            self._store[key] = (time.monotonic(), value)

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
