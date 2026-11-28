"""Validate and manage the private RaySkip daily challenge inventory."""

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
from tempfile import NamedTemporaryFile, TemporaryDirectory
from urllib.error import HTTPError
from urllib.request import urlopen
from zoneinfo import ZoneInfo

import daily_quality


TORONTO = ZoneInfo("America/Toronto")
STOCK_DAYS = 7
MAX_PAYLOAD_BYTES = 65_536
ROOT = Path(__file__).resolve().parent
SUPPORT = ROOT.parent / "RaySkipSupport"
# The app's own decoder, scene, shot planner and scorer run on the test simulator (RaySkip/tests).
ENGINE_CHECK = ROOT.parent / "RaySkip" / "tests" / "check_daily_engine.py"
ARCHIVE = ROOT / "challenges"
UPSTREAM = "https://raw.githubusercontent.com/jack28257/RaySkipDaily/main/challenges/"


def toronto_today():
    return dt.datetime.now(TORONTO).date()


def release_at(day):
    return int(dt.datetime.combine(day, dt.time(hour=8), TORONTO).timestamp()) * 1000


def stock_dates(today):
    return [today + dt.timedelta(days=offset) for offset in range(1, STOCK_DAYS + 1)]


def d1(sql):
    command = ["./node_modules/.bin/wrangler", "d1", "execute", "rayskip-feedback", "--remote",
               "--json", "--command", sql]
    run = subprocess.run(command, cwd=SUPPORT, capture_output=True, text=True, timeout=45)
    if run.returncode:
        raise RuntimeError("Could not read or update the RaySkip production inventory.")
    results = json.loads(run.stdout)
    if len(results) != 1 or not results[0]["success"]:
        raise RuntimeError("The inventory database did not confirm the operation.")
    return results[0]["results"]


def sql_text(raw):
    return "'" + raw.decode("utf-8").replace("'", "''") + "'"


def stored_between(first, last):
    rows = d1(f"SELECT date, release_at, payload FROM daily_challenges WHERE date BETWEEN '{first}' AND '{last}' ORDER BY date;")
    return {dt.date.fromisoformat(row["date"]): row for row in rows}


def validate_payload(raw, day):
    if not 0 < len(raw) <= MAX_PAYLOAD_BYTES:
        raise ValueError("Daily JSON exceeds the client's size limit.")
    payload = json.loads(raw)
    challenge = payload["challenge"]
    if (challenge["date"], challenge["id"], challenge["level"]["id"]) != (
        day.isoformat(), f"daily-{day}", int(day.strftime("%Y%m%d"))
    ):
        raise ValueError("The payload date and IDs must match the inventory date.")
    daily_quality.validate_challenge(payload)
    return payload


def check_candidate(raw, day, neighbors):
    payload = validate_payload(raw, day)
    level = payload["challenge"]["level"]
    if level.get("demo", {}).get("targetColors") and any(target["radius"] != .028 for target in level["targets"]):
        raise ValueError("All targets in a colored puzzle must have radius 0.028.")
    profile = daily_quality.clarity_profile(payload, daily_quality.BOARD_SIZES)
    if profile is None or (payload["challenge"]["difficulty"] == "Advanced" and profile["minIntendedChanges"] < 4):
        raise ValueError("The puzzle did not pass the aiming and shortcut checks for its difficulty.")
    if payload["validation"].get("quality") != profile:
        raise ValueError("The quality metadata differs from the latest validation.")
    family = daily_quality.family_for(payload)
    signature = daily_quality.route_signature(payload)
    if not family:
        raise ValueError("A route family is required.")
    for other_day, other in neighbors.items():
        if other_day == day or abs((other_day - day).days) > daily_quality.LOOKBACK_DAYS:
            continue
        if (family == daily_quality.family_for(other) or signature == daily_quality.route_signature(other)
                or daily_quality.is_mirrored_copy(payload, other)):
            raise ValueError(f"The route repeats a puzzle planned or played on {other_day}.")


def engine_check(paths):
    """Run candidates (files named YYYY-MM-DD.json) through the shipping game engine. Prints outcomes only."""
    if not ENGINE_CHECK.exists():
        raise RuntimeError(f"The game engine check is missing: {ENGINE_CHECK}")
    run = subprocess.run(["python3", str(ENGINE_CHECK), *map(str, paths)], capture_output=True, text=True, timeout=900)
    lines = [line for line in run.stdout.splitlines() if line.startswith(("PASS", "FAIL", "    "))]
    print("\n".join(lines))
    if run.returncode:
        raise ValueError("The game engine rejected the puzzle (see the outcomes above)." if lines
                         else "The game engine check could not run: " + (run.stderr.strip().splitlines() or ["no output"])[-1])


def nearby_puzzles(day):
    span = dt.timedelta(days=daily_quality.LOOKBACK_DAYS)
    rows = stored_between(day - span, day + span)
    outcomes = {date: json.loads(row["payload"]) for date, row in rows.items()}
    for offset in range(-span.days, span.days + 1):
        date = day + dt.timedelta(days=offset)
        path = ARCHIVE / f"{date}.json"
        if date not in outcomes and path.exists():
            outcomes[date] = json.loads(path.read_bytes())
    return rows, outcomes


def public_archive(day):
    try:
        with urlopen(UPSTREAM + f"{day}.json", timeout=12) as response:
            return response.read(MAX_PAYLOAD_BYTES + 1)
    except HTTPError as error:
        if error.code != 404:
            raise
        return None


