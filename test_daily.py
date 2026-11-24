import copy
import datetime as dt
import hashlib
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo
from unittest.mock import patch

import generate_daily as daily


def app_contract_samples():
    # All changes are in memory. Both the native loader and the publisher use these cases.
    archive = Path(__file__).parent / 'challenges'
    classic = json.loads((archive / '2026-10-17.json').read_text())
    targets = classic['challenge']['level']['targets']
    classic['challenge']['level']['targets'] = [targets[0], *targets[-2:]]
    yield 'three classic targets', classic, False

    unknown_target = json.loads((archive / '2026-10-22.json').read_text())
    unknown_target['challenge']['level']['demo']['targetColors']['999'] = 'amber'
    yield 'color for an unknown target', unknown_target, False

    for name, boundary, extreme in (('lower', .15, min), ('upper', .935, max)):
        stock = json.loads((archive / '2026-11-15.json').read_text())
        level = stock['challenge']['level']
        level['dailyBoard'] = {'movesMirrors': True, 'walls': []}
        for mirror in level['mirrors']:
            mirror['length'] = .148
        edge = extreme(m['position']['y'] for m in level['mirrors'])
        for obj in [level['emitter'], *level['mirrors'], *level['targets']]:
            position = obj['position']
            position['y'] = boundary if position['y'] == edge else position['y'] + (boundary - edge)
        yield f'{name} stock boundary', stock, True
        outside = copy.deepcopy(stock)
        mirror = next(m for m in outside['challenge']['level']['mirrors'] if m['position']['y'] == boundary)
        mirror['position']['y'] += -.000001 if boundary == .15 else .000001
        yield f'outside {name} stock boundary', outside, False


