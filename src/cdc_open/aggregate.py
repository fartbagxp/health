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


def aggregate_series(
    key: str, raw_dir: Path = _RAW_DIR, out_dir: Path = _OUT_DIR
) -> int:
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


def aggregate_wastewater_activity(
    raw_dir: Path = _RAW_DIR, out_dir: Path = _OUT_DIR
) -> int:
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
        writer = csv.DictWriter(
            f, fieldnames=_PLACES_COUNTY_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in _PLACES_COUNTY_COLUMNS})

    return len(rows)


# U.S. Census Bureau regions, the four-way split KFF and Force of Infection's
# regional editions use. DC counts toward the South; territories are dropped.
CENSUS_REGIONS = {
    "Northeast": ["CT", "ME", "MA", "NH", "RI", "VT", "NJ", "NY", "PA"],
    "Midwest": ["IL", "IN", "MI", "OH", "WI", "IA", "KS", "MN", "MO", "NE", "ND", "SD"],
    "South": [
        "DE",
        "DC",
        "FL",
        "GA",
        "MD",
        "NC",
        "SC",
        "VA",
        "WV",
        "AL",
        "KY",
        "MS",
        "TN",
        "AR",
        "LA",
        "OK",
        "TX",
    ],
    "West": [
        "AZ",
        "CO",
        "ID",
        "MT",
        "NV",
        "NM",
        "UT",
        "WY",
        "AK",
        "CA",
        "HI",
        "OR",
        "WA",
    ],
}

# Census Bureau Vintage 2024 resident population estimates (July 1, 2024),
# used only as the per-100k denominator for the regional rates below.
STATE_POPULATION_2024 = {
    "AL": 5_157_699,
    "AK": 740_133,
    "AZ": 7_582_384,
    "AR": 3_088_354,
    "CA": 39_431_263,
    "CO": 5_957_493,
    "CT": 3_675_069,
    "DE": 1_051_917,
    "DC": 702_250,
    "FL": 23_372_215,
    "GA": 11_180_878,
    "HI": 1_446_146,
    "ID": 2_001_619,
    "IL": 12_710_158,
    "IN": 6_924_275,
    "IA": 3_241_488,
    "KS": 2_970_606,
    "KY": 4_588_372,
    "LA": 4_597_740,
    "ME": 1_405_012,
    "MD": 6_263_220,
    "MA": 7_136_171,
    "MI": 10_140_459,
    "MN": 5_793_151,
    "MS": 2_943_045,
    "MO": 6_245_466,
    "MT": 1_137_233,
    "NE": 2_005_465,
    "NV": 3_267_467,
    "NH": 1_409_032,
    "NJ": 9_500_851,
    "NM": 2_130_256,
    "NY": 19_867_248,
    "NC": 11_046_024,
    "ND": 796_568,
    "OH": 11_883_304,
    "OK": 4_095_393,
    "OR": 4_272_371,
    "PA": 13_078_751,
    "RI": 1_112_308,
    "SC": 5_478_831,
    "SD": 924_669,
    "TN": 7_227_750,
    "TX": 31_290_831,
    "UT": 3_503_613,
    "VT": 648_493,
    "VA": 8_811_195,
    "WA": 7_958_180,
    "WV": 1_769_979,
    "WI": 5_960_975,
    "WY": 587_618,
}


def aggregate_flu_census_region(
    raw_dir: Path = _RAW_DIR, out_dir: Path = _OUT_DIR
) -> int:
    """Weekly confirmed flu new hospital admissions per Census region, as a
    count and a rate per 100k residents, from nhsn_hrd.csv's per-state rows
    (~22k rows / ~38MB raw). The rate is what makes regions comparable: the
    South alone holds ~39% of the U.S. population, so raw counts would put it
    on top every week regardless of where flu is actually rising first."""
    state_region = {
        st: region for region, states in CENSUS_REGIONS.items() for st in states
    }

    raw_path = raw_dir / "nhsn_hrd.csv"
    totals: dict[tuple[date, str], float] = defaultdict(float)
    with raw_path.open(newline="") as f:
        for row in csv.DictReader(f):
            region = state_region.get((row.get("jurisdiction") or "").strip())
            if not region:
                continue
            try:
                d = datetime.fromisoformat(
                    (row.get("weekendingdate") or "")[:10]
                ).date()
                value = float(row.get("totalconfflunewadm") or "")
            except ValueError:
                continue
            totals[(d, region)] += value

    region_pop = {
        region: sum(STATE_POPULATION_2024[st] for st in states)
        for region, states in CENSUS_REGIONS.items()
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "flu_census_region.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["week_end", "region", "flu_new_admissions", "rate_per_100k"])
        for (week, region), count in sorted(totals.items()):
            writer.writerow(
                [
                    week.isoformat(),
                    region,
                    int(count),
                    round(count / region_pop[region] * 100_000, 3),
                ]
            )

    return len(totals)


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

    print("  aggregating flu_census_region ...", end=" ", flush=True)
    n = aggregate_flu_census_region()
    print(f"{n} weekly points -> {_OUT_DIR / 'flu_census_region.csv'}")


if __name__ == "__main__":
    aggregate_all()
