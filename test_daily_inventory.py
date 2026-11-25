import datetime as dt
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

import daily_inventory as inventory


class DailyInventoryTests(unittest.TestCase):
    def test_release_uses_eight_toronto_across_daylight_saving(self):
        for date, utc_hour in ((dt.date(2026, 3, 7), 13), (dt.date(2026, 3, 8), 12),
                               (dt.date(2026, 10, 31), 12), (dt.date(2026, 11, 1), 13)):
            instant = dt.datetime.fromtimestamp(inventory.release_at(date) / 1000, dt.timezone.utc)
            self.assertEqual(instant.date(), date)
            self.assertEqual(instant.hour, utc_hour)
        self.assertEqual(inventory.stock_dates(dt.date(2026, 12, 28))[-1], dt.date(2027, 1, 4))

    def test_nearby_future_slot_is_included_in_uniqueness_check(self):
        day = dt.date(2026, 11, 25)
        raw = (inventory.ARCHIVE / f"{day}.json").read_bytes()
        duplicate = json.loads(raw)
        inventory.check_candidate(raw, day, {})
        with self.assertRaisesRegex(ValueError, "repeats a puzzle"):
            inventory.check_candidate(raw, day, {day + dt.timedelta(days=2): duplicate})

    def test_explicit_replacement_cannot_overwrite_current_day(self):
        day = dt.date(2026, 11, 25)
        with patch.object(inventory, "toronto_today", return_value=day), patch.object(inventory, "d1") as db:
            with self.assertRaises(ValueError):
                inventory.put(Path(f"{day}.json"), replace=True, allow_today=True)
            db.assert_not_called()

    def test_sql_preserves_valid_utf8_and_quotes(self):
        raw = "八点\n'RaySkip'".encode("utf-8")
        with sqlite3.connect(":memory:") as db:
            self.assertEqual(db.execute("SELECT " + inventory.sql_text(raw)).fetchone()[0], raw.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
