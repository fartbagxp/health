"""
US Fentanyl (Synthetic Opioid) Deaths by Month, National (1999–present)

Queries two CDC WONDER datasets:
  D77  — Multiple Cause of Death, 1999–2020 (ICD-10, bridged-race, final)
  D176 — Provisional Mortality Statistics, 2018 through Last Week (provisional)

Both queries group by Year × Month (national level) and filter by Multiple Cause of
Death (MCD) code:
  T40.4  Poisoning by other synthetic narcotics (fentanyl and analogues)

T40.4 is coded as a contributing (multiple) cause, not necessarily the underlying
cause of death. The underlying cause is typically "Accidental poisoning" (X40-X44),
but T40.4 identifies the specific substance involved. This matches the methodology
used by the CDC's VSRR provisional overdose counts and by researchers tracking the
fentanyl epidemic (see https://github.com/dawaldron/fentanyl-deaths).

Merge strategy: D77 for 1999–2020 (final data preferred); D176 for 2021–present
(provisional). The 2018–2020 overlap is present in both; D77 is used for those
years as it contains finalized death certificate data.

Suppression note: CDC WONDER suppresses monthly counts below 10 deaths. In early
years (1999–2013) some months may be suppressed — those rows are omitted from the
output rather than imputed.

Output:
  data/raw/wonder/fentanyl-deaths-by-month.csv
    year        – calendar year (integer)
    month       – month number 1–12 (integer)
    deaths      – T40.4 death count for the month (integer, blank if suppressed)
    provisional – true if from D176 provisional data, false if from D77 final data

Usage:
    uv run python src/wonder/queries/fetch_fentanyl_deaths.py
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

RATE_LIMIT_SLEEP = 16

MONTH_NAMES = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

# D77 has final data through 2020; prefer it over D176 for 1999-2020
D77_PREFERRED_THROUGH = 2020


def _is_year(label: str) -> bool:
    s = label.strip()
    return len(s) == 4 and s.isdigit() and 1900 <= int(s) <= 2099


def _parse_month(label: str) -> int | None:
    """Parse a WONDER month label like 'Jan', 'February', '01', etc."""
    label = label.strip()
    # Try short name (Jan, Feb, ...)
    if label[:3] in MONTH_NAMES:
        return MONTH_NAMES[label[:3]]
    # Try numeric string
    try:
        m = int(label)
        if 1 <= m <= 12:
            return m
    except ValueError:
        pass
    return None


def parse_rows(client: WonderClient, xml: str, provisional: bool) -> list[dict]:
    """
    Parse Year × Month response from D77 (hierarchical) or D176 (flat).

    D77 uses hierarchical rows: the year only appears in the first sub-row of
    each year group; subsequent month sub-rows omit the year column.

        First sub-row:      cell[0].label=year  cell[1].label=month  cell[2].value=deaths
        Subsequent sub-rows: cell[0].label=month  cell[1].value=deaths  (no year cell)

    D176 uses the same hierarchical format.

    Suppressed months (< 10 deaths) have no numeric value and are included with
    deaths=None so callers can decide how to handle them.
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
            # First sub-row for this year: [Year, Month, Deaths, ...]
            current_year = int(c0_label)
            if len(cells) < 3:
                continue
            month_label = (cells[1].label or "").strip()
            deaths = cells[2].get_numeric_value()
        else:
            # Continuation sub-row: [Month, Deaths, ...]
            if current_year is None:
                continue
            month_label = c0_label
            if len(cells) < 2:
                continue
            deaths = cells[1].get_numeric_value()

        month = _parse_month(month_label)
        if month is None:
            continue

        records.append({
            "year": current_year,
            "month": month,
            "deaths": deaths,
            "provisional": provisional,
        })
    return records


def run_query(client: WonderClient, dataset_id: str, query_file: Path, provisional: bool) -> list[dict]:
    print(f"  → [{dataset_id}] {query_file.name} …", flush=True)
    try:
        xml = client.execute_query_file(str(query_file))
    except RuntimeError as exc:
        print(f"    ERROR: {exc}", file=sys.stderr)
        return []

    records = parse_rows(client, xml, provisional)
    years = sorted({r["year"] for r in records})
    if years:
        print(f"    {len(records)} rows  |  years {years[0]}–{years[-1]}", flush=True)
    else:
        print("    0 rows", flush=True)
    return records


def merge(d77_records: list[dict], d176_records: list[dict]) -> list[dict]:
    """Use D77 for 1999–2020 (final); D176 for 2021+ (provisional)."""
    combined: dict[tuple[int, int], dict] = {}

    for rec in d77_records:
        if rec["year"] <= D77_PREFERRED_THROUGH:
            combined[(rec["year"], rec["month"])] = rec

    for rec in d176_records:
        if rec["year"] > D77_PREFERRED_THROUGH:
            combined[(rec["year"], rec["month"])] = rec

    return sorted(combined.values(), key=lambda r: (r["year"], r["month"]))


def write_csv(records: list[dict], out_path: Path) -> None:
    years = sorted({r["year"] for r in records})
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "month", "deaths", "provisional"])
        for rec in records:
            writer.writerow([
                rec["year"],
                rec["month"],
                "" if rec["deaths"] is None else int(rec["deaths"]),
                str(rec["provisional"]).lower(),
            ])
    print(f"  ✓ {out_path.name}  ({len(records)} rows  |  years {years[0]}–{years[-1]})")


def main() -> None:
    client = WonderClient(timeout=120)
    print("Fetching fentanyl (T40.4) death data from CDC WONDER …\n")

    d77_records: list[dict] = []
    d176_records: list[dict] = []

    queries = [
        ("D77",  QUERIES_DIR / "fentanyl-deaths-by-month-1999-2020-req.xml",  False),
        ("D176", QUERIES_DIR / "fentanyl-deaths-by-month-2018-2024-req.xml",  True),
    ]

    for i, (ds_id, qfile, provisional) in enumerate(queries):
        if i > 0:
            print(f"  (waiting {RATE_LIMIT_SLEEP}s for rate limit …)", flush=True)
            time.sleep(RATE_LIMIT_SLEEP)

        records = run_query(client, ds_id, qfile, provisional)
        if ds_id == "D77":
            d77_records = records
        else:
            d176_records = records

    if not d77_records and not d176_records:
        print("\nNo data returned — check errors above.", file=sys.stderr)
        sys.exit(1)

    print(f"\nMerging: D77 for 1999–{D77_PREFERRED_THROUGH}, D176 for {D77_PREFERRED_THROUGH + 1}+")
    merged = merge(d77_records, d176_records)
    print(f"Total merged rows: {len(merged)}")

    print("\nWriting output …")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(merged, OUTPUT_DIR / "fentanyl-deaths-by-month.csv")

    years = sorted({r["year"] for r in merged})
    print(f"\n── Annual T40.4 deaths ({years[0]}–{years[-1]}) ────────────────────────")
    annual: dict[int, int] = {}
    for rec in merged:
        if rec["deaths"] is not None:
            annual[rec["year"]] = annual.get(rec["year"], 0) + int(rec["deaths"])
    for year in sorted(annual):
        prov = " (provisional)" if any(r["year"] == year and r["provisional"] for r in merged) else ""
        print(f"  {year}: {annual[year]:>6}{prov}")

    print("\nDone.")


if __name__ == "__main__":
    main()
