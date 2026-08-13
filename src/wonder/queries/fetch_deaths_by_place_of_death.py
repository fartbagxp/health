"""
US Deaths by Place of Death and Month, National (2018–present)

Queries CDC WONDER dataset:
  D176 — Provisional Mortality Statistics, 2018 through Last Week (provisional)

Groups by Year × Month × Place of Death (D176.V21), covering all causes of
death, restricted to none of the usual cause filters.

Place of death categories (D176.V21):
  Medical Facility - Inpatient
  Medical Facility - Outpatient or ER
  Medical Facility - Dead on Arrival
  Medical Facility - Status unknown
  Decedent's home
  Hospice facility
  Nursing home/long term care
  Other
  Place of death unknown

With 3 group-by dimensions, WONDER returns flat rows — each row carries all
three labels explicitly. Month label format is "Jan., 2018".

Suppression note: CDC WONDER suppresses counts < 10. Suppressed rows are
written with an empty deaths value.

Output:
  data/raw/wonder/deaths-by-place-of-death.csv
    year      – calendar year (integer)
    month     – month number 1-12 (integer)
    place     – place of death category (human-readable)
    deaths    – death count (integer, blank if suppressed)

Usage:
    uv run python src/wonder/queries/fetch_deaths_by_place_of_death.py
"""

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from wonder.client import WonderClient

QUERIES_DIR = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "wonder"

QUERY_FILE = QUERIES_DIR / "deaths-by-place-of-death-2018-2024-req.xml"

MONTH_ABBR = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def _is_year(label: str) -> bool:
    s = label.strip()
    return len(s) == 4 and s.isdigit() and 1900 <= int(s) <= 2099


def _parse_month(label: str) -> int | None:
    """Parse month number from labels like 'Jan., 2018'."""
    s = label.strip()
    abbr = s[:3].capitalize()
    return MONTH_ABBR.get(abbr)


def parse_rows(client: WonderClient, xml: str) -> list[dict]:
    """
    Parse Year × Month × Place-of-death response (flat format).

    With 3 group-by dimensions, WONDER returns fully flat rows — every row
    has all three labels present:
        cells[0].label = Year   (e.g. "2018")
        cells[1].label = Month  (e.g. "Jan., 2018")
        cells[2].label = Place of death (e.g. "Decedent's home")
        cells[3].value = Deaths count or "Suppressed"
    """
    rows = client.parse_response_table(xml)
    records = []

    for row in rows:
        if row.is_total:
            continue
        cells = row.cells
        if len(cells) < 4:
            continue

        year_label = (cells[0].label or "").strip()
        if not _is_year(year_label):
            continue
        year = int(year_label)

        month = _parse_month((cells[1].label or "").strip())
        if month is None:
            continue

        place = (cells[2].label or "").strip()
        if not place:
            continue

        deaths = cells[3].get_numeric_value()

        records.append(
            {
                "year": year,
                "month": month,
                "place": place,
                "deaths": deaths,
            }
        )
    return records


def run_query(client: WonderClient, query_file: Path) -> list[dict]:
    print(f"  → [D176] {query_file.name} …", flush=True)
    try:
        xml = client.execute_query_file(str(query_file))
    except RuntimeError as exc:
        print(f"    ERROR: {exc}", file=sys.stderr)
        return []

    records = parse_rows(client, xml)
    years = sorted({r["year"] for r in records})
    places = sorted({r["place"] for r in records})
    if years:
        print(
            f"    {len(records)} rows  |  years {years[0]}–{years[-1]}  |  places {places}",
            flush=True,
        )
    else:
        print("    0 rows", flush=True)
    return records


def write_csv(records: list[dict], out_path: Path) -> None:
    years = sorted({r["year"] for r in records})
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "month", "place", "deaths"])
        for rec in sorted(records, key=lambda r: (r["year"], r["month"], r["place"])):
            writer.writerow(
                [
                    rec["year"],
                    rec["month"],
                    rec["place"],
                    "" if rec["deaths"] is None else int(rec["deaths"]),
                ]
            )
    print(
        f"  ✓ {out_path.name}  ({len(records)} rows  |  years {years[0]}–{years[-1]})"
    )


def main() -> None:
    client = WonderClient(timeout=120)
    print("Fetching deaths by place of death from CDC WONDER …\n")

    records = run_query(client, QUERY_FILE)

    if not records:
        print("\nNo data returned — check errors above.", file=sys.stderr)
        sys.exit(1)

    print("\nWriting output …")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(records, OUTPUT_DIR / "deaths-by-place-of-death.csv")
    print("\nDone.")


if __name__ == "__main__":
    main()
