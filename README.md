# SolarInfo

Grab daily solar production from the Enphase Enlighten API and daily weather from OpenWeatherMap, and log them side by side in a CSV for analysis (does cloudiness actually explain the production dip? — yes, but graph it yourself).

## How it works

Two scripts append to `Weatherburn_Solar_Production.csv`, and **must run in order** (they cooperate to build one CSV row):

1. `OpenWeather.py` (via `WeatherDaily.bat`) appends the row up to and including the weather fields, **without a trailing newline**.
2. `SolarDataDailyGrab.py` (via `SolarDaily.bat`) appends the day's production in kWh plus the newline that closes the row.

`SolarBackData.py` is a one-off backfiller that re-fetches a hardcoded date range and **overwrites** the CSV with `date,kWh` rows only.

Production is fetched with `energy_lifetime?start_date=D&end_date=D`, so the scheduled scripts are intended to run once daily (originally ~2 PM) after the day closes. Note: as written, the weather half records *today* while the solar half records *yesterday* — the two halves describe different days.

## Requirements

- Python 3 with `requests` (`pip install requests`)
- An Enphase Enlighten account + public API key
- An OpenWeatherMap API key

> **The Enphase v2 public API (`api.enphaseenergy.com/api/v2`) reached end of life on June 30, 2024.** The scripts here target that dead endpoint; they will not return data until migrated to [Enphase API v4](https://developer-v4.enphase.com/) (bearer-token auth, `/v4/systems/{id}/production`). The OpenWeather `/data/2.5/weather` endpoint still works.

## Configuration

Credentials live in two files that are **not** in this repo (keep them out of it):

| File | Format |
| --- | --- |
| `SolarLoginInfo.txt` | Free-form lines; the scripts read line **6** = API key, line **7** = user ID, line **8** = system ID (1-based). Anything can occupy lines 1–5, but line count/order is load-bearing. |
| `OpenWeatherAPI.txt` | Line 1 = your OpenWeatherMap APPID |

The location zip (default `43065`) and the CSV name are hardcoded in `OpenWeather.py` / `SolarDataDailyGrab.py`.

## Scheduling (Windows)

Edit the absolute paths inside `SolarDaily.bat` and `WeatherDaily.bat` (they were written for `E:\python\Solar Daily`), then register them as scheduled tasks — `WeatherDaily` first, `SolarDaily` a few minutes later. The scripts open their data files by relative path, so the task's *Start in* directory matters.

## Output

`Weatherburn_Solar_Production.csv`:

| Column | Meaning |
| --- | --- |
| Date | Local run date of the weather half |
| Temperature | °F from `main.temp_max` (station max near run time, not a true daily max) |
| Humidity | Percent |
| Sky | Condition description |
| Cloudiness | Percent cloud cover |
| Wind | m/s (note: temp is converted to °F, wind is not converted) |
| Sunrise / Sunset | Unix epoch seconds, local-tz shift applied server-side |
| Daylight_hr | Sunset − sunrise, hours |
| kWh | Enphase production (Wh ÷ 1000) |

## Known limitations

- Built against the retired Enphase v2 API; needs migration to v4.
- No error handling on the Enphase request: a failed/limited response crashes the script mid-row, leaving a dangling comma that corrupts every subsequent append until the CSV is repaired by hand.
- Row integrity depends on strict task ordering and on both runs succeeding; a skipped or overlapping task scrambles rows.
- Weather is a 2 PM snapshot, not a daily aggregate (no min/max/avg or daily cloud cover).
- API request URLs are built by string interpolation and neither request sets a timeout.
- No data-visualization code in this repo despite the name (the original goal was to plot production vs. cloudiness).

## License

No license file in the repo yet.
