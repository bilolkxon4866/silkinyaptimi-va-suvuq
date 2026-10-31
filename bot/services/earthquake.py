
import aiohttp
import asyncio
import logging

from datetime import datetime, timedelta, timezone
from math import radians, sin, cos, sqrt, atan2


USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

EMSC_URL = "https://www.seismicportal.eu/fdsnws/event/1/query"

# «Silkindimi?» soniyalarda javob berishi uchun manbani uzoq kutmaymiz.
SOURCE_TIMEOUT_SECONDS = 8

LOOKBACK_MINUTES = 30

# Ikki manbadagi yozuv bitta zilzila deb hisoblanadigan chegaralar.
MERGE_MAX_SECONDS = 60
MERGE_MAX_KM = 100
MERGE_MAX_MAGNITUDE_DIFF = 1.0

# USGS va EMSC'da zilzila bo'lmagan hodisalar (portlash, karyer) ham keladi.
EMSC_EARTHQUAKE_TYPES = {None, "", "ke", "se"}

# Magnitudaga qarab taxminiy sezilish radiusi (gipotsentrgacha, km).
# Tushuntirish README.md'da.
FELT_RADIUS_KM = [
    (7.0, 1500),
    (6.0, 800),
    (5.0, 300),
    (4.0, 120),
    (3.0, 40),
    (2.5, 15),
]


def parse_time(value):
    if not value:
        return None

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ).astimezone(timezone.utc)


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def calculate_distance(lat1, lon1, lat2, lon2):
    """Ikki koordinata orasidagi masofani kilometrda hisoblaydi."""

    earth_radius = 6371

    lat1, lon1, lat2, lon2 = map(
        radians, [lat1, lon1, lat2, lon2]
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )

    return earth_radius * 2 * atan2(
        sqrt(a), sqrt(1 - a)
    )


def normalize_usgs(feature):
    properties = feature.get("properties", {})
    coordinates = feature.get("geometry", {}).get("coordinates", [])

    if len(coordinates) < 3 or properties.get("time") is None:
        return None

    if properties.get("type") not in (None, "earthquake"):
        return None

    lon, lat, depth = coordinates

    return {
        "ids": [f"USGS:{feature.get('id') or properties.get('code')}"],
        "sources": ["USGS"],
        "time": datetime.fromtimestamp(
            properties["time"] / 1000,
            tz=timezone.utc
        ),
        "latitude": float(lat),
        "longitude": float(lon),
        "depth": to_float(depth),
        "place": properties.get("place"),
        "url": properties.get("url"),
        "magnitudes": [{
            "source": "USGS",
            "value": to_float(properties.get("mag")),
            "type": properties.get("magType") or "",
            "reviewed": properties.get("status") == "reviewed",
            "agency": (properties.get("net") or "").upper(),
        }],
    }


def normalize_emsc(feature):
    properties = feature.get("properties", {})
    coordinates = feature.get("geometry", {}).get("coordinates", [])

    lat = properties.get("lat")
    lon = properties.get("lon")
    # geometry'dagi chuqurlik manfiy keladi, shuning uchun properties'dan olamiz.
    depth = properties.get("depth")

    if len(coordinates) >= 3:
        lon = lon if lon is not None else coordinates[0]
        lat = lat if lat is not None else coordinates[1]
        depth = depth if depth is not None else abs(coordinates[2])

    event_time = parse_time(properties.get("time"))

    if lat is None or lon is None or event_time is None:
        return None

    if properties.get("evtype") not in EMSC_EARTHQUAKE_TYPES:
        return None

    region = properties.get("flynn_region")

    return {
        "ids": [f"EMSC:{feature.get('id') or properties.get('unid')}"],
        "sources": ["EMSC"],
        "time": event_time,
        "latitude": float(lat),
        "longitude": float(lon),
        "depth": to_float(depth),
        "place": region.title() if region else None,
        "url": None,
        "magnitudes": [{
            "source": "EMSC",
            "value": to_float(properties.get("mag")),
            "type": properties.get("magtype") or "",
            "reviewed": False,
            "agency": properties.get("auth") or "",
        }],
    }


async def fetch_events(session, url, params, normalize):
    async with session.get(url, params=params) as response:
        response.raise_for_status()
        data = await response.json(content_type=None)

    events = []

    for feature in data.get("features", []):
        event = normalize(feature)

        if event:
            events.append(event)

    return events


def build_params(start_time, end_time, output_format):
    return {
        "format": output_format,
        "starttime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "endtime": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "orderby": "time",
        "limit": 500
    }


def magnitude_priority(magnitude):
    """Qaysi magnitudaga ko'proq ishonish kerakligini baholaydi."""

    score = 0

    # Moment magnituda (Mw) kuchli zilzilalar uchun eng to'g'ri o'lchov.
    if magnitude["type"].lower().startswith("mw"):
        score += 4

    # Seysmolog qo'lda tekshirgan yozuv avtomatikdan ishonchliroq.
    if magnitude["reviewed"]:
        score += 2

    # Kichik zilzilalarda EMSC mahalliy agentliklar o'lchovini beradi,
    # USGS esa ko'pincha uzoq stansiyalar bo'yicha mb hisoblaydi.
    if magnitude["source"] == "EMSC":
        score += 1

    return score


