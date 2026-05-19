"""Market session and time-window utilities (US Eastern)."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def now_et() -> datetime:
    return datetime.now(ET)


def minutes_since_midnight(dt: datetime | None = None) -> int:
    dt = dt or now_et()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ET)
    else:
        dt = dt.astimezone(ET)
    return dt.hour * 60 + dt.minute


def is_market_hours(dt: datetime | None = None) -> bool:
    m = minutes_since_midnight(dt)
    return 9 * 60 + 30 <= m < 16 * 60


def in_session_window(
    dt: datetime | None,
    am_start: int,
    am_end: int,
    pm_start: int,
    pm_end: int,
    enable_pm: bool,
    lunch_start: int,
    lunch_end: int,
) -> bool:
    m = minutes_since_midnight(dt)
    if lunch_start <= m < lunch_end:
        return False
    in_am = am_start <= m < am_end
    in_pm = enable_pm and pm_start <= m < pm_end
    return in_am or in_pm


def is_late_day(minutes_before_close: int, dt: datetime | None = None) -> bool:
    m = minutes_since_midnight(dt)
    close_minutes = 16 * 60
    return m >= close_minutes - minutes_before_close


def is_opening_skip(skip_minutes: int, dt: datetime | None = None) -> bool:
    m = minutes_since_midnight(dt)
    open_minutes = 9 * 60 + 30
    return open_minutes <= m < open_minutes + skip_minutes
