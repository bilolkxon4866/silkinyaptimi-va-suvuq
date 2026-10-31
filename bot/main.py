
import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton
)

from bot.config import BOT_TOKEN

from bot.database.db import (
    init_db,
    save_location,
    get_location,
    subscribe_user,
    unsubscribe_user,
    get_users_to_monitor,
    start_watch,
    mark_watch_found,
    pop_finished_watches,
    notification_already_sent,
    mark_notification_sent,
    delete_old_notifications
)

from bot.services.earthquake import (
    get_recent_earthquakes,
    get_nearby_felt_earthquakes
)

from bot.services.messages import (
    format_event,
    format_failed_sources,
    NOTHING_YET_TEXT,
    SOURCES_DOWN_TEXT,
    WATCH_FINISHED_TEXT
)

from bot.services.timezones import find_timezone_name


# LOGGING
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


MONITORING_INTERVAL_SECONDS = 60
WATCH_MINUTES = 30

BUTTON_CHECK = "🌍 Silkindimi?"
BUTTON_SUBSCRIBE = "🔔 Xabarnomaga obuna bo‘lish"
BUTTON_UNSUBSCRIBE = "🔕 Xabarnomani to‘xtatish"
BUTTON_LOCATION = "📍 Joylashuvni yangilash"


# KEYBOARD
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BUTTON_CHECK)],
        [
            KeyboardButton(text=BUTTON_SUBSCRIBE),
            KeyboardButton(text=BUTTON_UNSUBSCRIBE)
        ],
        [
            KeyboardButton(
                text=BUTTON_LOCATION,
                request_location=True
            )
        ]
    ],
    resize_keyboard=True
)

ASK_LOCATION_TEXT = (
    "Pastdagi «📍 Joylashuvni yangilash» tugmasini bosing.\n"
    "Kompyuterdan bo'lsangiz: 📎 → Joylashuv (Location).\n\n"
    "Joylashuv faqat yaqin zilzilalarni aniqlash uchun saqlanadi."
)


# START
@dp.message(CommandStart())
async def start_handler(message: Message):
    location = await get_location(message.from_user.id)

    if location:
        text = (
            "Assalomu alaykum! 👋\n\n"
            "Joylashuvingiz saqlangan. Silkingandek tuyulsa, "
            f"«{BUTTON_CHECK}» tugmasini bosing.\n\n"
            "🔔 Avtomatik xabar olish uchun obuna bo‘ling."
        )
    else:
        text = (
            "Assalomu alaykum! 👋\n\n"
            "Siz «Silkinyaptimi?» botidasiz. Kechasi silkingandek "
            "tuyulsa, bir tugma bilan zilzila bo'lgan-bo'lmaganini "
            "bilib olasiz.\n\n"
            "Boshlash uchun joylashuvingizni bir marta yuboring.\n"
            + ASK_LOCATION_TEXT
        )

    await message.answer(text, reply_markup=main_keyboard)


@dp.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        f"{BUTTON_CHECK} — oxirgi 30 daqiqada yaqiningizda sezilishi "
        "mumkin bo'lgan zilzila bo'lganini tekshiradi.\n"
        f"{BUTTON_SUBSCRIBE} — yaqiningizdagi sezilarli zilzilalar "
        "haqida avtomatik xabar.\n"
        f"{BUTTON_LOCATION} — joylashuvni o'zgartirish.\n\n"
        "Ma'lumot manbalari: USGS va EMSC.",
        reply_markup=main_keyboard
    )


# SAVE LOCATION
@dp.message(F.location)
async def location_handler(message: Message):
    latitude = message.location.latitude
    longitude = message.location.longitude
    timezone_name = find_timezone_name(latitude, longitude)

    await save_location(
        message.from_user.id,
        latitude,
        longitude,
        timezone_name
    )

    await message.answer(
        "✅ Joylashuvingiz saqlandi!\n\n"
        f"🕒 Vaqt mintaqangiz: {timezone_name}\n"
        "Keyingi safar qayta yuborishingiz shart emas.\n\n"
        f"Endi «{BUTTON_CHECK}» tugmasidan foydalanishingiz mumkin.",
        reply_markup=main_keyboard
    )


