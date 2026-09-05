"""
US Mortality by Year — Total Deaths and Top 5 Causes (1979–2024)

Queries three CDC WONDER datasets:
  D16  — Compressed Mortality, 1979–1998 (ICD-9)
  D77  — Multiple Cause of Death, 1999–2020 (ICD-10, final)
  D176 — Provisional Mortality, 2021–2024 (ICD-10, provisional)

Each query groups by Year × ICD Chapter (UCD).
Results are combined, then exported as:
  mortality-total-by-year.csv         — total deaths per year
  mortality-top5-causes-by-year.csv   — top 5 ICD chapters per year (long format)

Response format differences:
  D77/D176 — flat rows: every row has [year, cause, deaths, ...]
  D16      — hierarchical rows: the first sub-row in each year group has
              [year, cause, deaths]; subsequent sub-rows within the same year
              only have [cause, deaths] (year column is omitted/merged).
              The parser carries the year forward accordingly.

Usage:
    uv run python src/wonder/queries/fetch_mortality_by_year.py
"""

import argparse
import csv
import sys
import time
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from wonder.client import WonderClient  # noqa: E402
from wonder.queries._final_cache import read_final_cache, write_final_cache  # noqa: E402
from wonder.queries._merge_guard import require_complete  # noqa: E402

# ── Query configuration ────────────────────────────────────────────────────────
QUERIES_DIR = Path(__file__).parent

QUERY_FILES = [
    # dataset_id, path, hierarchical_format
    ("D16", QUERIES_DIR / "mortality-by-year-cause-1979-1998-req.xml", True),
    ("D77", QUERIES_DIR / "mortality-by-year-cause-1999-2020-req.xml", False),
    ("D176", QUERIES_DIR / "mortality-by-year-cause-2021-2024-req.xml", False),
]

OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "wonder"

# D16 (1979–1998) and D77 (1999–2020) are FINAL data CDC will not revise; only
# D176 (2021+) is provisional. We cache the two final eras together as one
# 1979–2020 snapshot and reuse it instead of re-querying WONDER (2 of 3 queries
# saved per run). Refresh with --refresh-final.
MORTALITY_FINAL_THROUGH = 2020
FINAL_CACHE_CSV = "mortality-by-year-cause-final-1979-2020.csv"
FINAL_CACHE_FIELDS = ["year", "cause", "deaths"]

# CDC WONDER requires ≥15 s between consecutive API requests
RATE_LIMIT_SLEEP = 16


# ── Row parsers ────────────────────────────────────────────────────────────────


def _is_year(label: str) -> bool:
    """Return True if label looks like a 4-digit year (1900–2099)."""
    s = label.strip()
    return len(s) == 4 and s.isdigit() and 1900 <= int(s) <= 2099


def parse_flat_rows(client: WonderClient, xml: str) -> list[dict]:
    """
    Parse flat-format response (D77, D176).

    Cell layout per data row:
        cell[0].label — Year
        cell[1].label — ICD Chapter
        cell[2].value — Deaths count (comma-formatted)
    """
    rows = client.parse_response_table(xml)
    records = []
    for row in rows:
        if row.is_total:
            continue
        cells = row.cells
        if len(cells) < 3:
            continue
        year_label = (cells[0].label or "").strip()
        cause_label = (cells[1].label or "").strip()
        if not year_label or not cause_label or not _is_year(year_label):
            continue
        deaths = cells[2].get_numeric_value()
        if deaths is None:
            continue
        records.append(
            {"year": int(year_label), "cause": cause_label, "deaths": int(deaths)}
        )
    return records


def parse_hierarchical_rows(client: WonderClient, xml: str) -> list[dict]:
    """
    Parse hierarchical-format response (D16).

    D16 "merged-cell" layout — only the first sub-row in each year group
    includes the year; subsequent sub-rows shift left by one column:

        First sub-row:      cell[0].label=year   cell[1].label=cause  cell[2].value=deaths
        Subsequent sub-rows: cell[0].label=cause  cell[1].value=deaths  (no year cell)

    We carry the last seen year forward.
    """
    rows = client.parse_response_table(xml)
    records = []
    current_year: int | None = None

    for row in rows:
        if row.is_total:
            continue
        cells = row.cells
        if not cells:
            continue

        c0_label = (cells[0].label or "").strip()

        if _is_year(c0_label):
            # First sub-row for this year: [year, cause, deaths, ...]
            current_year = int(c0_label)
            if len(cells) < 3:
                continue
            cause_label = (cells[1].label or "").strip()
            deaths = cells[2].get_numeric_value()
        else:
            # Continuation sub-row: [cause, deaths, ...]
            if current_year is None:
                continue
            cause_label = c0_label
            if len(cells) < 2:
                continue
            deaths = cells[1].get_numeric_value()

        if not cause_label or deaths is None:
            continue
        records.append(
            {"year": current_year, "cause": cause_label, "deaths": int(deaths)}
        )

    return records


# ── Query runner ───────────────────────────────────────────────────────────────


