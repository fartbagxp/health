"""
Fetch COVID-19, RSV, and combined respiratory hospitalization data and save as CSV.

Equivalent Python port of the JS data-fetching script.
Output files are written to data/raw/resp/.

Usage:
    uv run python -m cdc_open.fetch_resp
"""

import csv
import os
import sys
from pathlib import Path

import requests

_BASE_URL = "https://data.cdc.gov/resource"
_OUT_DIR = Path("data/raw/resp")
_LIMIT = 1000


def _fetch(dataset_id: str, params: dict) -> list[dict]:
    headers = {"Accept": "application/json"}
    token = os.environ.get("CDC_DATA_APP_TOKEN")
    if token:
        headers["X-App-Token"] = token
    resp = requests.get(
        f"{_BASE_URL}/{dataset_id}.json",
        params=params,
        headers=headers,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fetch_covid_hosp(out_dir: Path) -> list[dict]:
    """COVID-19 hospitalizations (7dk4-g6vg) — national, archived 2020–2024."""
    print("Fetching COVID-19 hospitalization data (7dk4-g6vg)...", end=" ", flush=True)
    data = _fetch(
        "7dk4-g6vg",
        {
            "$where": "state='USA'",
            "$order": "week_ending_date ASC",
            "$limit": _LIMIT,
        },
    )
    rows = [
        {
            "date": d["week_ending_date"].split("T")[0],
            "hospitalizations": round(
                float(d.get("total_adm_all_covid_confirmed") or 0)
            ),
            "avg_daily": round(float(d.get("avg_adm_all_covid_confirmed") or 0), 2),
            "pct_inpatient_beds": round(
                float(d.get("avg_percent_inpatient_beds") or 0), 2
            ),
        }
        for d in data
    ]
    path = out_dir / "covid-hospitalizations.csv"
    _write_csv(
        path, rows, ["date", "hospitalizations", "avg_daily", "pct_inpatient_beds"]
    )
    if rows:
        print(f"{len(rows)} rows ({rows[0]['date']} – {rows[-1]['date']}) -> {path}")
    else:
        print(f"0 rows -> {path}")
    return rows


def fetch_rsv_hosp(out_dir: Path) -> list[dict]:
    """RSV hospitalization rates (29hc-w46k) — RSV-NET national, 2020-21 through 2023-24."""
    print("Fetching RSV hospitalization data (29hc-w46k)...", end=" ", flush=True)
    seasons = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]
    season_clause = " OR ".join(f"season='{s}'" for s in seasons)
    data = _fetch(
        "29hc-w46k",
        {
            "$where": (
                f"({season_clause})"
                " AND state='RSV-NET'"
                " AND age_category='All'"
                " AND sex='All'"
                " AND race='All'"
            ),
            "$order": "week_ending_date ASC",
            "$limit": 2000,
        },
    )
    rows = [
        {
            "date": d["week_ending_date"].split("T")[0]
            if "T" in d.get("week_ending_date", "")
            else d.get("week_ending_date", ""),
            "rate": round(float(d.get("rate") or 0), 4),
            "cumulative_rate": round(float(d.get("cumulative_rate") or 0), 4),
            "season": d.get("season", ""),
        }
        for d in data
        if d.get("week_ending_date")
    ]
    path = out_dir / "rsv-hospitalizations.csv"
    _write_csv(path, rows, ["date", "rate", "cumulative_rate", "season"])
    if rows:
        print(f"{len(rows)} rows ({rows[0]['date']} – {rows[-1]['date']}) -> {path}")
    else:
        print(f"0 rows -> {path}")
    return rows


def fetch_respiratory_combined(out_dir: Path) -> list[dict]:
    """Combined COVID/flu/RSV hospital data (ua7e-t2fy) — NHSN national, 2020–present."""
    print("Fetching combined respiratory data (ua7e-t2fy)...", end=" ", flush=True)
    data = _fetch(
        "ua7e-t2fy",
        {
            "$where": "jurisdiction='USA'",
            "$order": "weekendingdate DESC",
            "$limit": _LIMIT,
        },
    )
    rows = [
        {
            "date": d["weekendingdate"].split("T")[0]
            if d.get("weekendingdate")
            else "",
            "covid_new_admissions": int(float(d.get("totalconfc19newadm") or 0)),
            "flu_new_admissions": int(float(d.get("totalconfflunewadm") or 0)),
            "rsv_new_admissions": int(float(d.get("totalconfrsvnewadm") or 0)),
            "covid_inpatients": int(float(d.get("totalconfc19hosppats") or 0)),
            "flu_inpatients": int(float(d.get("totalconffluhosppats") or 0)),
            "rsv_inpatients": int(float(d.get("totalconfrsvhosppats") or 0)),
            "covid_icu": int(float(d.get("totalconfc19icupats") or 0)),
            "flu_icu": int(float(d.get("totalconffluicupats") or 0)),
            "rsv_icu": int(float(d.get("totalconfrsvicupats") or 0)),
        }
        for d in data
        if d.get("weekendingdate")
    ]
    rows.sort(key=lambda r: r["date"])
    path = out_dir / "respiratory-combined.csv"
    _write_csv(
        path,
        rows,
        [
            "date",
            "covid_new_admissions",
            "flu_new_admissions",
            "rsv_new_admissions",
            "covid_inpatients",
            "flu_inpatients",
            "rsv_inpatients",
            "covid_icu",
            "flu_icu",
            "rsv_icu",
        ],
    )
    if rows:
        print(f"{len(rows)} rows ({rows[0]['date']} – {rows[-1]['date']}) -> {path}")
    else:
        print(f"0 rows -> {path}")
    return rows


def main() -> None:
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    failed = []

    for label, fn in [
        ("COVID hospitalizations", lambda: fetch_covid_hosp(_OUT_DIR)),
        ("RSV hospitalizations", lambda: fetch_rsv_hosp(_OUT_DIR)),
        ("Combined respiratory (NHSN)", lambda: fetch_respiratory_combined(_OUT_DIR)),
    ]:
        try:
            fn()
        except Exception as exc:
            print(f"ERROR: {exc}")
            failed.append((label, exc))

    print(f"\nDone: {3 - len(failed)} succeeded, {len(failed)} failed.")
    if failed:
        for label, exc in failed:
            print(f"  FAILED {label}: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
