
"""Ikkala botni bitta jarayonda ishga tushiradi (hosting uchun).

PORT o'rnatilgan bo'lsa (Render), sog'liq tekshiruvi uchun kichik
veb-server ham ochiladi: bepul tarif uxlab qolmasligi uchun unga
har 10 daqiqada ping yuboriladi.
"""

import asyncio
import logging
import os

from aiohttp import web
from dotenv import load_dotenv


load_dotenv()


async def start_health_server(port):
    app = web.Application()
    app.router.add_get("/", lambda request: web.Response(text="ok"))

    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()

    logging.info("Health server: %s port", port)


async def main():
    logging.basicConfig(level=logging.INFO)

    tasks = []

    if os.getenv("BOT_TOKEN"):
        from bot.main import main as quake_main
        tasks.append(quake_main())

    if os.getenv("FROST_BOT_TOKEN"):
        from frost.main import main as frost_main
        tasks.append(frost_main())

    if not tasks:
        raise ValueError("BOT_TOKEN yoki FROST_BOT_TOKEN kerak.")

    if os.getenv("PORT"):
        await start_health_server(int(os.getenv("PORT")))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
