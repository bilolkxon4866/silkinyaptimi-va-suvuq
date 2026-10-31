
"""Sovuq bo'yicha hisob-kitoblar. Tarmoq va bazasiz, faqat ma'lumot ustida."""

from datetime import date, datetime, timedelta
from statistics import median


# 2 m balandlikdagi harorat chegaralari (°C). Tushuntirish README'da.
GROUND_FROST = 2.0   # yerda qirov: ko'chat, pomidor, gul
FROST = 0.0          # havo sovug'i: o'rik guli, uzum barglari
HARD_FROST = -2.0    # kuchli sovuq: gul va mevaning katta qismi nobud

LEVEL_NONE = 0
LEVEL_GROUND = 1
LEVEL_FROST = 2
LEVEL_HARD = 3

# Ochiq va shamolsiz tunda yer 2 m dagi havodan 2–4° sovuqroq bo'ladi.
CLEAR_SKY_MAX_CLOUD = 30
CALM_MAX_WIND_KMH = 10

ALERT_HORIZON_HOURS = 48
ALERT_SEASON_MARGIN_DAYS = 21

NIGHT_START_HOUR = 18
NIGHT_END_HOUR = 9


def parse_local(value):
    """Open-Meteo vaqti («2026-10-31T05:00»), joyning mahalliy vaqti."""

    return datetime.fromisoformat(value)


def day_key(day):
    """Sanani yildan qat'i nazar solishtirish uchun (29-fevral 28-ga teng)."""

    if day.month == 2 and day.day == 29:
        return date(2001, 2, 28)

    return date(2001, day.month, day.day)


# ARXIV

def daily_minimums(times, temperatures):
    """{sana: (eng past harorat, o'sha soat)}."""

    result = {}

    for time_text, temperature in zip(times, temperatures):
        if temperature is None:
            continue

        moment = parse_local(time_text)
        day = moment.date()

        if day not in result or temperature < result[day][0]:
            result[day] = (temperature, moment.hour)

    return result


def season_dates(minimums, threshold):
    """Har yil uchun oxirgi bahorgi va birinchi kuzgi sovuq sanasi.

    Sovuq bo'lmagan yil uchun None.
    """

    years = sorted({day.year for day in minimums})
    last_spring = {year: None for year in years}
    first_autumn = {year: None for year in years}

    for day in sorted(minimums):
        if minimums[day][0] > threshold:
            continue

        if day.month <= 6:
            last_spring[day.year] = day
        elif first_autumn[day.year] is None:
            first_autumn[day.year] = day

    return last_spring, first_autumn


def spring_summary(last_spring):
    """«N yildan N-1 tasida shu sanadan keyin sovuq bo'lmagan»."""

    years = len(last_spring)
    frost_years = {
        year: day for year, day in last_spring.items() if day
    }

    if len(frost_years) <= 1:
        return {"years": years, "safe_after": None}

    # Sovuqsiz yil eng «erta» hisoblanadi.
    keys = sorted(
        day_key(day) if day else date(2001, 1, 1)
        for day in last_spring.values()
    )
    worst_year = max(frost_years, key=lambda y: day_key(frost_years[y]))

    return {
        "years": years,
        "safe_after": keys[-2],
        "typical": median_day([day_key(d) for d in frost_years.values()]),
        "worst": frost_years[worst_year],
    }


def autumn_summary(first_autumn):
    """«N yildan N-1 tasida birinchi sovuq shu sanadan keyin kelgan»."""

    years = len(first_autumn)
    frost_years = {
        year: day for year, day in first_autumn.items() if day
    }

    if len(frost_years) <= 1:
        return {"years": years, "harvest_by": None}

    keys = sorted(
        day_key(day) if day else date(2001, 12, 31)
        for day in first_autumn.values()
    )
    worst_year = min(frost_years, key=lambda y: day_key(frost_years[y]))

    return {
        "years": years,
        # Shu kungacha yig'ilsa, N-1 yilda sovuqdan oldin ulguriladi.
        "harvest_by": keys[1] - timedelta(days=1),
        "typical": median_day([day_key(d) for d in frost_years.values()]),
        "worst": frost_years[worst_year],
    }


def median_day(keys):
    ordinals = sorted(key.toordinal() for key in keys)
    return date.fromordinal(int(median(ordinals)))


def typical_frost_hour(minimums):
    hours = [
        hour for temperature, hour in minimums.values()
        if temperature <= FROST
    ]

    return int(median(hours)) if hours else None


