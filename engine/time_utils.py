from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


DEFAULT_TIMEZONE = ZoneInfo("Europe/Lisbon")


def parse_target_time(value: str | None, *, now: datetime | None = None) -> datetime | None:
    if not value:
        return None

    now = now or datetime.now(DEFAULT_TIMEZONE)
    text = value.strip().lower()

    date_part = None
    time_part = None

    if text.startswith("tomorrow"):
        date_part = (now + timedelta(days=1)).date()
        time_part = text.replace("tomorrow", "", 1).strip()
    elif text.startswith("today"):
        date_part = now.date()
        time_part = text.replace("today", "", 1).strip()
    else:
        try:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo:
                return parsed.astimezone(DEFAULT_TIMEZONE)
            return parsed.replace(tzinfo=DEFAULT_TIMEZONE)
        except ValueError:
            pass

    if date_part is None:
        raise ValueError(
            "Use an ISO datetime like 2026-05-17T09:00 or a phrase like tomorrow 9am"
        )

    hour, minute = _parse_time_part(time_part or "09:00")
    return datetime.combine(date_part, datetime.min.time(), DEFAULT_TIMEZONE).replace(
        hour=hour,
        minute=minute,
    )


def target_time_label(target_time: datetime | None) -> str:
    if not target_time:
        return "right now"
    local = target_time.astimezone(DEFAULT_TIMEZONE)
    return local.strftime("%A %Y-%m-%d at %H:%M")


def _parse_time_part(value: str) -> tuple[int, int]:
    text = value.strip().replace(".", ":")
    if not text:
        return 9, 0

    meridiem = None
    if text.endswith("am") or text.endswith("pm"):
        meridiem = text[-2:]
        text = text[:-2].strip()

    if ":" in text:
        hour_text, minute_text = text.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    else:
        hour = int(text)
        minute = 0

    if meridiem == "pm" and hour != 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("Time must be between 00:00 and 23:59")
    return hour, minute
