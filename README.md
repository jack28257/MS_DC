# RaySkip daily challenges

The Codex scheduled task **RaySkip 每日关卡生成发布** replenishes **seven future dates** at 07:00 America/Toronto from its dedicated chat and this local checkout. It authors original puzzles, validates them and uploads them to the website's private Cloudflare D1 inventory. The Mac and desktop app are needed for replenishment.

The iPhone reminds the player at 08:00 Toronto time and checks the active date when the game returns to the foreground.

At 08:00 Toronto time, the website starts serving the puzzle for that date. It freezes the puzzle at opening and serves earlier dates from either the inventory or the public GitHub archive.

The scheduled task authors each puzzle and checks it against recent routes before upload. The Python geometry solver verifies an unsolved starting layout and a Perfect-capable route at seven board sizes, including short landscape.

The App requests its active date from `https://rayskip.com/daily/challenges/YYYY-MM-DD.json`. An already downloaded and validated puzzle is cached on the device for that day. The website rejects requests for future dates until their opening time. Public `challenges/YYYY-MM-DD.json` files are immutable archives of opened puzzles.

## Run and recover

```sh
python3 -m unittest -v test_daily test_daily_inventory
python3 daily_inventory.py status
python3 daily_inventory.py history YYYY-MM-DD
python3 daily_inventory.py put /private/path/YYYY-MM-DD.json
```

Use the status command to find the earliest gap. The uploader rechecks the solver, aiming margin and recent routes on both sides of that date. It uses the existing authenticated Wrangler connection in the sibling `RaySkipSupport` checkout. A replacement requires `--replace` and must occur before release. A missing current day can be repaired with `put --allow-today` after checking its archive.

Use `python3 daily_inventory.py archive YYYY-MM-DD` after 08:00 on that date, then commit and push the verified dated archive file on its own. Future puzzle JSON belongs in the private inventory. The retired same-day publisher and GitHub Actions workflow are available in Git history.

On 2026-10-18, no natural GitHub scheduled run appeared and the dated file was missing after 08:00. The generator itself passed verification. Today's puzzle was generated locally, validated at all four board sizes and pushed to GitHub in `d67f9e0`; the public files and the paired iPhone's GitHub load were verified. The Codex task was then enabled at the user's request. Its first natural 07:00 execution succeeded on 2026-10-19 at 07:01 Toronto (`6c14fcb`).

Published date files are immutable. Tests cover recent-route exclusion on both sides of an inventory date, seven-size solutions, archive byte equality, and Toronto opening times across daylight-saving changes.


## Puzzle validation

`mechanic_daily.py` traces splitter, color-filter, and obstacle routes. New splitters specify two fixed `outputAnglesDegrees` in world coordinates. Both outlets use those headings regardless of the incoming ray. The solver checks the authored route in the current game and in the previous client, which uses the stored reflection angle. Every splitter must matter, every filter must cause a wrong-color failure if removed, and each wall must block a shortcut that wins when it is removed. Every board size must have a Perfect-capable route and an unsolved initial layout.

Some puzzles include an optional `level.dailyBoard` that adds movable mirrors, walls, or both. Movable mirrors start at the bottom of the board. `level.mirrors` contains their reference positions for the solver. Walls use normalized top-left coordinates. The validator checks the reference and movable layouts, tests legal stock placement and aiming clearance, and requires each wall to block a route that would otherwise win.

`daily_quality.py` measures aiming margin and computes route signatures. The inventory rejects a route family or flip-equivalent structure within seven dates on either side of a candidate. The aiming check offsets each mirror independently in both directions by 0.50° in portrait and 0.25° in landscape. On the reference board it screens for one-mirror clears using the authored settings and a 5° sweep. Standard and Advanced use the smallest clearing subset of authored angle changes on that board. Player testing measures enjoyment and time to solve.

The validator supports archived red-zone and splitter definitions. Native and Python tests share contract cases through `test_daily.app_contract_samples()`. Its mechanical fixtures are stored under `fixtures/`.
