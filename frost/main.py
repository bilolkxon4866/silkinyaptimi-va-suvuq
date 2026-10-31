
import asyncio
import logging
import os

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from dotenv import load_dotenv

from frost import db
from frost.analysis import (
    LEVEL_FROST,
    LEVEL_NONE,
    build_climate,
    forecast_nights,
    in_alert_season,
)
from frost.messages import (
    ALL_CLEAR_TEXT,
    SAMPLE_PREFIX,
    format_alert,
    format_climate,
    format_evening_reminder,
    format_nights,
    format_trust,
)
from frost.openmeteo import (
    archive_period,
    fetch_archive,
    fetch_forecast,
    grid_key,
)


load_dotenv()

FROST_BOT_TOKEN = os.getenv("FROST_BOT_TOKEN")

if not FROST_BOT_TOKEN:
    raise ValueError("FROST_BOT_TOKEN .env faylida topilmadi!")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=FROST_BOT_TOKEN)
dp = Dispatcher()


MONITORING_INTERVAL_SECONDS = 60 * 60
EVENING_REMINDER_HOUR = 17

BUTTON_NIGHTS = "❄️ Yaqin kechalar"
BUTTON_CLIMATE = "📅 Qachon ekish, qachon yig'ish"
BUTTON_TRUST = "🤔 Ishonsa bo'ladimi?"
BUTTON_ALERTS_ON = "🔔 Ogohlantirishni yoqish"
BUTTON_ALERTS_OFF = "🔕 O'chirish"
BUTTON_LOCATION = "📍 Joyni o'zgartirish"


main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BUTTON_NIGHTS)],
        [KeyboardButton(text=BUTTON_CLIMATE)],
        [
            KeyboardButton(text=BUTTON_TRUST),
            KeyboardButton(text=BUTTON_LOCATION, request_location=True),
        ],
        [
            KeyboardButton(text=BUTTON_ALERTS_ON),
            KeyboardButton(text=BUTTON_ALERTS_OFF),
        ],
    ],
    resize_keyboard=True
)

ASK_LOCATION_TEXT = (
    "Bog'ingiz qayerdaligini bir marta yuboring: pastdagi "
    f"«{BUTTON_LOCATION}» tugmasini bosing.\n"
    "Kompyuterdan bo'lsangiz: 📎 → Joylashuv (Location)."
)


def local_now(timezone_name):
    """Joyning hozirgi vaqti, Open-Meteo vaqtlari bilan bir xil ko'rinishda."""

    return datetime.now(ZoneInfo(timezone_name)).replace(tzinfo=None)


async def load_climate(latitude, longitude):
    """10 yillik xulosa: bazadan, bo'lmasa arxivdan hisoblab."""

    key = grid_key(latitude, longitude)
    start, end = archive_period()
    period = f"{start.year}-{end.year}"

    climate = await db.get_climate(key, period)

    if climate is None:
        archive = await fetch_archive(latitude, longitude)
        climate = build_climate(
            archive["hourly"]["time"],
            archive["hourly"]["temperature_2m"]
        )
        await db.save_climate(key, period, climate)

    return climate


async def require_user(message):
    user = await db.get_user(message.from_user.id)

    if user is None:
        await message.answer(ASK_LOCATION_TEXT, reply_markup=main_keyboard)

    return user


# START
@dp.message(CommandStart())
async def start_handler(message: Message):
    user = await db.get_user(message.from_user.id)

    if user:
        text = (
            "Assalomu alaykum! 👋\n\n"
            "Bog'ingiz joyi saqlangan. Sovuq kutilsa, 1–2 kun oldin "
            "o'zim yozaman."
        )
    else:
        text = (
            "Assalomu alaykum! 👋\n\n"
            "Men «Sovuq urishi» botiman. Bahorda o'rik guli va "
            "ko'chatni, kuzda uzumni nobud qiladigan tungi sovuqdan "
            "1–2 kun oldin ogohlantiraman. Qachon ekish va qachongacha "
            "yig'ishni ham 10 yillik ob-havodan aytib beraman.\n\n"
            + ASK_LOCATION_TEXT
        )

    await message.answer(text, reply_markup=main_keyboard)


@dp.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        f"{BUTTON_NIGHTS} — keyingi 2 kecha sovuq bo'ladimi.\n"
        f"{BUTTON_CLIMATE} — 10 yillik ob-havodan maslahat.\n"
        f"{BUTTON_TRUST} — bu raqamlar qanchalik aniq.\n"
        "/namuna — sovuq kutilganda keladigan xabar namunasi.",
        reply_markup=main_keyboard
    )


# SAVE LOCATION
@dp.message(F.location)
async def location_handler(message: Message):
    latitude = message.location.latitude
    longitude = message.location.longitude

    status = await message.answer("⏳ Bog'ingiz uchun 10 yillik ob-havoni ko'ryapman...")

    try:
        forecast = await fetch_forecast(latitude, longitude)
    except Exception:
        logging.exception("Prognoz olinmadi")
        await status.edit_text(
            "❌ Ob-havo xizmati hozir javob bermayapti. "
            "Birozdan keyin joyni qayta yuboring."
        )
        return

    # Vaqt mintaqasini Open-Meteo joy bo'yicha o'zi aniqlaydi.
    await db.save_user(
        message.from_user.id,
        latitude,
        longitude,
        forecast["timezone"],
        forecast.get("elevation")
    )

    text = (
        "✅ Joy saqlandi. Endi sovuq kutilsa, 1–2 kun oldin yozaman.\n"
        f"🕒 Vaqt mintaqasi: {forecast['timezone']}\n\n"
    )

    try:
        climate = await load_climate(latitude, longitude)
        today = local_now(forecast["timezone"]).date()
        text += format_climate(climate, today)
    except Exception:
        logging.exception("Arxiv olinmadi")
        text += (
            f"10 yillik maslahatni keyinroq «{BUTTON_CLIMATE}» "
            "tugmasi orqali ko'ring."
        )

    await status.delete()
    await message.answer(text, reply_markup=main_keyboard)


