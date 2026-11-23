"""Authored route families, sampled layouts and a branch tracer matching the iOS scene.

Counterfactual witnesses check that the intended solution uses each filter and
splitter and that every red zone blocks an otherwise winning shortcut.
"""
import copy
import math
from dataclasses import dataclass
import mirror_daily_validator as v


def circle_entry(origin, direction, center, radius):
    offset = v.v_sub(origin, center)
    if v.length(offset) <= radius:
        return {"point": origin, "distance": 0.0}
    b = v.dot(offset, direction)
    discriminant = b*b - v.dot(offset, offset) + radius*radius
    if discriminant < 0:
        return None
    distance = -b - math.sqrt(discriminant)
    return {"point": v.v_add(origin, v.v_mul(direction, distance)), "distance": distance} if distance > v.EPS else None


def route_angles(level, routes=None):
    demo = level["demo"]
    explicit = {int(k): a for k, a in demo["solutionAngles"].items()}
    return explicit | v.angles_along_routes(level, routes if routes is not None else demo["solutionPaths"])


def trace(level, angles=None, *, use_daily_board=True):
    level, walls = v.active_board(level, angles or {}, use_daily_board)
    demo = level.get("demo", {})
    queue = [(v.point_from_normalized(level["emitter"]["position"]), v.angle_to_vector(level["emitter"]["directionDegrees"]), "white", 0., 0)]
    segments, red_distance, red_point, failure = [], math.inf, None, None
    processed = 0
    while queue and processed < 256:
        queue.sort(key=lambda r: r[3])
        origin, direction, color, travelled, interactions = queue.pop(0)
        processed += 1
        if interactions >= 24:
            failure = "limit"
            continue
        bounds = v.STAGE_RECT
        if not (bounds['x']-1 <= origin[0] <= bounds['x']+bounds['width']+1 and bounds['y']-1 <= origin[1] <= bounds['y']+bounds['height']+1):
            continue
        hit = v.ray_exit_point(origin, direction)
        if not hit:
            continue
        kind, obj = "boundary", None
        mirror = v.nearest_mirror_hit(level, origin, direction, hit['distance'], angle_overrides=angles)
        if mirror:
            hit, kind, obj = mirror, "mirror", next(m for m in level['mirrors'] if m['id'] == mirror['mirrorID'])
        for splitter in demo.get('splitters', ()):
            center = v.point_from_normalized(splitter['position'])
            axis = v.v_mul(v.angle_to_vector(splitter['angleDegrees']), v.scaled_length(splitter['length'])/2)
            candidate = v.ray_segment_intersection(origin, direction, v.v_sub(center, axis), v.v_add(center, axis))
            if candidate and candidate['distance'] < hit['distance']:
                hit, kind, obj = candidate, 'splitter', splitter
        for filter_ in demo.get('filters', ()):
            center, radius = v.point_from_normalized(filter_['position']), v.scaled_length(filter_['radius'])
            if v.dist(origin, center) <= radius + .1:
                continue
            candidate = circle_entry(origin, direction, center, radius)
            if candidate and candidate['distance'] < hit['distance']:
                hit, kind, obj = candidate, 'filter', filter_
        for hazard in demo.get('hazards', ()):
            candidate = circle_entry(origin, direction, v.point_from_normalized(hazard['position']), v.scaled_length(hazard['radius']))
            if candidate and candidate['distance'] <= hit['distance']:
                hit, kind, obj = candidate, 'red', hazard
        wall = v.nearest_wall_hit(walls, origin, direction, hit['distance'])
        if wall:
            hit, kind, obj = wall, 'wall', None
        start, distance, rejected = origin, travelled, False
        for target in v.target_hits_on_segment(level, origin, direction, hit['distance'], set()):
            required = demo.get('targetColors', {}).get(str(target['targetID']))
            if required is not None and required != color:
                failure = failure or 'wrongColor'
                segments.append(dict(start=start, end=target['point'], color=color, distance=distance, targetID=None, rejectedTargetID=target['targetID']))
                rejected = True
                break
            segments.append(dict(start=start, end=target['point'], color=color, distance=distance, targetID=target['targetID']))
            distance += v.dist(start, target['point'])
            start = target['point']
        if rejected:
            continue
        segments.append(dict(start=start, end=hit['point'], color=color, distance=distance, targetID=None))
        distance = travelled + hit['distance']
        if kind == 'red':
            if distance < red_distance:
                red_distance, red_point = distance, hit['point']
            continue
        def enqueue(d, c):
            wall = v.nearest_wall_hit(walls, hit['point'], d, .8)
            offset = wall['distance'] / 2 if wall else .8
            queue.append((v.v_add(hit['point'],v.v_mul(d,offset)),d,c,distance+offset,interactions+1))
        if kind == 'splitter':
            enqueue(direction, color)
            enqueue(v.reflect(direction,obj['angleDegrees']),color)
        elif kind == 'filter':
            enqueue(direction,obj['color'])
        elif kind == 'mirror':
            enqueue(v.reflect(direction,(angles or {}).get(obj['id'],obj['angleDegrees'])),color)
    if queue:
        failure = 'limit'
    if red_point is not None:
        failure = 'red'
        clipped = []
        for segment in segments:
            if segment['distance'] >= red_distance:
                continue
            length = v.dist(segment['start'],segment['end'])
            allowed = min(length,red_distance-segment['distance'])
            piece = dict(segment,end=v.v_add(segment['start'],v.v_mul(v.norm(v.v_sub(segment['end'],segment['start'])),allowed)))
            if allowed + .01 < length:
                piece['targetID'] = None
            clipped.append(piece)
        segments = clipped
    collected = {s['targetID'] for s in segments if s['targetID'] is not None}
    clear = len(collected) == len(level['targets']) and red_point is None and failure != 'limit'
    return dict(outcome='clear' if clear else 'failed',failure=None if clear else failure or 'missed',segments=segments,collected=sorted(collected))


