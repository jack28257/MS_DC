"""Release checks for daily puzzles and tools for comparing published routes."""

from contextlib import contextmanager
from itertools import combinations

import mechanic_daily
import mirror_daily_validator as solver


LOOKBACK_DAYS = 7
# Scene sizes a daily must work at. The last six were added on 2026-11-27: tall phones (height about 1.9 to 2.0
# times the width), the smallest phone and an iPad. The game engine check uses the same thirteen sizes.
BOARD_SIZES = ((390, 620), (402, 520), (440, 700), (700, 600), (600, 210), (780, 230), (852, 270),
               (393, 748), (402, 788), (430, 850), (440, 868), (320, 460), (768, 900))
PORTRAIT_MARGIN_DEGREES = 0.50
LANDSCAPE_MARGIN_DEGREES = 0.25
SHORTCUT_STEP_DEGREES = 5


@contextmanager
def board_size(size):
    width, height = size
    inset = max(18., min(width, height) * .045)
    original = solver.STAGE_RECT
    solver.STAGE_RECT = dict(x=inset, y=inset, width=width - 2 * inset, height=height - 2 * inset)
    try:
        yield
    finally:
        solver.STAGE_RECT = original


def validate_challenge(payload):
    for size in BOARD_SIZES:
        with board_size(size):
            solver.validate_level(payload)


def route_signature(payload):
    """Ignore object coordinates, colors, and flips when comparing route structure."""
    level = payload['challenge']['level']
    demo = level.get('demo')
    if not demo and family_for(payload) == 'classic-zigzag':
        return (('zigzag',),)

    points = lambda objects: {(obj['position']['x'], obj['position']['y']) for obj in objects}
    junctions = points(demo['splitters']) if demo else set()
    mirrors = points(level['mirrors'])
    targets = points(level['targets'])

    def point_role(point):
        if point in junctions:
            return 'junction'
        if point in mirrors:
            return 'mirror'
        if point in targets:
            return 'target'
        return 'source'

    def axis(delta):
        if abs(delta) < .012:
            return 0
        return 1 if delta > 0 else -1

    paths = demo['solutionPaths'] if demo else [[obj['position'] for obj in (
        level['emitter'], *level['mirrors'], level['targets'][-1]
    )]]
    routes = [[(point['x'], point['y']) for point in route] for route in paths]
    roles_and_vectors = [tuple((point_role(a), axis(b[0] - a[0]), axis(b[1] - a[1]), point_role(b))
                               for a, b in zip(route, route[1:])) for route in routes]

    return min(tuple(sorted(tuple((start, x * sx, y * sy, end) for start, x, y, end in route)
                            for route in roles_and_vectors))
               for sx in (-1, 1) for sy in (-1, 1))


COPY_TOLERANCE = .05
# The board's eight symmetries in normalized coordinates: flips of either axis, with or without swapping the axes.
BOARD_SYMMETRIES = tuple(
    (lambda swap, fx, fy: lambda x, y: ((1 - y if fx else y, 1 - x if fy else x) if swap
                                        else (1 - x if fx else x, 1 - y if fy else y)))(swap, fx, fy)
    for swap in (False, True) for fx in (False, True) for fy in (False, True))


def layout_groups(payload):
    """Object positions by kind (emitter, mirrors, targets, optics, wall centres) in normalized coordinates."""
    level = payload['challenge']['level']
    demo = level.get('demo') or {}
    walls = (level.get('dailyBoard') or {}).get('walls', [])
    position = lambda obj: (obj['position']['x'], obj['position']['y'])
    return {
        'emitter': [position(level['emitter'])],
        'mirrors': [position(obj) for obj in level['mirrors']],
        'targets': [position(obj) for obj in level['targets']],
        'splitters': [position(obj) for obj in demo.get('splitters', [])],
        'filters': [position(obj) for obj in demo.get('filters', [])],
        'hazards': [position(obj) for obj in demo.get('hazards', [])],
        'walls': [(wall['x'] + wall['width'] / 2, wall['y'] + wall['height'] / 2) for wall in walls if 'width' in wall],
    }


def is_mirrored_copy(first, second, tolerance=COPY_TOLERANCE):
    """True when some flip, quarter turn or transposition of `first` puts every object within `tolerance` of an
    object of the same kind in `second`: a re-skin of the same puzzle, which `route_signature` misses when the
    axes are swapped."""
    a, b = layout_groups(first), layout_groups(second)
    if any(len(a[kind]) != len(b[kind]) for kind in a):
        return False
    for symmetry in BOARD_SYMMETRIES:
        if all(min(((x2 - u) ** 2 + (y2 - v) ** 2) ** .5 for x2, y2 in b[kind]) <= tolerance
               for kind in a for u, v in (symmetry(x, y) for x, y in a[kind])):
            return True
    return False


def family_for(payload):
    default = 'classic-zigzag' if payload['schemaVersion'] == 1 else None
    return payload.get('validation', {}).get('routeFamily', default)


def clarity_profile(payload, sizes):
    """Check aiming margin on every board and screen for quick ways to clear."""
    level = payload['challenge']['level']
    mechanic = payload['schemaVersion'] == 2
    board = level.get('dailyBoard') or {}
    trace = mechanic_daily.trace if mechanic or board else solver.compute_shot_plan
    solve_angles = mechanic_daily.route_angles if mechanic else solver.official_angles
    mirror_ids = [mirror['id'] for mirror in level['mirrors']]

    def clears(angles):
        return trace(level, angles)['outcome'] == 'clear'

    for size in sizes:
        margin = PORTRAIT_MARGIN_DEGREES if size[0] <= size[1] else LANDSCAPE_MARGIN_DEGREES
        with board_size(size):
            solution = solve_angles(level)
            for key in mirror_ids:
                for sign in (-1, 1):
                    adjusted = dict(solution)
                    adjusted[key] += sign * margin
                    if not clears(adjusted):
                        return None
                    if board.get('movesMirrors') and not solver.legal_stock_layout(level, adjusted, board['walls']):
                        return None

    with board_size(sizes[0]):
        solution = solve_angles(level)
        for key in mirror_ids:
            if clears({key: solution[key]}) or any(
                clears({key: angle}) for angle in range(0, 180, SHORTCUT_STEP_DEGREES)
            ):
                return None
        # This searches subsets of the authored solution, which is a bound on tuning work,
        # rather than an exhaustive search of every possible route through the board.
        moves = next(
            count for count in range(2, len(mirror_ids) + 1)
            if any(clears({key: solution[key] for key in group}) for group in combinations(mirror_ids, count))
        )

    return dict(minIntendedChanges=moves, portraitMarginDegrees=PORTRAIT_MARGIN_DEGREES,
                landscapeMarginDegrees=LANDSCAPE_MARGIN_DEGREES,
                shortcutSweepStepDegrees=SHORTCUT_STEP_DEGREES)
