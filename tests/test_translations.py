from __future__ import annotations

from skypulse._translations import TRANSLATIONS, get_label


class TestGetLabel:
    def test_english_aqi(self) -> None:
        assert get_label("aqi_label", "1", "en") == "Good"
        assert get_label("aqi_label", "5", "en") == "Very Poor"

    def test_ukrainian_aqi(self) -> None:
        assert get_label("aqi_label", "1", "uk") == "Добре"
        assert get_label("aqi_label", "5", "uk") == "Дуже погано"

    def test_english_uv_risk(self) -> None:
        assert get_label("uv_risk", "low", "en") == "Low"
        assert get_label("uv_risk", "extreme", "en") == "Extreme"

    def test_ukrainian_uv_risk(self) -> None:
        assert get_label("uv_risk", "low", "uk") == "Низький"
        assert get_label("uv_risk", "very_high", "uk") == "Дуже високий"

    def test_english_circadian(self) -> None:
        assert get_label("circadian_quality", "excellent", "en") == "Excellent"
        assert get_label("circadian_quality", "extreme_dark", "en") == "Extreme Dark"

    def test_ukrainian_circadian(self) -> None:
        assert get_label("circadian_quality", "excellent", "uk") == "Відмінно"
        assert get_label("circadian_quality", "extreme_dark", "uk") == "Полярна ніч"

    def test_english_storm_severity(self) -> None:
        assert get_label("storm_severity", "G0", "en") == "Quiet"
        assert get_label("storm_severity", "G5", "en") == "Extreme storm"

    def test_ukrainian_storm_severity(self) -> None:
        assert get_label("storm_severity", "G0", "uk") == "Спокійно"
        assert get_label("storm_severity", "G5", "uk") == "Екстремальна буря"

    def test_english_health_level(self) -> None:
        assert get_label("health_level", "none", "en") == "None"
        assert get_label("health_level", "severe", "en") == "Severe"

    def test_ukrainian_health_level(self) -> None:
        assert get_label("health_level", "none", "uk") == "Відсутній"
        assert get_label("health_level", "severe", "uk") == "Серйозний"

    def test_fallback_unknown_language(self) -> None:
        result = get_label("aqi_label", "1", "fr")
        assert result == "Good"

    def test_fallback_unknown_key(self) -> None:
        result = get_label("aqi_label", "99", "en")
        assert result == "99"

    def test_fallback_unknown_category(self) -> None:
        result = get_label("nonexistent", "key", "en")
        assert result == "key"

    def test_all_categories_have_both_languages(self) -> None:
        en = TRANSLATIONS["en"]
        uk = TRANSLATIONS["uk"]
        assert set(en.keys()) == set(uk.keys())
        for category in en:
            assert set(en[category].keys()) == set(uk[category].keys()), (
                f"Category '{category}' has mismatched keys between en and uk"
            )