Point = tuple[float, float]
Path = tuple[Point, ...]


@dataclass(frozen=True)
class RouteLayout:
    kind: str
    source: Point
    mirrors: tuple[Point, ...]
    targets: tuple[Point, ...]
    paths: tuple[Path, ...]
    junctions: tuple[Point, ...] = ()
    obstacles: tuple[tuple[Point, tuple[Path, ...]], ...] = ()
    filters: tuple[tuple[Point, int], ...] = ()
    target_colors: tuple[tuple[int, int], ...] = ()
    wall_shortcuts: tuple[tuple[Point, tuple[Path, ...]], ...] = ()


def between(start, end, fraction=.5):
    return (start[0] + (end[0] - start[0]) * fraction,
            start[1] + (end[1] - start[1]) * fraction)


def obstacle_hook():
    source, first, fork = (.07, .25), (.29, .25), (.29, .68)
    detour, goal = (.12, .88), (.85, .68)
    return RouteLayout(
        'hazard', source, (first, fork, detour), (goal,),
        ((source, first, fork, detour, goal),),
        obstacles=((between(fork, goal), ((source, first, fork, goal),)),))


def obstacle_switchback():
    source, first, fork = (.07, .24), (.27, .24), (.27, .63)
    left, far, goal = (.11, .80), (.65, .85), (.65, .63)
    waymark = between(first, fork)
    return RouteLayout(
        'hazard', source, (first, fork, left, far), (waymark, goal),
        ((source, first, fork, left, far, goal),),
        obstacles=((between(fork, goal), ((source, first, fork, goal),)),))


def obstacle_crossing():
    source, first, fork = (.08, .26), (.32, .26), (.62, .43)
    left, goal = (.22, .60), (.62, .85)
    waymark = between(first, fork)
    return RouteLayout(
        'hazard', source, (first, fork, left), (waymark, goal),
        ((source, first, fork, left, goal),),
        obstacles=((between(fork, goal), ((source, first, fork, goal),)),))


def split_relay():
    source, junction = (.07, .25), (.29, .25)
    up, left, upper_goal = (.29, .66), (.12, .86), (.79, .69)
    across, far, outer_goal = (.76, .25), (.76, .47), (.59, .85)
    outer_path = (junction, across, far, outer_goal)
    return RouteLayout(
        'splitter', source, (up, left, across, far), (upper_goal, outer_goal),
        ((junction, up, left, upper_goal), outer_path),
        junctions=(junction,),
        wall_shortcuts=((between(up, upper_goal), ((junction, up, upper_goal), outer_path)),))


