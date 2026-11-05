#! python3
"""Daily solar grab: yesterday's Enphase production, keyed by its own date.

Writes to solar_staging.csv and rebuilds the archive CSV via csvstore, so a
failure here leaves the archive exactly as it was (the old scheme could
strand a half-written row).
"""

import csvstore
import enphase


def main():
    conf = csvstore.load_config("SolarLoginInfo.txt", required=("system_id", "token"))
    day, kwh = enphase.fetch_yesterday_kwh(conf["system_id"], conf["token"], conf.get("key"))
    csvstore.upsert_solar(day, kwh)
    csvstore.merge_final()
    print(f"Recorded {day}: {kwh:.3f} kWh")


if __name__ == "__main__":
    main()
