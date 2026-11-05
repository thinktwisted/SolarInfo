"""Minimal Enphase Monitoring API v4 client (daily production only).

Auth: OAuth2 bearer token. For personal use this is a Personal Access
Token generated at https://entrez.enphaseenergy.com (sign in with your
Enlighten account). Developer-app OAuth access tokens additionally need
the application API key, passed via the optional api_key argument.
Endpoints: https://developer-v4.enphase.com/docs

v4 GET /api/v4/systems/{id}/energy_lifetime?start_date&end_date returns a
daily Wh time series, one entry per day from start_date, no gaps — a whole
range costs one request (v2 needed one request per day, hence the old
sleep(8) loop).
"""

import sys
from datetime import date, timedelta

import requests

BASE_URL = "https://api.enphaseenergy.com/api/v4"
TIMEOUT = 30  # seconds; fail loudly instead of hanging a scheduled task


def _get(url, token, params, api_key=None):
    headers = {"Authorization": f"Bearer {token}"}
    if api_key:  # only for developer-app tokens; homeowner PATs omit it
        headers["key"] = api_key
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as exc:
        sys.exit(f"ERROR: Enphase request failed: {exc}")
    if resp.status_code != 200:
        sys.exit(f"ERROR: Enphase API returned {resp.status_code}: {resp.text.strip()}")
    return resp.json()


def fetch_production(system_id, token, start_iso, end_iso, api_key=None):
    """Daily kWh production as {YYYY-MM-DD: float} for the returned range."""
    data = _get(
        f"{BASE_URL}/systems/{system_id}/energy_lifetime",
        token,
        {"start_date": start_iso, "end_date": end_iso},
        api_key=api_key,
    )
    start = date.fromisoformat(data["start_date"])  # clamped to operational date
    days = {}
    for offset, wh in enumerate(data["production"]):  # Wh per day, no gaps
        days[(start + timedelta(days=offset)).isoformat()] = wh / 1000.0
    return days


def fetch_yesterday_kwh(system_id, token, api_key=None):
    """Yesterday's (local) total production in kWh, keyed by its own date."""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    kwh = fetch_production(system_id, token, yesterday, yesterday, api_key).get(yesterday)
    if kwh is None:
        sys.exit(f"ERROR: Enphase returned no data for {yesterday}")
    return yesterday, kwh