def build_climate(times, temperatures):
    """10 yillik soatlik arxivdan buvi uchun kerakli xulosalar."""

    minimums = daily_minimums(times, temperatures)
    # Yarim yil bo'lsa, «10 yildan 9 tasida» noto'g'ri chiqadi.
    full_years = {
        day.year for day in minimums
        if day.month == 12 and day.day == 31
    } & {
        day.year for day in minimums
        if day.month == 1 and day.day == 1
    }
    minimums = {
        day: value for day, value in minimums.items()
        if day.year in full_years
    }

    spring_frost, autumn_frost = season_dates(minimums, FROST)
    spring_ground, autumn_ground = season_dates(minimums, GROUND_FROST)

    return {
        "first_year": min(full_years),
        "last_year": max(full_years),
        "spring_frost": spring_summary(spring_frost),
        "spring_ground": spring_summary(spring_ground),
        "autumn_frost": autumn_summary(autumn_frost),
        "autumn_ground": autumn_summary(autumn_ground),
        "frost_hour": typical_frost_hour(minimums),
    }


def in_alert_season(climate, today):
    """Qish o'rtasida har kecha sovuq: ogohlantirish shovqin bo'lib qoladi.

    Ogohlantirish bahorgi oxirgi sovuqdan 3 hafta oldindan to kuzgi
    birinchi sovuqdan 3 hafta keyingacha ishlaydi.
    """

    if climate is None:
        return True

    spring = climate["spring_frost"].get("typical")
    autumn = climate["autumn_frost"].get("typical")

    if spring is None or autumn is None:
        return True

    margin = timedelta(days=ALERT_SEASON_MARGIN_DAYS)
    key = day_key(today)

    return spring - margin <= key <= autumn + margin


# PROGNOZ

def hour_level(temperature, soil, cloud, wind):
    if temperature is None:
        return LEVEL_NONE

    if temperature <= HARD_FROST:
        return LEVEL_HARD

    if temperature <= FROST:
        return LEVEL_FROST

    if temperature <= GROUND_FROST:
        clear_and_calm = (
            (cloud is not None and cloud <= CLEAR_SKY_MAX_CLOUD)
            and (wind is not None and wind <= CALM_MAX_WIND_KMH)
        )

        if clear_and_calm or (soil is not None and soil <= 0):
            return LEVEL_GROUND

    return LEVEL_NONE


def forecast_nights(hourly, now):
    """Prognozni tunlarga bo'ladi. Tun tong sanasi bilan ataladi.

    now: joyning mahalliy vaqti (tzinfo'siz), Open-Meteo vaqtlari bilan bir xil.
    """

    nights = {}

    rows = zip(
        hourly["time"],
        hourly["temperature_2m"],
        hourly.get("soil_temperature_0cm") or [None] * len(hourly["time"]),
        hourly.get("cloud_cover") or [None] * len(hourly["time"]),
        hourly.get("wind_speed_10m") or [None] * len(hourly["time"]),
    )

    for time_text, temperature, soil, cloud, wind in rows:
        moment = parse_local(time_text)

        if NIGHT_END_HOUR < moment.hour < NIGHT_START_HOUR:
            continue

        if temperature is None:
            continue

        morning = (
            moment.date() + timedelta(days=1)
            if moment.hour >= NIGHT_START_HOUR
            else moment.date()
        )

        night = nights.setdefault(morning, {
            "morning": morning,
            "min_temperature": temperature,
            "min_soil": soil,
            "coldest": moment,
            "level": LEVEL_NONE,
            "risk_hours": [],
        })

        if temperature < night["min_temperature"]:
            night["min_temperature"] = temperature
            night["coldest"] = moment

        if soil is not None and (
            night["min_soil"] is None or soil < night["min_soil"]
        ):
            night["min_soil"] = soil

        level = hour_level(temperature, soil, cloud, wind)

        if level:
            night["level"] = max(night["level"], level)
            night["risk_hours"].append(moment)

    horizon = now + timedelta(hours=ALERT_HORIZON_HOURS)

    return [
        night for night in sorted(nights.values(), key=lambda n: n["morning"])
        # Tugagan tunlar va 48 soatdan keyingilar kerak emas.
        if datetime.combine(night["morning"], datetime.min.time())
        + timedelta(hours=NIGHT_END_HOUR) > now
        and night["coldest"] <= horizon
    ]
