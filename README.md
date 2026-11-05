# SolarInfo

Grab daily solar production from the Enphase Enlighten API and daily weather from OpenWeatherMap, and log them side by side in a CSV for analysis (does cloudiness actually explain the production dip? — yes, but graph it yourself).

## How it works

Each script fetches its data and **upserts it into its own staging file, then rebuilds the combined CSV from staging + the existing archive**:

1. `OpenWeather.py` (`WeatherDaily.bat`) — current conditions for today's date → `weather_staging.csv`.
2. `SolarDataDailyGrab.py` (`SolarDaily.bat`) — **self-healing**: checks the last 14 days, and if any lack production data (e.g. a skipped/failed scheduled run), fetches them all in one `energy_lifetime` range call and fills the gaps, each row stamped with its own production date.
3. Both scripts then call `csvstore.merge_final()`, which regenerates `Weatherburn_Solar_Production.csv` (atomic temp-file rename, sorted by date, never half-written).

Run them in any order, twice, or skip a day — the worst case is an empty column, never a corrupted row.

## Pulling a date range

`SolarDataDailyGrab.py` (which replaces the old `SolarBackData.py`) takes optional date args — one range request covers any length of range:

```bash
python SolarDataDailyGrab.py                              # default: self-heal the lookback window
python SolarDataDailyGrab.py --start 2026-01-01 --end 2026-06-30
python SolarDataDailyGrab.py --start 2020-02-01           # that date through yesterday
python SolarDataDailyGrab.py --end 2024-12-31             # system install date through 2024
python SolarDataDailyGrab.py --start ... --end ... --refresh   # also re-pull dates already on record
```

Range mode fills only missing days; `--refresh` overwrites the range's dates with fresh values (rows outside the range are never touched). Dates are ISO; `--end` defaults to yesterday. Weather has no range option — the free endpoint only reports current conditions, so `OpenWeather.py` always records the day it runs.

`csvstore.py` holds the staging/merge logic; `enphase.py` is the v4 API client; `netutil.py` wraps every HTTP GET with retry/backoff. All file paths resolve next to the scripts, so the scheduled task's working directory doesn't matter.

## Reliability

Transient API failures don't lose a day's data, via two layers:

- **In-run retry/backoff** (`netutil.get_json`): connection errors, timeouts, HTTP 429/500/502/503/504, and malformed JSON are retried up to 3 times with exponential backoff (5s, 20s, 80s); a `Retry-After` header overrides the wait. Other 4xx (e.g. a bad/expired token) exit immediately — retrying them only wastes the run. On hard failure the script exits non-zero and the archive is left byte-identical.
- **Cross-day self-healing** (solar): production is backfillable from one range request, so the solar script re-checks its lookback window (14 days by default; set `lookback_days = N` in `SolarLoginInfo.txt`) and fills any day that's missing. A laptop that slept for a few days catches all of them up on the next successful run, at no extra request cost.

Weather can't self-heal a skipped day on the free tier — the current-conditions endpoint only reports *now*, so a missed `OpenWeather.py` run leaves that date's weather columns blank (past weather needs the paid One Call API).

## Requirements

- Python 3 with `requests` (`pip install requests`)
- An Enphase Enlighten account
- An OpenWeatherMap API key

Enphase migrated from API v2 to the **v4 Monitoring API** (v2 was decommissioned mid-2024). These scripts use v4: `GET /api/v4/systems/{id}/energy_lifetime`, which returns daily production for a date range in one call.

## Configuration

Credentials live in two files **not** in this repo (now also covered by `.gitignore` — keep it that way; an API key previously committed in a comment was scrubbed from history on 2026-11-05, but treat the old v2 key as burned and rotate/delete it in Enlighten).

### `SolarLoginInfo.txt`

```ini
system_id = 1234567
token = <your Enphase Personal Access Token>
lookback_days = 14    ; optional; self-heal window for unattended runs
```

Generate the token at https://entrez.enphaseenergy.com (sign in with your Enlighten account → *Generate Token*). Homeowner PATs are used directly as the bearer token; if you instead use a developer-app OAuth token, add `key = <application api key>`. The old v2 `key`/`user_id` fields are gone; v4 doesn't use `user_id`.

### `OpenWeatherAPI.txt`

Either line-based (first line = appid, optional second line = zip) or key=value:

```ini
appid = <your OpenWeatherMap key>
zip = 43065
```

The zip is Westerville, OH; change it to yours.

## Scheduling (Windows)

`SolarDaily.bat` / `WeatherDaily.bat` now `cd` to their own folder and invoke the `py` launcher — no machine-specific paths. Register them as scheduled tasks (daily, e.g. 2 PM); order is no longer significant.

## Output

`Weatherburn_Solar_Production.csv`:

| Column | Meaning |
| --- | --- |
| Date | The date the data describes (weather = snapshot day; kWh = production day) |
| Temperature | °F from `main.temp_max` (station reading near run time, not a true daily max) |
| Humidity | Percent |
| Sky | Condition description |
| Cloudiness | Percent cloud cover |
| Wind | m/s (temp is converted to °F, wind is not converted) |
| Sunrise / Sunset | Local `HH:MM` (older rows may still hold raw epoch seconds) |
| Daylight_hr | Sunset − sunrise, hours |
| kWh | Enphase production, Wh ÷ 1000 |

Staging files (`weather_staging.csv`, `solar_staging.csv`) are regenerable local state and gitignored; delete them and the next merge rebuilds from the archive.

## Known limitations

- Weather is a point-in-time snapshot (whatever the run-time call returns), not a daily min/max/avg. Enriching this needs OpenWeatherMap's paid One Call/Timemachine history API.
- Sunrise/sunset come from the *current-day* call, so a manually re-run day gets today's values.
- A hard-failed run exits non-zero and leaves data intact: solar self-heals next run (14-day window); a skipped weather day stays blank — see Reliability.
- No data-visualization code in this repo despite the name (the original goal was to plot production vs. cloudiness).

## License

No license file in the repo yet.
