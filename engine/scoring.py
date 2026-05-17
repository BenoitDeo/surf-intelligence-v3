import json
from functools import lru_cache
from pathlib import Path


OPTIMAL_CONDITIONS_PATH = Path(__file__).resolve().parents[1] / "config" / "optimal_conditions.json"


def evaluate_spot(spot_id, spot, forecast):
    profile = spot
    scores = {
        "wind": _wind_score(forecast, profile),
        "swell": _swell_score(forecast, profile),
        "period": _period_score(forecast, profile),
        "tide": _tide_score(forecast, profile),
        "safety": _safety_score(forecast, profile),
    }

    total = (
        scores["wind"] * 0.3
        + scores["swell"] * 0.3
        + scores["period"] * 0.15
        + scores["tide"] * 0.1
        + scores["safety"] * 0.15
    )

    return {
        "spot": spot_id,
        "name": profile["name"],
        "source": forecast.get("source"),
        "forecast": forecast,
        "scores": scores,
        "total_score": round(total, 2),
        "match_reasons": _match_reasons(forecast, profile, scores),
        "optimal_conditions": profile["optimal"],
        "confidence": profile.get("confidence", "unknown"),
    }


@lru_cache
def load_optimal_conditions():
    with OPTIMAL_CONDITIONS_PATH.open() as file:
        data = json.load(file)
    return {spot["key"]: spot for spot in data["spots"]}


def _wind_score(forecast, profile):
    optimal = profile["optimal"]
    avoid = profile.get("avoid", {})
    direction = forecast["wind_direction"]
    speed = forecast["wind_speed_kmh"]
    max_speed = optimal["max_wind_speed"]

    if direction in avoid.get("wind_directions", []):
        score = 3
    elif direction in optimal["wind_directions"]:
        score = 10
    else:
        score = 6

    if speed > max_speed:
        score -= min(5, (speed - max_speed) / 4)
    elif speed <= 10:
        score += 1

    return _clamp(score)


def _swell_score(forecast, profile):
    optimal = profile["optimal"]
    avoid = profile.get("avoid", {})
    height = forecast["swell_height_m"]
    direction = forecast.get("swell_direction")
    window = optimal["swell_height"]

    score = _range_score(
        height,
        window["min"],
        window["ideal_min"],
        window["ideal_max"],
        window["max"],
    )

    if direction:
        if direction in avoid.get("swell_directions", []):
            score -= 3
        elif direction in optimal.get("swell_directions", []):
            score += 1.5
        else:
            score -= 1

    return _clamp(score)


def _period_score(forecast, profile):
    period = forecast["swell_period_s"]
    window = profile["optimal"]["swell_period"]
    minimum = window["min"]
    ideal_minimum = window["ideal_min"]

    if period < minimum:
        return _clamp(3 + (period / minimum) * 3)
    if period < ideal_minimum:
        return _clamp(7 + ((period - minimum) / (ideal_minimum - minimum)) * 2)
    return 10


def _tide_score(forecast, profile):
    stage = forecast.get("tide_stage")
    movement = forecast.get("tide_movement")
    optimal = profile["optimal"]

    if not stage and not movement:
        return 6

    score = 5
    if stage in optimal.get("tide_stages", []):
        score += 3
    elif stage:
        score -= 1

    if movement in optimal.get("tide_movement", []):
        score += 2
    elif movement:
        score -= 1

    return _clamp(score)


def _safety_score(forecast, profile):
    avoid = profile.get("avoid", {})
    height = forecast["swell_height_m"]
    speed = forecast["wind_speed_kmh"]
    score = 10

    if height > avoid.get("swell_height_over", float("inf")):
        score -= min(7, (height - avoid["swell_height_over"]) * 3)

    abilities = set(profile.get("ability", []))
    if "advanced" in abilities and "beginner" not in abilities and height > 2.5:
        score -= 1
    if speed > profile["optimal"]["max_wind_speed"] + 8:
        score -= 2

    return _clamp(score)


def _range_score(value, minimum, ideal_minimum, ideal_maximum, maximum):
    if ideal_minimum <= value <= ideal_maximum:
        return 10
    if minimum <= value < ideal_minimum:
        span = ideal_minimum - minimum
        return 6 + ((value - minimum) / span) * 4 if span else 8
    if ideal_maximum < value <= maximum:
        span = maximum - ideal_maximum
        return 10 - ((value - ideal_maximum) / span) * 4 if span else 8
    if value < minimum:
        return max(0, 6 - (minimum - value) * 4)
    return max(0, 6 - (value - maximum) * 3)


def _match_reasons(forecast, profile, scores):
    reasons = []
    optimal = profile["optimal"]

    wind = f"{forecast['wind_direction']} {forecast['wind_speed_kmh']:.0f} km/h"
    if scores["wind"] >= 8:
        reasons.append(f"Wind is in the ideal window ({wind}).")
    elif scores["wind"] <= 4:
        reasons.append(f"Wind is hurting the spot ({wind}).")

    swell = f"{forecast['swell_height_m']:.1f} m at {forecast['swell_period_s']:.0f}s"
    if scores["swell"] >= 8 and scores["period"] >= 8:
        reasons.append(f"Swell fits the spot ({swell}).")
    elif scores["swell"] <= 4:
        reasons.append(f"Swell size is outside the preferred range ({swell}).")

    if forecast.get("swell_direction") in optimal.get("swell_directions", []):
        reasons.append(f"Swell direction {forecast['swell_direction']} is preferred.")

    if forecast.get("tide_stage"):
        tide = forecast["tide_stage"]
        if forecast.get("tide_movement"):
            tide = f"{tide}, {forecast['tide_movement']}"
        reasons.append(f"Tide read: {tide}.")

    return reasons


def _clamp(score):
    return round(max(0, min(10, score)), 2)