def split_offset():
    source, junction = (.07, .24), (.31, .24)
    direct_goal = (.31, .73)
    across, high, inner, far_goal = (.76, .24), (.78, .55), (.57, .76), (.84, .88)
    direct_path = (junction, direct_goal)
    return RouteLayout(
        'splitter', source, (across, high, inner), (direct_goal, far_goal),
        (direct_path, (junction, across, high, inner, far_goal)),
        junctions=(junction,),
        wall_shortcuts=((between(high, far_goal), (direct_path, (junction, across, high, far_goal))),))


def split_late():
    source, first, second, junction = (.07, .22), (.20, .22), (.20, .49), (.46, .49)
    direct_goal = (.46, .86)
    across, high, far_goal = (.80, .49), (.79, .73), (.62, .84)
    direct_path = (source, first, second, junction, direct_goal)
    return RouteLayout(
        'splitter', source, (first, second, across, high), (direct_goal, far_goal),
        (direct_path, (junction, across, high, far_goal)),
        junctions=(junction,),
        wall_shortcuts=((between(across, far_goal), (direct_path, (junction, across, far_goal))),))


def split_cascade():
    source, first_junction, second_junction = (.07, .22), (.27, .22), (.57, .22)
    first, first_goal = (.27, .53), (.11, .64)
    second, second_goal = (.57, .72), (.38, .86)
    third, fourth, third_goal = (.83, .22), (.83, .52), (.67, .57)
    first_path = (first_junction, first, first_goal)
    second_path = (second_junction, second, second_goal)
    return RouteLayout(
        'splitter', source, (first, second, third, fourth), (first_goal, second_goal, third_goal),
        (first_path, second_path, (second_junction, third, fourth, third_goal)),
        junctions=(first_junction, second_junction),
        wall_shortcuts=((between(third, third_goal), (first_path, second_path, (second_junction, third, third_goal))),))


def color_crossover():
    source, first, second, third = (.07, .26), (.30, .26), (.30, .73), (.73, .73)
    first_goal, second_goal = (.30, .57), (.73, .88)
    return RouteLayout(
        'filter', source, (first, second, third), (first_goal, second_goal),
        ((source, first, second, third, second_goal),),
        filters=((between(first, first_goal), 0), (between(second, third), 1)),
        target_colors=((1, 0), (2, 1)))


def color_shared():
    source, junction = (.07, .28), (.36, .28)
    up, across = (.36, .73), (.80, .28)
    near_goal, far_goal, other_goal = (.36, .53), (.60, .86), (.80, .65)
    return RouteLayout(
        'filter', source, (up, across), (near_goal, far_goal, other_goal),
        ((junction, up, far_goal), (junction, across, other_goal)),
        junctions=(junction,),
        filters=((between(source, junction), 0), (between(across, other_goal), 1)),
        target_colors=((1, 0), (2, 0), (3, 1)))


def combined_shortcut():
    source, junction = (.07, .25), (.30, .25)
    up, left, upper_goal = (.30, .67), (.12, .86), (.84, .67)
    across, outer_goal = (.80, .25), (.80, .52)
    outer_path = (junction, across, outer_goal)
    return RouteLayout(
        'combined', source, (up, left, across), (upper_goal, outer_goal),
        ((junction, up, left, upper_goal), outer_path), junctions=(junction,),
        obstacles=((between(up, upper_goal), ((junction, up, upper_goal), outer_path)),),
        filters=((between(junction, up), 0), (between(junction, across), 1)),
        target_colors=((1, 0), (2, 1)))


def combined_color_detour():
    source, junction = (.07, .21), (.29, .21)
    up, across_up, upper_goal = (.29, .60), (.46, .80), (.76, .86)
    across, outer, outer_goal = (.79, .21), (.79, .49), (.54, .44)
    upper_path, outer_path = (junction, up, across_up, upper_goal), (junction, across, outer, outer_goal)
    return RouteLayout(
        'combined', source, (up, across_up, across, outer), (upper_goal, outer_goal),
        (upper_path, outer_path), junctions=(junction,),
        obstacles=((between(up, upper_goal), ((junction, up, upper_goal), outer_path)),),
        filters=((between(junction, up), 0), (between(junction, across), 1)),
        target_colors=((1, 0), (2, 1)),
        wall_shortcuts=((between(across, outer_goal), (upper_path, (junction, across, outer_goal))),))


