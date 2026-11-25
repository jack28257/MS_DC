# RaySkip daily challenges

The Codex scheduled task **RaySkip 每日关卡生成发布** replenishes **seven future dates** at 07:00 America/Toronto from its dedicated chat and this local checkout. It authors original puzzles, validates them and uploads them to the website's private Cloudflare D1 inventory. The Mac and desktop app are needed for replenishment.

The iPhone reminds the player at 08:00 Toronto time and checks the active date when the game returns to the foreground.

At 08:00 Toronto time, the website starts serving the puzzle for that date. It freezes the puzzle at opening and serves earlier dates from either the inventory or the public GitHub archive. The GitHub Actions workflow is disabled.

`generate_daily.py` samples a set of twelve route families using a date seed and recent published history. Each family has its own sequence of turns, goals and mechanisms. The generator samples positions, sizes and starting angles within that structure. A geometry solver verifies an unsolved starting layout and a Perfect-capable route at seven board sizes, including short landscape.

The App requests its active date from `https://rayskip.com/daily/challenges/YYYY-MM-DD.json`. An already downloaded and validated puzzle is cached on the device for that day. The website rejects requests for future dates until their opening time. Public `challenges/YYYY-MM-DD.json` files are immutable archives of opened puzzles.

## Run and recover

```sh
python3 -m unittest -v test_daily test_daily_inventory
python3 daily_inventory.py status
python3 daily_inventory.py history YYYY-MM-DD
python3 daily_inventory.py put /private/path/YYYY-MM-DD.json
```

Use the status command to find the earliest gap. The uploader rechecks the solver, aiming margin and recent routes on both sides of that date. It uses the existing authenticated Wrangler connection in the sibling `RaySkipSupport` checkout. A replacement requires `--replace` and must occur before release. A missing current day can be repaired with `put --allow-today` after checking its archive.

Use `python3 daily_inventory.py archive YYYY-MM-DD` after 08:00 on that date, then commit and push the verified dated archive file on its own. Future puzzle JSON belongs in the private inventory. The [GitHub Actions workflow](https://github.com/jack28257/RaySkipDaily/actions/workflows/daily.yml) remains disabled.

On 2026-10-18, no natural GitHub scheduled run appeared and the dated file was missing after 08:00. The generator itself passed verification. Today's puzzle was generated locally, validated at all four board sizes and pushed to GitHub in `d67f9e0`; the public files and the paired iPhone's GitHub load were verified. The Codex task was then enabled at the user's request. Its first natural 07:00 execution succeeded on 2026-10-19 at 07:01 Toronto (`6c14fcb`).

Published date files are immutable across generator updates. Same-day retries reuse the validated published file. Retrospective tests run a 140-day sequence in memory and verify both difficulty bands, all twelve families, recent-route exclusion, seven-size solutions, same-day stability and Toronto boundaries across daylight-saving changes.


## Generated mechanics

`mechanic_daily.py` samples fresh positions and initial angles for splitter routes, wall detours, color-filter routes and combinations, with plain classic puzzles retained in the rotation. New splitters specify two fixed `outputAnglesDegrees` in world coordinates. Both outlets use those headings regardless of the incoming ray. The solver checks the authored route in the current game and in the previous client, which uses the stored reflection angle. Every splitter must matter, every filter must cause a wrong-color failure if removed, and each wall must block a shortcut that wins when it is removed. Every board size must have a Perfect-capable route and an unsolved initial layout. No tutorial is added to Daily mode.

Some puzzles include an optional `level.dailyBoard` that adds movable mirrors, walls, or both. Movable mirrors start at the bottom of the board. `level.mirrors` contains their reference positions for the solver. Walls use normalized top-left coordinates. The validator checks the reference and movable layouts, tests legal stock placement and aiming clearance, and requires each wall to block a route that would otherwise win. The generator leaves at least two ordinary daily puzzles between these boards.

`daily_quality.py` rejects a route family or a flip-equivalent route structure that appeared in the previous seven dates. It tests the authored solution with each mirror independently offset in both directions by 0.50° in portrait and 0.25° in landscape. On the reference board it screens for one-mirror clears using the authored settings and a 5° sweep. Standard and Advanced use the smallest clearing subset of authored angle changes on that board. These checks characterize the designed route and do not enumerate every possible solution. Player testing measures enjoyment and time to solve.

Already published dates remain immutable. The validator can still read archived red-zone and splitter definitions. New mechanics first appear on an unpublished execution date. Rerunning publication for an existing valid date preserves its bytes, timestamp and Git history. Tests generate samples in memory or temporary test directories.
