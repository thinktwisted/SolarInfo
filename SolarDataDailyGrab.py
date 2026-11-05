#! python3
"""Solar production grabber: daily self-heal window or an explicit date range.

Default (no date args): ensure every day in the lookback window has data —
normally just yesterday, but skipped/failed scheduled runs heal in one
range request. A fully current run makes zero API calls. Set the window
with `lookback_days = N` in SolarLoginInfo.txt (default 14).

Range mode: --start/--end pull exactly the dates you choose.
  python SolarDataDailyGrab.py --start 2026-01-01 --end 2026-06-30
  --start omitted  -> from the system's operational date (full history)
  --end omitted    -> through yesterday
This replaces the old SolarBackData.py. Already-recorded days are kept
as-is unless --refresh re-pulls them (with no date args, --refresh
re-pulls the whole window).

Dates are ISO YYYY-MM-DD. Rows key by their own production date and go
through staging + atomic merge (csvstore), so a failure leaves the
archive untouched.
"""

import argparse
import sys
from datetime import date, timedelta

import csvstore
import enphase

DEFAULT_LOOKBACK_DAYS = 14


def _iso(text):
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got '{text}'")


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Pull Enphase daily production (no date args = self-heal window).")
    parser.add_argument("--start", type=_iso,
                        help="first date to pull (range mode; default: operational date)")
    parser.add_argument("--end", type=_iso, help="last date to pull (default: yesterday)")
    parser.add_argument("--refresh", action="store_true",
                        help="re-pull dates already on record instead of only filling gaps")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    today = date.today()
    conf = csvstore.load_config("SolarLoginInfo.txt", required=("system_id", "token"))
    known = csvstore.known_solar_dates()

    if args.start or args.end:
        start = args.start
        end = args.end or today - timedelta(days=1)
        if end > today:
            sys.exit(f"ERROR: --end {end} is in the future")
        if start and start > end:
            sys.exit(f"ERROR: --start {start} is after --end {end}")
        if end == today:
            print(f"WARN: {end} is still in progress; its total will be partial",
                  file=sys.stderr)
        days = enphase.fetch_production(
            conf["system_id"], conf["token"],
            start.isoformat() if start else None, end.isoformat(), conf.get("key"))
        if not days:
            sys.exit(f"ERROR: Enphase returned no data for "
                     f"{start or '(operational start)'}..{end}")
        todo = days if args.refresh else {d: v for d, v in days.items() if d not in known}
    else:
        lookback = _lookback(conf)
        end = today - timedelta(days=1)
        window = [(today - timedelta(days=n)).isoformat() for n in range(1, lookback + 1)]
        missing = [d for d in window if d not in known]
        if not missing and not args.refresh:
            print(f"Solar data up to date (checked back to {window[-1]})")
            return
        days = enphase.fetch_production(conf["system_id"], conf["token"],
                                        window[-1], end.isoformat(), conf.get("key"))
        if not days:
            sys.exit(f"ERROR: Enphase returned no data for {window[-1]}..{end}")
        todo = {d: v for d, v in days.items() if args.refresh or d in set(missing)}
    if not todo:
        print(f"Nothing new for {args.start.isoformat() if args.start else 'the checked range'}..{end}"
              f" — all dates present (use --refresh to re-pull)")
        return

    for day, kwh in sorted(todo.items()):
        csvstore.upsert_solar(day, kwh)
    csvstore.merge_final()

    latest = max(todo)
    extra = sorted(d for d in todo if d != latest)
    print(f"Recorded {latest}: {todo[latest]:.3f} kWh"
          + (f" (+{len(extra)} more day(s) in range)" if extra else ""))


def _lookback(conf):
    raw = conf.get("lookback_days", str(DEFAULT_LOOKBACK_DAYS))
    try:
        value = int(raw)
    except ValueError:
        value = -1
    if value < 1:
        sys.exit(f"ERROR: lookback_days must be a positive integer, got '{raw}'")
    return value


if __name__ == "__main__":
    main()
