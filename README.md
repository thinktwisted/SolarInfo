# SolarInfo

Grab daily solar production from the Enphase Enlighten API and daily weather from OpenWeatherMap, and log them side by side in a CSV for analysis (does cloudiness actually explain the production dip? — yes, but graph it yourself).

## How it works

Each script fetches its data and **upserts it into its own staging file, then rebuilds the combined CSV from staging + the existing archive**:

1. `OpenWeather.py` (`WeatherDaily.bat`) — current conditions for today's date → `weather_staging.csv`.
2. `SolarDataDailyGrab.py` (`SolarDaily.bat`) — yesterday's production, stamped with *its own* date, from Enphase → `solar_staging.csv`.
3. Both scripts then call `csvstore.merge_final()`, which regenerates `Weatherburn_Solar_Production.csv` (atomic temp-file rename, sorted by date, never half-written).

Run them in any order, twice, or skip a day — the worst case is an empty column, never a corrupted row. `SolarBackData.py` backfills a date range through the same path (one API request covers the whole range).

`csvstore.py` holds the staging/merge logic; `enphase.py` is the v4 API client. All file paths resolve next to the scripts, so the scheduled task's working directory doesn't matter.

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
- No error-retry: a failed API call exits non-zero and leaves prior data intact — rerun the task when it clears.
- No data-visualization code in this repo despite the name (the original goal was to plot production vs. cloudiness).

## License

No license file in the repo yet.
