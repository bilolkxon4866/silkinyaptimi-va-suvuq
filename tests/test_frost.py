
import unittest

from datetime import date, datetime, timedelta

from frost.analysis import (
    LEVEL_FROST,
    LEVEL_GROUND,
    LEVEL_HARD,
    LEVEL_NONE,
    build_climate,
    forecast_nights,
    in_alert_season,
)
from frost.messages import format_alert, format_climate


def archive(years, frost_days, cold=-1.0, warm=10.0, frost_hour=6):
    """Soatlik arxiv: frost_days kunlarida frost_hour soatda sovuq."""

    times, temperatures = [], []
    day = date(years[0], 1, 1)

    while day <= date(years[-1], 12, 31):
        for hour in range(24):
            times.append(f"{day.isoformat()}T{hour:02d}:00")
            is_frost = day in frost_days and hour == frost_hour
            temperatures.append(cold if is_frost else warm)

        day += timedelta(days=1)

    return times, temperatures


YEARS = list(range(2016, 2026))


def spring_frosts(last_days):
    """Har yil uchun oxirgi bahorgi sovuq sanasi (kun, oy)."""

    return {
        date(year, month, day)
        for year, (month, day) in zip(YEARS, last_days)
    }


class ClimateTests(unittest.TestCase):
    def test_nine_of_ten_years(self):
        # 9 yilda oxirgi sovuq 5-aprelgacha, bir yilda 20-aprel.
        last = [(3, 10 + i) for i in range(8)] + [(4, 5), (4, 20)]
        times, temperatures = archive(YEARS, spring_frosts(last))

        climate = build_climate(times, temperatures)
        spring = climate["spring_frost"]

        self.assertEqual(spring["years"], 10)
        self.assertEqual(spring["safe_after"], date(2001, 4, 5))
        self.assertEqual(spring["worst"], date(2025, 4, 20))

        text = format_climate(climate, date(2027, 3, 1))
        self.assertIn("10 yildan 9 tasida 5-apreldan keyin bo'lmagan", text)

    def test_frost_hour_is_local(self):
        times, temperatures = archive(
            YEARS, spring_frosts([(3, 1)] * 10), frost_hour=6
        )
        self.assertEqual(build_climate(times, temperatures)["frost_hour"], 6)

    def test_partial_year_is_dropped(self):
        times, temperatures = archive(YEARS, spring_frosts([(3, 1)] * 10))
        # Joriy yilning boshi qo'shilsa ham, faqat 10 ta to'liq yil.
        times += ["2026-01-01T00:00"]
        temperatures += [5.0]

        climate = build_climate(times, temperatures)
        self.assertEqual(climate["last_year"], 2025)
        self.assertEqual(climate["spring_frost"]["years"], 10)

    def test_autumn_harvest_date(self):
        firsts = [(10, 20 + i) for i in range(9)] + [(10, 5)]
        frost_days = {
            date(year, month, day)
            for year, (month, day) in zip(YEARS, firsts)
        }
        climate = build_climate(*archive(YEARS, frost_days))

        # Ikkinchi eng erta sovuq 20-oktabr: 19-oktabrgacha yig'ish kerak.
        self.assertEqual(
            climate["autumn_frost"]["harvest_by"], date(2001, 10, 19)
        )
        text = format_climate(climate, date(2026, 9, 1))
        self.assertIn("Uzumni 19-oktabrgacha uzib oling", text)

    def test_no_alerts_in_deep_winter(self):
        last = [(3, 15)] * 10
        firsts = {date(year, 11, 5) for year in YEARS}
        climate = build_climate(*archive(YEARS, spring_frosts(last) | firsts))

        self.assertFalse(in_alert_season(climate, date(2027, 1, 15)))
        self.assertTrue(in_alert_season(climate, date(2027, 3, 1)))
        self.assertTrue(in_alert_season(climate, date(2026, 11, 20)))


def forecast(start, temperatures, cloud=0, wind=3, soil=None):
    times = [
        (start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M")
        for i in range(len(temperatures))
    ]

    return {
        "time": times,
        "temperature_2m": temperatures,
        "cloud_cover": [cloud] * len(times),
        "wind_speed_10m": [wind] * len(times),
        "soil_temperature_0cm": [soil] * len(times),
    }


class ForecastTests(unittest.TestCase):
    now = datetime(2026, 4, 1, 15, 0)
    start = datetime(2026, 4, 1, 0, 0)

    def nights(self, cold, **kwargs):
        temperatures = [10.0] * 72
        temperatures[24 + 6] = cold   # 2-aprel tongi, soat 6
        hourly = forecast(self.start, temperatures, **kwargs)
        return {n["morning"]: n for n in forecast_nights(hourly, self.now)}

    def test_levels(self):
        morning = date(2026, 4, 2)
        self.assertEqual(self.nights(-3)[morning]["level"], LEVEL_HARD)
        self.assertEqual(self.nights(-0.5)[morning]["level"], LEVEL_FROST)
        self.assertEqual(self.nights(1.5)[morning]["level"], LEVEL_GROUND)

    def test_cloudy_windy_plus_two_is_not_ground_frost(self):
        nights = self.nights(1.5, cloud=90, wind=20)
        self.assertEqual(nights[date(2026, 4, 2)]["level"], LEVEL_NONE)

    def test_past_and_far_nights_are_skipped(self):
        nights = self.nights(-1)
        # 1-aprel tongi o'tib ketgan, 4-aprel tongi 48 soatdan keyin.
        self.assertNotIn(date(2026, 4, 1), nights)
        self.assertNotIn(date(2026, 4, 4), nights)

    def test_alert_text(self):
        night = self.nights(-1.4, soil=-3.0)[date(2026, 4, 2)]
        text = format_alert(night, self.now.date())

        self.assertIn("Bugun kechasi sovuq", text)
        self.assertIn("2-aprel, payshanba tongi, soat 6", text)
        self.assertIn("−1° gacha", text)
        self.assertIn("Ko'chatlarni", text)
        self.assertIn("termometr emas", text)


if __name__ == "__main__":
    unittest.main()
