"""
US Drug Deaths by Substance and Month, National (1999–present)

Queries two CDC WONDER datasets:
  D77  — Multiple Cause of Death, 1999–2020 (ICD-10, bridged-race, final)
  D176 — Provisional Mortality Statistics, 2018 through Last Week (provisional)

Both queries group by Year × Month × MCD drug code (V13-level3), restricted to
seven specific Multiple Cause of Death codes:

  T40.1  Heroin
  T40.2  Other opioids (natural & semi-synthetic: oxycodone, hydrocodone, etc.)
  T40.3  Methadone
  T40.4  Other synthetic narcotics (fentanyl and analogues)
  T40.5  Cocaine
  T40.7  Cannabis (derivatives)
  T43.6  Psychostimulants with abuse potential (methamphetamine, amphetamines, MDMA)

These are Multiple Cause of Death codes — the drug appears anywhere on the death
certificate, not necessarily as the underlying cause.

With 3 group-by dimensions, WONDER returns flat rows — each row carries all three
labels (Year, Month, Drug) explicitly. Month label format is "Jan., 1999".

Merge strategy: D77 for 1999–2020 (final); D176 for 2021–present (provisional).

Suppression note: CDC WONDER suppresses counts < 10. Cannabis (T40.7) deaths are
extremely rare; many months are suppressed. Suppressed rows are written with an
empty deaths value.

Output:
  data/raw/wonder/drug-deaths-by-month.csv
    year        – calendar year (integer)
    month       – month number 1–12 (integer)
    drug_code   – ICD-10 T/X code (e.g. T40.5)
    drug_name   – human-readable substance label
    deaths      – death count (integer, blank if suppressed)
    provisional – true if from D176 provisional data, false if D77 final

Usage:
    uv run python src/wonder/queries/fetch_drug_deaths_monthly.py
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

WONDER_LABEL_TO_CODE: dict[str, tuple[str, str]] = {
    "Heroin":                                    ("T40.1", "Heroin"),
    "Other opioids":                             ("T40.2", "Other opioids (natural & semi-synthetic)"),
    "Methadone":                                 ("T40.3", "Methadone"),
    "Other synthetic narcotics":                 ("T40.4", "Synthetic opioids excl. methadone (fentanyl)"),
    "Cocaine":                                   ("T40.5", "Cocaine"),
    "Cannabis (derivatives)":                    ("T40.7", "Cannabis"),
    "Psychostimulants with abuse potential":     ("T43.6", "Psychostimulants (methamphetamine, amphetamines, MDMA)"),
}

MONTH_ABBR = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,  "May": 5,  "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

D77_PREFERRED_THROUGH = 2020


def _is_year(label: str) -> bool:
    s = label.strip()
    return len(s) == 4 and s.isdigit() and 1900 <= int(s) <= 2099


def _parse_month(label: str) -> int | None:
    """Parse month number from labels like 'Jan., 1999' or 'January' or 'Jan'."""
    s = label.strip()
    abbr = s[:3].capitalize()
    return MONTH_ABBR.get(abbr)


def parse_rows(client: WonderClient, xml: str, provisional: bool) -> list[dict]:
    """
    Parse Year × Month × MCD drug-code response (flat format).

    With 3 group-by dimensions, WONDER returns fully flat rows — every row has
    all three labels present:
        cells[0].label = Year  (e.g. "1999")
        cells[1].label = Month (e.g. "Jan., 1999")
        cells[2].label = Drug  (e.g. "Heroin")
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

        drug_label = (cells[2].label or "").strip()
        parsed = WONDER_LABEL_TO_CODE.get(drug_label)
        if parsed is None:
            continue
        drug_code, drug_name = parsed

        deaths = cells[3].get_numeric_value()

        records.append({
            "year": year,
            "month": month,
            "drug_code": drug_code,
            "drug_name": drug_name,
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
    drugs = sorted({r["drug_code"] for r in records})
    if years:
        months = sorted({(r["year"], r["month"]) for r in records})
        print(
            f"    {len(records)} rows  |  years {years[0]}–{years[-1]}"
            f"  |  {len(months)} year-months  |  drugs {drugs}",
            flush=True,
        )
    else:
        print("    0 rows", flush=True)
    return records


def merge(d77: list[dict], d176: list[dict]) -> list[dict]:
    """Use D77 for 1999–2020 (final); D176 for 2021+ (provisional)."""
    combined: dict[tuple, dict] = {}
    for rec in d77:
        if rec["year"] <= D77_PREFERRED_THROUGH:
            combined[(rec["year"], rec["month"], rec["drug_code"])] = rec
    for rec in d176:
        if rec["year"] > D77_PREFERRED_THROUGH:
            combined[(rec["year"], rec["month"], rec["drug_code"])] = rec
    return sorted(combined.values(), key=lambda r: (r["year"], r["month"], r["drug_code"]))


def write_csv(records: list[dict], out_path: Path) -> None:
    years = sorted({r["year"] for r in records})
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "month", "drug_code", "drug_name", "deaths", "provisional"])
        for rec in records:
            writer.writerow([
                rec["year"],
                rec["month"],
                rec["drug_code"],
                rec["drug_name"],
                "" if rec["deaths"] is None else int(rec["deaths"]),
                str(rec["provisional"]).lower(),
            ])
    print(f"  ✓ {out_path.name}  ({len(records)} rows  |  years {years[0]}–{years[-1]})")


def main() -> None:
    client = WonderClient(timeout=120)
    print("Fetching drug deaths by substance and month from CDC WONDER …\n")

    queries = [
        ("D77",  QUERIES_DIR / "drug-deaths-by-month-1999-2020-req.xml",  False),
        ("D176", QUERIES_DIR / "drug-deaths-by-month-2018-2024-req.xml",  True),
    ]

    d77_records: list[dict] = []
    d176_records: list[dict] = []

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
    print(f"Total merged rows: {len(merged)}\n")

    print("Writing output …")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(merged, OUTPUT_DIR / "drug-deaths-by-month.csv")
    print("\nDone.")


if __name__ == "__main__":
    main()
