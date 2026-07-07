"""
Roll up large raw CDC Open datasets into small, chart-ready weekly series.

Some Socrata datasets (NWSS wastewater surveillance) run into the hundreds
of thousands of rows at full resolution -- far past what git/GitHub can
carry as a tracked file, and far more detail than a national trend chart
needs. This produces a national weekly-median series per pathogen from the
raw per-site, per-sample data, matching the aggregation health-charts used
to do at build time (scripts/aggregate-wastewater.js).

Usage:
    uv run python -m cdc_open.aggregate
"""

import csv
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

_RAW_DIR = Path("data/raw/cdc_open")
_OUT_DIR = Path("data/processed/cdc_open")

DATE_KEY = "sample_collect_date"
VALUE_KEY = "pcr_target_flowpop_lin"

# Raw files here are fetched fresh every run and never committed (see
# .gitignore) -- only the aggregated output below is tracked.
WASTEWATER_SERIES = [
    "wastewater_covid",
    "wastewater_flu",
    "wastewater_rsv",
    "wastewater_h5",
    "wastewater_measles",
]


def _week_start(d: date) -> date:
    """Monday of the ISO week containing d."""
    return d - timedelta(days=d.weekday())


def weekly_median(rows: list[dict]) -> list[tuple[date, float]]:
    by_week: dict[date, list[float]] = defaultdict(list)
    for row in rows:
        raw_date = (row.get(DATE_KEY) or "").strip()
        try:
            d = datetime.fromisoformat(raw_date[:10]).date()
        except ValueError:
            continue
        try:
            value = float(row.get(VALUE_KEY) or "")
        except ValueError:
            continue
        if value < 0:
            continue
        by_week[_week_start(d)].append(value)

    result = []
    for week, values in by_week.items():
        values.sort()
        mid = len(values) // 2
        median = values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2
        result.append((week, median))
    return sorted(result)


def aggregate_series(key: str, raw_dir: Path = _RAW_DIR, out_dir: Path = _OUT_DIR) -> int:
    raw_path = raw_dir / f"{key}.csv"
    with raw_path.open(newline="") as f:
        rows = list(csv.DictReader(f))

    weekly = weekly_median(rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{key}.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow([DATE_KEY, VALUE_KEY])
        for week, median in weekly:
            writer.writerow([week.isoformat(), median])

    return len(weekly)


def aggregate_all(series: list[str] = WASTEWATER_SERIES) -> None:
    for key in series:
        print(f"  aggregating {key} ...", end=" ", flush=True)
        n = aggregate_series(key)
        print(f"{n} weekly points -> {_OUT_DIR / f'{key}.csv'}")


if __name__ == "__main__":
    aggregate_all()