@dp.message(F.text == BUTTON_NIGHTS)
async def nights_handler(message: Message):
    user = await require_user(message)

    if user is None:
        return

    try:
        forecast = await fetch_forecast(user["latitude"], user["longitude"])
    except Exception:
        logging.exception("Prognoz olinmadi")
        await message.answer(
            "❌ Ob-havo xizmati hozir javob bermayapti. "
            "Birozdan keyin qayta urinib ko'ring."
        )
        return

    now = local_now(user["timezone"])
    nights = forecast_nights(forecast["hourly"], now)
    text = format_nights(nights, now.date())

    if not user["alerts_on"]:
        text += f"\n\n🔕 Ogohlantirish o'chirilgan. «{BUTTON_ALERTS_ON}»."

    await message.answer(text)


@dp.message(F.text == BUTTON_CLIMATE)
async def climate_handler(message: Message):
    user = await require_user(message)

    if user is None:
        return

    try:
        climate = await load_climate(user["latitude"], user["longitude"])
    except Exception:
        logging.exception("Arxiv olinmadi")
        await message.answer(
            "❌ Arxiv hozir javob bermayapti. Birozdan keyin qayta "
            "urinib ko'ring."
        )
        return

    await message.answer(
        format_climate(climate, local_now(user["timezone"]).date())
    )


@dp.message(F.text == BUTTON_TRUST)
async def trust_handler(message: Message):
    user = await require_user(message)

    if user is not None:
        await message.answer(format_trust(user))


@dp.message(F.text == BUTTON_ALERTS_ON)
async def alerts_on_handler(message: Message):
    if await require_user(message) is None:
        return

    await db.set_alerts(message.from_user.id, True)
    await message.answer(
        "🔔 Ogohlantirish yoqildi. Sovuq kutilsa, 1–2 kun oldin "
        "va o'sha kuni kechqurun yana eslataman."
    )


@dp.message(F.text == BUTTON_ALERTS_OFF)
async def alerts_off_handler(message: Message):
    if await require_user(message) is None:
        return

    await db.set_alerts(message.from_user.id, False)
    await message.answer(
        f"🔕 Ogohlantirish o'chirildi. Qayta yoqish: «{BUTTON_ALERTS_ON}»."
    )


@dp.message(Command("namuna"))
async def sample_handler(message: Message):
    """Kuzda sovuq bo'lmasa ham, tekshiruvchi xabarni ko'ra olishi uchun."""

    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    morning = now.date() + timedelta(days=1)
    coldest = datetime.combine(morning, datetime.min.time()) + timedelta(hours=6)

    night = {
        "morning": morning,
        "min_temperature": -1.4,
        "min_soil": -3.2,
        "coldest": coldest,
        "level": LEVEL_FROST,
        "risk_hours": [coldest - timedelta(hours=2), coldest + timedelta(hours=1)],
    }

    await message.answer(SAMPLE_PREFIX + format_alert(night, now.date()))


# AUTOMATIC MONITORING
async def check_user(user):
    now = local_now(user["timezone"])

    try:
        climate = await load_climate(user["latitude"], user["longitude"])
    except Exception:
        logging.exception("Arxiv olinmadi, mavsum tekshirilmaydi")
        climate = None

    if not in_alert_season(climate, now.date()):
        return

    forecast = await fetch_forecast(user["latitude"], user["longitude"])

    for night in forecast_nights(forecast["hourly"], now):
        stored = await db.get_alert(user["user_id"], night["morning"])
        stored_level, evening_sent = stored or (LEVEL_NONE, 0)

        is_evening = (
            now.hour >= EVENING_REMINDER_HOUR
            and night["morning"] == now.date() + timedelta(days=1)
        )

        if night["level"] > stored_level:
            # Yangi sovuq yoki prognoz kuchaydi.
            text = format_alert(night, now.date())
        elif is_evening and stored and not evening_sent:
            text = (
                format_evening_reminder(night)
                if night["level"] > LEVEL_NONE
                else ALL_CLEAR_TEXT
            )
        else:
            continue

        await bot.send_message(user["user_id"], text)
        await db.save_alert(
            user["user_id"],
            night["morning"],
            night["level"],
            is_evening
        )


async def monitoring_loop():
    while True:
        try:
            users = await db.get_alert_users()
            logging.info("Sovuq monitoringi: %s ta foydalanuvchi.", len(users))

            for user in users:
                try:
                    await check_user(user)
                except Exception:
                    logging.exception(
                        "Tekshiruvda xatolik: %s", user["user_id"]
                    )

            await db.delete_old_alerts()

        except Exception:
            logging.exception("Sovuq monitoringi siklida xatolik")

        await asyncio.sleep(MONITORING_INTERVAL_SECONDS)


# MAIN
async def main():
    await db.init_db()

    logging.info("Sovuq urishi bot ishga tushdi, monitoring yoqildi.")

    monitoring_task = asyncio.create_task(monitoring_loop())

    try:
        await dp.start_polling(bot)

    finally:
        monitoring_task.cancel()

        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass

        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