class DailyTests(unittest.TestCase):
    def test_app_contract(self):
        for name, payload, valid in app_contract_samples():
            with self.subTest(name=name):
                if valid:
                    daily.validate_challenge(payload)
                else:
                    with self.assertRaises(AssertionError):
                        daily.validate_challenge(payload)

    def test_optimized_interpreter_cannot_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, "-O", str(daily.ROOT / "generate_daily.py"),
                                     "--date", "2026-10-17", "--output", tmp], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requires Python assertions", result.stderr)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_mixed_daily_rotation_enforces_route_and_aiming_quality(self):
        fingerprints = set()
        kinds = set()
        families = set()
        bands = set()
        boards = set()
        previous = []
        for i in range(140):
            day = dt.date(2026, 5, 15) + dt.timedelta(days=i)
            with self.subTest(day=day):
                payload = daily.generate_challenge(day, previous)
                daily.validate_challenge(payload)
                self.assertEqual(payload["validation"]["quality"], daily.quality.clarity_profile(payload, daily.BOARD_SIZES))
                recent = previous[-daily.quality.LOOKBACK_DAYS:]
                family = daily.quality.family_for(payload)
                signature = daily.quality.route_signature(payload)
                self.assertNotIn(family, [daily.quality.family_for(old) for old in recent])
                self.assertNotIn(signature, [daily.quality.route_signature(old) for old in recent])
                self.assertGreaterEqual(payload["validation"]["quality"]["minIntendedChanges"], 2)
                families.add(family)
                bands.add(payload['challenge']['difficulty'])
                board = daily.board_options(payload)
                if any(board):
                    self.assertFalse(any(any(daily.board_options(old)) for old in previous[-2:]))
                    self.assertLessEqual(len(payload['challenge']['level']['mirrors']), 5)
                boards.add(board)
                previous.append(payload)
                level = dict(payload["challenge"]["level"])
                kinds.add(level.get('demo', {}).get('kind', 'classic'))
                level.pop("id")
                fingerprints.add(hashlib.sha256(json.dumps(level, sort_keys=True).encode()).hexdigest())
        self.assertEqual(len(fingerprints), 140)
        self.assertEqual(families, {'classic-zigzag', *daily.mechanic_daily.ROUTE_FAMILIES})
        self.assertEqual(kinds, {'classic', 'splitter', 'hazard', 'filter', 'combined'})
        self.assertEqual(bands, {'Standard', 'Advanced'})
        self.assertEqual(boards, {(False, False), (False, True), (True, False), (True, True)})

    def test_combined_stock_board_is_solvable_with_and_without_optional_data(self):
        payload = self.combined_stock_fixture()
        legacy = copy.deepcopy(payload)
        del legacy['challenge']['level']['dailyBoard']
        for size in daily.BOARD_SIZES:
            with self.subTest(size=size), daily.quality.board_size(size):
                result = daily.validator.validate_level(payload)
                old_result = daily.validator.validate_level(legacy)
                self.assertEqual(result.pop('dailyBoardChecks'), ['movableMirrors', 'wall-1'])
                self.assertEqual(result, old_result)
                self.assertEqual(result['mechanicChecks'], ['splitter-1', 'filter-1', 'filter-2', 'hazard-1'])

    def test_invalid_stock_board_or_decorative_wall_is_rejected(self):
        cases = [
            ('Wall outside the board', lambda level: level['dailyBoard']['walls'][0].update(x=0)),
            ('Wall does not block the shortcut', lambda level: level['dailyBoard']['walls'][0].update(x=.93, y=.90)),
            ('Invalid stock mirror length', lambda level: level['mirrors'][0].update(length=.15)),
        ]
        for message, mutate in cases:
            payload = self.combined_stock_fixture()
            mutate(payload['challenge']['level'])
            with self.subTest(message=message), self.assertRaisesRegex(AssertionError, message):
                daily.validate_challenge(payload)

    @staticmethod
    def combined_stock_fixture():
        return daily.mechanic_daily.sample(dt.date(2026, 9, 1), random.Random(5),
                                           family='combined-color-detour', moves_mirrors=True, walls=True)

    def test_legacy_flipped_routes_share_a_signature(self):
        folder = Path(__file__).parent / 'challenges'
        first = json.loads((folder / '2026-11-14.json').read_text())
        flipped = json.loads((folder / '2026-11-22.json').read_text())
        self.assertEqual(daily.quality.route_signature(first), daily.quality.route_signature(flipped))

    def test_publication_consults_only_preceding_dates(self):
        day = dt.date(2026, 10, 30)
        existing = self.load_archived_fixture('2026-10-29')
        future = self.load_archived_fixture('2026-10-31')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / 'challenges'
            folder.mkdir()
            for payload in (existing, future):
                (folder / f"{payload['challenge']['date']}.json").write_text(json.dumps(payload))
            with patch.object(daily, 'generate_challenge', wraps=daily.generate_challenge) as generate:
                daily.publish(day, root)
            self.assertEqual(generate.call_args.args, (day, [existing]))

    @staticmethod
    def load_archived_fixture(day):
        return json.loads((Path(__file__).parent / 'challenges' / f'{day}.json').read_text())

    def test_rerun_determinism_and_calendar_boundaries(self):
        for key in ("2026-10-17", "2025-12-31", "2026-01-01", "2024-02-29"):
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
            dated = root / "challenges" / "2026-10-17.json"
            daily.publish(day, root)
            self.assertEqual([p for p in root.rglob("*.json")], [dated])
            self.assertEqual(json.loads(dated.read_text())["challenge"]["date"], day.isoformat())
            published = dated.read_bytes()
            timestamp = dated.stat().st_mtime_ns
            with patch.object(daily, "generate_challenge", side_effect=AssertionError("Published puzzle regenerated")):
                daily.publish(day, root)
            self.assertEqual(dated.read_bytes(), published)
            self.assertEqual(dated.stat().st_mtime_ns, timestamp)
            self.assertEqual([p for p in root.rglob("*.json")], [dated])

    def test_legacy_published_puzzles_remain_byte_identical(self):
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'challenges').mkdir()
            file=Path(__file__).parent/'challenges/2026-10-19.json'
            shutil.copyfile(file,root/'challenges'/file.name)
            before=(root/'challenges'/file.name).read_bytes()
            with patch.object(daily,'generate_challenge',side_effect=AssertionError('Legacy puzzle replaced')):
                daily.publish(dt.date(2026,10,19),root)
            self.assertEqual((root/'challenges'/file.name).read_bytes(),before)


if __name__ == "__main__":
    unittest.main()
