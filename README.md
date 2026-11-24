# RaySkip daily generator

The Codex scheduled task **RaySkip 每日关卡生成发布** generates, validates and publishes **one new puzzle every day at 07:00 America/Toronto** from this repository. It returns to the existing project chat and uses the local checkout; the Mac must be on and online and the desktop app running.

The iPhone reminds the player at 08:00 Toronto time and checks the active date when the game returns to the foreground.

The Codex task validates and reuses the first published puzzle for each date. The GitHub Actions workflow is disabled.

`generate_daily.py` samples a set of twelve route families using a date seed and recent published history. Each family has its own sequence of turns, goals and mechanisms. The generator samples positions, sizes and starting angles within that structure. A geometry solver verifies an unsolved starting layout and a Perfect-capable route at seven board sizes, including short landscape.

Each publication adds one immutable `challenges/YYYY-MM-DD.json` file. The app resets the challenge at 08:00 Toronto time and requests that date’s file from `https://rayskip.com/daily/challenges/YYYY-MM-DD.json`. This endpoint serves the GitHub file. Keeping past files lets the previous challenge remain accessible between 07:00 publication and the 08:00 reset. No future puzzles are generated in advance, and the app has no offline daily generator or persistent daily-content cache.

## Run and recover

```sh
python3 -m unittest -v test_daily
python3 generate_daily.py
python3 generate_daily.py --date 2026-10-17 --output /tmp/rayskip-daily
```

To recover a missed publication, use the existing Codex task or validate the challenge locally and commit only the current dated file. A failed solver check stops publication and retains the previous files. The Codex task uses the existing local GitHub sign-in. The disabled [GitHub Actions workflow](https://github.com/jack28257/RaySkipDaily/actions/workflows/daily.yml) remains in the repository.

The one-hour gap before the phone reset allows time for publishing. iOS presents the local notification at 08:00 if notifications are allowed. The app fetches when it opens or returns to the foreground.

On 2026-10-18, no natural GitHub scheduled run appeared and the dated file was missing after 08:00. The generator itself passed verification. Today's puzzle was generated locally, validated at all four board sizes and pushed to GitHub in `d67f9e0`; the public files and the paired iPhone's GitHub load were verified. The Codex task was then enabled at the user's request. Its first natural 07:00 execution succeeded on 2026-10-19 at 07:01 Toronto (`6c14fcb`).

Published date files are immutable across generator updates. Same-day retries reuse the validated published file. Retrospective tests run a 140-day sequence in memory and verify both difficulty bands, all twelve families, recent-route exclusion, seven-size solutions, same-day stability and Toronto boundaries across daylight-saving changes.


## Generated mechanics

`mechanic_daily.py` samples fresh positions and initial angles for splitter routes, wall detours, color-filter routes and combinations, with plain classic puzzles retained in the rotation. New splitters specify two fixed `outputAnglesDegrees` in world coordinates. Both outlets use those headings regardless of the incoming ray. The solver checks the authored route in the current game and in the previous client, which uses the stored reflection angle. Every splitter must matter, every filter must cause a wrong-color failure if removed, and each wall must block a shortcut that wins when it is removed. Every board size must have a Perfect-capable route and an unsolved initial layout. No tutorial is added to Daily mode.

Some puzzles include an optional `level.dailyBoard` that adds movable mirrors, walls, or both. Movable mirrors start at the bottom of the board. `level.mirrors` contains their reference positions for the solver. Walls use normalized top-left coordinates. The validator checks the reference and movable layouts, tests legal stock placement and aiming clearance, and requires each wall to block a route that would otherwise win. The generator leaves at least two ordinary daily puzzles between these boards.

`daily_quality.py` rejects a route family or a flip-equivalent route structure that appeared in the previous seven dates. It tests the authored solution with each mirror independently offset in both directions by 0.50° in portrait and 0.25° in landscape. On the reference board it screens for one-mirror clears using the authored settings and a 5° sweep. Standard and Advanced use the smallest clearing subset of authored angle changes on that board. These checks characterize the designed route and do not enumerate every possible solution. Player testing measures enjoyment and time to solve.

Already published dates remain immutable. The validator can still read archived red-zone and splitter definitions. New mechanics first appear on an unpublished execution date. Rerunning publication for an existing valid date preserves its bytes, timestamp and Git history. Tests generate samples in memory or temporary test directories.
