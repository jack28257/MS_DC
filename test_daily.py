import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

import generate_daily as daily


class DailyTests(unittest.TestCase):
    def test_full_variant_cycle_has_solvable_unsolved_puzzles(self):
        templates = daily.load_templates()
        self.assertEqual(len(templates), 128)
        # Covers every template and both horizontal/vertical reflections.
        for i in range(len(templates) * 4):
            day = daily.EPOCH + dt.timedelta(days=20480 + i)
            with self.subTest(day=day):
                daily.validate_challenge(daily.challenge_for(day, templates))

    def test_calendar_boundaries_and_determinism(self):
        for key in ("2026-10-17", "2026-12-31", "2027-01-01", "2028-02-29", "2035-01-01"):
            day = dt.date.fromisoformat(key)
            first = daily.challenge_for(day)
            self.assertEqual(first, daily.challenge_for(day))
            self.assertEqual(first["challenge"]["date"], key)
            self.assertNotEqual(first["challenge"]["level"]["mirrors"],
                                daily.challenge_for(day + dt.timedelta(days=1))["challenge"]["level"]["mirrors"])

    def test_eight_am_reset_across_dst(self):
        for day in ((2026, 3, 8), (2026, 11, 1), (2026, 10, 17)):
            before = dt.datetime(*day, 7, 59, tzinfo=ZoneInfo("America/Toronto"))
            after = dt.datetime(*day, 8, 0, tzinfo=ZoneInfo("America/Toronto"))
            self.assertEqual(daily.active_day(before), before.date() - dt.timedelta(days=1))
            self.assertEqual(daily.active_day(after), after.date())

    def test_feed_covers_local_days_and_old_client(self):
        day = dt.date(2026, 10, 17)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            daily.publish(day, path)
            feed = json.loads((path / "DailyChallenges.json").read_text())
            self.assertEqual(len(feed["challenges"]), 39)
            self.assertEqual(feed["startDate"], "2026-10-14")
            self.assertEqual(feed["endDate"], "2026-11-21")
            old = json.loads((path / "DailyChallenge.json").read_text())
            self.assertEqual(old, daily.challenge_for(day))
            self.assertIn(old["challenge"], feed["challenges"])


if __name__ == "__main__":
    unittest.main()
