#!/usr/bin/env python3
"""Generate one new, solver-checked puzzle each day and publish it as JSON."""
import argparse
import datetime as dt
import hashlib
import json
import random
from pathlib import Path
from zoneinfo import ZoneInfo

import mirror_daily_validator as validator

ROOT = Path(__file__).resolve().parent
BOARD_SIZES = ((390, 620), (402, 520), (440, 700), (700, 600))


def publication_day(now=None):
    now = now or dt.datetime.now(ZoneInfo("America/Toronto"))
    return now.astimezone(ZoneInfo("America/Toronto")).date()


def validate_challenge(payload):
    original = validator.STAGE_RECT
    try:
        for width, height in BOARD_SIZES:
            inset = max(18.0, min(width, height) * 0.045)
            validator.STAGE_RECT = {"x": inset, "y": inset,
                                    "width": width - 2 * inset, "height": height - 2 * inset}
            validator.validate_level(payload)
            assert validator.compute_shot_plan(payload["challenge"]["level"])["outcome"] != "clear", "Puzzle starts solved"
    finally:
        validator.STAGE_RECT = original


def generate_challenge(day):
    # Seed by date so rerunning a job cannot replace a puzzle already being played.
    seed = int.from_bytes(hashlib.sha256(f"MirrorShot-v2:{day.isoformat()}".encode()).digest(), "big")
    rng = random.Random(seed)
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
                 "mirrors": [{"id": i + 1, "position": p, "length": rng.uniform(0.11, 0.15),
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


def publish(day, output):
    dated = output / "challenges" / f"{day.isoformat()}.json"
    if dated.exists():
        # Keep the first published puzzle immutable, even after generator changes.
        payload = json.loads(dated.read_text())
        if payload["challenge"]["date"] != day.isoformat():
            raise ValueError("Archived challenge date does not match its filename")
        validate_challenge(payload)
    else:
        payload = generate_challenge(day)
        dated.parent.mkdir(parents=True, exist_ok=True)
        dated.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    (output / "DailyChallenge.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"Generated and validated daily challenge {day}: {dated.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=dt.date.fromisoformat)
    parser.add_argument("--output", type=Path, default=ROOT)
    args = parser.parse_args()
    publish(args.date or publication_day(), args.output)
