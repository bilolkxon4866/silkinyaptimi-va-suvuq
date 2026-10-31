
from datetime import timedelta

from frost.analysis import (
    LEVEL_FROST,
    LEVEL_GROUND,
    LEVEL_HARD,
    LEVEL_NONE,
    day_key,
)


MONTHS = [
    "yanvar", "fevral", "mart", "aprel", "may", "iyun",
    "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
]

WEEKDAYS = [
    "dushanba", "seshanba", "chorshanba", "payshanba",
    "juma", "shanba", "yakshanba",
]

LEVEL_TITLES = {
    LEVEL_GROUND: "yerda qirov",
    LEVEL_FROST: "sovuq",
    LEVEL_HARD: "kuchli sovuq",
}

MODEL_NOTE = (
    "ℹ️ Bu ob-havo modeli (~10 km katakcha), hovlingizdagi termometr "
    "emas. Pastqam joy, ariq bo'yi va ochiq dalada tunda 1–3° "
    "sovuqroq bo'ladi."
)


def format_day(day):
    return f"{day.day}-{MONTHS[day.month - 1]}"


def format_temperature(value):
    rounded = round(value)

    if rounded > 0:
        return f"+{rounded}°"

    if rounded < 0:
        return f"−{abs(rounded)}°"

    return "0°"


def relative_night(morning, today):
    days = (morning - today).days

    if days <= 0:
        return "Bugun tongda"

    if days == 1:
        return "Bugun kechasi"

    if days == 2:
        return "Ertaga kechasi"

    return f"{format_day(morning)} tongida"


def format_hours(night):
    hours = night["risk_hours"] or [night["coldest"]]
    start, end = min(hours), max(hours)

    if start == end:
        return f"soat {start.hour} atrofida"

    return f"soat {start.hour}:00 dan {end.hour + 1}:00 gacha"


def is_spring(day):
    return day.month <= 6


def advice(level, spring):
    if spring:
        tips = [
            "Ko'chatlarni (pomidor, bodring, qalampir) plyonka, eski "
            "choyshab yoki chelak bilan yoping. Ertalab quyosh chiqqach "
            "oching.",
            "Tuvak va yashikdagi ko'chatlarni uyga yoki ayvonga oling.",
            "Kechqurun yerni sug'oring: nam tuproq issiqni ko'proq "
            "ushlaydi.",
        ]

        if level >= LEVEL_FROST:
            tips.append(
                "Gullagan o'rik, shaftoli: yosh daraxtni mato bilan "
                "yoping, kattasining tagini sug'oring."
            )
    else:
        tips = [
            "Pomidor, qalampir, baqlajonni yig'ib oling: ular birinchi "
            "qirovda nobud bo'ladi.",
            "Gul tuvaklarini uyga kiriting.",
        ]

        if level >= LEVEL_FROST:
            tips.append("Uzumni uzib oling yoki ustini yoping.")

    if level >= LEVEL_FROST:
        tips.append(
            "Shlang, bochka va chelakdagi suvni to'king: muzlab yoriladi."
        )

    if level >= LEVEL_HARD:
        tips.append("Hovlidagi quvur va kranlarni o'rang.")

    return "\n".join(f"• {tip}" for tip in tips)


def format_alert(night, today):
    morning = night["morning"]
    title = LEVEL_TITLES[night["level"]]

    lines = [
        f"❄️ {relative_night(morning, today)} {title}!",
        "",
        (
            f"📅 {format_day(morning)}, {WEEKDAYS[morning.weekday()]} "
            f"tongi, {format_hours(night)}"
        ),
        f"🌡 Havo (2 m): {format_temperature(night['min_temperature'])} gacha",
    ]

    if night["min_soil"] is not None:
        lines.append(
            f"🌱 Yer yuzi: {format_temperature(night['min_soil'])} gacha"
        )

    lines += [
        "",
        "Nima qilish kerak:",
        advice(night["level"], is_spring(morning)),
        "",
        MODEL_NOTE,
    ]

    return "\n".join(lines)


def format_evening_reminder(night):
    return (
        f"⏰ Eslatma: bugun kechasi {LEVEL_TITLES[night['level']]}, "
        f"{format_temperature(night['min_temperature'])} gacha, "
        f"{format_hours(night)}.\n\n"
        "Ko'chatlarni yopdingizmi? Suvni to'kdingizmi?"
    )


ALL_CLEAR_TEXT = (
    "🌤 Yaxshi xabar: prognoz yaxshilandi, bugun kechasi sovuq "
    "kutilmayapti. Yopib qo'ygan bo'lsangiz ham zarari yo'q."
)


def format_nights(nights, today):
    if not nights:
        return "Prognoz hozircha yo'q. Birozdan keyin qayta urinib ko'ring."

    lines = ["🌙 Yaqin kechalar:", ""]

    for night in nights:
        name = relative_night(night["morning"], today)
        temperature = format_temperature(night["min_temperature"])

        if night["level"] == LEVEL_NONE:
            verdict = "✅ sovuq yo'q"
        else:
            verdict = f"❄️ {LEVEL_TITLES[night['level']]}"

        line = f"{name}: {temperature}"

        if night["min_soil"] is not None:
            line += f" (yer {format_temperature(night['min_soil'])})"

        lines.append(f"{line} — {verdict}")

    if all(night["level"] == LEVEL_NONE for night in nights):
        lines += ["", "Hozircha xotirjam bo'ling. Sovuq kutilsa, o'zim yozaman."]

    return "\n".join(lines)


