from __future__ import annotations

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(hour=int(hour), minute=int(minute))


def now_et() -> datetime:
    return datetime.now(UTC).astimezone(ET)


def is_within_window(target: datetime, start_hhmm: str, end_hhmm: str) -> bool:
    start_t = parse_hhmm(start_hhmm)
    end_t = parse_hhmm(end_hhmm)
    local_t = target.timetz().replace(tzinfo=None)
    return start_t <= local_t <= end_t


def session_label(target: datetime) -> str:
    hhmm = target.strftime("%H:%M")
    if "09:30" <= hhmm <= "10:30":
        return "open_drive"
    if "10:30" < hhmm <= "11:30":
        return "morning_extension"
    if "11:30" < hhmm < "13:30":
        return "lunch"
    if "13:30" <= hhmm <= "15:00":
        return "afternoon"
    if "15:00" < hhmm <= "16:00":
        return "power_hour"
    return "outside_rth"
