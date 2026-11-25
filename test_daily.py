import copy
import json
import unittest
from pathlib import Path

import daily_quality as quality
import mechanic_daily
import mirror_daily_validator as solver


ROOT = Path(__file__).resolve().parent


def archived_puzzle(day):
    return json.loads((ROOT / 'challenges' / f'{day}.json').read_text(encoding='utf-8'))


def mechanic_samples():
    return json.loads((ROOT / 'fixtures' / 'daily-mechanics.json').read_text(encoding='utf-8'))


def app_contract_samples():
    # All changes are in memory. Both the native loader and the publisher use these cases.
    classic = archived_puzzle('2026-10-17')
    targets = classic['challenge']['level']['targets']
    classic['challenge']['level']['targets'] = [targets[0], *targets[-2:]]
    yield 'three classic targets', classic, False

    unknown_target = archived_puzzle('2026-10-22')
    unknown_target['challenge']['level']['demo']['targetColors']['999'] = 'amber'
    yield 'color for an unknown target', unknown_target, False

    samples = mechanic_samples()
    fixed_splitter = samples['fixedSplitter']
    yield 'fixed splitter outlets', fixed_splitter, True
    duplicate_outlets = copy.deepcopy(fixed_splitter)
    duplicate_outlets['challenge']['level']['demo']['splitters'][0]['outputAnglesDegrees'] = [0, 360]
    yield 'same splitter outlet twice', duplicate_outlets, False
    yield 'classic wall detour', samples['wallDetour'], True

    for name, boundary, extreme in (('lower', .15, min), ('upper', .935, max)):
        stock = archived_puzzle('2026-11-15')
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
                    quality.validate_challenge(payload)
                else:
                    with self.assertRaises(AssertionError):
                        quality.validate_challenge(payload)

    def test_combined_stock_board_is_solvable_with_and_without_optional_data(self):
        payload = mechanic_samples()['combinedStock']
        legacy = copy.deepcopy(payload)
        del legacy['challenge']['level']['dailyBoard']
        for size in quality.BOARD_SIZES:
            with self.subTest(size=size), quality.board_size(size):
                result = solver.validate_level(payload)
                old_result = solver.validate_level(legacy)
                self.assertEqual(result.pop('dailyBoardChecks'), ['movableMirrors', 'wall-1', 'wall-2'])
                self.assertEqual(result, old_result)
                self.assertEqual(result['mechanicChecks'], ['splitter-1', 'filter-1', 'filter-2'])

    def test_published_splitter_layout_uses_fixed_outlets_without_looping(self):
        level = archived_puzzle('2026-11-24')['challenge']['level']
        for board in quality.BOARD_SIZES:
            with self.subTest(board=board), quality.board_size(board):
                angles = mechanic_daily.route_angles(level)
                for fixed in (False, True):
                    self.assertEqual(mechanic_daily.trace(level, angles, fixed_splitters=fixed)['outcome'], 'clear')
                    self.assertNotEqual(mechanic_daily.trace(level, fixed_splitters=fixed)['outcome'], 'clear')

    def test_fixed_outlet_departures_are_independent_of_incidence(self):
        level = {'emitter': {'position': {}, 'directionDegrees': 0}, 'mirrors': [], 'targets': [],
                 'demo': {'splitters': [{'id': 1, 'position': {'x': .5, 'y': .5}, 'length': .15,
                                         'angleDegrees': 45, 'outputAnglesDegrees': [0, 90]}]}}
        point = solver.point_from_normalized
        body = mechanic_daily.splitter_body_radius(level['demo']['splitters'][0])
        center = point({'x': .5, 'y': .5})
        outlet_offset = body * 18.3 / 20
        expected = {(center[0] + outlet_offset, center[1]), (center[0], center[1] + outlet_offset)}
        stage = solver.STAGE_RECT
        for incidence in (0, 45, 90, 180, 240, 285):
            with self.subTest(incidence=incidence):
                x, y = solver.angle_to_vector(incidence)
                level['emitter'].update(directionDegrees=incidence,
                                        position={'x': .5 - x * 70 / stage['width'],
                                                  'y': .5 - y * 70 / stage['height']})
                branches = mechanic_daily.trace(level)['segments'][1:]
                self.assertEqual({segment['start'] for segment in branches}, expected)

    def test_invalid_stock_board_or_decorative_wall_is_rejected(self):
        cases = [
            ('Wall outside the board', lambda level: level['dailyBoard']['walls'][0].update(x=0)),
            ('Wall does not block the shortcut', lambda level: level['dailyBoard']['walls'][0].update(x=.93, y=.90)),
            ('Invalid stock mirror length', lambda level: level['mirrors'][0].update(length=.15)),
        ]
        for message, mutate in cases:
            payload = mechanic_samples()['combinedStock']
            mutate(payload['challenge']['level'])
            with self.subTest(message=message), self.assertRaisesRegex(AssertionError, message):
                quality.validate_challenge(payload)

    def test_legacy_flipped_routes_share_a_signature(self):
        first = archived_puzzle('2026-11-14')
        flipped = archived_puzzle('2026-11-22')
        self.assertEqual(quality.route_signature(first), quality.route_signature(flipped))


if __name__ == "__main__":
    unittest.main()
