#! python3
"""Backfill historical daily production into the archive via Enphase v4.

v4 energy_lifetime returns a whole date range in one request (one entry per
day, no gaps), so unlike the old v2 script there is no per-day sleep loop.
Rows land in solar_staging.csv keyed by their own date, then merge into the
archive — a re-run simply overwrites the same dates.

Dates are ISO YYYY-MM-DD. Edit START/END below (or set via CLI args) to match
the range you need, then: python SolarBackData.py [START] [END]
"""

import sys
from datetime import date

import csvstore
import enphase

# Sensible default window; override with two CLI args if you need another range.
START = "2020-02-01"
END = date.today().isoformat()


def main():
    conf = csvstore.load_config("SolarLoginInfo.txt", required=("system_id", "token"))
    start = sys.argv[1] if len(sys.argv) > 1 else START
    end = sys.argv[2] if len(sys.argv) > 2 else END

    days = enphase.fetch_production(conf["system_id"], conf["token"], start, end, conf.get("key"))
    if not days:
        sys.exit(f"ERROR: no production data returned for {start}..{end}")

    for day, kwh in days.items():
        csvstore.upsert_solar(day, kwh)
    csvstore.merge_final()

    total = sum(days.values())
    print(f"Backfilled {len(days)} day(s) {start}..{end} (total {total:.1f} kWh)")


if __name__ == "__main__":
    main()
