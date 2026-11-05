#! python3
"""Daily solar grab with self-healing backfill.

Each run ensures every day in a recent lookback window has production
data — normally that's just yesterday, but if scheduled runs were skipped
(machine asleep, outage lasting days), one successful run heals them all:
v4 energy_lifetime returns a whole range in one request. Dates already on
record are never re-fetched.

Rows key by their own production date and go through staging + atomic
merge (csvstore), so a failure leaves the archive untouched.
"""

from datetime import date, timedelta

import csvstore
import enphase

LOOKBACK_DAYS = 14


def main():
    conf = csvstore.load_config("SolarLoginInfo.txt", required=("system_id", "token"))
    today = date.today()
    start = (today - timedelta(days=LOOKBACK_DAYS)).isoformat()
    end = (today - timedelta(days=1)).isoformat()  # through yesterday; today is incomplete

    known = csvstore.known_solar_dates()
    missing = [(today - timedelta(days=n)).isoformat()
               for n in range(1, LOOKBACK_DAYS + 1)
               if (today - timedelta(days=n)).isoformat() not in known]
    if not missing:
        print(f"Solar data up to date (checked back to {start})")
        return

    days = enphase.fetch_production(conf["system_id"], conf["token"],
                                    start, end, conf.get("key"))
    if end not in days:
        raise SystemExit(f"ERROR: Enphase returned no data for {end}")
    for day in missing:
        if day in days:  # days before the system went operational aren't returned
            csvstore.upsert_solar(day, days[day])
    csvstore.merge_final()
    healed = [d for d in missing if d != end]
    print(f"Recorded {end}: {days[end]:.3f} kWh"
          + (f" (self-healed {len(healed)} skipped day(s): {', '.join(healed)})" if healed else ""))


if __name__ == "__main__":
    main()
