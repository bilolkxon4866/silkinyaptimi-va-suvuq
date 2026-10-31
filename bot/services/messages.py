
from datetime import datetime, timezone

from bot.services.earthquake import trust_reason
from bot.services.timezones import get_timezone


def format_magnitude(item):
    text = f"{item['value']:.1f}"

    if item["type"]:
        text += f" ({item['type']})"

    return text


def format_utc_offset(local_time):
    offset = local_time.utcoffset()
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    hours, minutes = divmod(abs(total_minutes), 60)

    if minutes:
        return f"UTC{sign}{hours}:{minutes:02d}"

    return f"UTC{sign}{hours}"


def format_ago(event_time):
    minutes = int(
        (datetime.now(timezone.utc) - event_time).total_seconds() // 60
    )

    if minutes < 1:
        return "hozirgina"

    if minutes < 60:
        return f"{minutes} daqiqa oldin"

    return f"{minutes // 60} soat {minutes % 60} daqiqa oldin"


def describe_strength(event):
    if event["felt_ratio"] <= 0.3:
        return "Sizning joyingizda aniq sezilgan bo'lishi mumkin."

    return (
        "Sizning joyingizda yengil sezilgan bo'lishi mumkin, "
        "ko'pchilik umuman sezmagan bo'lishi ham mumkin."
    )


def format_magnitude_block(event):
    known = [
        item for item in event["magnitudes"]
        if item["value"] is not None
    ]

    if not known:
        return "📊 Magnituda: hali e'lon qilinmagan"

    values = {round(item["value"], 1) for item in known}

    if len(values) == 1:
        sources = ", ".join(item["source"] for item in known)
        return (
            f"📊 Magnituda: {format_magnitude(known[0])} "
            f"— {sources}"
        )

    trusted = event["trusted_magnitude"]
    lines = ["📊 Magnituda manbalarda farq qiladi:"]

    for item in known:
        line = f"   • {item['source']}: {format_magnitude(item)}"

        if item["agency"] and item["source"] == "EMSC":
            line += f", o'lchagan: {item['agency']}"

        lines.append(line)

    lines.append(
        f"   ✅ Ishonchlirog'i: {trusted['source']} "
        f"{trusted['value']:.1f}, chunki {trust_reason(trusted)}."
    )

    return "\n".join(lines)


def format_event(event, timezone_name, title):
    local_time = event["time"].astimezone(get_timezone(timezone_name))

    depth = (
        f"{event['depth']:.0f} km"
        if event["depth"] is not None
        else "noma'lum"
    )

    lines = [
        title,
        "",
        f"📍 Qayerda: {event['place']}",
        f"📏 Sizdan: ~{event['distance']} km",
        f"⬇️ Chuqurlik: {depth}",
        (
            f"🕒 Vaqt: {local_time:%d.%m.%Y %H:%M} "
            f"({format_utc_offset(local_time)}), "
            f"{format_ago(event['time'])}"
        ),
        format_magnitude_block(event),
        f"🌐 Manba: {', '.join(event['sources'])}",
    ]

    if event["url"]:
        lines.append(f"🔗 {event['url']}")

    lines += ["", describe_strength(event)]

    return "\n".join(lines)


def format_failed_sources(failed_sources):
    if not failed_sources:
        return ""

    names = " va ".join(failed_sources)

    return (
        f"\n\nℹ️ {names} hozir javob bermadi, "
        "qolgan manba bo'yicha tekshirildi."
    )


NOTHING_YET_TEXT = (
    "🟢 Oxirgi 30 daqiqada yaqiningizda sezilarli zilzila "
    "qayd etilmagan.\n\n"
    "Agar hozirgina silkingandek tuyulgan bo'lsa ham xavotir olmang: "
    "seysmik markazlar ma'lumotni odatda 2–20 daqiqada e'lon qiladi, "
    "u hali yo'lda bo'lishi mumkin.\n\n"
    "👀 Keyingi 30 daqiqa men kuzatib turaman. Biror narsa paydo "
    "bo'lsa, darhol yozaman. Bemalol dam olavering."
)

SOURCES_DOWN_TEXT = (
    "⏳ Seysmik markazlar hozir javob bermayapti. Bu zilzila bilan "
    "bog'liq emas, ularning serveri yoki internet sekinlashgan.\n\n"
    "👀 Keyingi 30 daqiqa qayta-qayta tekshirib turaman va ma'lumot "
    "kelishi bilan yozaman."
)

WATCH_FINISHED_TEXT = (
    "🟢 30 daqiqa kuzatdim: yaqiningizda sezilarli zilzila "
    "qayd etilmadi.\n\n"
    "Ehtimol, bu yuk mashinasi, shamol yoki boshqa tebranish bo'lgan. "
    "Xotirjam bo'ling."
)
