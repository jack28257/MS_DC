# Mirror Shot daily challenges

This repository publishes the daily puzzle data used by Mirror Shot. Publication runs on GitHub Actions, independently of the developer's Mac, without paid services or AI API keys.

## Publication

`.github/workflows/daily.yml` runs three times a day, on relevant code changes, and manually from Actions → Publish daily challenges → Run workflow. It uses only this repository's `GITHUB_TOKEN` with `contents: write`.

`generate_daily.py` computes the active Toronto date (08:00 local reset), validates every puzzle, and publishes:

- `DailyChallenge.json`: the active Toronto puzzle, retained for older clients.
- `DailyChallenges.json`: three preceding dates, the active date, and 35 future dates. New clients select their own local date, so time zones and a delayed scheduler do not block play.

Every publication runs deterministic-generation tests and the geometry/Perfect-score solver at four board sizes before committing. Failed validation fails the workflow and preserves the last publication. GitHub's workflow status and failure notifications provide the publication health signal. Scheduled jobs can be delayed or disabled by GitHub; the app's deterministic offline generator remains available if this happens.

## Puzzle design and offline parity

The immutable `DailyChallengeTemplates.json` contains 128 solver-checked paths. The calendar day chooses a template and horizontal/vertical reflections. Date-derived angle offsets scramble the initial mirror positions. The Swift client uses the identical algorithm and a bundled copy of this catalog: today's online, cached, and offline puzzle have the same identity and geometry. Normal campaign progress remains separate.

Do not change or reorder this version-1 catalog. Doing so would change saved daily puzzles and disagree with installed clients. A future catalog requires a new generator version and an app update.

`make_templates.py` is the one-time catalog authoring tool. Its candidates are accepted only when the solver proves a Perfect-capable path and a non-solved initial state at every supported test size. Re-run it only when authoring a new catalog version.

## Local commands

```sh
python3 -m unittest -v test_daily
python3 generate_daily.py
python3 generate_daily.py --date 2026-10-17 --output /tmp/mirrorshot-daily
```

Python 3.9+ and its standard library are sufficient. All generated files are ordinary public puzzle data. No credentials, signing files, player data or private game sources belong in this repository.
