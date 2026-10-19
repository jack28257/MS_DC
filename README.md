# Mirror Shot daily generator

The Codex scheduled task **MirrorShot 每日关卡生成发布** generates, validates and publishes **one new puzzle every day at 07:00 America/Toronto** from this repository. It returns to the existing project chat and uses the local checkout; the Mac must be on and online and the desktop app running. Automation ID: `mirrorshot`.

The iPhone reminds the player at 08:00, then fetches the active puzzle from GitHub when the game returns to the foreground. Before 08:00 Toronto it requests yesterday's dated file; from 08:00 it requests today's. Build 26 is required for the new schema 2 mechanic puzzles; subsequent content updates do not require reinstalling.

The existing GitHub Actions schedule remains enabled as a secondary attempt. Both publishers reuse an already published, valid dated puzzle. The Codex task skips generation and commits when both public files are already correct; it must not overwrite existing daily content, unrelated working changes or past puzzles.

`generate_daily.py` builds fresh mirror/target positions from a date seed. It rejects candidates until a geometry solver proves that the puzzle can achieve Perfect at seven board sizes, including short landscape and does not start solved. It uses Python's standard library; there is no AI API, paid service or template catalog.

Published files:

- `challenges/YYYY-MM-DD.json`: one immutable puzzle for that date.
- `DailyChallenge.json`: the latest publication, retained for older clients.

The app resets the challenge at 08:00 Toronto time and requests that date's file directly. Keeping past files lets the previous challenge remain accessible between 07:00 publication and the 08:00 reset. No future puzzles are generated in advance, and the app has no offline daily generator or persistent daily-content cache.

## Run and recover

```sh
python3 -m unittest -v test_daily
python3 generate_daily.py
python3 generate_daily.py --date 2026-10-17 --output /tmp/mirrorshot-daily
```

The workflow is [Publish daily challenges](https://github.com/jack28257/MS_DC/actions/workflows/daily.yml). Use Run workflow to retry after a failure, or use the generator locally and commit only the current dated file and the latest entry point. A failed solver check stops publication and retains the previous files. GitHub-hosted runs use this repository's `GITHUB_TOKEN` with `contents: write` and run independently of the Mac. The Codex task uses the existing local GitHub sign-in and requires the Mac and desktop app to be available.

GitHub schedules are best effort and may be delayed. The one-hour gap before the phone reset allows for normal job startup. iOS presents the local notification at 08:00 if notifications are allowed; fetching happens on foreground entry, not by assuming iOS will launch the app at an exact background time.

On 2026-10-18, no natural GitHub scheduled run appeared and the dated file was missing after 08:00. The generator itself passed verification. Today's puzzle was generated locally, validated at all four board sizes and pushed to GitHub in `d67f9e0`; the public files and the paired iPhone's GitHub load were verified. The Codex task was then enabled at the user's request. Its first natural 07:00 execution succeeded on 2026-10-19 at 07:01 Toronto (`6c14fcb`).

Published date files are immutable, including when a generator is improved. Same-day retries reuse the validated published file. Tests check 365 distinct daily layouts, solutions at seven sizes, re-run stability and Toronto dates across daylight-saving changes.


## Generated mechanics (schema 2)

`mechanic_daily.py` samples fresh positions and initial angles for splitters, red-zone detours, color-filter routes and combinations, with classic puzzles retained in the rotation. It uses the same optical rules as the native game, whose regression suite independently verifies generated fixtures. Every used splitter must matter, every filter must cause a wrong-color failure if removed, and each red zone must block a shortcut that wins when that zone is removed. All sizes must have a perfect-capable route and an unsolved initial layout. No tutorial is added to Daily mode.

Already published dates, including the 2026-10-19 classic puzzle, remain immutable. New mechanics first appear on an unpublished execution date. Repeated publication with an already correct entry leaves bytes, timestamps and Git history unchanged. Missing or incorrect entry points are repaired using the dated file. Test samples are generated only in memory or temporary test directories; they are not future publications.
