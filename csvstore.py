"""Shared CSV storage for the SolarInfo scripts.

Each script writes its half of a day's row into a per-source staging file
(atomic upsert keyed by ISO date), then regenerates the combined
Weatherburn_Solar_Production.csv from staging + existing archive rows.

This replaces the old split-append scheme (OpenWeather.py leaving a dangling
comma for SolarDataDailyGrab.py to terminate): rows never span two writes, so
an API failure, an out-of-order run, or two runs on the same day can no longer
corrupt the archive.

All paths are relative to this file's directory, so the working directory the
scheduled task uses does not matter.
"""

import csv
import os
import sys
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent

FINAL_CSV = DATA_DIR / "Weatherburn_Solar_Production.csv"
SOLAR_STAGING = DATA_DIR / "solar_staging.csv"
WEATHER_STAGING = DATA_DIR / "weather_staging.csv"

FINAL_FIELDS = [
    "Date", "Temperature", "Humidity", "Sky", "Cloudiness",
    "Wind", "Sunrise", "Sunset", "Daylight_hr", "kWh",
]

SOLAR_FIELDS = ["date", "kwh"]

WEATHER_FIELDS = [
    "date", "temperature", "humidity", "sky", "cloudiness",
    "wind", "sunrise", "sunset", "daylight_hr",
]

# weather staging column -> final CSV column
WEATHER_TO_FINAL = {
    "temperature": "Temperature",
    "humidity": "Humidity",
    "sky": "Sky",
    "cloudiness": "Cloudiness",
    "wind": "Wind",
    "sunrise": "Sunrise",
    "sunset": "Sunset",
    "daylight_hr": "Daylight_hr",
}


def yesterday():
    return (date.today() - timedelta(days=1)).isoformat()


def load_staging(path):
    """Read a staging CSV into {date: row dict}; missing file means empty."""
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {row["date"]: row for row in csv.DictReader(f) if row.get("date")}


def _atomic_write(path, fieldnames, rows):
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def upsert_staging(path, fieldnames, row):
    """Insert/replace one keyed row, store sorted by date, write atomically."""
    rows = load_staging(path)
    rows[row["date"]] = row
    _atomic_write(path, fieldnames, [rows[k] for k in sorted(rows)])


def upsert_solar(day_iso, kwh):
    upsert_staging(SOLAR_STAGING, SOLAR_FIELDS, {"date": day_iso, "kwh": f"{kwh:.3f}"})


def upsert_weather(day_iso, weather):
    row = {"date": day_iso}
    row.update(weather)
    upsert_staging(WEATHER_STAGING, WEATHER_FIELDS, row)


def merge_final():
    """Rebuild the archive CSV from staging overlays on the existing rows.

    Staging wins for the (date, source) pairs it covers; every other existing
    row is preserved untouched. Output is written atomically.
    """
    weather = load_staging(WEATHER_STAGING)
    solar = load_staging(SOLAR_STAGING)

    rows = {}
    if FINAL_CSV.exists():
        with open(FINAL_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("Date"):
                    rows[row["Date"]] = row

    for day, wrow in weather.items():
        row = rows.setdefault(day, {field: "" for field in FINAL_FIELDS})
        row["Date"] = day
        for src, dst in WEATHER_TO_FINAL.items():
            row[dst] = wrow.get(src, "")
    for day, srow in solar.items():
        row = rows.setdefault(day, {field: "" for field in FINAL_FIELDS})
        row["Date"] = day
        row["kWh"] = srow.get("kwh", "")

    _atomic_write(FINAL_CSV, FINAL_FIELDS, [rows[d] for d in sorted(rows)])


def load_config(filename, required=()):
    """Parse a config file of `key = value` lines (with optional #comments).

    Bare non-empty lines (the legacy positional format) are returned under
    conf["_lines"]. Values are lower-cased keys -> raw strings.
    """
    path = DATA_DIR / filename
    if not path.exists():
        sys.exit(
            f"ERROR: {path.name} not found next to the scripts. "
            f"See README.md for its format."
        )
    conf = {"_lines": []}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            conf[key.strip().lower()] = value.strip()
        else:
            conf["_lines"].append(line)
    missing = [key for key in required if not conf.get(key)]
    if missing:
        sys.exit(
            f"ERROR: {path.name} is missing required entries: {', '.join(missing)}. "
            f"See README.md for its format."
        )
    return conf
