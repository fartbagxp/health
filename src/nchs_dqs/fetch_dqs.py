"""
Fetch NCHS Data Query System (DQS) slices and save as CSV.

DQS publishes each "Health, United States" topic as a Socrata dataset on
data.cdc.gov, all sharing one tidy schema:

    topic · subtopic · classification · group · subgroup
          · estimate_type · time_period · estimate · estimate_lci · estimate_uci

`classification = 'Total'` is the all-persons row; other classifications are
demographic / geographic / socioeconomic cuts. `group` is a SoQL reserved word,
so it must be backtick-quoted in a $select.

This first slice archives three shapes that exercise the whole health-charts
pipeline:

  * national_health_spending.csv  — a single long trend line (1960-present)
  * drug_overdose_by_type.csv     — a multi-line demographic/type split
  * low_birthweight_by_state.csv  — one value per state, for a choropleth

Output: data/raw/dqs/*.csv

Usage:
    uv run python -m nchs_dqs.fetch_dqs
"""

import csv
import os
from pathlib import Path

import requests

from nchs_dqs.datasets import DATASETS

_BASE_URL = "https://data.cdc.gov/resource"
_OUT_DIR = Path("data/raw/dqs")
_TIMEOUT = 60
_LIMIT = 50000

# 2-digit state FIPS, keyed by the full state name DQS uses in the `subgroup`
# column (Title Case, "District of Columbia"). 50 states + DC = 51 rows, which
# is exactly what the Geographic-Characteristic classification carries.
_STATE_TO_FIPS: dict[str, str] = {
    "Alabama": "01", "Alaska": "02", "Arizona": "04", "Arkansas": "05",
    "California": "06", "Colorado": "08", "Connecticut": "09", "Delaware": "10",
    "District of Columbia": "11", "Florida": "12", "Georgia": "13", "Hawaii": "15",
    "Idaho": "16", "Illinois": "17", "Indiana": "18", "Iowa": "19",
    "Kansas": "20", "Kentucky": "21", "Louisiana": "22", "Maine": "23",
    "Maryland": "24", "Massachusetts": "25", "Michigan": "26", "Minnesota": "27",
    "Mississippi": "28", "Missouri": "29", "Montana": "30", "Nebraska": "31",
    "Nevada": "32", "New Hampshire": "33", "New Jersey": "34", "New Mexico": "35",
    "New York": "36", "North Carolina": "37", "North Dakota": "38",
    "Ohio": "39", "Oklahoma": "40", "Oregon": "41", "Pennsylvania": "42",
    "Rhode Island": "44", "South Carolina": "45", "South Dakota": "46",
    "Tennessee": "47", "Texas": "48", "Utah": "49", "Vermont": "50",
    "Virginia": "51", "Washington": "53", "West Virginia": "54",
    "Wisconsin": "55", "Wyoming": "56",
}


