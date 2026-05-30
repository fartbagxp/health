"""
Tick-Borne Disease Cases by Year and Disease (2016–2023)

Source: CDC WONDER — NNDSS Annual Summary Data (D130)

Diseases covered:
  Babesiosis (Total, Confirmed, Probable)
  Ehrlichiosis and Anaplasmosis (Anaplasma phagocytophilum, Ehrlichia
    chaffeensis, Ehrlichia ewingii, Undetermined)
  Lyme disease (Total, Confirmed, Probable)
  Spotted fever rickettsiosis (Total, Confirmed, Probable)
  Tularemia
  Powassan virus disease (Neuroinvasive, Non-neuroinvasive)

Response format: hierarchical rows — year only appears in cell[0] of the
first disease sub-row for each year; subsequent sub-rows omit the year.

Outputs:
  tick-borne-diseases-by-year.csv   — year, disease, cases (long format)

Usage:
    uv run python src/wonder/queries/fetch_tick_borne_diseases.py
"""

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from wonder.client import WonderClient  # noqa: E402

QUERY_FILE = Path(__file__).parent / "tick-borne-diseases-by-year-2016-2023-req.xml"
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "wonder"


def _is_year(label: str) -> bool:
    s = label.strip()
    return len(s) == 4 and s.isdigit() and 1900 <= int(s) <= 2099


def parse(client: WonderClient, xml: str) -> list[dict]:
    """
    Hierarchical row parser: carry the year forward when cell[0] is a
    disease name rather than a year.

        First sub-row:  cell[0]=year  cell[1]=disease  cell[2]=cases
        Later sub-rows: cell[0]=disease  cell[1]=cases
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

        c0 = (cells[0].label or "").strip()

        if _is_year(c0):
            current_year = int(c0)
            if len(cells) < 3:
                continue
            disease = (cells[1].label or "").strip()
            cases = cells[2].get_numeric_value()
        else:
            if current_year is None:
                continue
            disease = c0
            if len(cells) < 2:
                continue
            cases = cells[1].get_numeric_value()

        if not disease or cases is None:
            continue
        records.append({"year": current_year, "disease": disease, "cases": int(cases)})

    return records


def main() -> None:
    client = WonderClient(timeout=60)

    print("Fetching tick-borne disease data from CDC WONDER (D130) …")
    try:
        xml = client.execute_query_file(str(QUERY_FILE))
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    records = parse(client, xml)
    years = sorted({r["year"] for r in records})
    diseases = sorted({r["disease"] for r in records})
    print(
        f"  {len(records)} rows  |  years {years[0]}–{years[-1]}  |  {len(diseases)} diseases"
    )

    out = OUTPUT_DIR / "tick-borne-diseases-by-year.csv"
    with open(out, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "disease", "cases"])
        for r in records:
            writer.writerow([r["year"], r["disease"], r["cases"]])
    print(f"  ✓ Wrote {out.name}")

    # ── Preview ────────────────────────────────────────────────────────────────
    # Show Total/aggregate rows only to avoid double-counting
    TOTALS = {
        "Lyme disease, Total",
        "Babesiosis, Total",
        "Spotted fever rickettsiosis, Total",
        "Ehrlichiosis and Anaplasmosis, Anaplasma phagocytophilum infection",
        "Ehrlichiosis and Anaplasmosis, Ehrlichia chaffeensis infection",
        "Ehrlichiosis and Anaplasmosis, Ehrlichia ewingii infection",
        "Ehrlichiosis and Anaplasmosis, Undetermined ehrlichiosis/anaplasmosis",
        "Tularemia",
        "Arboviral diseases, Powassan virus disease, Neuroinvasive",
        "Arboviral diseases, Powassan virus disease, Non-neuroinvasive",
    }

    # Build {disease: {year: cases}} for totals
    from collections import defaultdict

    table: dict[str, dict[int, int]] = defaultdict(dict)
    for r in records:
        if r["disease"] in TOTALS:
            table[r["disease"]][r["year"]] = r["cases"]

    col_w = 60
    yr_w = 7
    print()
    print(f"\n{'Disease':<{col_w}}" + "".join(f"{y:>{yr_w}}" for y in years))
    print("-" * (col_w + yr_w * len(years)))

    display_order = [
        "Lyme disease, Total",
        "Spotted fever rickettsiosis, Total",
        "Ehrlichiosis and Anaplasmosis, Anaplasma phagocytophilum infection",
        "Ehrlichiosis and Anaplasmosis, Ehrlichia chaffeensis infection",
        "Ehrlichiosis and Anaplasmosis, Ehrlichia ewingii infection",
        "Ehrlichiosis and Anaplasmosis, Undetermined ehrlichiosis/anaplasmosis",
        "Babesiosis, Total",
        "Tularemia",
        "Arboviral diseases, Powassan virus disease, Neuroinvasive",
        "Arboviral diseases, Powassan virus disease, Non-neuroinvasive",
    ]

    for disease in display_order:
        yr_data = table.get(disease, {})
        row_str = f"{disease:<{col_w}}"
        for y in years:
            v = yr_data.get(y)
            row_str += f"{v:>{yr_w},}" if v is not None else f"{'N/A':>{yr_w}}"
        print(row_str)

    print()
    print("Done.")


if __name__ == "__main__":
    main()
