#!/usr/bin/env python3
"""Generate one new, solver-checked puzzle each day and publish it as JSON."""
import argparse
import datetime as dt
import hashlib
import json
import random
from tempfile import NamedTemporaryFile
from pathlib import Path
from zoneinfo import ZoneInfo

import daily_quality as quality
import mirror_daily_validator as validator
import mechanic_daily

ROOT = Path(__file__).resolve().parent
BOARD_SIZES = ((390, 620), (402, 520), (440, 700), (700, 600), (600, 210), (780, 230), (852, 270))


def publication_day(now=None):
    now = now or dt.datetime.now(ZoneInfo("America/Toronto"))
    return now.astimezone(ZoneInfo("America/Toronto")).date()


def validate_challenge(payload):
    for size in BOARD_SIZES:
        with quality.board_size(size):
            validator.validate_level(payload)
            if payload["schemaVersion"] == 1:
                assert validator.compute_shot_plan(payload["challenge"]["level"])["outcome"] != "clear", "Puzzle starts solved"


def board_options(payload):
    board = payload["challenge"]["level"].get("dailyBoard") or {}
    return board.get("movesMirrors", False), bool(board.get("walls"))


def preferred_board(recent, rng):
    options = [board_options(puzzle) for puzzle in recent]
    if any(moves or walls for moves, walls in options[-2:]):
        return False, False
    special_boards = [(True, False), (False, True), (True, True)]
    rng.shuffle(special_boards)
    return min(special_boards, key=options.count)


def generate_challenge(day, history=()):
    seed = int.from_bytes(hashlib.sha256(f"RaySkip-v5:{day.isoformat()}".encode()).digest(), "big")
    rng = random.Random(seed)
    families = {"classic-zigzag": "classic", **mechanic_daily.ROUTE_FAMILIES}
    recent = tuple(history)[-quality.LOOKBACK_DAYS:]
    recent_families = {quality.family_for(puzzle) for puzzle in recent}
    recent_routes = {quality.route_signature(puzzle) for puzzle in recent}
    previous_kind = recent[-1]["challenge"]["level"].get("demo", {}).get("kind", "classic") if recent else None
    eligible = [name for name in families if name not in recent_families]
    rng.shuffle(eligible)
    desired_board = preferred_board(recent, rng)
    eligible.sort(key=lambda name: families[name] == previous_kind)
    advanced_recently = any(puzzle["challenge"].get("difficulty") == "Advanced" for puzzle in recent[-2:])
    preferred = "Advanced" if not advanced_recently and rng.random() < 0.55 else "Standard"
    alternate = None
    alternate_rank = (-1, -1)

    for attempt in range(20):
        for family in eligible:
            moves, walls = desired_board
            walls = walls and family in mechanic_daily.WALL_FAMILIES
            if family == "classic-zigzag":
                payload = generate_classic_challenge(day, rng, moves_mirrors=moves)
            else:
                payload = mechanic_daily.sample(day, rng, family=family, moves_mirrors=moves, walls=walls)
            if quality.route_signature(payload) in recent_routes:
                continue
            try:
                validate_challenge(payload)
            except AssertionError:
                continue
            profile = quality.clarity_profile(payload, BOARD_SIZES)
            if profile is None:
                continue
            band = "Advanced" if profile["minIntendedChanges"] >= 4 else "Standard"
            payload["challenge"]["difficulty"] = band
            payload.setdefault("validation", {}).update(routeFamily=family, quality=profile)
            rank = (board_options(payload) == desired_board, band == preferred)
            if rank == (True, True):
                return payload
            if rank > alternate_rank:
                alternate = payload
                alternate_rank = rank
        if attempt >= 2 and alternate is not None:
            return alternate
    raise RuntimeError(f"No daily puzzle met the variation, difficulty and aiming checks for {day}")


