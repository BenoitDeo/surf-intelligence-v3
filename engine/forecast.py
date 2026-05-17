from datetime import datetime, timezone
from typing import Any

from engine.time_utils import DEFAULT_TIMEZONE


WIND_SPEED_KEYS = ("windSpeed", "wind_speed", "wind_speed_kmh", "windKmh", "wind")
WIND_DIRECTION_KEYS = ("windDir", "wind_direction", "windDirection", "dir")
SWELL_HEIGHT_KEYS = ("swellHeight", "swell_height", "swell_height_m", "waveHeight", "waves")
SWELL_PERIOD_KEYS = ("swellPeriod", "swell_period", "swell_period_s", "wavePeriod", "period")
SWELL_DIRECTION_KEYS = (
    "swellDir",
    "swell_direction",
    "swellDirection",
    "waveDir",
    "wave_direction",
    "waveDirection",
)
TIDE_STAGE_KEYS = ("tideStage", "tide_stage", "tide", "tideState")
TIDE_MOVEMENT_KEYS = ("tideMovement", "tide_movement", "tideTrend")
TIMESTAMP_KEYS = ("timestamp", "time", "datetime", "date")
FORECAST_DATE_KEYS = ("forecastDate", "forecast_date")
FORECAST_HOUR_KEYS = ("forecastHour", "forecast_hour")


def normalize_windguru_forecast(payload: Any, target_time: datetime | None = None) -> dict[str, Any]:
    record = _forecast_record(payload, target_time)

    wind_speed = _number_from(record, WIND_SPEED_KEYS)
    wind_direction = _direction_from(record, WIND_DIRECTION_KEYS)
    swell_height = _number_from(record, SWELL_HEIGHT_KEYS)
    swell_period = _number_from(record, SWELL_PERIOD_KEYS)
    swell_direction = _direction_from(record, SWELL_DIRECTION_KEYS)

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
        "timestamp": _timestamp_from(record),
        "wind_speed_kmh": wind_speed,
        "wind_direction": wind_direction,
        "swell_height_m": swell_height,
        "swell_period_s": swell_period,
        "swell_direction": swell_direction,
        "tide_stage": _stage_from(record, TIDE_STAGE_KEYS),
        "tide_movement": _movement_from(record, TIDE_MOVEMENT_KEYS),
    }


def _forecast_record(payload: Any, target_time: datetime | None) -> dict[str, Any]:
    records = _forecast_records(payload)
    if not records:
        raise ValueError("No forecast record found in provider response")
    if not target_time:
        return records[0]

    dated_records = [
        (record_time, record)
        for record in records
        if (record_time := _datetime_from(record, TIMESTAMP_KEYS)) is not None
    ]
    if not dated_records:
        return records[0]

    target = target_time.astimezone(DEFAULT_TIMEZONE)
    return min(dated_records, key=lambda item: abs(item[0] - target))[1]


def _forecast_records(payload: Any) -> list[dict[str, Any]]:
    records = []
    if isinstance(payload, list):
        for item in payload:
            records.extend(_forecast_records(item))
    if isinstance(payload, dict):
        if any(key in payload for key in WIND_SPEED_KEYS + SWELL_HEIGHT_KEYS):
            records.append(payload)
        for value in payload.values():
            records.extend(_forecast_records(value))
    return records


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


def _datetime_from(record: dict[str, Any], keys: tuple[str, ...]) -> datetime | None:
    forecast_datetime = _forecast_datetime_from(record)
    if forecast_datetime:
        return forecast_datetime

    value = _value_from(record, keys)
    if value is None:
        return None
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        return datetime.fromtimestamp(timestamp, timezone.utc).astimezone(DEFAULT_TIMEZONE)

    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo:
        return parsed.astimezone(DEFAULT_TIMEZONE)
    return parsed.replace(tzinfo=DEFAULT_TIMEZONE)


def _forecast_datetime_from(record: dict[str, Any]) -> datetime | None:
    forecast_date = _value_from(record, FORECAST_DATE_KEYS)
    forecast_hour = _value_from(record, FORECAST_HOUR_KEYS)
    if forecast_date is None or forecast_hour is None:
        return None

    try:
        date = datetime.fromisoformat(str(forecast_date)).date()
        hour = int(float(forecast_hour))
    except ValueError:
        return None

    if not 0 <= hour <= 23:
        return None
    return datetime.combine(date, datetime.min.time(), DEFAULT_TIMEZONE).replace(hour=hour)


def _degrees_to_compass(degrees: float) -> str:
    directions = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    index = round(degrees / 45) % len(directions)
    return directions[index]


def _stage_from(record: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    value = _value_from(record, keys)
    if value is None:
        return None
    text = str(value).strip().lower()
    if "low" in text:
        return "low"
    if "mid" in text:
        return "mid"
    if "high" in text:
        return "high"
    return text or None


def _timestamp_from(record: dict[str, Any]) -> str:
    parsed = _datetime_from(record, TIMESTAMP_KEYS)
    if parsed:
        return parsed.isoformat()
    value = _value_from(record, TIMESTAMP_KEYS)
    if value:
        return str(value)
    return datetime.now(timezone.utc).isoformat()


def _movement_from(record: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    value = _value_from(record, keys)
    if value is None:
        return None
    text = str(value).strip().lower()
    if any(token in text for token in ("rising", "incoming", "flood")):
        return "rising"
    if any(token in text for token in ("falling", "outgoing", "ebb")):
        return "falling"
    return text or None
