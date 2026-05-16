from concurrent.futures import ThreadPoolExecutor, as_completed

from config.spots import SPOTS
from engine.forecast import normalize_windguru_forecast
from engine.scoring import evaluate_spot
from jobs.fetch_apify import fetch_windguru_forecast


def get_best_spot(spot_keys=None):
    spots = _selected_spots(spot_keys)
    best = None
    best_score = -1
    results = []
    errors = {}

    with ThreadPoolExecutor(max_workers=min(8, len(spots) or 1)) as executor:
        futures = {
            executor.submit(_fetch_and_evaluate, spot_id, spot): spot_id
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
        "summary": recommendation_text(best, ranked),
        "best_spot": best,
        "all_spots": ranked,
        "errors": errors,
    }


def recommendation_text(best, ranked):
    if not best:
        return "I could not fetch enough current Windguru data to recommend a spot."

    forecast = best["forecast"]
    runners_up = ", ".join(item["name"] for item in ranked[1:4]) or "none"

    return (
        f"Best call right now: {best['name']} "
        f"({best['total_score']}/10). "
        f"Wind {forecast['wind_direction']} at {forecast['wind_speed_kmh']:.0f} km/h, "
        f"swell {forecast['swell_height_m']:.1f} m at "
        f"{forecast['swell_period_s']:.0f}s. "
        f"Next checks: {runners_up}."
    )


def _selected_spots(spot_keys):
    if not spot_keys:
        return SPOTS

    return {
        spot_id: SPOTS[spot_id]
        for spot_id in spot_keys
        if spot_id in SPOTS
    }


def _fetch_and_evaluate(spot_id, spot):
    payload = fetch_windguru_forecast(spot["windguru_spot_id"])
    forecast = normalize_windguru_forecast(payload)
    return evaluate_spot(spot_id, spot, forecast)
