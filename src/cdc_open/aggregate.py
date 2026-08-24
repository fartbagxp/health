"""
Roll up large raw CDC Open datasets into small, chart-ready weekly series.

Some Socrata datasets (NWSS wastewater surveillance) run into the hundreds
of thousands of rows at full resolution -- far past what git/GitHub can
carry as a tracked file, and far more detail than a national trend chart
needs. This produces a national weekly-median series per pathogen from the
raw per-site, per-sample data, matching the aggregation health-charts used
to do at build time (scripts/aggregate-wastewater.js).

wastewater_activity (WVAL scored activity levels) uses the same per-site
raw shape but a different schema, so it gets its own aggregation function
(aggregate_wastewater_activity) rather than the shared PCR-concentration
one below.

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
    "wastewater_mpox",
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


def aggregate_wastewater_activity(raw_dir: Path = _RAW_DIR, out_dir: Path = _OUT_DIR) -> int:
    """National weekly median WVAL (Wastewater Viral Activity Level) score per
    pathogen, from wastewater_activity.csv's per-site rows (~500k rows / ~65MB
    at full resolution -- same reason the PCR-concentration series above are
    never committed raw)."""
    raw_path = raw_dir / "wastewater_activity.csv"
    with raw_path.open(newline="") as f:
        rows = list(csv.DictReader(f))

    by_week_pathogen: dict[tuple[date, str], list[float]] = defaultdict(list)
    for row in rows:
        raw_date = (row.get("week_end") or "").strip()
        pathogen = (row.get("pathogen_target") or "").strip()
        if not pathogen:
            continue
        try:
            d = datetime.fromisoformat(raw_date[:10]).date()
        except ValueError:
            continue
        try:
            value = float(row.get("site_wval") or "")
        except ValueError:
            continue
        if value < 0:
            continue
        by_week_pathogen[(d, pathogen)].append(value)

    result = []
    for (week, pathogen), values in by_week_pathogen.items():
        values.sort()
        mid = len(values) // 2
        median = values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2
        result.append((week, pathogen, median))
    result.sort()

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "wastewater_activity.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["week_end", "pathogen_target", "median_wval"])
        for week, pathogen, median in result:
            writer.writerow([week.isoformat(), pathogen, median])

    return len(result)


def aggregate_nwss_metric(raw_dir: Path = _RAW_DIR, out_dir: Path = _OUT_DIR) -> int:
    """National weekly-median COVID-19 wastewater activity *percentile* from
    nwss_metric.csv (2ew6-ywp6, ~840k per-site rows / far past GitHub's limit).

    This is the interpreted metric the public NWSS dashboard shows: each site's
    `percentile` is where its current level sits within its own history (0–100).
    We take the national median across sites per ISO week, keyed on the sample
    window end date, giving one small chart-ready series."""
    raw_path = raw_dir / "nwss_metric.csv"
    with raw_path.open(newline="") as f:
        rows = list(csv.DictReader(f))

    by_week: dict[date, list[float]] = defaultdict(list)
    for row in rows:
        raw_date = (row.get("date_end") or "").strip()
        try:
            d = datetime.fromisoformat(raw_date[:10]).date()
        except ValueError:
            continue
        try:
            value = float(row.get("percentile") or "")
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
        result.append((week, round(median, 2)))
    result.sort()

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "nwss_metric.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["week_end", "median_percentile"])
        for week, median in result:
            writer.writerow([week.isoformat(), median])

    return len(result)


_PLACES_COUNTY_COLUMNS = [
    "locationid",
    "stateabbr",
    "locationname",
    "measureid",
    "data_value",
    "totalpopulation",
]


def aggregate_places_county(raw_dir: Path = _RAW_DIR, out_dir: Path = _OUT_DIR) -> int:
    """Slim places_county.csv down to what health-charts' choropleth map
    actually joins on: crude-prevalence rows for real counties (5-digit FIPS
    -- drops the national 'US' aggregate row), and only the columns it reads.
    The raw file carries both crude and age-adjusted rows plus confidence
    intervals and descriptive text health-charts never touches, so this cuts
    both the row count and the column count roughly in half each -- the raw
    ~12MB file becomes well under 1MB."""
    raw_path = raw_dir / "places_county.csv"
    with raw_path.open(newline="") as f:
        rows = [
            row
            for row in csv.DictReader(f)
            if row.get("datavaluetypeid") == "CrdPrv"
            and len(row.get("locationid") or "") == 5
            and row.get("data_value")
        ]

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "places_county.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_PLACES_COUNTY_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in _PLACES_COUNTY_COLUMNS})

    return len(rows)


def aggregate_all(series: list[str] = WASTEWATER_SERIES) -> None:
    for key in series:
        print(f"  aggregating {key} ...", end=" ", flush=True)
        n = aggregate_series(key)
        print(f"{n} weekly points -> {_OUT_DIR / f'{key}.csv'}")

    print("  aggregating wastewater_activity ...", end=" ", flush=True)
    n = aggregate_wastewater_activity()
    print(f"{n} weekly points -> {_OUT_DIR / 'wastewater_activity.csv'}")

    print("  aggregating nwss_metric ...", end=" ", flush=True)
    n = aggregate_nwss_metric()
    print(f"{n} weekly points -> {_OUT_DIR / 'nwss_metric.csv'}")

    print("  aggregating places_county ...", end=" ", flush=True)
    n = aggregate_places_county()
    print(f"{n} rows -> {_OUT_DIR / 'places_county.csv'}")


if __name__ == "__main__":
    aggregate_all()
