#! python3
"""Daily weather grab: current conditions snapshot, keyed by today's date.

Writes to weather_staging.csv and rebuilds the archive CSV via csvstore.
Run it after SolarDataDailyGrab.py or before, either order; on the same day
or a day apart; the merge always keys both halves by their own dates.

Config: OpenWeatherAPI.txt — `appid=...` (or first bare line = appid, second =
zip) for backwards compatibility. Default zip 43065 (Westerville, OH).
API docs: https://openweathermap.org/current
"""

import sys
from datetime import date, datetime

import netutil

import csvstore

ZIP_DEFAULT = "43065"


def main():
    conf = csvstore.load_config("OpenWeatherAPI.txt")
    lines = conf["_lines"]
    appid = conf.get("appid") or (lines[0] if lines else None)
    if not appid:
        sys.exit("ERROR: OpenWeatherAPI.txt has no appid. See README.md.")
    zip_code = conf.get("zip") or (lines[1] if len(lines) > 1 else ZIP_DEFAULT)

    data = netutil.get_json(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"zip": zip_code, "appid": appid},
        label="OpenWeatherMap",
    )

    main_ = data["main"]
    sys_ = data["sys"]
    weather = {
        # temp_max on this endpoint is a station reading near run time,
        # not a true daily maximum — same caveat as the original script.
        "temperature": f"{round((main_['temp_max'] - 273.15) * 9 / 5 + 32, 1)}",
        "humidity": str(main_["humidity"]),
        "sky": data["weather"][0]["description"],
        "cloudiness": str(data["clouds"]["all"]),
        "wind": str(data["wind"]["speed"]),  # m/s
        "sunrise": _hms(sys_["sunrise"]),
        "sunset": _hms(sys_["sunset"]),
        "daylight_hr": f"{round((sys_['sunset'] - sys_['sunrise']) / 3600, 2)}",
    }

    today = date.today().isoformat()
    csvstore.upsert_weather(today, weather)
    csvstore.merge_final()
    print(f"Recorded {today}: {weather['temperature']} F, {weather['sky']}")


def _hms(epoch):
    return datetime.fromtimestamp(epoch).strftime("%H:%M")


if __name__ == "__main__":
    main()