_LAYOUTS = {
    'obstacle-hook': obstacle_hook(),
    'obstacle-switchback': obstacle_switchback(),
    'obstacle-crossing': obstacle_crossing(),
    'split-relay': split_relay(),
    'split-offset': split_offset(),
    'split-late': split_late(),
    'split-cascade': split_cascade(),
    'color-crossover': color_crossover(),
    'color-shared': color_shared(),
    'combined-shortcut': combined_shortcut(),
    'combined-color-detour': combined_color_detour(),
}
ROUTE_FAMILIES = {family: layout.kind for family, layout in _LAYOUTS.items()}
WALL_FAMILIES = frozenset(family for family, layout in _LAYOUTS.items() if layout.wall_shortcuts)


def sample(day, rng, family=None, *, moves_mirrors=False, walls=False):
    family = family if family is not None else rng.choice(tuple(_LAYOUTS))
    layout = _LAYOUTS[family]
    # A common transform preserves collinearity along routes, including required goals and devices.
    flip_x, flip_y = rng.choice((False, True)), rng.choice((False, True))
    scale_x, scale_y = rng.uniform(.91, 1.06), rng.uniform(.91, 1.06)
    shift_x, shift_y = rng.uniform(-.019, .019), rng.uniform(-.026, .026)

    def point(position):
        x, y = position
        x = .5 + (x - .5) * scale_x + shift_x
        y = .5 + (y - .5) * scale_y + shift_y
        return {'x': 1 - x if flip_x else x, 'y': 1 - y if flip_y else y}

    def paths(routes):
        return [[point(position) for position in route] for route in routes]

    colors = ['cyan', 'amber']
    rng.shuffle(colors)
    # All junctions receive a horizontal ray travelling in the emitter's forward direction.
    splitter_angle = -45 if flip_x != flip_y else 45
    demo = dict(kind=layout.kind,
                splitters=[dict(id=i, position=point(p), angleDegrees=splitter_angle, length=.15)
                           for i, p in enumerate(layout.junctions, 1)],
                hazards=[dict(id=i, position=point(p), radius=rng.uniform(.039, .048))
                         for i, (p, _) in enumerate(layout.obstacles, 1)],
                filters=[dict(id=i, position=point(p), radius=rng.uniform(.034, .041), color=colors[color])
                         for i, (p, color) in enumerate(layout.filters, 1)],
                targetColors={str(i): colors[color] for i, color in layout.target_colors},
                solutionAngles={}, solutionPaths=paths(layout.paths))
    mirrors = [dict(id=i, position=point(p), length=.148 if moves_mirrors else rng.uniform(.136, .165),
                    angleDegrees=0, isRotatable=True)
               for i, p in enumerate(layout.mirrors, 1)]
    targets = [dict(id=i, position=point(p), radius=rng.uniform(.033, .039))
               for i, p in enumerate(layout.targets, 1)]
    level = dict(id=int(day.strftime('%Y%m%d')), name='Daily Challenge', shotLimit=1, parShots=1,
                 emitter=dict(position=point(layout.source), directionDegrees=180 if flip_x else 0),
                 mirrors=mirrors, targets=targets, demo=demo)
    angles = route_angles(level)
    for mirror in mirrors:
        mirror['angleDegrees'] = angles[mirror['id']] + rng.choice((-1, 1)) * rng.uniform(23, 70)
    challenge = dict(id=f'daily-{day.isoformat()}', date=day.isoformat(), title='Daily Challenge',
                     localizedTitle={'en': 'Daily Challenge', 'fr': 'Défi du jour', 'zh': '每日挑战'},
                     difficulty='Challenge', level=level)
    hazard_routes = {str(i): paths(routes) for i, (_, routes) in enumerate(layout.obstacles, 1)}
    validation = dict(hazardRoutes=hazard_routes, routeFamily=family)
    wall_rectangles = []
    if walls:
        if not layout.wall_shortcuts:
            raise ValueError(f"No wall shortcut authored for {family}")
        for center, _ in layout.wall_shortcuts:
            transformed = point(center)
            width = .048 * scale_x
            height = .046 * scale_y
            wall_rectangles.append(dict(x=transformed['x'] - width / 2,
                                        y=1 - transformed['y'] - height / 2, width=width, height=height))
        validation['wallRoutes'] = {str(i): paths(routes) for i, (_, routes) in enumerate(layout.wall_shortcuts, 1)}
    if moves_mirrors or wall_rectangles:
        level['dailyBoard'] = dict(movesMirrors=moves_mirrors, walls=wall_rectangles)
    return dict(schemaVersion=2, challenge=challenge,
                validation=validation)


