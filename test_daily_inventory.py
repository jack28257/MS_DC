import datetime as dt
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from tempfile import TemporaryDirectory
from unittest import mock
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

    def test_board_sizes_include_tall_phones(self):
        self.assertTrue(any(height / width >= 1.9 for width, height in inventory.daily_quality.BOARD_SIZES))

    def test_put_requires_the_game_engine_to_accept_the_puzzle(self):
        today = dt.date(2026, 11, 27)
        day = today + dt.timedelta(days=3)
        with TemporaryDirectory() as folder:
            path = Path(folder) / f"{day}.json"
            path.write_text("{}")
            with mock.patch.object(inventory, "toronto_today", return_value=today), \
                 mock.patch.object(inventory, "nearby_puzzles", return_value=({}, {})), \
                 mock.patch.object(inventory, "check_candidate"), \
                 mock.patch.object(inventory, "engine_check", side_effect=ValueError("engine")) as engine, \
                 mock.patch.object(inventory, "d1") as database:
                with self.assertRaisesRegex(ValueError, "engine"):
                    inventory.put(path)
                engine.assert_called_once_with([path])
                database.assert_not_called()

    def test_nearby_slots_on_both_sides_are_included_in_uniqueness_check(self):
        # 2026-11-26 passes at all thirteen sizes; 11-24 and 11-25 (already opened) miss the margin on tall phones.
        day = dt.date(2026, 11, 26)
        raw = (inventory.ARCHIVE / f"{day}.json").read_bytes()
        duplicate = json.loads(raw)
        inventory.check_candidate(raw, day, {})
        for offset in (-2, 2):
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError, "repeats a puzzle"):
                inventory.check_candidate(raw, day, {day + dt.timedelta(days=offset): duplicate})

    def test_mirrored_or_rotated_copy_of_a_nearby_puzzle_is_a_repeat(self):
        # Phase 9: route signatures ignore flips but not swapped axes, so a copy turned a quarter turn or mirrored
        # across the diagonal (renamed family) used to pass as new. A near-identical layout is a repeat either way.
        day = dt.date(2026, 11, 26)
        raw = (inventory.ARCHIVE / f"{day}.json").read_bytes()
        for name, turn in (("transposed", lambda x, y: (y, x)), ("quarter turn", lambda x, y: (1 - y, x)),
                           ("flipped", lambda x, y: (1 - x, y))):
            twin = json.loads(raw)
            twin["validation"]["routeFamily"] = "renamed-" + name
            level = twin["challenge"]["level"]
            demo = level.get("demo") or {}
            objects = [level["emitter"], *level["mirrors"], *level["targets"],
                       *demo.get("splitters", []), *demo.get("filters", []), *demo.get("hazards", [])]
            for point in [obj["position"] for obj in objects] + [pt for path in demo.get("solutionPaths", []) for pt in path]:
                point["x"], point["y"] = turn(point["x"], point["y"])
            with self.subTest(copy=name), self.assertRaisesRegex(ValueError, "repeats a puzzle"):
                inventory.check_candidate(raw, day, {day + dt.timedelta(days=3): twin})
        # Other opened puzzles nearby are not copies of it.
        neighbours = {other: json.loads((inventory.ARCHIVE / f"{other}.json").read_bytes())
                      for other in (dt.date(2026, 11, 23), dt.date(2026, 11, 24), dt.date(2026, 11, 25), dt.date(2026, 11, 27))}
        inventory.check_candidate(raw, day, neighbours)

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

    def test_optimized_interpreter_cannot_use_inventory(self):
        result = subprocess.run([sys.executable, "-O", str(inventory.ROOT / "daily_inventory.py"), "--help"],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires Python assertions", result.stderr)

    def test_archive_preserves_original_bytes_and_refuses_replacement(self):
        day = dt.date(2026, 10, 19)
        raw = (inventory.ARCHIVE / f"{day}.json").read_bytes()
        row = {"release_at": 0, "payload": raw.decode("utf-8")}
        with (tempfile.TemporaryDirectory() as folder,
              patch.object(inventory, "ARCHIVE", Path(folder)),
              patch.object(inventory, "release_at", return_value=0),
              patch.object(inventory, "stored_between", return_value={day: row})):
            path = inventory.ARCHIVE / f"{day}.json"
            inventory.archive(day)
            self.assertEqual(path.read_bytes(), raw)
            timestamp = path.stat().st_mtime_ns

            inventory.archive(day)
            self.assertEqual(path.stat().st_mtime_ns, timestamp)

            row["payload"] += "\n"
            with self.assertRaisesRegex(ValueError, "existing public archive differs"):
                inventory.archive(day)
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(path.stat().st_mtime_ns, timestamp)


if __name__ == "__main__":
    unittest.main()
