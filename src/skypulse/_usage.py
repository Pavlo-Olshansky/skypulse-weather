from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Dict


class UsageTracker:
    """Tracks API calls per provider per day and computes adaptive TTL."""

    def __init__(self, limits: Dict[str, int]) -> None:
        self._limits = limits
        self._counts: Dict[str, int] = {}
        self._reset_date = datetime.now(timezone.utc).date()
        self._lock = threading.Lock()

    def record(self, provider: str) -> None:
        with self._lock:
            self._maybe_reset()
            self._counts[provider] = self._counts.get(provider, 0) + 1

    def usage_ratio(self, provider: str) -> float:
        with self._lock:
            self._maybe_reset()
            limit = self._limits.get(provider, 0)
            if limit <= 0:
                return 0.0
            return self._counts.get(provider, 0) / limit

    def effective_ttl(self, provider: str, base_ttl: int) -> int:
        ratio = self.usage_ratio(provider)
        if ratio < 0.5:
            return base_ttl
        if ratio < 0.75:
            return 1800
        return 3600

    def _maybe_reset(self) -> None:
        today = datetime.now(timezone.utc).date()
        if today > self._reset_date:
            self._counts.clear()
            self._reset_date = today
