"""Market session and time-of-day utilities (US/Eastern)."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

MORNING_START = time(9, 35)
MORNING_END = time(11, 30)
AFTERNOON_START = time(13, 30)
AFTERNOON_END = time(15, 30)
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)
LUNCH_START = time(11, 30)
LUNCH_END = time(13, 30)


def now_et() -> datetime:
    return datetime.now(ET)


def is_market_hours(dt: datetime | None = None) -> bool:
    dt = dt or now_et()
    if dt.weekday() >= 5:
        return False
    t = dt.time()
    return MARKET_OPEN <= t < MARKET_CLOSE


def is_trading_session(dt: datetime | None = None) -> bool:
    dt = dt or now_et()
    if not is_market_hours(dt):
        return False
    t = dt.time()
    in_morning = MORNING_START <= t <= MORNING_END
    in_afternoon = AFTERNOON_START <= t <= AFTERNOON_END
    in_lunch = LUNCH_START <= t < LUNCH_END
    return (in_morning or in_afternoon) and not in_lunch


def minutes_since_open(dt: datetime | None = None) -> float:
    dt = dt or now_et()
    open_dt = dt.replace(hour=9, minute=30, second=0, microsecond=0)
    return max(0.0, (dt - open_dt).total_seconds() / 60.0)


def minutes_to_close(dt: datetime | None = None) -> float:
    dt = dt or now_et()
    close_dt = dt.replace(hour=16, minute=0, second=0, microsecond=0)
    return max(0.0, (close_dt - dt).total_seconds() / 60.0)


def time_of_day_bucket(dt: datetime | None = None) -> str:
    dt = dt or now_et()
    t = dt.time()
    if t < time(10, 0):
        return "open_0930_1000"
    if t < time(11, 30):
        return "morning_1000_1130"
    if t < time(13, 30):
        return "lunch_1130_1330"
    if t < time(15, 0):
        return "afternoon_1330_1500"
    return "close_1500_1600"


def is_major_release_window(dt: datetime | None = None) -> bool:
    """Heuristic: common US macro release times (8:30 AM ET pre-market / 10:00 AM)."""
    dt = dt or now_et()
    t = dt.time()
    # 8:25-8:40 CPI/jobs, 9:55-10:05 ISM/consumer
    if time(8, 25) <= t <= time(8, 40):
        return True
    if time(9, 55) <= t <= time(10, 5):
        return True
    if time(13, 55) <= t <= time(14, 5):
        return True
    return False
