#!/usr/bin/env python3
"""One-time authoring tool. Keep published templates stable for existing clients."""
import json
import random
from pathlib import Path

import mirror_daily_validator as validator
from generate_daily import validate_challenge


def build_templates(count=128):
    rng = random.Random(20261017)
    levels = []
    for attempt in range(10000):
        n = rng.randint(3, 5)
        lower, upper = rng.uniform(0.28, 0.37), rng.uniform(0.63, 0.72)
        ys = [lower if i % 2 == 0 else upper for i in range(n)]
        if rng.choice((False, True)):
            ys = [1 - y for y in ys]
        points = [{"x": 0.20 + i * 0.60 / (n - 1) + rng.uniform(-0.015, 0.015),
                   "y": y + rng.uniform(-0.025, 0.025)} for i, y in enumerate(ys)]
        emitter = {"x": 0.065, "y": points[0]["y"]}
        end = {"x": rng.uniform(0.92, 0.95), "y": rng.uniform(0.30, 0.70)}
        chain = [emitter] + points
        targets = []
        for i in range(n):
            start, finish = chain[i:i + 2]
            t = rng.uniform(0.43, 0.59)
            targets.append({"id": i + 1, "position": {
                "x": start["x"] + (finish["x"] - start["x"]) * t,
                "y": start["y"] + (finish["y"] - start["y"]) * t}, "radius": 0.027})
        targets.append({"id": n + 1, "position": end, "radius": 0.027})
        level = {"id": 20261017, "name": "Daily Challenge", "shotLimit": 1, "parShots": 1,
                 "emitter": {"position": emitter, "directionDegrees": 0},
                 "mirrors": [{"id": i + 1, "position": p, "length": 0.13,
                              "angleDegrees": 0, "isRotatable": True} for i, p in enumerate(points)],
                 "targets": targets}
        angles = validator.official_angles(level)
        for mirror in level["mirrors"]:
            mirror["angleDegrees"] = angles[mirror["id"]]
        payload = {"schemaVersion": 1, "challenge": {
            "id": "daily-2026-10-17", "date": "2026-10-17", "title": "Daily Challenge",
            "localizedTitle": {"en": "Daily Challenge", "fr": "Défi du jour", "zh": "每日挑战"}, "level": level}}
        # Validate a scrambled copy; catalog entries retain their reference solution angles.
        import copy
        scrambled = copy.deepcopy(payload)
        for mirror in scrambled["challenge"]["level"]["mirrors"]:
            mirror["angleDegrees"] += 35
        try:
            validate_challenge(scrambled)
        except AssertionError:
            continue
        levels.append(level)
        if len(levels) == count:
            return {"schemaVersion": 1, "generatorVersion": 1, "levels": levels}
    raise RuntimeError("Could not author enough validated templates")


if __name__ == "__main__":
    path = Path(__file__).with_name("DailyChallengeTemplates.json")
    if path.exists():
        raise SystemExit("Catalog already exists. Changing it would change existing daily puzzles.")
    path.write_text(json.dumps(build_templates(), ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"Authored 128 validated templates: {path}")
