"""
Fetch CDC BEAM (Bacteria, Enterics, Ameba, and Mycotics) foodborne pathogen data.

Queries the BEAM Dashboard Report Data (jbhn-e8xn) via Socrata, aggregating
human isolate counts by month and pathogen into a single flat CSV.

Output: data/raw/cdc_open/beam_foodborne.csv

Usage:
    uv run python -m cdc_open.fetch_beam
"""

import csv
import os
from pathlib import Path

import requests

_BASE_URL = "https://data.cdc.gov/resource"
_BEAM_ID = "jbhn-e8xn"
_OUT_DIR = Path("data/raw/cdc_open")
_TIMEOUT = 120


def _fetch(params: dict) -> list[dict]:
    headers = {"Accept": "application/json"}
    token = os.environ.get("CDC_DATA_APP_TOKEN")
    if token:
        headers["X-App-Token"] = token
    resp = requests.get(
        f"{_BASE_URL}/{_BEAM_ID}.json",
        params=params,
        headers=headers,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fetch_beam_foodborne(out_dir: Path = _OUT_DIR) -> list[dict]:
    """Aggregate human BEAM isolates by month and pathogen, national total."""
    print("Fetching BEAM foodborne pathogen data (jbhn-e8xn) ...", end=" ", flush=True)

    raw = _fetch({
        "$select": "year,month,pathogen,sum(number_of_isolates) as isolates",
        "$where": "source_type='Human'",
        "$group": "year,month,pathogen",
        "$order": "year,month,pathogen",
        "$limit": 5000,
    })

    rows = []
    for r in raw:
        year = r.get("year", "")
        month = r.get("month", "")
        pathogen = r.get("pathogen", "")
        isolates = r.get("isolates", "")
        if not (year and month and pathogen and isolates):
            continue
        date = f"{int(year):04d}-{int(month):02d}-01"
        rows.append({"date": date, "pathogen": pathogen, "isolates": int(isolates)})

    rows.sort(key=lambda r: (r["date"], r["pathogen"]))

    path = out_dir / "beam_foodborne.csv"
    _write_csv(path, rows, ["date", "pathogen", "isolates"])

    pathogens = sorted({r["pathogen"] for r in rows})
    date_range = f"{rows[0]['date'][:7]} – {rows[-1]['date'][:7]}" if rows else "no data"
    print(f"{len(rows)} rows ({date_range}, pathogens: {', '.join(pathogens)}) -> {path}")
    return rows


def main() -> None:
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        fetch_beam_foodborne(_OUT_DIR)
        print("\nDone.")
    except Exception as exc:
        print(f"FAILED: {exc}")
        raise


if __name__ == "__main__":
    main()