def put(path, *, replace=False, allow_today=False):
    day = dt.date.fromisoformat(path.stem)
    today = toronto_today()
    if day not in stock_dates(today):
        if not (allow_today and day == today and not replace):
            raise ValueError("Use a date in the next seven days. A missing current day can be repaired with --allow-today.")
        if (ARCHIVE / f"{day}.json").exists() or public_archive(day) is not None:
            raise ValueError("The current day already has a published GitHub archive.")
    raw = path.read_bytes()
    rows, neighbors = nearby_puzzles(day)
    current = rows.get(day)
    if current and current["payload"].encode("utf-8") == raw:
        if current["release_at"] != release_at(day):
            raise ValueError(f"The stored release time for {day} does not match 08:00 Toronto.")
        print(f"{day} is already stored with the same content.")
        return
    if current and not replace:
        raise ValueError(f"{day} is already prepared. An explicit --replace is required before release.")
    check_candidate(raw, day, neighbors)
    engine_check([path])
    data = sql_text(raw)
    conflict = "DO NOTHING"
    if current:
        previous_data = sql_text(current["payload"].encode("utf-8"))
        conflict = ("DO UPDATE SET payload=excluded.payload "
                    f"WHERE daily_challenges.payload={previous_data} "
                    "AND daily_challenges.release_at=excluded.release_at")
    d1(f"INSERT INTO daily_challenges (date, payload, release_at) VALUES ('{day}', {data}, {release_at(day)}) "
       f"ON CONFLICT(date) {conflict};")
    stored = stored_between(day, day).get(day)
    if not stored or stored["release_at"] != release_at(day) or stored["payload"].encode("utf-8") != raw:
        raise RuntimeError("Could not verify the selected content after writing the inventory.")
    print(f"{day} is stored and verified.")


def is_prepared(row, day):
    if row is None or row["release_at"] != release_at(day):
        return False
    try:
        validate_payload(row["payload"].encode("utf-8"), day)
    except (AssertionError, ValueError, KeyError, TypeError):
        return False
    return True


def status():
    today = toronto_today()
    dates = stock_dates(today)
    rows = stored_between(today, dates[-1])
    ready = [day for day in dates if is_prepared(rows.get(day), day)]
    missing = [day for day in dates if day not in ready]
    consecutive = (missing[0] - today).days - 1 if missing else STOCK_DAYS
    open_today = (is_prepared(rows[today], today) if today in rows else (ARCHIVE / f"{today}.json").exists())
    print(json.dumps(dict(today=str(today), todayReady=open_today, readyCount=len(ready), horizon=STOCK_DAYS,
                          consecutive=consecutive, missing=[str(day) for day in missing],
                          earliestGap=str(missing[0]) if missing else None)))


def verify_stock():
    """Re-check every prepared, unopened puzzle with today's rules and the game engine. Prints dates only."""
    today = toronto_today()
    dates = stock_dates(today)
    rows = stored_between(dates[0], dates[-1])
    with TemporaryDirectory(prefix="rayskip-stock-") as folder:
        paths, failed = [], []
        for day in dates:
            row = rows.get(day)
            if row is None:
                print(f"MISSING {day}")
                continue
            raw = row["payload"].encode("utf-8")
            try:
                payload = validate_payload(raw, day)
                if daily_quality.clarity_profile(payload, daily_quality.BOARD_SIZES) is None:
                    raise ValueError("aiming or shortcut check")
            except (AssertionError, ValueError, KeyError, TypeError) as error:
                failed.append(day)
                print(f"FAIL {day} (Python rules: {type(error).__name__})")
                continue
            path = Path(folder) / f"{day}.json"
            path.write_bytes(raw)
            paths.append(path)
        if paths:
            try:
                engine_check(paths)
            except ValueError:
                failed.append("engine")
    if failed:
        raise SystemExit("Some prepared puzzles fail today's rules. Redesign them and store them with put --replace.")
    print("All prepared puzzles pass today's rules and the game engine.")


def history(day):
    _, neighbors = nearby_puzzles(day)
    print(json.dumps({str(date): {"family": daily_quality.family_for(payload),
                                  "signature": daily_quality.route_signature(payload)}
                      for date, payload in sorted(neighbors.items()) if date != day}))


def archive(day):
    rows = stored_between(day, day)
    row = rows.get(day)
    if not row:
        print(f"{day} is not in private inventory.")
        return
    if row["release_at"] != release_at(day) or int(dt.datetime.now(TORONTO).timestamp() * 1000) < row["release_at"]:
        raise ValueError(f"{day} has not opened yet.")
    raw = row["payload"].encode("utf-8")
    validate_payload(raw, day)
    path = ARCHIVE / f"{day}.json"
    with NamedTemporaryFile(dir=ARCHIVE, suffix=".tmp") as temporary:
        temporary.write(raw)
        temporary.flush()
        try:
            os.link(temporary.name, path)
        except FileExistsError:
            if path.read_bytes() != raw:
                raise ValueError("The existing public archive differs from the released inventory and was preserved.")
            print(f"{day} is already archived.")
        else:
            print(f"Archived {day} locally.")


def main():
    if not __debug__:
        raise SystemExit("Daily inventory validation requires a non-optimized Python interpreter.")
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    modes.add_parser("status")
    modes.add_parser("verify-stock")
    modes.add_parser("history").add_argument("date", type=dt.date.fromisoformat)
    modes.add_parser("archive").add_argument("date", type=dt.date.fromisoformat)
    store = modes.add_parser("put")
    store.add_argument("path", type=Path)
    store.add_argument("--replace", action="store_true")
    store.add_argument("--allow-today", action="store_true")
    args = parser.parse_args()
    if args.mode == "status":
        status()
    elif args.mode == "verify-stock":
        verify_stock()
    elif args.mode == "history":
        history(args.date)
    elif args.mode == "archive":
        archive(args.date)
    else:
        put(args.path, replace=args.replace, allow_today=args.allow_today)


if __name__ == "__main__":
    main()
