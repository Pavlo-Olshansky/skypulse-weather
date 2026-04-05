from __future__ import annotations

from skypulse._constants import HEALTH_DISCLAIMER, STORM_KP_THRESHOLD
from skypulse._translations import get_label
from skypulse.models.health import HealthImpact

KP_TO_G_SCALE: dict[int, str] = {
    0: "G0", 1: "G0", 2: "G0", 3: "G0", 4: "G0",
    5: "G1", 6: "G2", 7: "G3", 8: "G4", 9: "G5",
}

_HEALTH_I18N: dict[str, dict[str, dict[str, object]]] = {
    "en": {
        "G0": {
            "affected_systems": [],
            "recommendations": ["No health impact expected from current geomagnetic conditions."],
            "disclaimer": HEALTH_DISCLAIMER,
        },
        "G1": {
            "affected_systems": ["nervous"],
            "recommendations": [
                "Sensitive individuals may experience mild headaches or sleep disruption.",
                "Stay hydrated and maintain regular sleep schedule.",
            ],
            "disclaimer": HEALTH_DISCLAIMER,
        },
        "G2": {
            "affected_systems": ["cardiovascular", "nervous"],
            "recommendations": [
                "Migraine-prone and cardiovascular-sensitive individuals should monitor symptoms.",
                "Avoid strenuous activity if feeling unwell.",
            ],
            "disclaimer": HEALTH_DISCLAIMER,
        },
        "G3": {
            "affected_systems": ["cardiovascular", "nervous", "general"],
            "recommendations": [
                "Significant health effects possible for sensitive groups.",
                "Cardiovascular patients should monitor blood pressure.",
                "Expect possible sleep disruption.",
            ],
            "disclaimer": HEALTH_DISCLAIMER,
        },
        "G4": {
            "affected_systems": ["cardiovascular", "nervous", "general"],
            "recommendations": [
                "Broad population may notice effects.",
                "Cardiovascular patients should consult doctor if symptomatic.",
                "Minimize stress and physical exertion.",
            ],
            "disclaimer": HEALTH_DISCLAIMER,
        },
        "G5": {
            "affected_systems": ["cardiovascular", "nervous", "general"],
            "recommendations": [
                "Extreme geomagnetic conditions.",
                "All sensitive groups should take precautions.",
                "Seek medical attention for unusual symptoms.",
            ],
            "disclaimer": HEALTH_DISCLAIMER,
        },
    },
    "uk": {
        "G0": {
            "affected_systems": [],
            "recommendations": ["Вплив на здоров'я від поточних геомагнітних умов не очікується."],
            "disclaimer": "Оцінка впливу на здоров'я має інформаційний характер і базується на опублікованих дослідженнях кореляції геомагнітної активності з впливом на здоров'я. Це не є медичною порадою. Зверніться до лікаря з особистих питань здоров'я.",
        },
        "G1": {
            "affected_systems": ["нервова"],
            "recommendations": [
                "Чутливі люди можуть відчувати легкий головний біль або порушення сну.",
                "Пийте достатньо води та дотримуйтесь режиму сну.",
            ],
            "disclaimer": "Оцінка впливу на здоров'я має інформаційний характер і базується на опублікованих дослідженнях кореляції геомагнітної активності з впливом на здоров'я. Це не є медичною порадою. Зверніться до лікаря з особистих питань здоров'я.",
        },
        "G2": {
            "affected_systems": ["серцево-судинна", "нервова"],
            "recommendations": [
                "Людям, схильним до мігрені та серцево-судинних захворювань, слід стежити за симптомами.",
                "Уникайте надмірного фізичного навантаження при поганому самопочутті.",
            ],
            "disclaimer": "Оцінка впливу на здоров'я має інформаційний характер і базується на опублікованих дослідженнях кореляції геомагнітної активності з впливом на здоров'я. Це не є медичною порадою. Зверніться до лікаря з особистих питань здоров'я.",
        },
        "G3": {
            "affected_systems": ["серцево-судинна", "нервова", "загальний стан"],
            "recommendations": [
                "Можливий значний вплив на здоров'я чутливих груп населення.",
                "Пацієнтам із серцево-судинними захворюваннями слід контролювати тиск.",
                "Можливі порушення сну.",
            ],
            "disclaimer": "Оцінка впливу на здоров'я має інформаційний характер і базується на опублікованих дослідженнях кореляції геомагнітної активності з впливом на здоров'я. Це не є медичною порадою. Зверніться до лікаря з особистих питань здоров'я.",
        },
        "G4": {
            "affected_systems": ["серцево-судинна", "нервова", "загальний стан"],
            "recommendations": [
                "Широке населення може відчути вплив.",
                "Пацієнтам із серцево-судинними захворюваннями слід звернутися до лікаря при появі симптомів.",
                "Мінімізуйте стрес та фізичне навантаження.",
            ],
            "disclaimer": "Оцінка впливу на здоров'я має інформаційний характер і базується на опублікованих дослідженнях кореляції геомагнітної активності з впливом на здоров'я. Це не є медичною порадою. Зверніться до лікаря з особистих питань здоров'я.",
        },
        "G5": {
            "affected_systems": ["серцево-судинна", "нервова", "загальний стан"],
            "recommendations": [
                "Екстремальні геомагнітні умови.",
                "Усім чутливим групам слід вжити запобіжних заходів.",
                "Зверніться по медичну допомогу при незвичних симптомах.",
            ],
            "disclaimer": "Оцінка впливу на здоров'я має інформаційний характер і базується на опублікованих дослідженнях кореляції геомагнітної активності з впливом на здоров'я. Це не є медичною порадою. Зверніться до лікаря з особистих питань здоров'я.",
        },
    },
}

