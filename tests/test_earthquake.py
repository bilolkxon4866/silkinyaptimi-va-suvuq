
import unittest

from datetime import datetime, timedelta, timezone

from bot.services.earthquake import (
    normalize_emsc,
    normalize_usgs,
    merge_duplicate_events,
    get_nearby_felt_earthquakes,
)
from bot.services.messages import format_event


TASHKENT = (41.31, 69.28)
EVENT_TIME = datetime(2026, 10, 31, 21, 14, 5, tzinfo=timezone.utc)


def usgs_feature(mag=4.6, mag_type="mb", lat=41.10, lon=69.05,
                 seconds=0, status="automatic", event_id="us7000test"):
    timestamp = (EVENT_TIME + timedelta(seconds=seconds)).timestamp()

    return {
        "id": event_id,
        "properties": {
            "mag": mag,
            "magType": mag_type,
            "time": int(timestamp * 1000),
            "place": "25 km SW of Tashkent, Uzbekistan",
            "status": status,
            "type": "earthquake",
            "net": "us",
            "url": "https://earthquake.usgs.gov/earthquakes/eventpage/x",
        },
        "geometry": {"coordinates": [lon, lat, 10.0]},
    }


def emsc_feature(mag=4.3, mag_type="ml", lat=41.15, lon=69.00,
                 seconds=3, evtype="ke", event_id="20261031_0000100"):
    event_time = EVENT_TIME + timedelta(seconds=seconds)

    return {
        "id": event_id,
        "properties": {
            "time": event_time.strftime("%Y-%m-%dT%H:%M:%S.0Z"),
            "lat": lat,
            "lon": lon,
            "depth": 12.0,
            "mag": mag,
            "magtype": mag_type,
            "flynn_region": "UZBEKISTAN",
            "evtype": evtype,
            "auth": "NDC KZ",
        },
        "geometry": {"coordinates": [lon, lat, -12.0]},
    }


class MergeTests(unittest.TestCase):
    def test_same_quake_from_two_sources_is_merged(self):
        events = merge_duplicate_events([
            normalize_usgs(usgs_feature()),
            normalize_emsc(emsc_feature()),
        ])

        self.assertEqual(len(events), 1)
        self.assertEqual(sorted(events[0]["sources"]), ["EMSC", "USGS"])
        self.assertEqual(len(events[0]["ids"]), 2)
        self.assertEqual(
            events[0]["place"], "25 km SW of Tashkent, Uzbekistan"
        )

    def test_two_quakes_from_same_source_are_not_merged(self):
        events = merge_duplicate_events([
            normalize_emsc(emsc_feature(event_id="a")),
            normalize_emsc(emsc_feature(event_id="b", seconds=20)),
        ])

        self.assertEqual(len(events), 2)

    def test_far_apart_quakes_are_not_merged(self):
        events = merge_duplicate_events([
            normalize_usgs(usgs_feature()),
            normalize_emsc(emsc_feature(lat=38.5, lon=68.8)),
        ])

        self.assertEqual(len(events), 2)

    def test_emsc_depth_is_positive(self):
        self.assertEqual(normalize_emsc(emsc_feature())["depth"], 12.0)

    def test_quarry_blasts_are_skipped(self):
        self.assertIsNone(normalize_emsc(emsc_feature(evtype="qb")))


class TrustTests(unittest.TestCase):
    def merged(self, **usgs):
        return merge_duplicate_events([
            normalize_usgs(usgs_feature(**usgs)),
            normalize_emsc(emsc_feature()),
        ])[0]

    def test_local_emsc_magnitude_wins_for_small_quake(self):
        event = self.merged()
        self.assertEqual(event["trusted_magnitude"]["source"], "EMSC")
        self.assertEqual(event["max_magnitude"], 4.6)

    def test_moment_magnitude_wins(self):
        event = self.merged(mag=4.5, mag_type="mww")
        self.assertEqual(event["trusted_magnitude"]["source"], "USGS")

    def test_message_shows_both_magnitudes_and_advice(self):
        event = self.merged()
        nearby = get_nearby_felt_earthquakes([event], *TASHKENT)
        text = format_event(nearby[0], "Asia/Tashkent", "Sarlavha")

        self.assertIn("USGS: 4.6 (mb)", text)
        self.assertIn("EMSC: 4.3 (ml)", text)
        self.assertIn("Ishonchlirog'i: EMSC 4.3", text)
        # 21:14 UTC Toshkentda 02:14 (UTC+5), keyingi kun.
        self.assertIn("01.11.2026 02:14 (UTC+5)", text)


class FeltTests(unittest.TestCase):
    def event(self, mag, lat=41.10, lon=69.05):
        return merge_duplicate_events([
            normalize_usgs(usgs_feature(mag=mag, lat=lat, lon=lon)),
        ])[0]

    def test_moderate_quake_nearby_is_felt(self):
        self.assertEqual(
            len(get_nearby_felt_earthquakes([self.event(4.0)], *TASHKENT)),
            1
        )

    def test_tiny_quake_is_not_felt(self):
        self.assertEqual(
            get_nearby_felt_earthquakes([self.event(2.0)], *TASHKENT),
            []
        )

    def test_small_quake_far_away_is_not_felt(self):
        far = self.event(3.5, lat=38.5, lon=68.8)
        self.assertEqual(get_nearby_felt_earthquakes([far], *TASHKENT), [])

    def test_shared_event_is_not_modified(self):
        event = self.event(4.0)
        get_nearby_felt_earthquakes([event], *TASHKENT)
        self.assertNotIn("distance", event)


if __name__ == "__main__":
    unittest.main()
