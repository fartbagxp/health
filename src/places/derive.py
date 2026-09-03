"""
Build the small slices health-charts reads from git.

DoltHub's SQL API caps every response at 1000 rows, so anything that needs the
whole country at once -- the county choropleth above all -- cannot come from a
live query. Those payloads stay here, as committed CSVs served off
raw.githubusercontent.com exactly like every other dataset in this repo. Live
SQL covers the drill-down case, where one county's measures fits the cap
comfortably.

Covers both families behind CDC's PLACES portal: the six BRFSS categories
(40 measures) and the seventh page, the ACS-derived Non-Medical Factors
(9 measures). measures.csv is the union, so health-charts has one catalog for
all seven pages.

Reads the county exports straight from Socrata rather than back out of Dolt: it
costs about ten seconds for both, keeps the two tiers independent, and means
these files are still produced when a DoltHub import fails.

Supersedes cdc_open.aggregate.aggregate_places_county(), which produced the
same six columns for 8 of the 40 PLACES measures, crude only.

Usage:
    uv run python -m places.derive
"""

import argparse
import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

from places.client import PlacesClient
from places.datasets import NMF_PERIOD, dataset, nmf_dataset
from places.transform import NMF_CATEGORY_NAME

RAW_DIR = Path("data/raw/places")
OUT_DIR = Path("data/processed/places")

# Same column layout the existing data/processed/cdc_open/places_county.csv
# uses, so health-charts needs a path change rather than a parsing change.
COUNTY_COLUMNS = [
    "locationid",
    "stateabbr",
    "locationname",
    "measureid",
    "data_value",
    "totalpopulation",
]
# The ACS family reports a margin of error rather than confidence limits, so
# it carries one extra column. Charts that ignore it read the first six exactly
# as they read county_crude.csv.
NMF_COUNTY_COLUMNS = [
    "locationid",
    "stateabbr",
    "locationname",
    "measureid",
    "data_value",
    "moe",
    "totalpopulation",
]
STATE_COLUMNS = [
    "stateabbr",
    "measureid",
    "data_value_type",
    "data_value",
    "population",
]
NMF_STATE_COLUMNS = ["stateabbr", "measureid", "data_value", "population"]
# `data_source` distinguishes the two families -- 'BRFSS' for the six PLACES
# categories, '5-year ACS' for Non-Medical Factors.
MEASURE_COLUMNS = [
    "measureid",
    "categoryid",
    "category",
    "measure",
    "short_question_text",
    "data_value_unit",
    "data_source",
]

_VALUE_TYPES = {"CrdPrv": "county_crude.csv", "AgeAdjPrv": "county_ageadj.csv"}


def derive(
    release: int = 2025,
    out_dir: Path = OUT_DIR,
    keep_raw: bool = False,
    period: str = NMF_PERIOD,
) -> dict[str, int]:
    """Build every committed slice. measures.csv spans both families."""
    client = PlacesClient(os.environ.get("CDC_DATA_APP_TOKEN"))
    out_dir.mkdir(parents=True, exist_ok=True)
    measures: dict[str, dict[str, str]] = {}

    counts = _derive_places(client, release, out_dir, measures, keep_raw)
    counts |= _derive_nmf(client, period, out_dir, measures, keep_raw)

    counts["measures.csv"] = _write(
        out_dir / "measures.csv",
        MEASURE_COLUMNS,
        [measures[k] for k in sorted(measures)],
    )
    return counts


