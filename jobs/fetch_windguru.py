import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from dotenv import load_dotenv


WINDGURU_API_URL = "https://www.windguru.cz/int/iapi.php"
DEFAULT_CACHE_TTL_SECONDS = 60 * 60 * 3
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_WAVE_FALLBACK_SPOT_ID = 501140

_CACHE: dict[tuple[str, int], tuple[float, Any]] = {}


class WindguruForecastError(RuntimeError):
    pass


def fetch_windguru_forecast(spot_id: int, *, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> list[dict]:
    return fetch_windguru_forecasts([spot_id], timeout=timeout)


def fetch_windguru_forecasts(
    spot_ids: list[int],
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> list[dict]:
    load_dotenv()
    if not spot_ids:
        raise WindguruForecastError("No Windguru spot IDs were supplied")

    records = []
    for spot_id in spot_ids:
        records.extend(_fetch_spot_records(int(spot_id), timeout=timeout))
    if not records:
        raise WindguruForecastError("Windguru returned no forecast records")
    return records


def _fetch_spot_records(spot_id: int, *, timeout: int) -> list[dict]:
    cached = _cache_get("spot_records", spot_id)
    if cached is not None:
        return cached

    metadata = _request_json({"q": "forecast_spot", "id_spot": spot_id}, timeout=timeout)
    tabs = metadata.get("tabs") or []
    if not tabs:
        raise WindguruForecastError(f"Windguru returned no forecast tabs for spot {spot_id}")

    wind_source = _source_from_tabs(tabs, preferred_model=3, required_vars=("WINDSPD", "WINDDIR", "SMER"))
    wave_spot_id = spot_id
    try:
        wave_source = _source_from_tabs(tabs, preferred_model=84, required_vars=("HTSGW", "PERPW", "DIRPW"))
    except WindguruForecastError:
        fallback_spot_id = _wave_fallback_spot_id()
        if fallback_spot_id == spot_id:
            raise
        fallback_metadata = _request_json(
            {"q": "forecast_spot", "id_spot": fallback_spot_id},
            timeout=timeout,
        )
        fallback_tabs = fallback_metadata.get("tabs") or []
        wave_source = _source_from_tabs(
            fallback_tabs,
            preferred_model=84,
            required_vars=("HTSGW", "PERPW", "DIRPW"),
        )
        wave_spot_id = fallback_spot_id

    wind = _fetch_forecast(spot_id, wind_source, timeout=timeout)
    wave = _fetch_forecast(wave_spot_id, wave_source, timeout=timeout)
    records = _merge_forecasts(spot_id, wind, wave, wave_spot_id=wave_spot_id)
    _cache_set("spot_records", spot_id, records)
    return records


def _source_from_tabs(tabs: list[dict], *, preferred_model: int, required_vars: tuple[str, ...]) -> dict:
    for tab in tabs:
        if int(tab.get("id_model") or 0) == preferred_model:
            return _source_from_tab(tab, preferred_model)

    for tab in tabs:
        if not _tab_has_vars(tab, required_vars):
            continue

        model_arr = tab.get("id_model_arr") or []
        for model_key in ("id_model_wave", "id_model_wind", "id_model"):
            model_id = _int_or_none(tab.get(model_key))
            source = _source_for_model(model_arr, model_id)
            if source:
                return source

        if model_arr:
            return model_arr[0]
        return _source_from_tab(tab, preferred_model)

    raise WindguruForecastError(f"No Windguru forecast tab found for model {preferred_model}")


def _source_from_tab(tab: dict, preferred_model: int) -> dict:
    model_arr = tab.get("id_model_arr") or []
    source = _source_for_model(model_arr, preferred_model)
    if source:
        return source
    if model_arr:
        return model_arr[0]
    return {
        "id_model": tab["id_model"],
        "rundef": tab.get("rundef", ""),
        "period": tab.get("model_period") or 6,
        "cachefix": tab.get("cachefix", ""),
    }


def _source_for_model(model_arr: list[dict], model_id: int | None) -> dict | None:
    if model_id is None:
        return None
    for source in model_arr:
        if _int_or_none(source.get("id_model")) == model_id:
            return source
    return None


def _tab_has_vars(tab: dict, required_vars: tuple[str, ...]) -> bool:
    params = set((tab.get("options") or {}).get("params") or [])
    return bool(params.intersection(required_vars))


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _fetch_forecast(spot_id: int, source: dict, *, timeout: int) -> dict:
    params = {
        "q": "forecast",
        "id_model": source["id_model"],
        "rundef": source.get("rundef", ""),
        "id_spot": spot_id,
    }
    if source.get("period"):
        params["WGCACHEABLE"] = int(source["period"]) * 3600
    if source.get("cachefix"):
        params["cachefix"] = source["cachefix"]

    return _request_json(params, timeout=timeout)


def _request_json(params: dict[str, Any], *, timeout: int) -> Any:
    response = requests.get(
        WINDGURU_API_URL,
        params=params,
        headers={
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.windguru.cz/",
            "User-Agent": "SurfCheck/1.0 (+https://github.com/BenoitDeo/surf-intelligence-v3)",
        },
        timeout=timeout,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise WindguruForecastError(
            f"Windguru request failed with HTTP {response.status_code}: {response.text[:300]}"
        ) from exc

    payload = response.json()
    if isinstance(payload, dict) and payload.get("return") == "error":
        raise WindguruForecastError(payload.get("message", "Windguru returned an error"))
    return payload


def _merge_forecasts(spot_id: int, wind: dict, wave: dict, *, wave_spot_id: int) -> list[dict]:
    wind_fcst = wind.get("fcst") or {}
    wave_fcst = wave.get("fcst") or {}
    wind_hours = wind_fcst.get("hours") or []
    wave_by_hour = {hour: index for index, hour in enumerate(wave_fcst.get("hours") or [])}
    initstamp = wind_fcst.get("initstamp") or wind.get("wgmodel", {}).get("initstamp")
    if initstamp is None:
        raise WindguruForecastError(f"Windguru forecast is missing initstamp for spot {spot_id}")

    records = []
    for wind_index, hour in enumerate(wind_hours):
        wave_index = wave_by_hour.get(hour)
        if wave_index is None:
            continue
        records.append(
            {
                "spotId": str(spot_id),
                "timestamp": _forecast_timestamp(initstamp, hour),
                "windSpeed": _knots_to_kmh(_value_at(wind_fcst, "WINDSPD", wind_index)),
                "windDirection": _value_at(wind_fcst, "WINDDIR", wind_index),
                "waveHeight": _value_at(wave_fcst, "HTSGW", wave_index),
                "wavePeriod": _value_at(wave_fcst, "PERPW", wave_index),
                "waveDirection": _value_at(wave_fcst, "DIRPW", wave_index),
                "source": "windguru_direct",
                "waveSpotId": str(wave_spot_id),
            }
        )
    return records


def _knots_to_kmh(value: Any) -> float | None:
    if value is None:
        return None
    return float(value) * 1.852


def _forecast_timestamp(initstamp: int | float, hour: int | float) -> str:
    return (
        datetime.fromtimestamp(float(initstamp), timezone.utc)
        + timedelta(hours=float(hour))
    ).isoformat()


def _value_at(data: dict, key: str, index: int) -> Any:
    values = data.get(key) or []
    if index >= len(values):
        return None
    return values[index]


def _cache_get(kind: str, spot_id: int) -> Any | None:
    key = (kind, spot_id)
    item = _CACHE.get(key)
    if item is None:
        return None
    expires_at, value = item
    if expires_at < time.time():
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(kind: str, spot_id: int, value: Any) -> None:
    _CACHE[(kind, spot_id)] = (time.time() + _cache_ttl_seconds(), value)


def _cache_ttl_seconds() -> int:
    try:
        return max(300, int(os.getenv("WINDGURU_CACHE_TTL_SECONDS", DEFAULT_CACHE_TTL_SECONDS)))
    except ValueError:
        return DEFAULT_CACHE_TTL_SECONDS


def _wave_fallback_spot_id() -> int:
    try:
        return int(os.getenv("WINDGURU_WAVE_FALLBACK_SPOT_ID", DEFAULT_WAVE_FALLBACK_SPOT_ID))
    except ValueError:
        return DEFAULT_WAVE_FALLBACK_SPOT_ID
