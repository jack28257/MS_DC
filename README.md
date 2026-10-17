# Mirror Shot daily generator

GitHub Actions generates and publishes **one new puzzle every day at 07:00 America/Toronto**. The iPhone reminds the player at 08:00, then fetches the active puzzle from GitHub when the game returns to the foreground.

`generate_daily.py` builds fresh mirror/target positions from a date seed. It rejects candidates until a geometry solver proves that the puzzle can achieve Perfect at four board sizes and does not start solved. It uses Python's standard library; there is no AI API, paid service or template catalog.

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

The workflow is [Publish daily challenges](https://github.com/jack28257/MS_DC/actions/workflows/daily.yml). Use Run workflow to retry after a failure. A failed solver check stops publication and retains the previous files. The job uses this repository's `GITHUB_TOKEN` with `contents: write`; no personal token or Mac needs to remain online.

GitHub schedules are best effort and may be delayed. The one-hour gap before the phone reset allows for normal job startup. iOS presents the local notification at 08:00 if notifications are allowed; fetching happens on foreground entry, not by assuming iOS will launch the app at an exact background time.

Published date files are immutable, including when a generator is improved. Same-day retries reuse the validated published file. Tests check 365 distinct daily layouts, solutions at four sizes, re-run stability and Toronto dates across daylight-saving changes.
