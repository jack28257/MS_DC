#!/usr/bin/env python3
import json
import math
import sys

EPS = 1e-9
SCENE_WIDTH = 390.0
SCENE_HEIGHT = 620.0
INSET = max(18.0, min(SCENE_WIDTH, SCENE_HEIGHT) * 0.045)
STAGE_RECT = {
    "x": INSET,
    "y": INSET,
    "width": max(SCENE_WIDTH - INSET * 2, 1.0),
    "height": max(SCENE_HEIGHT - INSET * 2, 1.0),
}
MIN_TARGET_RADIUS = 6.0
MAX_REFLECTIONS = 20
OFFICIAL_TOLERANCE = 0.35


def v_add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def v_sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def v_mul(a, scalar):
    return (a[0] * scalar, a[1] * scalar)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def length(v):
    return math.hypot(v[0], v[1])


def norm(v):
    current = length(v)
    if current <= EPS:
        return (0.0, 0.0)
    return (v[0] / current, v[1] / current)


def dist(a, b):
    return length(v_sub(a, b))


def point_from_normalized(p):
    return (
        STAGE_RECT["x"] + p["x"] * STAGE_RECT["width"],
        STAGE_RECT["y"] + p["y"] * STAGE_RECT["height"],
    )


def scaled_length(value):
    return value * min(STAGE_RECT["width"], STAGE_RECT["height"])


def angle_to_vector(degrees):
    radians = degrees * math.pi / 180.0
    return norm((math.cos(radians), math.sin(radians)))


def vector_to_angle(vector):
    return math.degrees(math.atan2(vector[1], vector[0]))


def reflect(direction, across_line_angle_degrees):
    line_direction = angle_to_vector(across_line_angle_degrees)
    reflected = v_sub(v_mul(line_direction, 2 * dot(direction, line_direction)), direction)
    return norm(reflected)


def ray_segment_intersection(origin, direction, segment_start, segment_end):
    segment_vector = v_sub(segment_end, segment_start)
    denominator = cross(direction, segment_vector)
    if abs(denominator) <= EPS:
        return None

    offset = v_sub(segment_start, origin)
    ray_distance = cross(offset, segment_vector) / denominator
    segment_position = cross(offset, direction) / denominator

    if ray_distance <= EPS or segment_position < -EPS or segment_position > 1 + EPS:
        return None
    return {"point": v_add(origin, v_mul(direction, ray_distance)), "distance": ray_distance}


def ray_circle_intersection(origin, direction, center, radius, max_distance):
    to_center = v_sub(center, origin)
    projected = dot(to_center, direction)
    if projected < -radius or projected > max_distance + radius:
        return None

    clamped = min(max(projected, 0.0), max_distance)
    closest = v_add(origin, v_mul(direction, clamped))
    if dist(closest, center) > radius:
        return None
    return {"point": closest, "distance": clamped}


def ray_exit_point(origin, direction):
    candidates = []
    if abs(direction[0]) > EPS:
        x_edge = STAGE_RECT["x"] + STAGE_RECT["width"] if direction[0] > 0 else STAGE_RECT["x"]
        candidates.append((x_edge - origin[0]) / direction[0])
    if abs(direction[1]) > EPS:
        y_edge = STAGE_RECT["y"] + STAGE_RECT["height"] if direction[1] > 0 else STAGE_RECT["y"]
        candidates.append((y_edge - origin[1]) / direction[1])

    positive = [c for c in candidates if c > EPS]
    if not positive:
        return None
    distance_out = min(positive)
    return {"point": v_add(origin, v_mul(direction, distance_out)), "distance": distance_out}


def closest_point_on_segment(start, end, point):
    segment = v_sub(end, start)
    length_sq = dot(segment, segment)
    if length_sq <= EPS:
        return start
    progress = min(max(dot(v_sub(point, start), segment) / length_sq, 0.0), 1.0)
    return v_add(start, v_mul(segment, progress))


def mirror_segment(mirror, angle_degrees=None):
    center = point_from_normalized(mirror["position"])
    direction = angle_to_vector(mirror["angleDegrees"] if angle_degrees is None else angle_degrees)
    half_length = scaled_length(mirror["length"]) / 2.0
    return {
        "start": v_sub(center, v_mul(direction, half_length)),
        "end": v_add(center, v_mul(direction, half_length)),
        "center": center,
    }


def shortest_mirror_line_angle_delta(start_degrees, end_degrees):
    delta = math.fmod(end_degrees - start_degrees, 180.0)
    if delta > 90:
        delta -= 180
    if delta < -90:
        delta += 180
    return delta


def mirror_angle(incoming_direction, outgoing_direction):
    bisector = norm(v_add(norm(incoming_direction), norm(outgoing_direction)))
    if length(bisector) <= EPS:
        return vector_to_angle((-incoming_direction[1], incoming_direction[0]))
    return vector_to_angle(bisector)


