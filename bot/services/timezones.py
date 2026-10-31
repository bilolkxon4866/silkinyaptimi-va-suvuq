
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    from timezonefinder import TimezoneFinder

    _finder = TimezoneFinder()
except ImportError:
    _finder = None


DEFAULT_TIMEZONE = "Asia/Tashkent"


def find_timezone_name(latitude, longitude):
    """Koordinata bo'yicha vaqt mintaqasini aniqlaydi (masalan Asia/Tashkent)."""

    if _finder is not None:
        name = _finder.timezone_at(lat=latitude, lng=longitude)

        if name:
            return name

    return DEFAULT_TIMEZONE


def get_timezone(name):
    try:
        return ZoneInfo(name or DEFAULT_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        return timezone(timedelta(hours=5))