def choose_trusted_magnitude(magnitudes):
    known = [item for item in magnitudes if item["value"] is not None]

    if not known:
        return None

    return max(known, key=magnitude_priority)


def trust_reason(magnitude):
    if magnitude["type"].lower().startswith("mw"):
        return (
            "bu moment magnituda (Mw), zilzila kuchini "
            "eng to'g'ri ko'rsatadigan o'lchov"
        )

    if magnitude["reviewed"]:
        return "bu qiymatni seysmolog qo'lda tekshirgan"

    if magnitude["source"] == "EMSC":
        return (
            "EMSC hududdagi mahalliy seysmik stansiyalar "
            "ma'lumotiga tayanadi"
        )

    return "boshqa manbada bu hodisa uchun magnituda yo'q"


def is_same_event(event, other):
    if set(event["sources"]) & set(other["sources"]):
        return False

    time_difference = abs(
        (event["time"] - other["time"]).total_seconds()
    )

    if time_difference > MERGE_MAX_SECONDS:
        return False

    distance = calculate_distance(
        event["latitude"],
        event["longitude"],
        other["latitude"],
        other["longitude"]
    )

    if distance > MERGE_MAX_KM:
        return False

    first = choose_trusted_magnitude(event["magnitudes"])
    second = choose_trusted_magnitude(other["magnitudes"])

    if first and second:
        difference = abs(first["value"] - second["value"])

        if difference > MERGE_MAX_MAGNITUDE_DIFF:
            return False

    return True


def finalize_event(event):
    """Birlashtirilgan hodisa uchun asosiy magnituda va joyni tanlaydi."""

    trusted = choose_trusted_magnitude(event["magnitudes"])
    known = [
        item["value"]
        for item in event["magnitudes"]
        if item["value"] is not None
    ]

    event["trusted_magnitude"] = trusted
    event["magnitude"] = trusted["value"] if trusted else None
    # Sezilishni baholashda ehtiyot uchun eng katta qiymat olinadi.
    event["max_magnitude"] = max(known) if known else None
    event["place"] = event["place"] or "Noma'lum hudud"

    return event


def merge_duplicate_events(events):
    """USGS va EMSC'dagi bir xil zilzilani bitta hodisaga birlashtiradi."""

    merged = []

    for event in sorted(events, key=lambda item: item["time"]):
        duplicate = next(
            (
                existing for existing in merged
                if is_same_event(event, existing)
            ),
            None
        )

        if duplicate is None:
            merged.append(event)
            continue

        duplicate["ids"].extend(event["ids"])
        duplicate["sources"].extend(event["sources"])
        duplicate["magnitudes"].extend(event["magnitudes"])
        duplicate["url"] = duplicate["url"] or event["url"]

        # USGS joy nomi aniqroq: «25 km SW of Tashkent».
        if "USGS" in event["sources"] and event["place"]:
            duplicate["place"] = event["place"]

    merged = [finalize_event(event) for event in merged]

    return sorted(merged, key=lambda item: item["time"], reverse=True)


async def get_recent_earthquakes(minutes=LOOKBACK_MINUTES):
    """Ikki manbadan hodisalarni oladi.

    (hodisalar, javob bermagan manbalar ro'yxati) qaytaradi.
    """

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=minutes)

    timeout = aiohttp.ClientTimeout(total=SOURCE_TIMEOUT_SECONDS)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        results = await asyncio.gather(
            fetch_events(
                session,
                USGS_URL,
                build_params(start_time, end_time, "geojson"),
                normalize_usgs
            ),
            fetch_events(
                session,
                EMSC_URL,
                build_params(start_time, end_time, "json"),
                normalize_emsc
            ),
            return_exceptions=True
        )

    events = []
    failed_sources = []

    for source, result in zip(["USGS", "EMSC"], results):
        if isinstance(result, BaseException):
            logging.warning("%s javob bermadi: %r", source, result)
            failed_sources.append(source)
            continue

        events.extend(result)

    return merge_duplicate_events(events), failed_sources


def get_felt_distance_limit(magnitude):
    """Magnitudaga qarab taxminiy sezilish masofasini qaytaradi."""

    if magnitude is None:
        return 0

    for min_magnitude, radius in FELT_RADIUS_KM:
        if magnitude >= min_magnitude:
            return radius

    return 0


def get_nearby_felt_earthquakes(events, user_lat, user_lon):
    """Foydalanuvchiga yaqin, sezilishi mumkin bo'lgan zilzilalarni topadi.

    Umumiy hodisalarni o'zgartirmaslik uchun nusxa qaytaradi.
    """

    nearby_events = []

    for event in events:
        max_distance = get_felt_distance_limit(event["max_magnitude"])

        if max_distance == 0:
            continue

        distance = calculate_distance(
            user_lat,
            user_lon,
            event["latitude"],
            event["longitude"]
        )

        # Chuqur zilzila yuzada kuchsizroq seziladi.
        hypocentral = sqrt(distance ** 2 + (event["depth"] or 0) ** 2)

        if hypocentral <= max_distance:
            nearby_events.append({
                **event,
                "distance": round(distance),
                "felt_ratio": hypocentral / max_distance,
            })

    return sorted(
        nearby_events,
        key=lambda event: event["time"],
        reverse=True
    )