def official_angles(level):
    mirrors = level["mirrors"]
    if not mirrors:
        return {}

    targets = level["targets"]
    final_target = point_from_normalized(targets[-1]["position"])
    result = {}
    incoming = angle_to_vector(level["emitter"]["directionDegrees"])
    if length(incoming) <= EPS:
        return None

    for idx, mirror in enumerate(mirrors):
        center = point_from_normalized(mirror["position"])
        destination = (
            point_from_normalized(mirrors[idx + 1]["position"])
            if idx + 1 < len(mirrors)
            else final_target
        )
        outgoing = norm(v_sub(destination, center))
        if length(outgoing) <= EPS:
            return None
        result[mirror["id"]] = mirror_angle(incoming, outgoing)
        incoming = outgoing
    return result


def nearest_mirror_hit(level, origin, direction, max_distance, excluding=None, angle_overrides=None):
    best = None
    angle_overrides = angle_overrides or {}
    for mirror in level["mirrors"]:
        if mirror["id"] == excluding:
            continue
        segment = mirror_segment(mirror, angle_overrides.get(mirror["id"]))
        hit = ray_segment_intersection(origin, direction, segment["start"], segment["end"])
        if not hit:
            continue
        if hit["distance"] >= max_distance - 0.5:
            continue
        if best is None or hit["distance"] < best["distance"]:
            best = {
                "mirrorID": mirror["id"],
                "point": hit["point"],
                "distance": hit["distance"],
            }
    return best


def target_radius(target):
    return max(MIN_TARGET_RADIUS, scaled_length(target["radius"]))


def target_hits_on_segment(level, origin, direction, max_distance, already_collected):
    hits = []
    for target in level["targets"]:
        if target["id"] in already_collected:
            continue
        hit = ray_circle_intersection(
            origin,
            direction,
            point_from_normalized(target["position"]),
            target_radius(target),
            max_distance,
        )
        if hit:
            hits.append({"targetID": target["id"], "point": hit["point"], "distance": hit["distance"]})
    hits.sort(key=lambda item: item["distance"])
    return hits


def add_step(steps, end, collected_target_id=None, reflected_mirror_id=None):
    if steps and dist(steps[-1]["end"], end) < 0.5:
        if collected_target_id is not None:
            steps.append(
                {
                    "end": end,
                    "collectedTargetID": collected_target_id,
                    "reflectedMirrorID": reflected_mirror_id,
                }
            )
        return
    steps.append(
        {
            "end": end,
            "collectedTargetID": collected_target_id,
            "reflectedMirrorID": reflected_mirror_id,
        }
    )


def compute_shot_plan(level, angle_overrides=None):
    angle_overrides = angle_overrides or {}
    origin = point_from_normalized(level["emitter"]["position"])
    direction = angle_to_vector(level["emitter"]["directionDegrees"])
    collected = set()
    steps = []
    reflection_count = 0

    if length(direction) <= EPS:
        return {"steps": steps, "outcome": "failed"}

    bounds = (
        STAGE_RECT["x"] - 1,
        STAGE_RECT["y"] - 1,
        STAGE_RECT["x"] + STAGE_RECT["width"] + 1,
        STAGE_RECT["y"] + STAGE_RECT["height"] + 1,
    )

    while reflection_count <= MAX_REFLECTIONS:
        if not (bounds[0] <= origin[0] <= bounds[2] and bounds[1] <= origin[1] <= bounds[3]):
            return {"steps": steps, "outcome": "failed"}
        boundary_hit = ray_exit_point(origin, direction)
        if not boundary_hit:
            return {"steps": steps, "outcome": "failed"}

        mirror_hit = nearest_mirror_hit(level, origin, direction, boundary_hit["distance"], angle_overrides=angle_overrides)
        segment_end = mirror_hit["point"] if mirror_hit else boundary_hit["point"]
        segment_length = dist(origin, segment_end)

        for target_hit in target_hits_on_segment(level, origin, direction, segment_length, collected):
            if target_hit["targetID"] in collected:
                continue
            collected.add(target_hit["targetID"])
            add_step(steps, target_hit["point"], collected_target_id=target_hit["targetID"])
            if len(collected) == len(level["targets"]):
                return {"steps": steps, "outcome": "clear"}

        add_step(steps, segment_end, reflected_mirror_id=(mirror_hit["mirrorID"] if mirror_hit else None))

        if mirror_hit:
            if reflection_count >= MAX_REFLECTIONS:
                return {"steps": steps, "outcome": "failed"}
            mirror = next((m for m in level["mirrors"] if m["id"] == mirror_hit["mirrorID"]), None)
            if not mirror:
                return {"steps": steps, "outcome": "failed"}
            reflection_count += 1
            angle_degrees = angle_overrides.get(mirror["id"], mirror["angleDegrees"])
            direction = reflect(direction, angle_degrees)
            origin = v_add(mirror_hit["point"], v_mul(direction, 0.8))
            if length(direction) <= EPS:
                return {"steps": steps, "outcome": "failed"}
        else:
            return {"steps": steps, "outcome": "failed"}

    return {"steps": steps, "outcome": "failed"}


