"""
US Obesity & Diabetes as a Contributing Cause of Death, by Year (1999-present)

Queries two CDC WONDER datasets:
  D77  — Multiple Cause of Death, 1999-2020 (ICD-10, bridged-race, final)
  D176 — Provisional Mortality Statistics, 2018 through Last Week (provisional)

Both queries group by Year x Multiple Cause of Death (MCD) code and restrict
to two ICD-10 categories:

  E66        Obesity (all subtypes: E66.0-E66.9)
  E10-E14    Diabetes mellitus (all subtypes and complications)

These are Multiple Cause of Death codes -- the condition appears anywhere on
the death certificate (contributing factor), not necessarily as the
underlying cause. This is deliberately different from `leading_death.csv`
(cdc_open), which counts diabetes only when it is the *underlying* cause.
Obesity essentially never appears there, since it is rarely the immediate
cause of death -- it shows up as a contributing factor instead, which is
exactly what MCD captures and UCD does not.

WONDER returns the specific ICD-10 subcode (e.g. E66.0, E11.9) on each row
via the `cd` attribute; subcodes are summed into their parent category
(obesity or diabetes) per year rather than kept individually, since the
chart-relevant question is the category trend, not which complication.

Merge strategy: D77 for 1999-2020 (final); D176 for 2021-present (provisional).

Suppression note: CDC WONDER suppresses counts < 10. A handful of rare
subcodes (e.g. E12.x malnutrition-related diabetes) are suppressed most
years; this drops a small amount from the diabetes total but does not
meaningfully change the trend.

Output:
  data/raw/wonder/obesity-diabetes-deaths-by-year.csv
    year         - calendar year (integer)
    category     - "obesity" or "diabetes"
    deaths       - summed MCD death count across all subcodes (integer)
    provisional  - true if from D176 provisional data, false if D77 final

Usage:
    uv run python src/wonder/queries/fetch_obesity_diabetes_deaths.py
"""

import argparse
import csv
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from wonder.client import WonderClient  # noqa: E402
from wonder.queries._final_cache import read_final_cache, write_final_cache  # noqa: E402
from wonder.queries._merge_guard import require_complete  # noqa: E402

QUERIES_DIR = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "wonder"

RATE_LIMIT_SLEEP = 16

D77_PREFERRED_THROUGH = 2020

# The D77 half (1999-2020) is FINAL data CDC will not revise, so we cache it once
# and reuse it instead of re-querying WONDER. Refresh with --refresh-final.
FINAL_CACHE_CSV = "obesity-diabetes-deaths-by-year-final-1999-2020.csv"
FINAL_CACHE_FIELDS = ["year", "category", "deaths", "provisional"]

_YEAR_RE = re.compile(r"(\d{4})")


def _categorize(code: str) -> str | None:
    """Map an ICD-10 subcode to its parent category, or None if unrelated."""
    prefix = code[:3]
    if prefix == "E66":
        return "obesity"
    if prefix in ("E10", "E11", "E12", "E13", "E14"):
        return "diabetes"
    return None


def parse_rows(client: WonderClient, xml: str, provisional: bool) -> list[dict]:
    """
    Parse Year x MCD-subcode rows and aggregate subcodes into category totals.

    WONDER emits one row per (year, subcode) pair, repeating the year label
    on every row (not a true drill-down hierarchy for this grouping), e.g.:
        cell[0].label = "2018"                                    (or "2026 (provisional and partial)")
        cell[1].label = "Obesity due to excess calories"  cell[1].code = "E66.0"
        cell[2].value = "59"                                      (deaths)
    Total rows (grand total per year, and the overall grand total) have all
    cells blank except is_total, and are skipped.
    """
    rows = client.parse_response_table(xml)
    totals: dict[tuple[int, str], int] = defaultdict(int)

    for row in rows:
        if row.is_total:
            continue
        cells = row.cells
        if len(cells) < 3:
            continue

        year_match = _YEAR_RE.match((cells[0].label or "").strip())
        code = cells[1].code
        if year_match is None or not code:
            continue

        category = _categorize(code)
        if category is None:
            continue

        deaths = cells[2].get_numeric_value()
        if deaths is None:
            continue  # suppressed (<10) or non-numeric

        totals[(int(year_match.group(1)), category)] += int(deaths)

    return [
        {"year": year, "category": category, "deaths": deaths, "provisional": provisional}
        for (year, category), deaths in totals.items()
    ]


def run_query(client: WonderClient, dataset_id: str, query_file: Path, provisional: bool) -> list[dict]:
    print(f"  -> [{dataset_id}] {query_file.name} ...", flush=True)
    try:
        xml = client.execute_query_file(str(query_file))
    except RuntimeError as exc:
        print(f"    ERROR: {exc}", file=sys.stderr)
        return []

    records = parse_rows(client, xml, provisional)
    years = sorted({r["year"] for r in records})
    if years:
        print(f"    {len(records)} rows  |  years {years[0]}-{years[-1]}", flush=True)
    else:
        print("    0 rows", flush=True)
    return records