def validate_level(payload):
    challenge, level = payload['challenge'],payload['challenge']['level']
    demo = level['demo']
    assert payload['schemaVersion']==2
    assert challenge['id']==f"daily-{challenge['date']}" and level['id']==int(challenge['date'].replace('-',''))
    assert level['shotLimit']==level['parShots']==1
    assert 1 <= len(level['mirrors']) <= 8 and 1 <= len(level['targets']) <= 6
    assert demo['kind'] in ('splitter','hazard','filter','combined')
    assert len({m['id'] for m in level['mirrors']})==len(level['mirrors'])
    assert len({t['id'] for t in level['targets']})==len(level['targets'])
    objects=[level['emitter']]+level['mirrors']+level['targets']+demo['splitters']+demo['filters']+demo['hazards']
    assert all(0<p['position']['x']<1 and 0<p['position']['y']<1 for p in objects)
    assert all(m['isRotatable'] and .08<=m['length']<=.18 and math.isfinite(m['angleDegrees']) for m in level['mirrors'])
    assert all(.014<=t['radius']<=.04 for t in level['targets'])
    angles=route_angles(level)
    assert set(angles)=={m['id'] for m in level['mirrors']}
    if 'dailyBoard' not in level:
        return dict(officialAngles=angles, perfectScoreCapable=True,
                    mechanicChecks=validate_mechanic_routes(level, payload, angles))
    legacy_level = {key: value for key, value in level.items() if key != 'dailyBoard'}
    legacy_checks = validate_mechanic_routes(legacy_level, payload, angles)
    board_checks = v.validate_daily_board(payload, trace, angles)
    assert validate_mechanic_routes(level, payload, angles) == legacy_checks
    return dict(officialAngles=angles, perfectScoreCapable=True, mechanicChecks=legacy_checks,
                dailyBoardChecks=board_checks)


def validate_mechanic_routes(level, payload, angles):
    demo = level['demo']
    plan=trace(level,angles)
    assert plan['outcome']=='clear',plan
    assert trace(level)['outcome']!='clear','Puzzle starts solved'
    # Every target must be hit in the full precision core, matching the iOS demo score.
    for target in level['targets']:
        hits=[s for s in plan['segments'] if s['targetID']==target['id']]
        assert min(v.dist(s['end'],v.point_from_normalized(target['position'])) for s in hits) <= v.target_radius(target)*.4+1e-6
    checks=[]
    for splitter in demo['splitters']:
        copy_=copy.deepcopy(level);copy_['demo']['splitters']=[s for s in demo['splitters'] if s['id']!=splitter['id']]
        assert trace(copy_,angles)['outcome']!='clear','Decorative splitter'
        checks.append(f"splitter-{splitter['id']}")
    for filter_ in demo['filters']:
        copy_=copy.deepcopy(level);copy_['demo']['filters']=[f for f in demo['filters'] if f['id']!=filter_['id']]
        rejected=trace(copy_,angles)
        assert rejected['outcome']!='clear' and rejected['failure']=='wrongColor','Decorative filter'
        checks.append(f"filter-{filter_['id']}")
    for hazard in demo['hazards']:
        bypass=dict(angles);bypass.update(route_angles(level,payload['validation']['hazardRoutes'][str(hazard['id'])]))
        blocked=trace(level,bypass)
        copy_=copy.deepcopy(level);copy_['demo']['hazards']=[h for h in demo['hazards'] if h['id']!=hazard['id']]
        assert blocked['failure']=='red' and trace(copy_,bypass)['outcome']=='clear','Decorative red zone'
        checks.append(f"hazard-{hazard['id']}")
    return checks
