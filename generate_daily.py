#!/usr/bin/env python3
"""Publish deterministic, solver-checked daily puzzles. No API keys required."""
import argparse
import copy
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import mirror_daily_validator as validator

ROOT = Path(__file__).resolve().parent
EPOCH = dt.date(1970, 1, 1)
BOARD_SIZES = ((390, 620), (402, 520), (440, 700), (700, 600))


def load_templates():
    return json.loads((ROOT / "DailyChallengeTemplates.json").read_text())["levels"]


def challenge_for(day, templates=None):
    templates = templates if templates is not None else load_templates()
    ordinal = (day - EPOCH).days
    index = ordinal % len(templates)
    flip_y = (ordinal // len(templates)) % 2 == 1
    flip_x = (ordinal // (len(templates) * 2)) % 2 == 1
    level = copy.deepcopy(templates[index])
    date_key = day.isoformat()
    date_number = int(day.strftime("%Y%m%d"))

    def transform(point):
        return {"x": 1 - point["x"] if flip_x else point["x"],
                "y": 1 - point["y"] if flip_y else point["y"]}

    def angle(value):
        if flip_x:
            value = 180 - value
        if flip_y:
            value = -value
        return value

    level["id"] = date_number
    level["name"] = "Daily Challenge"
    level["emitter"]["position"] = transform(level["emitter"]["position"])
    level["emitter"]["directionDegrees"] = angle(level["emitter"]["directionDegrees"])
    for mirror in level["mirrors"]:
        mirror["position"] = transform(mirror["position"])
        offset = 20 + (date_number * 31 + mirror["id"] * 17) % 61
        sign = 1 if (date_number + mirror["id"]) % 2 == 0 else -1
        mirror["angleDegrees"] = angle(mirror["angleDegrees"]) + offset * sign
    for target in level["targets"]:
        target["position"] = transform(target["position"])
    return {"schemaVersion": 1, "challenge": {
        "id": f"daily-{date_key}", "date": date_key, "title": "Daily Challenge",
        "localizedTitle": {"en": "Daily Challenge", "fr": "Défi du jour", "zh": "每日挑战"},
        "difficulty": "Challenge", "level": level}}


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


def active_day(now=None):
    now = now or dt.datetime.now(ZoneInfo("America/Toronto"))
    return now.date() - dt.timedelta(days=1 if now.hour < 8 else 0)


def publish(day, output):
    templates = load_templates()
    challenges = []
    for offset in range(-3, 36):
        payload = challenge_for(day + dt.timedelta(days=offset), templates)
        validate_challenge(payload)
        challenges.append(payload["challenge"])
    feed = {"schemaVersion": 1, "generatorVersion": 1,
            "startDate": challenges[0]["date"], "endDate": challenges[-1]["date"],
            "challenges": challenges}
    output.mkdir(parents=True, exist_ok=True)
    (output / "DailyChallenges.json").write_text(json.dumps(feed, ensure_ascii=False, separators=(",", ":")) + "\n")
    (output / "DailyChallenge.json").write_text(json.dumps(challenge_for(day, templates), ensure_ascii=False, indent=2) + "\n")
    print(f"Validated and published {len(challenges)} challenges: {feed['startDate']} through {feed['endDate']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=dt.date.fromisoformat)
    parser.add_argument("--output", type=Path, default=ROOT)
    args = parser.parse_args()
    publish(args.date or active_day(), args.output)
