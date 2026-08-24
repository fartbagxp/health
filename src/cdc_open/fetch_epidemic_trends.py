"""
Fetch CDC's Center for Forecasting and Outbreak Analytics (CFA) epidemic-trends
nowcast and reduce it to a small, committed national trend series.

The source dataset ``5dqz-y4ea`` ("CDC Epidemic Trends and Rt") classifies the
recent trajectory of COVID-19, Influenza, and RSV in each state/day as Growing,
Likely Growing, Not Changing, Likely Declining, Declining, or Not Estimated. At
full resolution it re-publishes ~87 revision snapshots (~520k rows / ~72MB), far
past what a git repo should carry, so the bulk downloader skips it.

This script instead pulls only the latest ``as_of`` snapshot (~4k rows), then:

  * writes that raw snapshot to data/raw/cdc_open/epidemic_trends_rt.csv
    (state x disease x day trend categories, small enough to commit), and
  * accumulates a national daily rollup into
    data/processed/cdc_open/epidemic_trends_national.csv — for each (date,
    disease): how many states are growing, how many were estimated, and the
    share growing. Accumulating across weekly runs builds the long time series
    the single 4-week snapshot can't hold on its own.

Usage:
    uv run python -m cdc_open.fetch_epidemic_trends
"""

import csv
import os
import sys
from pathlib import Path

import requests

_BASE_URL = "https://data.cdc.gov/resource"
_DATASET_ID = "5dqz-y4ea"
_RAW_DIR = Path("data/raw/cdc_open")
_PROC_DIR = Path("data/processed/cdc_open")
_RAW_PATH = _RAW_DIR / "epidemic_trends_rt.csv"
_PROC_PATH = _PROC_DIR / "epidemic_trends_national.csv"

_RAW_COLUMNS = ["as_of", "disease", "state", "date", "category"]
_PROC_COLUMNS = ["date", "disease", "states_growing", "states_estimated", "pct_growing"]

# Categories that count as an upward trajectory.
_GROWING = {"Growing", "Likely Growing"}
# Everything except this is treated as an actual model estimate.
_NOT_ESTIMATED = "Not Estimated"


def _headers() -> dict:
    headers = {"Accept": "application/json"}
    token = os.environ.get("CDC_DATA_APP_TOKEN")
    if token:
        headers["X-App-Token"] = token
    return headers


def _get(params: dict) -> list[dict]:
    resp = requests.get(
        f"{_BASE_URL}/{_DATASET_ID}.json", params=params, headers=_headers(), timeout=90
    )
    resp.raise_for_status()
    return resp.json()


def _latest_as_of() -> str:
    rows = _get({"$select": "max(as_of) as m"})
    if not rows or not rows[0].get("m"):
        raise RuntimeError("could not determine latest as_of for 5dqz-y4ea")
    return rows[0]["m"]


def _fetch_snapshot(as_of: str) -> list[dict]:
    """All state x disease x day rows for one as_of snapshot."""
    rows: list[dict] = []
    offset = 0
    while True:
        page = _get(
            {
                "$where": f"as_of='{as_of}'",
                "$order": "date,disease,state",
                "$limit": 50_000,
                "$offset": offset,
            }
        )
        rows.extend(page)
        if len(page) < 50_000:
            break
        offset += 50_000
    return rows


def _clean_row(r: dict) -> dict:
    out = {}
    for k in _RAW_COLUMNS:
        v = r.get(k) or ""
        out[k] = v.split("T")[0] if k in ("as_of", "date") else v
    return out


def _write_raw(rows: list[dict]) -> None:
    _RAW_DIR.mkdir(parents=True, exist_ok=True)
    with _RAW_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_RAW_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(_clean_row(r) for r in rows)


def _rollup(rows: list[dict]) -> dict[tuple[str, str], dict]:
    """(date, disease) -> counts across states."""
    agg: dict[tuple[str, str], dict] = {}
    for r in rows:
        date = (r.get("date") or "").split("T")[0]
        disease = r.get("disease") or ""
        category = r.get("category") or ""
        if not date or not disease:
            continue
        key = (date, disease)
        entry = agg.setdefault(key, {"growing": 0, "estimated": 0})
        if category != _NOT_ESTIMATED:
            entry["estimated"] += 1
            if category in _GROWING:
                entry["growing"] += 1
    return agg


def _load_existing() -> dict[tuple[str, str], dict]:
    if not _PROC_PATH.exists():
        return {}
    out: dict[tuple[str, str], dict] = {}
    with _PROC_PATH.open(newline="") as f:
        for row in csv.DictReader(f):
            try:
                out[(row["date"], row["disease"])] = {
                    "growing": int(row["states_growing"]),
                    "estimated": int(row["states_estimated"]),
                }
            except (KeyError, ValueError):
                continue
    return out


def _write_rollup(merged: dict[tuple[str, str], dict]) -> int:
    _PROC_DIR.mkdir(parents=True, exist_ok=True)
    ordered = sorted(merged.items(), key=lambda kv: (kv[0][0], kv[0][1]))
    with _PROC_PATH.open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(_PROC_COLUMNS)
        for (date, disease), c in ordered:
            est = c["estimated"]
            pct = round(100 * c["growing"] / est, 1) if est else ""
            writer.writerow([date, disease, c["growing"], est, pct])
    return len(ordered)


def main() -> None:
    print("Fetching CFA epidemic trends (5dqz-y4ea)...", end=" ", flush=True)
    try:
        as_of = _latest_as_of()
        snapshot = _fetch_snapshot(as_of)
        print(f"latest as_of={as_of.split('T')[0]}, {len(snapshot)} rows")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    _write_raw(snapshot)
    print(f"  raw snapshot -> {_RAW_PATH}")

    # Merge this snapshot's rollup over anything already committed. New estimates
    # for a (date, disease) win, so re-run refinements replace prior values.
    merged = _load_existing()
    merged.update(_rollup(snapshot))
    n = _write_rollup(merged)
    print(f"  national rollup: {n} (date x disease) rows -> {_PROC_PATH}")


if __name__ == "__main__":
    main()