def spring_line(summary, what):
    if summary["safe_after"] is None:
        return f"• {what}: bu yerda bahorda deyarli bo'lmaydi."

    return (
        f"• {what}: {summary['years']} yildan {summary['years'] - 1} "
        f"tasida {format_day(summary['safe_after'])}dan keyin bo'lmagan. "
        f"Eng kechi: {summary['worst'].year}-yil "
        f"{format_day(summary['worst'])}."
    )


def autumn_line(summary, what):
    if summary["harvest_by"] is None:
        return f"• {what}: bu yerda kuzda deyarli bo'lmaydi."

    first_safe = summary["harvest_by"] + timedelta(days=1)

    return (
        f"• {what}: {summary['years']} yildan {summary['years'] - 1} "
        f"tasida {format_day(first_safe)} yoki undan keyin kelgan. "
        f"Eng ertasi: {summary['worst'].year}-yil "
        f"{format_day(summary['worst'])}."
    )


def main_advice(climate, today):
    """Hozirgi faslga mos bitta asosiy maslahat."""

    if is_spring(today):
        summary = climate["spring_ground"]

        if summary["safe_after"] is None:
            return "🌱 Ko'chatni istalgan vaqtda o'tqazsa bo'ladi."

        plant_from = summary["safe_after"] + timedelta(days=1)

        return (
            "🌱 Pomidor, bodring ko'chatini "
            f"{format_day(plant_from)}dan boshlab o'tqazing.\n"
            f"Oxirgi {summary['years']} yilning {summary['years'] - 1} "
            f"tasida {format_day(summary['safe_after'])}dan keyin "
            "yerda qirov bo'lmagan."
        )

    summary = climate["autumn_frost"]

    if summary["harvest_by"] is None:
        return "🍇 Bu yerda kuzgi sovuq kam bo'ladi, uzumga xavf yo'q."

    text = (
        f"🍇 Uzumni {format_day(summary['harvest_by'])}gacha uzib oling.\n"
        f"Oxirgi {summary['years']} yilning {summary['years'] - 1} "
        f"tasida birinchi sovuq shundan keyin kelgan."
    )

    if day_key(today) > summary["harvest_by"]:
        text += (
            "\n\n⚠️ Bu sana o'tib ketdi. Hali uzmagan bo'lsangiz, "
            "hozir uzing va ogohlantirishlarni kuzating."
        )

    return text


def format_climate(climate, today):
    period = f"{climate['first_year']}–{climate['last_year']}"

    lines = [
        main_advice(climate, today),
        "",
        "Bahor (oxirgi sovuq):",
        spring_line(climate["spring_frost"], "Sovuq, 0° dan past"),
        spring_line(climate["spring_ground"], "Yerda qirov"),
        "",
        "Kuz (birinchi sovuq):",
        autumn_line(climate["autumn_ground"], "Yerda qirov"),
        autumn_line(climate["autumn_frost"], "Sovuq, 0° dan past"),
    ]

    if climate["frost_hour"] is not None:
        lines += [
            "",
            f"⏰ Sovuq odatda tongda, soat {climate['frost_hour']} atrofida "
            "bo'ladi. Shuning uchun uni hech kim payqamaydi.",
        ]

    lines += [
        "",
        f"ℹ️ {period} yillar, Open-Meteo arxivi (soatlik). "
        "Bu ob-havo modeli, hovlingizdagi termometr emas.",
    ]

    return "\n".join(lines)


def format_trust(user):
    elevation = (
        f"{user['elevation']:.0f} m"
        if user["elevation"] is not None
        else "noma'lum"
    )

    return (
        "🤔 Bunga qanchalik ishonsa bo'ladi?\n\n"
        "Bu raqamlar sizning hovlingizdan emas, ob-havo modelidan "
        "olingan. Model sizning nuqtangiz uchun hisoblaydi, lekin u "
        "taxminan 10×10 km maydonni bir xil deb biladi.\n\n"
        f"📍 Model hisobga olgan balandlik: {elevation}.\n\n"
        "Sizning hovlingiz farq qilishi mumkin:\n"
        "• Pastqam joy, soy, ariq bo'yi tunda 1–3° sovuqroq. Sovuq havo "
        "suvdek pastga oqadi.\n"
        "• Ochiq dala va tomorqa shahar ichidagi hovlidan sovuqroq.\n"
        "• Devor yonida va daraxt tagida iliqroq.\n\n"
        "Prognoz aniqligi:\n"
        "• Ertangi tun: odatda 1–2° xato.\n"
        "• 2 kundan keyin: 2–3° gacha.\n\n"
        "Shuning uchun men havo 0° ga yetmasa ham, +2° da ogohlantiraman, "
        "agar tun ochiq va shamolsiz bo'lsa. Shunday tunda yer havodan "
        "2–4° sovuqroq bo'ladi va ko'chatda qirov tushadi.\n\n"
        "Maslahat: hovlingizga oddiy termometr osib, bir necha sovuq "
        "tongda meniki bilan solishtiring. Hovlingiz doim 2° sovuqroq "
        "chiqsa, mening ogohlantirishlarimni jiddiyroq qabul qiling."
    )


SAMPLE_PREFIX = "🧪 NAMUNA: sovuq kutilganda xabar shunday keladi.\n\n"
