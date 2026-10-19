"""Date-seeded optical puzzles and a branch tracer matching the iOS scene.

All geometry is sampled anew. Counterfactual witnesses make every red zone block
a real shortcut, every filter necessary, and every splitter feed a needed branch.
"""
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
    result = {int(k): a for k, a in level["demo"]["solutionAngles"].items()}
    for route in routes if routes is not None else level["demo"]["solutionPaths"]:
        for i in range(1, len(route)-1):
            for mirror in level["mirrors"]:
                if v.dist(v.point_from_normalized(route[i]), v.point_from_normalized(mirror["position"])) < .5:
                    before, center, after = map(v.point_from_normalized, route[i-1:i+2])
                    result[mirror["id"]] = v.mirror_angle(v.v_sub(center, before), v.v_sub(after, center))
    return result


def trace(level, angles=None):
    demo = level["demo"]
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
        for splitter in demo['splitters']:
            center = v.point_from_normalized(splitter['position'])
            axis = v.v_mul(v.angle_to_vector(splitter['angleDegrees']), v.scaled_length(splitter['length'])/2)
            candidate = v.ray_segment_intersection(origin, direction, v.v_sub(center, axis), v.v_add(center, axis))
            if candidate and candidate['distance'] < hit['distance']:
                hit, kind, obj = candidate, 'splitter', splitter
        for filter_ in demo['filters']:
            center, radius = v.point_from_normalized(filter_['position']), v.scaled_length(filter_['radius'])
            if v.dist(origin, center) <= radius + .1:
                continue
            candidate = circle_entry(origin, direction, center, radius)
            if candidate and candidate['distance'] < hit['distance']:
                hit, kind, obj = candidate, 'filter', filter_
        for hazard in demo['hazards']:
            candidate = circle_entry(origin, direction, v.point_from_normalized(hazard['position']), v.scaled_length(hazard['radius']))
            if candidate and candidate['distance'] <= hit['distance']:
                hit, kind, obj = candidate, 'red', hazard
        start, distance, rejected = origin, travelled, False
        for target in v.target_hits_on_segment(level, origin, direction, hit['distance'], set()):
            required = demo['targetColors'].get(str(target['targetID']))
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
            queue.append((v.v_add(hit['point'],v.v_mul(d,.8)),d,c,distance+.8,interactions+1))
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


def sample(day, rng):
    kind = ('combined','splitter','hazard','filter')[day.toordinal() % 4]
    split = kind != 'hazard'
    red = kind in ('hazard','combined')
    filtered = kind in ('filter','combined')
    point = lambda x,y: dict(x=x,y=y)
    low, mid, high = rng.uniform(.20,.28),rng.uniform(.64,.73),rng.uniform(.87,.92)
    sx, left, right = rng.uniform(.25,.34),rng.uniform(.08,.14),rng.uniform(.78,.87)
    emitter, junction = point(.055,low),point(sx,low)
    a, b, target_a = point(sx,mid),point(left,high),point(rng.uniform(.81,.90),mid)
    c, d, target_b = point(right,low),point(right,rng.uniform(.47,.57)),point(rng.uniform(.45,.62),high)
    positions = [a,b,c,d] if split else [junction,a,b]
    mirrors = [dict(id=i+1,position=p,length=rng.uniform(.14,.16),angleDegrees=rng.uniform(-85,85),isRotatable=True) for i,p in enumerate(positions)]
    targets = [dict(id=1,position=target_a,radius=rng.uniform(.026,.035))]
    if split:
        targets.append(dict(id=2,position=target_b,radius=rng.uniform(.026,.035)))
    paths = [[junction,a,b,target_a],[junction,c,d,target_b]] if split else [[emitter,junction,a,b,target_a]]
    shortcut = [[junction,a,target_a],[junction,c,d,target_b]] if split else [[emitter,junction,a,target_a]]
    colors = ['cyan','amber']
    rng.shuffle(colors)
    filters = ([dict(id=1,position=point(sx,(low+mid)/2),radius=.032,color=colors[0]),
                dict(id=2,position=point((sx+right)/2,low),radius=.032,color=colors[1])] if filtered else [])
    demo = dict(kind=kind,splitters=[dict(id=1,position=junction,angleDegrees=45,length=.15)] if split else [],
                hazards=[dict(id=1,position=point((sx+target_a['x'])/2,mid),radius=rng.uniform(.042,.055))] if red else [],
                filters=filters,targetColors={'1':colors[0],'2':colors[1]} if filtered else {},solutionAngles={},solutionPaths=paths)
    level = dict(id=int(day.strftime('%Y%m%d')),name='Daily Challenge',shotLimit=1,parShots=1,
                 emitter=dict(position=emitter,directionDegrees=0),mirrors=mirrors,targets=targets,demo=demo)
    # Affine reflections preserve the topology; all coordinates are freshly sampled.
    flip_x, flip_y = rng.choice((False,True)),rng.choice((False,True))
    seen = set()
    points = [emitter,junction,a,b,c,d,target_a,target_b]+[f['position'] for f in filters]+[h['position'] for h in demo['hazards']]
    for p in points:
        if id(p) in seen: continue
        seen.add(id(p))
        if flip_x: p['x']=1-p['x']
        if flip_y: p['y']=1-p['y']
    level['emitter']['directionDegrees']=180 if flip_x else 0
    if split: demo['splitters'][0]['angleDegrees'] = -45 if flip_x != flip_y else 45
    return dict(schemaVersion=2,challenge=dict(id=f'daily-{day.isoformat()}',date=day.isoformat(),title='Daily Challenge',
                localizedTitle={'en':'Daily Challenge','fr':'Défi du jour','zh':'每日挑战'},difficulty='Challenge',level=level),
                validation=dict(hazardRoutes={'1':shortcut} if red else {}))


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
    return dict(officialAngles=angles,perfectScoreCapable=True,mechanicChecks=checks)
