from __future__ import annotations

TRANSLATIONS: dict[str, dict[str, dict[str, str]]] = {
    "en": {
        "aqi_label": {
            "1": "Good",
            "2": "Fair",
            "3": "Moderate",
            "4": "Poor",
            "5": "Very Poor",
        },
        "uv_risk": {
            "low": "Low",
            "moderate": "Moderate",
            "high": "High",
            "very_high": "Very High",
            "extreme": "Extreme",
        },
        "circadian_quality": {
            "excellent": "Excellent",
            "good": "Good",
            "moderate": "Moderate",
            "poor": "Poor",
            "extreme_light": "Extreme Light",
            "extreme_dark": "Extreme Dark",
        },
        "storm_severity": {
            "G0": "Quiet",
            "G1": "Minor storm",
            "G2": "Moderate storm",
            "G3": "Strong storm",
            "G4": "Severe storm",
            "G5": "Extreme storm",
        },
        "health_level": {
            "none": "None",
            "low": "Low",
            "moderate": "Moderate",
            "high": "High",
            "severe": "Severe",
        },
    },
    "uk": {
        "aqi_label": {
            "1": "Добре",
            "2": "Прийнятно",
            "3": "Помірно",
            "4": "Погано",
            "5": "Дуже погано",
        },
        "uv_risk": {
            "low": "Низький",
            "moderate": "Помірний",
            "high": "Високий",
            "very_high": "Дуже високий",
            "extreme": "Екстремальний",
        },
        "circadian_quality": {
            "excellent": "Відмінно",
            "good": "Добре",
            "moderate": "Помірно",
            "poor": "Погано",
            "extreme_light": "Полярний день",
            "extreme_dark": "Полярна ніч",
        },
        "storm_severity": {
            "G0": "Спокійно",
            "G1": "Слабка буря",
            "G2": "Помірна буря",
            "G3": "Сильна буря",
            "G4": "Серйозна буря",
            "G5": "Екстремальна буря",
        },
        "health_level": {
            "none": "Відсутній",
            "low": "Низький",
            "moderate": "Помірний",
            "high": "Високий",
            "severe": "Серйозний",
        },
    },
}


def get_label(category: str, key: str, language: str = "en") -> str:
    lang = TRANSLATIONS.get(language, TRANSLATIONS["en"])
    return lang.get(category, {}).get(str(key), str(key))
