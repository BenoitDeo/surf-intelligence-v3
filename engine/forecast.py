from datetime import datetime, timezone
from typing import Any


WIND_SPEED_KEYS = ("windSpeed", "wind_speed", "wind_speed_kmh", "windKmh", "wind")
WIND_DIRECTION_KEYS = ("windDir", "wind_direction", "windDirection", "dir")
SWELL_HEIGHT_KEYS = ("swellHeight", "swell_height", "swell_height_m", "waveHeight", "waves")
SWELL_PERIOD_KEYS = ("swellPeriod", "swell_period", "swell_period_s", "wavePeriod", "period")
TIMESTAMP_KEYS = ("timestamp", "time", "datetime", "date")


def normalize_windguru_forecast(payload: Any) -> dict[str, Any]:
    record = _first_forecast_record(payload)

    wind_speed = _number_from(record, WIND_SPEED_KEYS)
    wind_direction = _direction_from(record, WIND_DIRECTION_KEYS)
    swell_height = _number_from(record, SWELL_HEIGHT_KEYS)
    swell_period = _number_from(record, SWELL_PERIOD_KEYS)

    missing = [
        name
        for name, value in {
            "wind_speed_kmh": wind_speed,
            "wind_direction": wind_direction,
            "swell_height_m": swell_height,
            "swell_period_s": swell_period,
        }.items()
        if value is None
    ]
    if missing:
        raise ValueError(f"Windguru forecast is missing: {', '.join(missing)}")

    return {
        "timestamp": _value_from(record, TIMESTAMP_KEYS)
        or datetime.now(timezone.utc).isoformat(),
        "wind_speed_kmh": wind_speed,
        "wind_direction": wind_direction,
        "swell_height_m": swell_height,
        "swell_period_s": swell_period,
    }


def _first_forecast_record(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        for item in payload:
            try:
                return _first_forecast_record(item)
            except ValueError:
                continue
    if isinstance(payload, dict):
        if any(key in payload for key in WIND_SPEED_KEYS + SWELL_HEIGHT_KEYS):
            return payload
        for value in payload.values():
            try:
                return _first_forecast_record(value)
            except ValueError:
                continue
    raise ValueError("No forecast record found in Apify response")


def _value_from(record: dict[str, Any], keys: tuple[str, ...]) -> Any:
    lowered = {key.lower(): value for key, value in record.items()}
    for key in keys:
        if key in record:
            return record[key]
        value = lowered.get(key.lower())
        if value is not None:
            return value
    return None


def _number_from(record: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    value = _value_from(record, keys)
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", ".")
    token = "".join(char for char in text if char.isdigit() or char in ".-")
    return float(token) if token else None


def _direction_from(record: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    value = _value_from(record, keys)
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return _degrees_to_compass(float(value))
    text = str(value).strip().upper()
    try:
        return _degrees_to_compass(float(text))
    except ValueError:
        return text


def _degrees_to_compass(degrees: float) -> str:
    directions = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    index = round(degrees / 45) % len(directions)
    return directions[index]
