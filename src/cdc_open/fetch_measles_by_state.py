"""
Fetch current-year measles case counts by state from CDC NNDSS.

Queries the same broad "NNDSS Weekly Notifiable Diseases" dataset (x9gk-5huc)
health-charts' companion tool pulse-code already explores via `pulse cdc-open
query nndss_measles`, but narrowed server-side to just the two measles labels
("Measles, Imported" / "Measles, Indigenous") and the last couple of years --
the full table covers every notifiable disease back to 2014 and would be
enormous (and mostly irrelevant) to pull down whole. `m2` in this feed is a
year-to-date cumulative count, so the output here is just each state's latest
cumulative total for the current year: one row per state (~55 rows), not a
weekly time series, since a state choropleth only needs one value per state.

Note: CDC changed the `states` column from ALL CAPS ("TEXAS") to Title Case
("Texas") starting with 2025 data -- this normalizes both to Title Case and
also drops non-state rows (HHS regions, "US RESIDENTS", territories not on
the map).

Output: data/raw/cdc_open/measles_by_state.csv (state, state_fips, year,
week, cases)

Usage:
    uv run python -m cdc_open.fetch_measles_by_state
"""

import csv
import os
from collections import defaultdict
from pathlib import Path

import requests

_BASE_URL = "https://data.cdc.gov/resource"
_NNDSS_ID = "x9gk-5huc"
_OUT_DIR = Path("data/raw/cdc_open")
_TIMEOUT = 60

_LABELS = ("Measles, Imported", "Measles, Indigenous")

# 2-digit FIPS -> state name (title case, matching the CSV's normalized
# `states` values). Only real states + DC are mapped -- NNDSS also carries
# HHS regions ("NEW ENGLAND"), a national total ("US RESIDENTS"), and a few
# territories with no county/state boundary in us-atlas, all excluded.
_STATE_TO_FIPS: dict[str, str] = {
    "Alabama": "01", "Alaska": "02", "Arizona": "04", "Arkansas": "05",
    "California": "06", "Colorado": "08", "Connecticut": "09", "Delaware": "10",
    "District of Columbia": "11", "Florida": "12", "Georgia": "13", "Hawaii": "15",
    "Idaho": "16", "Illinois": "17", "Indiana": "18", "Iowa": "19",
    "Kansas": "20", "Kentucky": "21", "Louisiana": "22", "Maine": "23",
    "Maryland": "24", "Massachusetts": "25", "Michigan": "26", "Minnesota": "27",
    "Mississippi": "28", "Missouri": "29", "Montana": "30", "Nebraska": "31",
    "Nevada": "32", "New Hampshire": "33", "New Jersey": "34", "New Mexico": "35",
    "New York": "36", "New York City": "36", "North Carolina": "37", "North Dakota": "38",
    "Ohio": "39", "Oklahoma": "40", "Oregon": "41", "Pennsylvania": "42",
    "Rhode Island": "44", "South Carolina": "45", "South Dakota": "46",
    "Tennessee": "47", "Texas": "48", "Utah": "49", "Vermont": "50",
    "Virginia": "51", "Washington": "53", "West Virginia": "54",
    "Wisconsin": "55", "Wyoming": "56",
}


def _fetch(params: dict) -> list[dict]:
    headers = {"Accept": "application/json"}
    token = os.environ.get("CDC_DATA_APP_TOKEN")
    if token:
        headers["X-App-Token"] = token
    resp = requests.get(
        f"{_BASE_URL}/{_NNDSS_ID}.json",
        params=params,
        headers=headers,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_measles_by_state(out_dir: Path = _OUT_DIR, min_year: int = 2024) -> list[dict]:
    """Each state's latest year-to-date cumulative measles case count."""
    print(f"Fetching NNDSS measles-by-state data ({_NNDSS_ID}, {min_year}-present) ...", end=" ", flush=True)

    label_clause = " OR ".join(f"label='{label}'" for label in _LABELS)
    raw = _fetch({
        "$select": "states,year,week,label,m2",
        "$where": f"({label_clause}) AND year >= '{min_year}'",
        "$limit": 50000,
    })

    # Latest (year, week) seen per state, summing the two labels at that week.
    latest: dict[str, tuple[int, int]] = {}
    cases_at_latest: dict[str, float] = defaultdict(float)

    by_state_week: dict[tuple[str, int, int], float] = defaultdict(float)
    for row in raw:
        state = (row.get("states") or "").strip().title()
        if state not in _STATE_TO_FIPS:
            continue
        try:
            year, week = int(row.get("year", 0)), int(row.get("week", 0))
            cases = float(row.get("m2") or 0)
        except (TypeError, ValueError):
            continue
        by_state_week[(state, year, week)] += cases

    for (state, year, week), cases in by_state_week.items():
        if state not in latest or (year, week) > latest[state]:
            latest[state] = (year, week)
            cases_at_latest[state] = cases

    rows = []
    for state, (year, week) in sorted(latest.items()):
        rows.append({
            "state": state,
            "state_fips": _STATE_TO_FIPS[state],
            "year": year,
            "week": week,
            "cases": int(cases_at_latest[state]),
        })
    rows.sort(key=lambda r: -r["cases"])

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "measles_by_state.csv"
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["state", "state_fips", "year", "week", "cases"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    total = sum(r["cases"] for r in rows)
    print(f"{len(rows)} states, {total} total cases -> {path}")
    return rows


def main() -> None:
    try:
        fetch_measles_by_state()
        print("\nDone.")
    except Exception as exc:
        print(f"FAILED: {exc}")
        raise


if __name__ == "__main__":
    main()
