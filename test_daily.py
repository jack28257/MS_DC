import datetime as dt
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo
from unittest.mock import patch

import generate_daily as daily


class DailyTests(unittest.TestCase):
    def test_one_year_of_new_solvable_puzzles(self):
        fingerprints = set()
        for i in range(365):
            day = dt.date(2026, 10, 17) + dt.timedelta(days=i)
            with self.subTest(day=day):
                payload = daily.generate_challenge(day)
                daily.validate_challenge(payload)
                level = dict(payload["challenge"]["level"])
                level.pop("id")
                fingerprints.add(hashlib.sha256(json.dumps(level, sort_keys=True).encode()).hexdigest())
        self.assertEqual(len(fingerprints), 365)

    def test_rerun_determinism_and_calendar_boundaries(self):
        for key in ("2026-10-17", "2026-12-31", "2027-01-01", "2028-02-29"):
            day = dt.date.fromisoformat(key)
            self.assertEqual(daily.generate_challenge(day), daily.generate_challenge(day))

    def test_seven_am_publication_uses_today_even_before_eight(self):
        for date in ((2026, 3, 8), (2026, 11, 1), (2026, 10, 17)):
            seven = dt.datetime(*date, 7, 0, tzinfo=ZoneInfo("America/Toronto"))
            self.assertEqual(daily.publication_day(seven), seven.date())
            self.assertEqual(daily.publication_day(seven.astimezone(dt.timezone.utc)), seven.date())

    def test_publish_only_today_and_preserve_existing_puzzle(self):
        day = dt.date(2026, 10, 17)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            daily.publish(day, root)
            self.assertEqual([p.name for p in (root / "challenges").iterdir()], ["2026-10-17.json"])
            previous = json.loads((root / "DailyChallenge.json").read_text())["challenge"]
            with patch.object(daily, "generate_challenge", side_effect=AssertionError("Published puzzle regenerated")):
                daily.publish(day, root)
            self.assertEqual(json.loads((root / "DailyChallenge.json").read_text())["challenge"], previous)
            self.assertFalse((root / "DailyChallenges.json").exists())


if __name__ == "__main__":
    unittest.main()
