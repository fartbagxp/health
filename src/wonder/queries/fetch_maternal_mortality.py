"""
US Maternal Mortality by Year, National (1999–2024)

Queries two CDC WONDER datasets:
  D76  — Underlying Cause of Death, 1999–2020 (ICD-10, bridged-race, final)
  D158 — Underlying Cause of Death, 2018–2024 (ICD-10, single-race, final)

Both queries group by Year (national level) and filter underlying cause to:
  O00–O99  Pregnancy, childbirth and the puerperium
  A34      Obstetrical tetanus

NOTE — State-level data: the WONDER web service blocks state grouping and
state filtering for all mortality datasets ("Only national data are available
for this dataset when using the WONDER web service"). To get state-level data:
  1. Use the WONDER web UI directly at https://wonder.cdc.gov/ucd-icd10.html
     (D158, 2018–2024) or https://wonder.cdc.gov/ucd-icd10-expanded.html
     Select: Group by Year + State; UCD filter = O00-O99, A34; Export Results.
  2. Or use the NCHS published tables:
     https://www.cdc.gov/nchs/maternal-mortality/mmr-2018-2022-state-data.pdf

Merge strategy: D76 for 1999–2017; D158 for 2018–2024. The 2018–2020 overlap
is present in both; D158 is preferred as the more current final methodology.
Death counts match for those years when not broken down by race.

Output:
  maternal-mortality-by-year.csv
    year        – calendar year
    deaths      – raw maternal death count (national)
    population  – total US population denominator (all ages, all races)
    crude_rate  – WONDER crude rate per 100,000 population (NOT the official MMR)

Note on rates: the official maternal mortality rate uses LIVE BIRTHS as
denominator (per 100,000 live births), not population. Join with birth data
from births-by-year queries (D66 etc.) to compute the true MMR.

Pregnancy checkbox caveat: states adopted the 2003 revised death certificate
(adding a pregnancy checkbox) on a rolling schedule 2003–2017. This caused a
staggered artificial increase in reported counts nationally. The 2003 jump in
the data is partly measurement change, not a real increase.

Usage:
    uv run python src/wonder/queries/fetch_maternal_mortality.py
"""

import csv
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from wonder.client import WonderClient  # noqa: E402

QUERIES_DIR = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "wonder"

# CDC WONDER requires ≥15 s between consecutive API requests
RATE_LIMIT_SLEEP = 16

QUERY_FILES = [
    # (dataset_id, path, preferred_for_years_from)
    ("D76",  QUERIES_DIR / "maternal-mortality-by-year-1999-2020-req.xml",  None),
    ("D158", QUERIES_DIR / "maternal-mortality-by-year-2018-2024-req.xml",  2018),
]

# D158 is preferred from 2018 onward (more current final methodology)
D158_PREFERRED_FROM = 2018


def _is_year(label: str) -> bool:
    s = label.strip()
    return len(s) == 4 and s.isdigit() and 1900 <= int(s) <= 2099


def parse_rows(client: WonderClient, xml: str) -> list[dict]:
    """
    Parse flat response grouped by Year (national level).

    Cell layout when grouped by Year only:
        cell[0].label  — Year
        cell[1].value  — Deaths count
        cell[2].value  — Population
        cell[3].value  — Crude rate (per 100k population)
    """
    rows = client.parse_response_table(xml)
    records = []
    for row in rows:
        if row.is_total:
            continue
        cells = row.cells
        if len(cells) < 2:
            continue

        year_label = (cells[0].label or "").strip()
        if not _is_year(year_label):
            continue

        year = int(year_label)
        deaths = cells[1].get_numeric_value()
        population = cells[2].get_numeric_value() if len(cells) > 2 else None
        crude_rate = cells[3].get_numeric_value() if len(cells) > 3 else None

        records.append({
            "year": year,
            "deaths": deaths,
            "population": population,
            "crude_rate": crude_rate,
        })
    return records


def run_query(client: WonderClient, dataset_id: str, query_file: Path) -> list[dict]:
    print(f"  → [{dataset_id}] {query_file.name} …", flush=True)
    try:
        xml = client.execute_query_file(str(query_file))
    except RuntimeError as exc:
        print(f"    ERROR: {exc}", file=sys.stderr)
        return []

    records = parse_rows(client, xml)
    years = sorted({r["year"] for r in records})
    if years:
        print(f"    {len(records)} rows  |  years {years[0]}–{years[-1]}", flush=True)
    else:
        print("    0 rows", flush=True)
    return records


def merge(d76_records: list[dict], d158_records: list[dict]) -> list[dict]:
    """
    Prefer D158 for years >= D158_PREFERRED_FROM; use D76 for earlier years.
    """
    combined: dict[int, dict] = {}

    for rec in d76_records:
        if rec["year"] < D158_PREFERRED_FROM:
            combined[rec["year"]] = rec

    for rec in d158_records:
        combined[rec["year"]] = rec  # always overwrite with D158 for 2018+

    return sorted(combined.values(), key=lambda r: r["year"])


def write_csv(records: list[dict], out_path: Path) -> None:
    years = sorted({r["year"] for r in records})
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "deaths", "population", "crude_rate_per_100k_pop"])
        for rec in records:
            writer.writerow([
                rec["year"],
                "" if rec["deaths"] is None else int(rec["deaths"]),
                "" if rec["population"] is None else int(rec["population"]),
                "" if rec["crude_rate"] is None else rec["crude_rate"],
            ])
    print(f"  ✓ {out_path.name}  ({len(records)} rows  |  years {years[0]}–{years[-1]})")


def main() -> None:
    client = WonderClient(timeout=120)
    print("Fetching maternal mortality data from CDC WONDER …\n")

    d76_records: list[dict] = []
    d158_records: list[dict] = []

    for i, (ds_id, qfile, _) in enumerate(QUERY_FILES):
        if i > 0:
            print(f"  (waiting {RATE_LIMIT_SLEEP}s for rate limit …)", flush=True)
            time.sleep(RATE_LIMIT_SLEEP)

        records = run_query(client, ds_id, qfile)
        if ds_id == "D76":
            d76_records = records
        else:
            d158_records = records

    if not d76_records and not d158_records:
        print("\nNo data returned — check errors above.", file=sys.stderr)
        sys.exit(1)

    print(f"\nMerging: D76 for 1999–{D158_PREFERRED_FROM - 1}, D158 for {D158_PREFERRED_FROM}+")
    merged = merge(d76_records, d158_records)
    print(f"Total merged rows: {len(merged)}")


    print("\nWriting output …")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(merged, OUTPUT_DIR / "maternal-mortality-by-year.csv")

    # ── Quick preview ──────────────────────────────────────────────────────────
    years = sorted(r["year"] for r in merged if r["deaths"] is not None)
    print(f"\n── National maternal deaths ({years[0]}–{years[-1]}) ──────────────────")
    for rec in sorted(merged, key=lambda r: r["year"]):
        if rec["deaths"] is not None:
            print(f"  {rec['year']}: {int(rec['deaths']):>5} deaths")

    print("\nDone.")


if __name__ == "__main__":
    main()