def _derive_places(
    client: PlacesClient,
    release: int,
    out_dir: Path,
    measures: dict[str, dict[str, str]],
    keep_raw: bool,
) -> dict[str, int]:
    """County crude + age-adjusted + state rollup, from the PLACES export."""
    ds = dataset("county", release)
    raw = _fetch(client, ds.socrata_id, RAW_DIR / f"county_{release}.csv", "county")

    rows_by_type: dict[str, list[dict]] = {k: [] for k in _VALUE_TYPES}
    # (state, measure, type) -> [sum(value * population), sum(population)]
    weighted: dict[tuple[str, str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
    total = 0

    for row in client.read_csv(raw):
        total += 1
        location_id = row["LocationID"]
        value_type = row["DataValueTypeID"]
        value = row["Data_Value"].strip()
        # 5-digit FIPS only -- drops the national aggregate row.
        if len(location_id) != 5 or not value or value_type not in rows_by_type:
            continue

        measure_id = row["MeasureId"]
        population = row["TotalPopulation"].strip()
        rows_by_type[value_type].append(
            {
                "locationid": location_id,
                "stateabbr": row["StateAbbr"],
                "locationname": row["LocationName"],
                "measureid": measure_id,
                "data_value": value,
                "totalpopulation": population,
            }
        )
        if population:
            acc = weighted[(row["StateAbbr"], measure_id, value_type)]
            acc[0] += float(value) * float(population)
            acc[1] += float(population)

        measures.setdefault(
            measure_id,
            {
                "measureid": measure_id,
                "categoryid": row["CategoryID"],
                "category": row["Category"],
                "measure": row["Measure"],
                "short_question_text": row["Short_Question_Text"],
                "data_value_unit": row["Data_Value_Unit"],
                "data_source": row["DataSource"],
            },
        )

    counts: dict[str, int] = {}
    for value_type, filename in _VALUE_TYPES.items():
        counts[filename] = _write(
            out_dir / filename, COUNTY_COLUMNS, rows_by_type[value_type]
        )
    counts["state_rollup.csv"] = _write(
        out_dir / "state_rollup.csv",
        STATE_COLUMNS,
        [
            {
                "stateabbr": state,
                "measureid": measure_id,
                "data_value_type": value_type,
                # Population-weighted so a small county cannot swing a state mean.
                "data_value": f"{numerator / denominator:.1f}",
                "population": str(int(denominator)),
            }
            for (state, measure_id, value_type), (numerator, denominator) in sorted(
                weighted.items()
            )
            if denominator
        ],
    )
    print(f"  read {total:,} PLACES source rows")
    if not keep_raw:
        raw.unlink(missing_ok=True)
    return counts


def _derive_nmf(
    client: PlacesClient,
    period: str,
    out_dir: Path,
    measures: dict[str, dict[str, str]],
    keep_raw: bool,
) -> dict[str, int]:
    """County + state rollup for the Non-Medical Factors family.

    Note for anyone joining these against county_crude.csv: the two families
    do not agree on Connecticut. ACS 2017-2021 still uses the retired county
    FIPS 09001-09015, while PLACES 2025 uses the new planning regions
    09110-09190. County names differ cosmetically too ('Autauga County' here,
    'Autauga' there), which is harmless when joining on FIPS but visible in
    labels.
    """
    ds = nmf_dataset("county", period)
    raw = _fetch(
        client, ds.socrata_id, RAW_DIR / f"nmf_county_{period}.csv", "nmf county"
    )

    rows: list[dict] = []
    weighted: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
    total = 0

    for row in client.read_csv(raw):
        total += 1
        location_id = row["LocationID"]
        value = row["Data_Value"].strip()
        # 5-digit FIPS only -- drops the national aggregate (LocationID '59').
        if len(location_id) != 5 or not value:
            continue

        measure_id = row["MeasureID"]  # ID, not Id -- this family spells it so
        population = row["TotalPopulation"].strip()
        rows.append(
            {
                "locationid": location_id,
                "stateabbr": row["StateAbbr"],
                "locationname": row["LocationName"],
                "measureid": measure_id,
                "data_value": value,
                "moe": row.get("MOE", "").strip(),
                "totalpopulation": population,
            }
        )
        if population:
            acc = weighted[(row["StateAbbr"], measure_id)]
            acc[0] += float(value) * float(population)
            acc[1] += float(population)

        measures.setdefault(
            measure_id,
            {
                "measureid": measure_id,
                "categoryid": row["CategoryID"],
                # The source sets Category to the bare string 'SDOH'; stored
                # under the name CDC's own dataset titles and portal use.
                "category": NMF_CATEGORY_NAME,
                "measure": row["Measure"],
                "short_question_text": row["Short_Question_Text"],
                "data_value_unit": row["Data_Value_Unit"],
                "data_source": row["DataSource"],
            },
        )

    counts = {
        "nmf_county.csv": _write(out_dir / "nmf_county.csv", NMF_COUNTY_COLUMNS, rows),
        "nmf_state_rollup.csv": _write(
            out_dir / "nmf_state_rollup.csv",
            NMF_STATE_COLUMNS,
            [
                {
                    "stateabbr": state,
                    "measureid": measure_id,
                    "data_value": f"{numerator / denominator:.1f}",
                    "population": str(int(denominator)),
                }
                for (state, measure_id), (numerator, denominator) in sorted(
                    weighted.items()
                )
                if denominator
            ],
        ),
    }
    print(f"  read {total:,} Non-Medical Factors source rows")
    if not keep_raw:
        raw.unlink(missing_ok=True)
    return counts


def _fetch(client: PlacesClient, socrata_id: str, raw: Path, label: str) -> Path:
    if raw.exists():
        print(f"  reusing {raw} ({raw.stat().st_size:,} bytes)")
        return raw
    print(f"  downloading {label} ({socrata_id}) ...", end=" ", flush=True)
    print(f"{client.download(socrata_id, raw):,} bytes")
    return raw


def _write(path: Path, columns: list[str], rows: list[dict]) -> int:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=columns, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {len(rows):,} rows -> {path} ({path.stat().st_size / 1e6:.2f} MB)")
    return len(rows)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Build committed PLACES slices")
    parser.add_argument("--release", type=int, default=2025)
    parser.add_argument("--period", default=NMF_PERIOD)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--keep-raw", action="store_true")
    args = parser.parse_args()
    try:
        derive(args.release, args.out_dir, keep_raw=args.keep_raw, period=args.period)
    # A CLI entry point: report the failure on stderr and exit non-zero rather
    # than spilling a traceback into a workflow log.
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