def generate_classic_challenge(day, rng, *, moves_mirrors=False):
    for _ in range(2048):
        n = rng.randint(3, 5)
        lower, upper = rng.uniform(0.26, 0.38), rng.uniform(0.62, 0.74)
        ys = [lower if i % 2 == 0 else upper for i in range(n)]
        if rng.choice((False, True)):
            ys = [1 - y for y in ys]
        points = [{"x": 0.20 + i * 0.60 / (n - 1) + rng.uniform(-0.02, 0.02),
                   "y": y + rng.uniform(-0.03, 0.03)} for i, y in enumerate(ys)]
        emitter = {"x": rng.uniform(0.055, 0.085), "y": points[0]["y"]}
        end = {"x": rng.uniform(0.92, 0.95), "y": rng.uniform(0.27, 0.73)}
        chain = [emitter] + points
        targets = []
        for i in range(n):
            start, finish = chain[i:i + 2]
            t = rng.uniform(0.40, 0.62)
            targets.append({"id": i + 1, "position": {
                "x": start["x"] + (finish["x"] - start["x"]) * t,
                "y": start["y"] + (finish["y"] - start["y"]) * t}, "radius": rng.uniform(0.023, 0.032)})
        targets.append({"id": n + 1, "position": end, "radius": rng.uniform(0.023, 0.032)})
        level = {"id": int(day.strftime("%Y%m%d")), "name": "Daily Challenge", "shotLimit": 1, "parShots": 1,
                 "emitter": {"position": emitter, "directionDegrees": 0},
                 "mirrors": [{"id": i + 1, "position": p, "length": .148 if moves_mirrors else rng.uniform(0.11, 0.15),
                              "angleDegrees": 0, "isRotatable": True} for i, p in enumerate(points)],
                 "targets": targets}
        # Reflect entire paths for variety while preserving their intended geometry.
        if rng.choice((False, True)):
            for point in [emitter] + [m["position"] for m in level["mirrors"]] + [t["position"] for t in targets]:
                point["x"] = 1 - point["x"]
            level["emitter"]["directionDegrees"] = 180
        angles = validator.official_angles(level)
        for mirror in level["mirrors"]:
            mirror["angleDegrees"] = angles[mirror["id"]] + rng.choice((-1, 1)) * rng.uniform(22, 75)
        if moves_mirrors:
            level["dailyBoard"] = {"movesMirrors": True, "walls": []}
        payload = {"schemaVersion": 1, "challenge": {
            "id": f"daily-{day.isoformat()}", "date": day.isoformat(), "title": "Daily Challenge",
            "localizedTitle": {"en": "Daily Challenge", "fr": "Défi du jour", "zh": "每日挑战"},
            "difficulty": "Challenge", "level": level}}
        try:
            validate_challenge(payload)
            return payload
        except AssertionError:
            continue
    raise RuntimeError(f"Could not generate a valid puzzle for {day}")


def write_json(path, payload):
    # An interrupted publication leaves the previous file available for retry.
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        temporary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def publish(day, output):
    dated = output / "challenges" / f"{day.isoformat()}.json"
    if dated.exists():
        # Keep the first published puzzle immutable, even after generator changes.
        payload = json.loads(dated.read_text())
        if payload["challenge"]["date"] != day.isoformat():
            raise ValueError("Archived challenge date does not match its filename")
        validate_challenge(payload)
        print(f"Validated existing daily challenge {day}; no changes.")
        return

    recent_days = [day - dt.timedelta(days=offset) for offset in range(quality.LOOKBACK_DAYS, 0, -1)]
    recent_files = [output / "challenges" / f"{recent_day.isoformat()}.json" for recent_day in recent_days]
    history = [json.loads(path.read_text()) for path in recent_files if path.is_file()]
    payload = generate_challenge(day, history)
    dated.parent.mkdir(parents=True, exist_ok=True)
    write_json(dated, payload)
    print(f"Generated and validated daily challenge {day}: {dated.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=dt.date.fromisoformat)
    parser.add_argument("--output", type=Path, default=ROOT)
    args = parser.parse_args()
    publish(args.date or publication_day(), args.output)
