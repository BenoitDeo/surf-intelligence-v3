from datetime import datetime, timedelta
import re
from zoneinfo import ZoneInfo


DEFAULT_TIMEZONE = ZoneInfo("Europe/Lisbon")


def parse_target_time(value: str | None, *, now: datetime | None = None) -> datetime | None:
    if not value:
        return None

    now = now or datetime.now(DEFAULT_TIMEZONE)
    text = value.strip().lower()
    text = _clean_text(text)

    if _means_now(text):
        return None

    relative = _relative_time(text, now)
    if relative:
        return relative

    day_offset = _day_offset(text, now)
    if day_offset is not None:
        hour, minute = _time_from_keywords(text)
        return datetime.combine(
            (now + timedelta(days=day_offset)).date(),
            datetime.min.time(),
            DEFAULT_TIMEZONE,
        ).replace(hour=hour, minute=minute)

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


def _clean_text(text: str) -> str:
    replacements = {
        "?": " ",
        ",": " ",
        "best spot": " ",
        "best surf spot": " ",
        "surf spot": " ",
        "where should i surf": " ",
        "where to surf": " ",
        "forecast": " ",
        "conditions": " ",
        "near peniche": " ",
        "in peniche": " ",
        "at ": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return " ".join(text.split())


def _means_now(text: str) -> bool:
    return text in {
        "",
        "now",
        "right now",
        "current",
        "currently",
        "latest",
        "live",
        "asap",
        "today now",
        "this moment",
    }


def _relative_time(text: str, now: datetime) -> datetime | None:
    match = re.search(r"\bin\s+(\d+)\s*(hour|hours|hr|hrs|h)\b", text)
    if match:
        return now + timedelta(hours=int(match.group(1)))

    match = re.search(r"\bin\s+(\d+)\s*(minute|minutes|min|mins|m)\b", text)
    if match:
        return now + timedelta(minutes=int(match.group(1)))

    return None


def _day_offset(text: str, now: datetime) -> int | None:
    if any(token in text for token in ("day after tomorrow", "overmorrow")):
        return 2
    if any(token in text for token in ("tomorrow", "tmrw", "tmr", "next day")):
        return 1
    if any(token in text for token in ("today", "this morning", "this afternoon", "tonight", "this evening", "dawn patrol")):
        return 0

    weekdays = {
        "monday": 0,
        "mon": 0,
        "tuesday": 1,
        "tue": 1,
        "tues": 1,
        "wednesday": 2,
        "wed": 2,
        "thursday": 3,
        "thu": 3,
        "thur": 3,
        "thurs": 3,
        "friday": 4,
        "fri": 4,
        "saturday": 5,
        "sat": 5,
        "sunday": 6,
        "sun": 6,
    }
    for word, weekday in weekdays.items():
        if re.search(rf"\b(next\s+)?{word}\b", text):
            offset = (weekday - now.weekday()) % 7
            if offset == 0 or f"next {word}" in text:
                offset += 7
            return offset
    return None


def _time_from_keywords(text: str) -> tuple[int, int]:
    match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text)
    if match:
        return _parse_time_part(match.group(0))

    match = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", text)
    if match:
        return int(match.group(1)), int(match.group(2))

    keyword_times = [
        (("dawn patrol", "dawn", "sunrise", "early morning"), (7, 0)),
        (("morning", "breakfast"), (9, 0)),
        (("noon", "midday", "lunch"), (12, 0)),
        (("afternoon", "after lunch"), (15, 0)),
        (("evening", "sunset", "after work"), (18, 0)),
        (("tonight", "night"), (20, 0)),
        (("midnight",), (0, 0)),
    ]
    for keywords, time_value in keyword_times:
        if any(_contains_keyword(text, keyword) for keyword in keywords):
            return time_value

    return 9, 0


def _contains_keyword(text: str, keyword: str) -> bool:
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None
