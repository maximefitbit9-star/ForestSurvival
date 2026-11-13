"""Phase colour keys used by the renderer for each day/night phase."""

PHASES = {
    "dawn": {"sky": (0.55, 0.45, 0.55), "ambient": (0.45, 0.40, 0.45), "sun": 0.35, "fog": (0.7, 0.62, 0.65)},
    "day": {"sky": (0.45, 0.70, 0.95), "ambient": (0.55, 0.55, 0.55), "sun": 1.0, "fog": (0.75, 0.82, 0.92)},
    "dusk": {"sky": (0.85, 0.45, 0.25), "ambient": (0.45, 0.35, 0.30), "sun": 0.5, "fog": (0.85, 0.60, 0.45)},
    "night": {"sky": (0.02, 0.03, 0.08), "ambient": (0.10, 0.12, 0.20), "sun": 0.05, "fog": (0.03, 0.04, 0.09)},
}
