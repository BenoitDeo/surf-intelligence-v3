import os

from engine.forecast import normalize_windguru_forecast
from engine.scoring import evaluate_spot, load_optimal_conditions
from engine.time_utils import parse_target_time, target_time_label
from jobs.fetch_windguru import fetch_windguru_forecasts


SOURCE_POLICY = {
    "source_name": "Windguru direct forecast API",
    "provider": "windguru_direct",
    "allowed_live_sources": ["windguru_direct"],
    "external_live_sources_used": [],
    "rule": (
        "Recommendations are valid only when forecast data was fetched directly "
        "from Windguru. If Windguru data is unavailable, do not supplement with "
        "browsing, memory, Windy, Surfline, Apify, or any other source."
    ),
}


def get_best_spot(spot_keys=None, target_time=None):
    target = parse_target_time(target_time) if isinstance(target_time, str) else target_time
    spots = _selected_spots(spot_keys)
    best = None
    best_score = -1
    results = []
    errors = {}

    spot_items = list(spots.items())
    for chunk in _chunks(spot_items, _windguru_spots_per_batch()):
        windguru_ids = [spot["windguru_spot_id"] for _, spot in chunk]
        try:
            payload = fetch_windguru_forecasts(windguru_ids)
        except Exception as exc:
            payload = []
            for spot_id, spot in chunk:
                try:
                    payload.extend(fetch_windguru_forecasts([spot["windguru_spot_id"]]))
                except Exception as spot_exc:
                    errors[spot_id] = str(spot_exc or exc)
            if not payload:
                continue

        for spot_id, spot in chunk:
            try:
                result = _evaluate_from_payload(spot_id, spot, payload, target)
            except Exception as exc:
                errors[spot_id] = str(exc)
                continue

            results.append(result)

            if result["total_score"] > best_score:
                best_score = result["total_score"]
                best = result

    ranked = sorted(results, key=lambda item: item["total_score"], reverse=True)

    return {
        "target_time": target.isoformat() if target else None,
        "source_policy": SOURCE_POLICY,
        "summary": recommendation_text(best, ranked, target),
        "best_spot": best,
        "all_spots": ranked,
        "errors": errors,
    }


def recommendation_text(best, ranked, target_time=None):
    source_note = "Source: Windguru direct forecast API only."
    if not best:
        return (
            f"{source_note} I could not fetch enough Windguru forecast data for "
            f"{target_time_label(target_time)}, so I cannot make a surf call."
        )

    forecast = best["forecast"]
    runners_up = ", ".join(item["name"] for item in ranked[1:4]) or "none"

    return (
        f"{source_note} Best call for {target_time_label(target_time)}: {best['name']} "
        f"({best['total_score']}/10). "
        f"Wind {forecast['wind_direction']} at {forecast['wind_speed_kmh']:.0f} km/h, "
        f"swell {forecast['swell_height_m']:.1f} m at "
        f"{forecast['swell_period_s']:.0f}s. "
        f"Next checks: {runners_up}. "
        f"{' '.join(best['match_reasons'][:2])}"
    )


def _selected_spots(spot_keys):
    spot_profiles = {
        key: spot
        for key, spot in load_optimal_conditions().items()
        if spot.get("windguru_spot_id")
    }
    if not spot_keys:
        return spot_profiles

    return {
        spot_id: spot_profiles[spot_id]
        for spot_id in spot_keys
        if spot_id in spot_profiles
    }


def _evaluate_from_payload(spot_id, spot, payload, target_time):
    forecast = normalize_windguru_forecast(
        _records_for_spot(payload, spot["windguru_spot_id"]),
        target_time,
    )
    forecast["source"] = {
        "source_name": SOURCE_POLICY["source_name"],
        "provider": SOURCE_POLICY["provider"],
        "windguru_spot_id": spot["windguru_spot_id"],
        "external_live_sources_used": [],
    }
    return evaluate_spot(spot_id, spot, forecast)


def _records_for_spot(payload, windguru_spot_id):
    records = []
    expected = str(windguru_spot_id)
    for record in _flatten_records(payload):
        record_spot_id = (
            record.get("spotId")
            or record.get("spot_id")
            or record.get("location_id")
            or record.get("windguru_spot_id")
        )
        if record_spot_id is None or str(record_spot_id) == expected:
            records.append(record)
    if not records:
        raise ValueError(f"No direct Windguru forecast records found for spot {windguru_spot_id}")
    return records


def _flatten_records(payload):
    records = []
    if isinstance(payload, list):
        for item in payload:
            records.extend(_flatten_records(item))
    elif isinstance(payload, dict):
        if any(key in payload for key in ("spotId", "windSpeed", "windDirection", "waveHeight")):
            records.append(payload)
        for value in payload.values():
            records.extend(_flatten_records(value))
    return records


def _windguru_spots_per_batch():
    try:
        return max(1, int(os.getenv("WINDGURU_SPOTS_PER_BATCH", "4")))
    except ValueError:
        return 4


def _chunks(items, size):
    for index in range(0, len(items), size):
        yield items[index : index + size]
