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

from datetime import date, timedelta

import netutil

BASE_URL = "https://api.enphaseenergy.com/api/v4"


def _get(url, token, params, api_key=None):
    headers = {"Authorization": f"Bearer {token}"}
    if api_key:  # only for developer-app tokens; homeowner PATs omit it
        headers["key"] = api_key
    return netutil.get_json(url, params=params, headers=headers, label="Enphase")


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