G_SCALE_LEVELS: dict[str, str] = {
    "G0": "none", "G1": "low", "G2": "moderate",
    "G3": "high", "G4": "severe", "G5": "severe",
}

IMPACT_LEVELS = ["none", "low", "moderate", "high", "severe"]

AURORAL_BOUNDARY: dict[int, float] = {
    5: 65.0, 6: 60.0, 7: 55.0, 8: 50.0, 9: 45.0,
}


def kp_to_g_scale(kp: float) -> str:
    return KP_TO_G_SCALE.get(min(int(kp), 9), "G0")


def g_scale_to_severity(g_scale: str, language: str = "en") -> str:
    return get_label("storm_severity", g_scale, language)


def is_storm(kp: float) -> bool:
    return kp >= STORM_KP_THRESHOLD


def get_health_impact(kp: float, g_scale: str, language: str = "en") -> HealthImpact:
    lang_data = _HEALTH_I18N.get(language, _HEALTH_I18N["en"])
    info = lang_data.get(g_scale, lang_data["G0"])
    level = G_SCALE_LEVELS.get(g_scale, "none")
    return HealthImpact(
        level=get_label("health_level", level, language),
        kp_index=kp,
        g_scale=g_scale,
        affected_systems=list(info["affected_systems"]),  # type: ignore[arg-type]
        recommendations=list(info["recommendations"]),  # type: ignore[arg-type]
        disclaimer=str(info["disclaimer"]),
    )


def classify_latitude_zone(abs_latitude: float, kp: int) -> str:
    if kp < 5:
        return "low"
    boundary = AURORAL_BOUNDARY.get(kp, 45.0)
    if abs_latitude >= boundary:
        return "high"
    elif abs_latitude >= boundary - 15:
        return "mid"
    else:
        return "low"


def adjust_impact_for_latitude(base_level: str, zone: str) -> str:
    idx = IMPACT_LEVELS.index(base_level) if base_level in IMPACT_LEVELS else 0
    if zone == "mid":
        idx = max(0, idx - 1)
    elif zone == "low":
        idx = max(0, idx - 2)
    return IMPACT_LEVELS[idx]