# MANUAL EARTHQUAKE CHECK
@dp.message(F.text == BUTTON_CHECK)
async def earthquake_handler(message: Message):
    user_id = message.from_user.id
    location = await get_location(user_id)

    if not location:
        await message.answer(
            "Avval joylashuvingizni yuborishingiz kerak. 📍\n\n"
            + ASK_LOCATION_TEXT,
            reply_markup=main_keyboard
        )
        return

    latitude, longitude, timezone_name = location

    status = await message.answer("🔎 Tekshiryapman...")

    events, failed_sources = await get_recent_earthquakes()

    if len(failed_sources) == 2:
        await start_watch(user_id, WATCH_MINUTES)
        await status.edit_text(SOURCES_DOWN_TEXT)
        return

    nearby_events = get_nearby_felt_earthquakes(
        events,
        latitude,
        longitude
    )

    if not nearby_events:
        await start_watch(user_id, WATCH_MINUTES)
        await status.edit_text(
            NOTHING_YET_TEXT + format_failed_sources(failed_sources)
        )
        return

    await status.delete()

    for event in nearby_events:
        await message.answer(
            format_event(
                event,
                timezone_name,
                "⚠️ Ha, yaqiningizda zilzila qayd etildi"
            )
            + format_failed_sources(failed_sources)
        )

        # Monitoring shu hodisani qayta yubormasligi uchun.
        await mark_notification_sent(user_id, event["ids"])


# SUBSCRIBE
@dp.message(F.text == BUTTON_SUBSCRIBE)
async def subscribe_handler(message: Message):
    location = await get_location(message.from_user.id)

    if not location:
        await message.answer(
            "Avval joylashuvingizni yuboring. 📍\n\n" + ASK_LOCATION_TEXT
        )
        return

    await subscribe_user(message.from_user.id)

    await message.answer(
        "🔔 Xabarnoma yoqildi!\n\n"
        "Joyingizda sezilishi mumkin bo'lgan zilzila qayd etilsa, "
        "darhol xabar yuboraman. Sezilmaydigan mayda silkinishlar "
        "haqida bezovta qilmayman."
    )


# UNSUBSCRIBE
@dp.message(F.text == BUTTON_UNSUBSCRIBE)
async def unsubscribe_handler(message: Message):
    await unsubscribe_user(message.from_user.id)

    await message.answer(
        "🔕 Xabarnomalar to‘xtatildi.\n"
        "Istalgan vaqtda qayta obuna bo‘lishingiz mumkin."
    )


# AUTOMATIC MONITORING
async def notify_users(events):
    users = await get_users_to_monitor()

    logging.info(
        "Monitoring: %s ta hodisa, %s ta foydalanuvchi.",
        len(events),
        len(users)
    )

    for user_id, latitude, longitude, timezone_name in users:
        nearby_events = get_nearby_felt_earthquakes(
            events,
            latitude,
            longitude
        )

        for event in nearby_events:
            # Ma'lumot 2-20 daqiqa kechikib keladi, shuning uchun
            # vaqt bo'yicha emas, manba ID'lari bo'yicha tekshiramiz.
            if await notification_already_sent(user_id, event["ids"]):
                continue

            text = format_event(
                event,
                timezone_name,
                "⚠️ Yaqiningizda zilzila qayd etildi"
            )

            try:
                await bot.send_message(user_id, text)
            except Exception:
                logging.exception("Xabarnoma yuborilmadi: %s", user_id)
                continue

            await mark_notification_sent(user_id, event["ids"])
            await mark_watch_found(user_id)


async def finish_watches():
    for user_id in await pop_finished_watches():
        try:
            await bot.send_message(user_id, WATCH_FINISHED_TEXT)
        except Exception:
            logging.exception("Kuzatuv yakuni yuborilmadi: %s", user_id)


async def monitoring_loop():
    while True:
        try:
            events, failed_sources = await get_recent_earthquakes()

            if len(failed_sources) < 2:
                await notify_users(events)

            await finish_watches()
            await delete_old_notifications()

        except Exception:
            logging.exception("Avtomatik monitoring siklida xatolik")

        await asyncio.sleep(MONITORING_INTERVAL_SECONDS)


# MAIN
async def main():
    await init_db()

    logging.info("Silkinyaptimi bot ishga tushdi, monitoring yoqildi.")

    monitoring_task = asyncio.create_task(
        monitoring_loop()
    )

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
