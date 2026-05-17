from concurrent.futures import ThreadPoolExecutor, as_completed

from engine.forecast import normalize_windguru_forecast
from engine.scoring import evaluate_spot, load_optimal_conditions
from engine.time_utils import parse_target_time, target_time_label
from jobs.fetch_apify import APIFY_ACTOR_ID, fetch_windguru_forecast


SOURCE_POLICY = {
    "source_name": "Apify Windguru forecast actor",
    "provider": "apify",
    "actor_id": APIFY_ACTOR_ID,
    "allowed_live_sources": ["apify"],
    "external_live_sources_used": [],
    "rule": (
        "Recommendations are valid only when forecast data was fetched through "
        "Apify. If Apify data is unavailable, do not supplement with browsing, "
        "memory, Windy, Surfline, direct Windguru pages, or any other source."
    ),
}


def get_best_spot(spot_keys=None, target_time=None):
    target = parse_target_time(target_time) if isinstance(target_time, str) else target_time
    spots = _selected_spots(spot_keys)
    best = None
    best_score = -1
    results = []
    errors = {}

    with ThreadPoolExecutor(max_workers=min(8, len(spots) or 1)) as executor:
        futures = {
            executor.submit(_fetch_and_evaluate, spot_id, spot, target): spot_id
            for spot_id, spot in spots.items()
        }
        for future in as_completed(futures):
            spot_id = futures[future]
            try:
                result = future.result()
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
    source_note = "Source: Apify Windguru forecast actor only."
    if not best:
        return (
            f"{source_note} I could not fetch enough Apify forecast data for "
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


def _fetch_and_evaluate(spot_id, spot, target_time):
    payload = fetch_windguru_forecast(spot["windguru_spot_id"])
    forecast = normalize_windguru_forecast(payload, target_time)
    forecast["source"] = {
        "source_name": SOURCE_POLICY["source_name"],
        "provider": SOURCE_POLICY["provider"],
        "actor_id": SOURCE_POLICY["actor_id"],
        "windguru_spot_id": spot["windguru_spot_id"],
        "external_live_sources_used": [],
    }
    return evaluate_spot(spot_id, spot, forecast)
