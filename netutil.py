"""HTTP GET with retry/backoff for transient API failures.

Transient — retried up to RETRIES times with exponential backoff
(RETRY_BASE * 4**attempt, capped at RETRY_CAP): connection errors,
timeouts, HTTP 429/500/502/503/504, and malformed JSON bodies. When the
server sends Retry-After, its value wins over the schedule for that one
retry (still capped at RETRY_CAP).

Permanent — exits immediately, so a bad token fails fast instead of
burning the scheduled window: any other 4xx.

SOLARINFO_RETRY_BASE_SECONDS overrides the base delay (used by tests to
keep the suite fast).
"""

import os
import sys
import time

import requests

TIMEOUT = 30  # seconds per attempt; fail loudly instead of hanging a task
RETRIES = 3   # retries after the first attempt (4 calls worst case)
RETRY_BASE = float(os.environ.get("SOLARINFO_RETRY_BASE_SECONDS", "5"))
RETRY_CAP = 300.0

TRANSIENT_STATUSES = (429, 500, 502, 503, 504)


def get_json(url, params=None, headers=None, label="API"):
    """Return the decoded JSON body, or exit non-zero with the last error."""
    error = "no attempt made"
    forced_wait = None
    for attempt in range(1 + RETRIES):
        if attempt:
            if forced_wait is not None:
                delay, forced_wait = forced_wait, None
            else:
                delay = min(RETRY_BASE * (4 ** (attempt - 1)), RETRY_CAP)
            print(f"WARN: {error}; retrying in {delay:g}s "
                  f"({1 + RETRIES - attempt} attempt(s) left)", file=sys.stderr)
            time.sleep(delay)
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
        except requests.RequestException as exc:
            error = f"{label} request failed: {exc}"
            continue
        if resp.status_code == 200:
            try:
                return resp.json()
            except ValueError:
                error = f"{label} returned an undecodable body"
                continue
        if resp.status_code in TRANSIENT_STATUSES:
            error = f"{label} returned {resp.status_code}: {resp.text.strip()}"
            forced_wait = _retry_after(resp)
            continue
        sys.exit(f"ERROR: {label} returned {resp.status_code} "
                 f"(permanent, not retried): {resp.text.strip()}")
    sys.exit(f"ERROR: {error} — giving up after {1 + RETRIES} attempt(s)")


def _retry_after(resp):
    value = resp.headers.get("Retry-After") if resp.headers else None
    if value is None:
        return None
    try:
        return max(0.0, min(float(value), RETRY_CAP))
    except ValueError:
        return None
