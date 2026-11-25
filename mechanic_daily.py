"""Optical tracing and validation for published and current iOS rules."""
import copy
import math
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


def splitter_body_radius(splitter):
    return max(14, min(23, v.scaled_length(splitter['length']) * .48))


def splitter_outlets(level, splitter):
    if 'outputAnglesDegrees' in splitter:
        return tuple(v.angle_to_vector(angle % 360) for angle in splitter['outputAnglesDegrees'])
    center = v.point_from_normalized(splitter['position'])
    outlets = []
    for path in level['demo']['solutionPaths']:
        for start, end in zip(path, path[1:]):
            if start == splitter['position']:
                direction = v.norm(v.v_sub(v.point_from_normalized(end), center))
                if v.length(direction) > v.EPS and not any(v.dot(direction, outlet) > .999999 for outlet in outlets):
                    outlets.append(direction)
    if len(outlets) == 2:
        return outlets
    forward = v.angle_to_vector(level['emitter']['directionDegrees'])
    return forward, v.reflect(forward, splitter['angleDegrees'])


def trace(level, angles=None, *, use_daily_board=True, fixed_splitters=None):
    level, walls = v.active_board(level, angles or {}, use_daily_board)
    demo = level.get("demo", {})
    queue = [(v.point_from_normalized(level["emitter"]["position"]), v.angle_to_vector(level["emitter"]["directionDegrees"]), "white", 0., 0, None, frozenset())]
    segments, red_distance, red_point, failure = [], math.inf, None, None
    processed = 0
    while queue and processed < 256:
        queue.sort(key=lambda r: r[3])
        origin, direction, color, travelled, interactions, departing_splitter, splitter_ancestry = queue.pop(0)
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
            if splitter['id'] == departing_splitter:
                continue
            center = v.point_from_normalized(splitter['position'])
            fixed = fixed_splitters if fixed_splitters is not None else 'outputAnglesDegrees' in splitter
            if fixed:
                candidate = circle_entry(origin, direction, center, splitter_body_radius(splitter) * .79)
            else:
                axis = v.v_mul(v.angle_to_vector(splitter['angleDegrees']), v.scaled_length(splitter['length']) / 2)
                candidate = v.ray_segment_intersection(origin, direction, v.v_sub(center, axis), v.v_add(center, axis))
            if candidate and candidate['distance'] < hit['distance']:
                hit, kind, obj = candidate, 'fixedSplitter' if fixed else 'splitter', splitter
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
        def enqueue(d, c, *, start=None, offset=.8, departing=None, ancestry=splitter_ancestry):
            start = hit['point'] if start is None else start
            wall = v.nearest_wall_hit(walls, start, d, offset)
            advance = wall['distance'] / 2 if wall else offset
            queue.append((v.v_add(start, v.v_mul(d, advance)), d, c, distance + advance, interactions + 1, departing, ancestry))
        if kind == 'splitter':
            enqueue(direction, color)
            enqueue(v.reflect(direction,obj['angleDegrees']),color)
        elif kind == 'fixedSplitter':
            activation = (obj['id'], color)
            # The same branch returning with the same color would repeat both fixed paths.
            if activation in splitter_ancestry:
                continue
            ancestry = splitter_ancestry | {activation}
            center = v.point_from_normalized(obj['position'])
            outlet_offset = splitter_body_radius(obj) * (18.3 / 20)
            for outlet in splitter_outlets(level, obj):
                start = v.v_add(center, v.v_mul(outlet, outlet_offset))
                enqueue(outlet, color, start=start, offset=0, departing=obj['id'], ancestry=ancestry)
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


def validate_mechanics(payload):
    level = payload['challenge']['level']
    demo = level['demo']
    splitters, hazards, filters = demo['splitters'], demo['hazards'], demo['filters']
    target_colors = demo['targetColors']
    kinds = {
        'splitter': splitters and not hazards and not filters,
        'hazard': hazards and not splitters and not filters,
        'filter': filters and not hazards and target_colors,
        'combined': splitters and hazards and filters and target_colors,
    }
    assert kinds.get(demo['kind']), "Mechanics do not match the daily kind"
    assert len(splitters) <= 3 and len(hazards) <= 4 and len(filters) <= 4
    for objects in (splitters, hazards, filters):
        assert len({obj['id'] for obj in objects}) == len(objects), "Duplicate mechanic ID"
    assert all(.08 <= s['length'] <= .20 and math.isfinite(s['angleDegrees']) for s in splitters)
    for splitter in splitters:
        if 'outputAnglesDegrees' in splitter:
            outlets = splitter['outputAnglesDegrees']
            assert isinstance(outlets, list) and len(outlets) == 2, 'A splitter requires two outlet angles'
            assert all(type(angle) in (int, float) and math.isfinite(angle) for angle in outlets), 'Invalid splitter outlet angle'
            first, second = (angle % 360 for angle in outlets)
            assert abs(math.sin((first - second) * math.pi / 360)) > .0001, 'Splitter outlets must point in different directions'
    assert all(.02 <= h['radius'] <= .12 for h in hazards)
    assert all(.015 <= f['radius'] <= .06 and f['color'] in ('cyan', 'amber') for f in filters)
    assert target_colors.keys() <= {str(t['id']) for t in level['targets']}
    assert all(color in ('white', 'cyan', 'amber') for color in target_colors.values())
    assert demo['solutionAngles'].keys() <= {str(m['id']) for m in level['mirrors']}
    assert all(math.isfinite(a) for a in demo['solutionAngles'].values())
    paths = demo['solutionPaths']
    assert 1 <= len(paths) <= 8 and all(2 <= len(path) <= 12 for path in paths)
    points = [obj['position'] for obj in splitters + hazards + filters] + [p for path in paths for p in path]
    assert all(0 < p['x'] < 1 and 0 < p['y'] < 1 for p in points)
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
    if any('outputAnglesDegrees' in splitter for splitter in demo['splitters']):
        assert trace(level, angles, fixed_splitters=False)['outcome'] == 'clear', 'Previous client cannot solve this splitter layout'
        assert trace(level, fixed_splitters=False)['outcome'] != 'clear', 'Previous client starts solved'
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