def _fetch(dataset_id: str, params: dict) -> list[dict]:
    headers = {"Accept": "application/json"}
    token = os.environ.get("CDC_DATA_APP_TOKEN")
    if token:
        headers["X-App-Token"] = token
    resp = requests.get(
        f"{_BASE_URL}/{dataset_id}.json",
        params=params,
        headers=headers,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


# ─── National health spending (s57w-7gbe) ─────────────────────────────────────


def fetch_national_health_spending(out_dir: Path = _OUT_DIR) -> list[dict]:
    """
    U.S. national health spending, 1960-present, one row per year.

    The dataset publishes three measures as separate `estimate_type` values;
    this pivots them into wide columns so a single yearly row carries all three.
    """
    entry = DATASETS["national-health-spending"]
    dataset_id = entry.id
    print(f"Fetching national health spending ({dataset_id}, 1960-present) ...", end=" ", flush=True)

    raw = _fetch(
        dataset_id,
        {
            "$where": "classification='Total' AND estimate IS NOT NULL",
            "$select": "time_period, estimate_type, estimate",
            "$order": "time_period ASC",
            "$limit": _LIMIT,
        },
    )

    # estimate_type -> output column name
    measures = {
        "Number of dollars in billions": "dollars_billions",
        "Dollars per capita": "dollars_per_capita",
        "Percent of U.S. GDP": "pct_gdp",
    }

    by_year: dict[str, dict] = {}
    for row in raw:
        year = (row.get("time_period") or "").strip()
        col = measures.get((row.get("estimate_type") or "").strip())
        if not year or col is None:
            continue
        by_year.setdefault(year, {"year": year})[col] = row.get("estimate")

    rows = [by_year[y] for y in sorted(by_year)]
    fields = ["year", "dollars_billions", "dollars_per_capita", "pct_gdp"]
    path = out_dir / entry.csv
    _write_csv(path, rows, fields)
    print(f"{len(rows)} years -> {path}")
    return rows


# ─── Drug overdose death rates by drug type (rdjz-vn2n) ───────────────────────

# The dataset carries the drug type in `subtopic`; these are the labels it uses,
# mapped to short slugs used as the CSV's `drug_type` values (health-charts
# filters subSeries on these).
_DRUG_TYPES = {
    "All drug overdose deaths": "all",
    "Drug overdose deaths involving any opioid": "any_opioid",
    "Drug overdose deaths involving synthetic opioids other than methadone": "synthetic_opioids",
    "Drug overdose deaths involving natural and semisynthetic opioids": "natural_semisynthetic",
    "Drug overdose deaths involving heroin": "heroin",
    "Drug overdose deaths involving methadone": "methadone",
}


def fetch_drug_overdose_by_type(out_dir: Path = _OUT_DIR) -> list[dict]:
    """
    Age-adjusted drug-overdose death rate per 100,000, by drug type, per year.

    Long format: one row per (year, drug_type). All-persons ("Total"
    classification, "All ages") age-adjusted rates only.
    """
    entry = DATASETS["drug-overdose-deaths"]
    dataset_id = entry.id
    print(f"Fetching drug-overdose death rates by type ({dataset_id}) ...", end=" ", flush=True)

    raw = _fetch(
        dataset_id,
        {
            "$where": (
                "classification='Total' "
                "AND estimate_type='Deaths per 100,000 resident population, age adjusted' "
                "AND subgroup='All ages' AND estimate IS NOT NULL"
            ),
            "$select": "subtopic, time_period, estimate, estimate_lci, estimate_uci",
            "$order": "time_period ASC",
            "$limit": _LIMIT,
        },
    )

    rows = []
    for row in raw:
        drug_type = _DRUG_TYPES.get((row.get("subtopic") or "").strip())
        if drug_type is None:
            continue
        rows.append(
            {
                "year": (row.get("time_period") or "").strip(),
                "drug_type": drug_type,
                "rate": row.get("estimate"),
                "rate_lci": row.get("estimate_lci"),
                "rate_uci": row.get("estimate_uci"),
            }
        )

    rows.sort(key=lambda r: (r["drug_type"], r["year"]))
    fields = ["year", "drug_type", "rate", "rate_lci", "rate_uci"]
    path = out_dir / entry.csv
    _write_csv(path, rows, fields)
    n_types = len({r["drug_type"] for r in rows})
    print(f"{len(rows)} rows across {n_types} drug types -> {path}")
    return rows


# ─── Low birthweight live births by state (ga7k-kycn) ─────────────────────────


def fetch_low_birthweight_by_state(out_dir: Path = _OUT_DIR) -> list[dict]:
    """
    Percent of live births that are low birthweight, by state, latest year.

    One row per state (50 + DC), for a choropleth. Includes `state_fips` so the
    map can key on it directly.
    """
    entry = DATASETS["low-birthweight"]
    dataset_id = entry.id
    print(f"Fetching low-birthweight by state ({dataset_id}) ...", end=" ", flush=True)

    # Latest available year for the state-level series.
    latest = _fetch(
        dataset_id,
        {
            "$where": "classification='Geographic Characteristic' AND estimate IS NOT NULL",
            "$select": "max(time_period) as mx",
        },
    )
    year = (latest[0].get("mx") if latest else None) or ""

    raw = _fetch(
        dataset_id,
        {
            "$where": (
                f"classification='Geographic Characteristic' AND time_period='{year}' "
                "AND estimate IS NOT NULL"
            ),
            "$select": "subgroup, time_period, estimate",
            "$limit": _LIMIT,
        },
    )

    rows = []
    for row in raw:
        state = (row.get("subgroup") or "").strip()
        fips = _STATE_TO_FIPS.get(state)
        if fips is None:  # skip any non-state subgroup
            continue
        rows.append(
            {
                "state": state,
                "state_fips": fips,
                "year": (row.get("time_period") or "").strip(),
                "pct_low_birthweight": row.get("estimate"),
            }
        )

    rows.sort(key=lambda r: r["state"])
    fields = ["state", "state_fips", "year", "pct_low_birthweight"]
    path = out_dir / entry.csv
    _write_csv(path, rows, fields)
    print(f"{len(rows)} states (year {year}) -> {path}")
    return rows


def main() -> None:
    fetchers = (
        fetch_national_health_spending,
        fetch_drug_overdose_by_type,
        fetch_low_birthweight_by_state,
    )
    failed = []
    for fn in fetchers:
        try:
            fn()
        except Exception as exc:  # keep going so one bad source doesn't sink the rest
            print(f"FAILED ({fn.__name__}): {exc}")
            failed.append(fn.__name__)
    if failed:
        raise SystemExit(f"{len(failed)} fetch(es) failed: {', '.join(failed)}")
    print("\nDone.")


if __name__ == "__main__":
    main()
