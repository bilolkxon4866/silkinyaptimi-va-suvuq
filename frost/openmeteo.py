
import time

import aiohttp

from datetime import date


FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

FORECAST_VARIABLES = (
    "temperature_2m,soil_temperature_0cm,cloud_cover,wind_speed_10m"
)

ARCHIVE_YEARS = 10

# Model katakchasi ~10 km, shuning uchun 0.1° ga yaqin foydalanuvchilar
# bitta so'rovni bo'lishadi. Open-Meteo limiti: kuniga 10 000 so'rov.
FORECAST_CACHE_SECONDS = 30 * 60

_forecast_cache = {}


def grid_key(latitude, longitude):
    return f"{latitude:.1f},{longitude:.1f}"


async def get_json(url, params):
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()


async def fetch_forecast(latitude, longitude):
    """Soatlik prognoz, joyning mahalliy vaqtida (timezone=auto).

    timezone berilmasa, Open-Meteo vaqtni GMT'da qaytaradi va
    «soat 1 da sovuq» aslida Toshkentda soat 6 bo'lib chiqadi.
    """

    key = grid_key(latitude, longitude)
    cached = _forecast_cache.get(key)

    if cached and time.time() - cached[0] < FORECAST_CACHE_SECONDS:
        return cached[1]

    data = await get_json(FORECAST_URL, {
        "latitude": round(latitude, 2),
        "longitude": round(longitude, 2),
        "hourly": FORECAST_VARIABLES,
        "forecast_days": 4,
        "timezone": "auto",
    })

    _forecast_cache[key] = (time.time(), data)

    return data


def archive_period(today=None):
    """Oxirgi 10 ta to'liq yil, masalan 2016–2025."""

    today = today or date.today()
    last_year = today.year - 1

    return (
        date(last_year - ARCHIVE_YEARS + 1, 1, 1),
        date(last_year, 12, 31),
    )


async def fetch_archive(latitude, longitude):
    start, end = archive_period()

    return await get_json(ARCHIVE_URL, {
        "latitude": round(latitude, 2),
        "longitude": round(longitude, 2),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": "temperature_2m",
        "timezone": "auto",
    })
