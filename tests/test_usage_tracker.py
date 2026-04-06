from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import patch

from skypulse._usage import UsageTracker


class TestEffectiveTTL:
    def test_below_50_percent_returns_base_ttl(self) -> None:
        tracker = UsageTracker({"owm": 1000})
        for _ in range(499):
            tracker.record("owm")
        assert tracker.effective_ttl("owm", 300) == 300

    def test_at_50_percent_returns_1800(self) -> None:
        tracker = UsageTracker({"owm": 1000})
        for _ in range(500):
            tracker.record("owm")
        assert tracker.effective_ttl("owm", 300) == 1800

    def test_at_75_percent_returns_3600(self) -> None:
        tracker = UsageTracker({"owm": 1000})
        for _ in range(750):
            tracker.record("owm")
        assert tracker.effective_ttl("owm", 300) == 3600

    def test_above_75_percent_returns_3600(self) -> None:
        tracker = UsageTracker({"owm": 1000})
        for _ in range(900):
            tracker.record("owm")
        assert tracker.effective_ttl("owm", 300) == 3600


class TestUsageRatio:
    def test_zero_limit_returns_zero(self) -> None:
        tracker = UsageTracker({"owm": 0})
        tracker.record("owm")
        assert tracker.usage_ratio("owm") == 0.0

    def test_unknown_provider_returns_zero(self) -> None:
        tracker = UsageTracker({"owm": 1000})
        assert tracker.usage_ratio("unknown") == 0.0

    def test_multiple_providers_independent(self) -> None:
        tracker = UsageTracker({"owm": 100, "uv": 50})
        for _ in range(60):
            tracker.record("owm")
        for _ in range(10):
            tracker.record("uv")
        assert tracker.usage_ratio("owm") == 0.6
        assert tracker.usage_ratio("uv") == 0.2


class TestDailyReset:
    def test_reset_at_utc_date_boundary(self) -> None:
        tracker = UsageTracker({"owm": 100})
        for _ in range(80):
            tracker.record("owm")
        assert tracker.usage_ratio("owm") == 0.8

        tomorrow = date(2099, 1, 2)
        fake_tomorrow = datetime(2099, 1, 2, 0, 0, 1, tzinfo=timezone.utc)
        with patch("skypulse._usage.datetime") as mock_dt:
            mock_dt.now.return_value = fake_tomorrow
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            tracker._reset_date = date(2099, 1, 1)
            assert tracker.usage_ratio("owm") == 0.0
