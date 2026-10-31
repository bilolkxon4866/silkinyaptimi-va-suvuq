
import asyncio

from bot.services.earthquake import get_recent_earthquakes


async def main():
    print("Zilzila ma'lumotlari olinmoqda...\n")

    events, failed_sources = await get_recent_earthquakes()

    if failed_sources:
        print("Javob bermagan manbalar:", ", ".join(failed_sources))

    print(f"Topilgan hodisalar: {len(events)}\n")

    for event in events[:10]:
        magnitudes = ", ".join(
            f"{item['source']} {item['value']} {item['type']}"
            for item in event["magnitudes"]
        )

        print("-" * 40)
        print("Hudud:", event["place"])
        print("Manba:", ", ".join(event["sources"]))
        print("Magnitudalar:", magnitudes)
        print("Chuqurlik:", event["depth"], "km")
        print("Vaqt (UTC):", event["time"])


if __name__ == "__main__":
    asyncio.run(main())