def shot_segments(level, steps):
    points = [point_from_normalized(level["emitter"]["position"])] + [step["end"] for step in steps]
    return list(zip(points, points[1:]))


def target_path_accuracy(target, segments):
    if not segments:
        return 0.0
    center = point_from_normalized(target["position"])
    nearest = min(dist(closest_point_on_segment(start, end, center), center) for start, end in segments)
    radius = max(target_radius(target), 1.0)
    return min(max(1 - nearest / radius, 0.0), 1.0)


def mirror_control(level, steps):
    scores = []
    for step in steps:
        mirror_id = step["reflectedMirrorID"]
        if mirror_id is None:
            continue
        mirror = next((m for m in level["mirrors"] if m["id"] == mirror_id), None)
        if not mirror:
            continue
        segment = mirror_segment(mirror)
        half_length = max(dist(segment["start"], segment["end"]) / 2.0, 1.0)
        distance_from_center = dist(step["end"], segment["center"])
        normalized = min(max(distance_from_center / half_length, 0.0), 1.0)
        scores.append((1 - normalized) ** 0.72)
    if not scores:
        return 1.0
    return sum(scores) / len(scores)


def path_economy(path_length):
    board_diagonal = max(math.hypot(STAGE_RECT["width"], STAGE_RECT["height"]), 1.0)
    ratio = path_length / board_diagonal
    overflow = max(ratio - 1.15, 0.0)
    return min(max(1 - overflow / 2.0, 0.0), 1.0)


def validate_level(payload):
    challenge = payload["challenge"]
    level = challenge["level"]
    assert payload["schemaVersion"] == 1
    assert challenge["id"] == f"daily-{challenge['date']}"
    assert challenge["title"] == "Daily Challenge"
    assert challenge["localizedTitle"] == {
        "en": "Daily Challenge",
        "fr": "Défi du jour",
        "zh": "每日挑战",
    }
    assert level["id"] == int(challenge["date"].replace("-", ""))
    assert level["name"] == "Daily Challenge"
    assert level["shotLimit"] == 1
    assert level["parShots"] == 1
    assert 3 <= len(level["mirrors"]) <= 5
    assert 3 <= len(level["targets"]) <= 6

    for point in [level["emitter"]["position"]] + [m["position"] for m in level["mirrors"]] + [t["position"] for t in level["targets"]]:
        assert 0.0 < point["x"] < 1.0
        assert 0.0 < point["y"] < 1.0

    for mirror in level["mirrors"]:
        assert 0.08 <= mirror["length"] <= 0.16

    for target in level["targets"]:
        assert 0.014 <= target["radius"] <= 0.04

    angles = official_angles(level)
    assert angles is not None

    deltas = {}
    for mirror in level["mirrors"]:
        delta = abs(shortest_mirror_line_angle_delta(mirror["angleDegrees"], angles[mirror["id"]]))
        deltas[mirror["id"]] = delta
        assert math.isfinite(mirror["angleDegrees"])

    plan = compute_shot_plan(level, angle_overrides=angles)
    assert plan["outcome"] == "clear"
    collected = [step["collectedTargetID"] for step in plan["steps"] if step["collectedTargetID"] is not None]
    assert collected == [target["id"] for target in level["targets"]]

    segments = shot_segments(level, plan["steps"])
    path_length = sum(dist(start, end) for start, end in segments)
    accuracy_scores = [target_path_accuracy(target, segments) for target in level["targets"]]
    accuracy = sum(accuracy_scores) / len(accuracy_scores)
    worst_accuracy = min(accuracy_scores)
    mirror_control_score = mirror_control(level, plan["steps"])
    path_economy_score = path_economy(path_length)
    reflection_count = len([step for step in plan["steps"] if step["reflectedMirrorID"] is not None])
    reflection_efficiency = max(0.0, 1 - max(reflection_count - max(len(level["mirrors"]), 1), 0) * 0.18)

    perfect = (
        accuracy >= 0.965
        and worst_accuracy >= 0.910
        and mirror_control_score >= 0.865
        and path_economy_score >= 0.665
        and reflection_efficiency >= 0.995
    )
    assert perfect

    return {
        "officialAngles": angles,
        "authoredOfficialAngleDeltas": deltas,
        "targetOrder": collected,
        "reflectionCount": reflection_count,
        "accuracy": accuracy,
        "worstAccuracy": worst_accuracy,
        "mirrorControl": mirror_control_score,
        "pathEconomy": path_economy_score,
        "perfectScoreCapable": perfect,
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: mirror_daily_validator.py <DailyChallenge.json>")
    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    result = validate_level(payload)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
