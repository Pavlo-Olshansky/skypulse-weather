from __future__ import annotations

from skypulse._constants import HEALTH_DISCLAIMER, STORM_KP_THRESHOLD
from skypulse.models.health import HealthImpact

KP_TO_G_SCALE: dict[int, str] = {
    0: "G0", 1: "G0", 2: "G0", 3: "G0", 4: "G0",
    5: "G1", 6: "G2", 7: "G3", 8: "G4", 9: "G5",
}

G_SCALE_SEVERITY: dict[str, str] = {
    "G0": "Quiet",
    "G1": "Minor storm",
    "G2": "Moderate storm",
    "G3": "Strong storm",
    "G4": "Severe storm",
    "G5": "Extreme storm",
}

G_SCALE_HEALTH: dict[str, dict[str, object]] = {
    "G0": {
        "level": "none",
        "affected_systems": [],
        "recommendations": ["No health impact expected from current geomagnetic conditions."],
    },
    "G1": {
        "level": "low",
        "affected_systems": ["nervous"],
        "recommendations": [
            "Sensitive individuals may experience mild headaches or sleep disruption.",
            "Stay hydrated and maintain regular sleep schedule.",
        ],
    },
    "G2": {
        "level": "moderate",
        "affected_systems": ["cardiovascular", "nervous"],
        "recommendations": [
            "Migraine-prone and cardiovascular-sensitive individuals should monitor symptoms.",
            "Avoid strenuous activity if feeling unwell.",
        ],
    },
    "G3": {
        "level": "high",
        "affected_systems": ["cardiovascular", "nervous", "general"],
        "recommendations": [
            "Significant health effects possible for sensitive groups.",
            "Cardiovascular patients should monitor blood pressure.",
            "Expect possible sleep disruption.",
        ],
    },
    "G4": {
        "level": "severe",
        "affected_systems": ["cardiovascular", "nervous", "general"],
        "recommendations": [
            "Broad population may notice effects.",
            "Cardiovascular patients should consult doctor if symptomatic.",
            "Minimize stress and physical exertion.",
        ],
    },
    "G5": {
        "level": "severe",
        "affected_systems": ["cardiovascular", "nervous", "general"],
        "recommendations": [
            "Extreme geomagnetic conditions.",
            "All sensitive groups should take precautions.",
            "Seek medical attention for unusual symptoms.",
        ],
    },
}

IMPACT_LEVELS = ["none", "low", "moderate", "high", "severe"]

AURORAL_BOUNDARY: dict[int, float] = {
    5: 65.0, 6: 60.0, 7: 55.0, 8: 50.0, 9: 45.0,
}


def kp_to_g_scale(kp: float) -> str:
    return KP_TO_G_SCALE.get(min(int(kp), 9), "G0")


def g_scale_to_severity(g_scale: str) -> str:
    return G_SCALE_SEVERITY.get(g_scale, "Quiet")


def is_storm(kp: float) -> bool:
    return kp >= STORM_KP_THRESHOLD


def get_health_impact(kp: float, g_scale: str) -> HealthImpact:
    info = G_SCALE_HEALTH.get(g_scale, G_SCALE_HEALTH["G0"])
    return HealthImpact(
        level=str(info["level"]),
        kp_index=kp,
        g_scale=g_scale,
        affected_systems=list(info["affected_systems"]),  # type: ignore[arg-type]
        recommendations=list(info["recommendations"]),  # type: ignore[arg-type]
        disclaimer=HEALTH_DISCLAIMER,
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