def run_query(
    client: WonderClient, dataset_id: str, query_file: Path, hierarchical: bool
) -> list[dict]:
    print(f"  → [{dataset_id}] {query_file.name} …", flush=True)
    try:
        xml = client.execute_query_file(str(query_file))
    except RuntimeError as exc:
        print(f"    ERROR: {exc}", file=sys.stderr)
        return []

    if hierarchical:
        records = parse_hierarchical_rows(client, xml)
    else:
        records = parse_flat_rows(client, xml)

    years = sorted({r["year"] for r in records})
    if years:
        print(f"    {len(records)} rows  |  years {years[0]}–{years[-1]}", flush=True)
    else:
        print("    0 rows", flush=True)
    return records


# ── Data combination ───────────────────────────────────────────────────────────


def combine(all_records: list[dict]) -> dict[int, dict[str, int]]:
    """Merge into {year: {cause: deaths}}, keeping max on overlap."""
    result: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for rec in all_records:
        y, c, d = rec["year"], rec["cause"], rec["deaths"]
        result[y][c] = max(result[y][c], d)
    return result


# ── Output writers ─────────────────────────────────────────────────────────────


def write_total_by_year(data: dict[int, dict[str, int]], out_path: Path) -> None:
    years = sorted(data.keys())
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "total_deaths"])
        for y in years:
            writer.writerow([y, sum(data[y].values())])
    print(f"  ✓ {out_path.name}  ({len(years)} years)")


def write_top5_by_year(data: dict[int, dict[str, int]], out_path: Path) -> None:
    years = sorted(data.keys())
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "rank", "cause", "deaths"])
        for y in years:
            top5 = sorted(data[y].items(), key=lambda x: x[1], reverse=True)[:5]
            for rank, (cause, deaths) in enumerate(top5, start=1):
                writer.writerow([y, rank, cause, deaths])
    print(f"  ✓ {out_path.name}  ({len(years)} years × top-5)")


# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh-final",
        action="store_true",
        help="Re-query WONDER for the final 1979–2020 data instead of reusing "
             "the cached snapshot (use only if CDC restates the historical series).",
    )
    args = parser.parse_args()

    client = WonderClient(timeout=120)
    all_records: list[dict] = []

    print("Fetching US mortality data from CDC WONDER …\n")

    query_by_id = {ds_id: (qfile, hier) for ds_id, qfile, hier in QUERY_FILES}
    final_cache = OUTPUT_DIR / FINAL_CACHE_CSV
    final_from_cache = final_cache.exists() and not args.refresh_final

    per_source: dict[str, list[dict]] = {}

    # Final eras D16 (1979–1998) + D77 (1999–2020) — reuse the cached snapshot
    # when present; otherwise query both and (below) persist them together.
    if final_from_cache:
        cached = read_final_cache(final_cache, int_fields=("year", "deaths"))
        all_records.extend(cached)
        yrs = sorted({r["year"] for r in cached})
        print(
            f"  → [D16+D77] reusing cache {final_cache.name} "
            f"({len(cached)} rows  |  years {yrs[0]}–{yrs[-1]})",
            flush=True,
        )
    else:
        for ds_id in ("D16", "D77"):
            qfile, hierarchical = query_by_id[ds_id]
            records = run_query(client, ds_id, qfile, hierarchical)
            per_source[ds_id] = records
            all_records.extend(records)
            print(f"  (waiting {RATE_LIMIT_SLEEP}s for rate limit …)", flush=True)
            time.sleep(RATE_LIMIT_SLEEP)

    # D176 (2021+) — provisional, always re-fetched.
    qfile, hierarchical = query_by_id["D176"]
    d176_records = run_query(client, "D176", qfile, hierarchical)
    per_source["D176"] = d176_records
    all_records.extend(d176_records)

    # A partial failure (e.g. one query hitting a WONDER 429 and returning [])
    # must abort rather than silently write a CSV missing an entire era. The
    # final half must reach both 1998 (D16) and 2020 (D77); D176 must reach 2021.
    final_recs = [r for r in all_records if r["year"] <= MORTALITY_FINAL_THROUGH]
    require_complete(
        ("final era (…1998, D16)", final_recs, 1998),
        ("final era (…2020, D77)", final_recs, 2020),
        ("D176 (2021–2024)", d176_records, 2021),
    )

    # Persist the final snapshot when it came fresh from WONDER (and validated).
    if not final_from_cache:
        write_final_cache(final_recs, final_cache, FINAL_CACHE_FIELDS)

    print(f"\nTotal records: {len(all_records)}")
    data = combine(all_records)
    years = sorted(data.keys())
    print(f"Years covered: {years[0]}–{years[-1]}\n")

    print("Writing output CSVs …")
    write_total_by_year(data, OUTPUT_DIR / "mortality-total-by-year.csv")
    write_top5_by_year(data, OUTPUT_DIR / "mortality-top5-causes-by-year.csv")

    # ── Quick preview ──────────────────────────────────────────────────────────
    print("\n── Total deaths (most recent 10 years) ───────────────────────────")
    for y in years[-10:]:
        total = sum(data[y].values())
        print(f"  {y}: {total:,}")

    latest = years[-1]
    print(f"\n── Top 5 causes of death ({latest}) ─────────────────────────────")
    top5 = sorted(data[latest].items(), key=lambda x: x[1], reverse=True)[:5]
    for rank, (cause, deaths) in enumerate(top5, start=1):
        print(f"  {rank}. {cause}: {deaths:,}")

    print("\nDone.")


if __name__ == "__main__":
    main()