def merge(d77: list[dict], d176: list[dict]) -> list[dict]:
    """Use D77 for 1999-2020 (final); D176 for 2021+ (provisional)."""
    combined: dict[tuple, dict] = {}
    for rec in d77:
        if rec["year"] <= D77_PREFERRED_THROUGH:
            combined[(rec["year"], rec["category"])] = rec
    for rec in d176:
        if rec["year"] > D77_PREFERRED_THROUGH:
            combined[(rec["year"], rec["category"])] = rec
    return sorted(combined.values(), key=lambda r: (r["year"], r["category"]))


def write_csv(records: list[dict], out_path: Path) -> None:
    years = sorted({r["year"] for r in records})
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "category", "deaths", "provisional"])
        for rec in records:
            writer.writerow([
                rec["year"],
                rec["category"],
                rec["deaths"],
                str(rec["provisional"]).lower(),
            ])
    print(f"  [ok] {out_path.name}  ({len(records)} rows  |  years {years[0]}-{years[-1]})")


def print_summary(records: list[dict]) -> None:
    years = sorted({r["year"] for r in records})
    lookup = {(r["year"], r["category"]): r for r in records}

    col_w = 12
    header = f"{'Year':<6}" + "".join(f"{c.capitalize():>{col_w}}" for c in ("obesity", "diabetes"))
    print(header)
    print("-" * len(header))
    for yr in years:
        row = f"{yr:<6}"
        for c in ("obesity", "diabetes"):
            rec = lookup.get((yr, c))
            val = f"{rec['deaths']:,}" if rec else "-"
            row += f"{val:>{col_w}}"
        prov = " *" if any(lookup.get((yr, c), {}).get("provisional") for c in ("obesity", "diabetes")) else ""
        print(row + prov)
    print("\n* provisional")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh-final",
        action="store_true",
        help="Re-query WONDER for the final 1999-2020 data instead of reusing "
             "the cached snapshot (use only if CDC restates the historical series).",
    )
    args = parser.parse_args()

    client = WonderClient(timeout=120)
    print("Fetching obesity & diabetes contributing-cause deaths from CDC WONDER ...\n")

    final_cache = OUTPUT_DIR / FINAL_CACHE_CSV
    d77_from_cache = final_cache.exists() and not args.refresh_final

    d77_records: list[dict] = []
    d176_records: list[dict] = []

    # D77 (final, 1999-2020) — reuse the cached snapshot when present.
    if d77_from_cache:
        d77_records = read_final_cache(
            final_cache,
            int_fields=("year",),
            nullable_int_fields=("deaths",),
            bool_fields=("provisional",),
        )
        yrs = sorted({r["year"] for r in d77_records})
        print(
            f"  -> [D77] reusing cache {final_cache.name} "
            f"({len(d77_records)} rows  |  years {yrs[0]}-{yrs[-1]})",
            flush=True,
        )
    else:
        d77_records = run_query(
            client, "D77", QUERIES_DIR / "obesity-diabetes-deaths-by-year-1999-2020-req.xml", False
        )
        print(f"  (waiting {RATE_LIMIT_SLEEP}s for rate limit ...)", flush=True)
        time.sleep(RATE_LIMIT_SLEEP)

    # D176 (provisional, 2021+) — always re-fetched; these counts get revised.
    d176_records = run_query(
        client, "D176", QUERIES_DIR / "obesity-diabetes-deaths-by-year-2018-2024-req.xml", True
    )

    # A partial failure (e.g. one query hitting a WONDER 429 and returning [])
    # must abort rather than silently write a truncated CSV missing an era.
    require_complete(
        ("D77 (final, 1999-2020)", d77_records, D77_PREFERRED_THROUGH),
        ("D176 (provisional, 2021+)", d176_records),
    )

    print(f"\nMerging: D77 for 1999-{D77_PREFERRED_THROUGH}, D176 for {D77_PREFERRED_THROUGH + 1}+")
    merged = merge(d77_records, d176_records)
    print(f"Total merged rows: {len(merged)}\n")

    print("\nWriting output ...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Persist the final snapshot when it came fresh from WONDER (and validated).
    if not d77_from_cache:
        write_final_cache(
            [r for r in d77_records if r["year"] <= D77_PREFERRED_THROUGH],
            final_cache,
            FINAL_CACHE_FIELDS,
        )
    write_csv(merged, OUTPUT_DIR / "obesity-diabetes-deaths-by-year.csv")

    print("\n-- Deaths with obesity / diabetes as a contributing cause (MCD) --------")
    print_summary(merged)
    print("\nDone.")


if __name__ == "__main__":
    main()
