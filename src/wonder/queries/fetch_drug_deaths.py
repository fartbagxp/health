"""
US Drug Deaths by Substance and Year, National (1999–present)

Queries two CDC WONDER datasets:
  D77  — Multiple Cause of Death, 1999–2020 (ICD-10, bridged-race, final)
  D176 — Provisional Mortality Statistics, 2018 through Last Week (provisional)

Both queries group by Year × MCD drug code (V13-level3) and restrict to seven
specific Multiple Cause of Death codes:

  T40.1  Heroin
  T40.2  Other opioids (natural & semi-synthetic: oxycodone, hydrocodone, etc.)
  T40.3  Methadone
  T40.4  Other synthetic narcotics (fentanyl and analogues)
  T40.5  Cocaine
  T40.7  Cannabis (derivatives)
  T43.6  Psychostimulants with abuse potential (methamphetamine, amphetamines, MDMA)

These are Multiple Cause of Death codes — the drug appears anywhere on the
death certificate, not necessarily as the underlying cause. This methodology
is consistent with how the CDC tracks drug-specific overdose involvement
(see CDC VSRR Drug Overdose Surveillance).

Merge strategy: D77 for 1999–2020 (final); D176 for 2021–present (provisional).

Suppression note: CDC WONDER suppresses counts < 10. Cannabis (T40.7) deaths
are extremely rare; most years before ~2016 are suppressed.

Output:
  data/raw/wonder/drug-deaths-by-year.csv
    year        – calendar year (integer)
    drug_code   – ICD-10 T/X code (e.g. T40.5)
    drug_name   – human-readable substance label
    deaths      – death count (integer, blank if suppressed)
    provisional – true if from D176 provisional data, false if D77 final

Usage:
    uv run python src/wonder/queries/fetch_drug_deaths.py
"""

import argparse
import csv
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from wonder.client import WonderClient  # noqa: E402

QUERIES_DIR = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "wonder"

# The chart consumes this merged file.
OUTPUT_CSV = "drug-deaths-by-year.csv"

# The D77 half (1999–2020) is FINAL data — CDC will not revise it — so we cache
# it here once and reuse it on subsequent runs instead of re-querying WONDER.
# That keeps the historical era out of harm's way (a failed/rate-limited fetch
# can never shrink it) and halves per-run WONDER load. Refresh with
# --refresh-final if CDC ever restates the historical series.
FINAL_CACHE_CSV = "drug-deaths-by-year-final-1999-2020.csv"

RATE_LIMIT_SLEEP = 16

# WONDER returns drug names as row labels (not ICD codes).
# Map from the label WONDER uses → (ICD code, canonical name).
WONDER_LABEL_TO_CODE: dict[str, tuple[str, str]] = {
    "Heroin":                                    ("T40.1", "Heroin"),
    "Other opioids":                             ("T40.2", "Other opioids (natural & semi-synthetic)"),
    "Methadone":                                 ("T40.3", "Methadone"),
    "Other synthetic narcotics":                 ("T40.4", "Synthetic opioids excl. methadone (fentanyl)"),
    "Cocaine":                                   ("T40.5", "Cocaine"),
    "Cannabis (derivatives)":                    ("T40.7", "Cannabis"),
    "Psychostimulants with abuse potential":     ("T43.6", "Psychostimulants (methamphetamine, amphetamines, MDMA)"),
}

D77_PREFERRED_THROUGH = 2020


def _is_year(label: str) -> bool:
    s = label.strip()
    return len(s) == 4 and s.isdigit() and 1900 <= int(s) <= 2099


def _parse_drug_label(label: str) -> tuple[str, str] | None:
    """
    Map a WONDER drug name label to (icd_code, canonical_name).
    Returns None if the label is not one of the queried drugs.
    """
    return WONDER_LABEL_TO_CODE.get(label.strip())


def parse_rows(client: WonderClient, xml: str, provisional: bool) -> list[dict]:
    """
    Parse Year × MCD drug-code response (hierarchical format).

    D77 / D176 use hierarchical rows when grouped by Year × something:
        First sub-row:       cell[0].label=Year   cell[1].label=DrugCode  cell[2].value=Deaths
        Subsequent sub-rows: cell[0].label=DrugCode  cell[1].value=Deaths
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
            current_year = int(c0_label)
            if len(cells) < 3:
                continue
            drug_label = (cells[1].label or "").strip()
            deaths = cells[2].get_numeric_value()
        else:
            if current_year is None:
                continue
            drug_label = c0_label
            if len(cells) < 2:
                continue
            deaths = cells[1].get_numeric_value()

        parsed = _parse_drug_label(drug_label)
        if parsed is None:
            continue
        drug_code, drug_name = parsed

        records.append({
            "year": current_year,
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
        print(f"    {len(records)} rows  |  years {years[0]}–{years[-1]}  |  drugs {drugs}", flush=True)
    else:
        print("    0 rows", flush=True)
    return records


def merge(d77: list[dict], d176: list[dict]) -> list[dict]:
    """Use D77 for 1999–2020 (final); D176 for 2021+ (provisional)."""
    combined: dict[tuple, dict] = {}
    for rec in d77:
        if rec["year"] <= D77_PREFERRED_THROUGH:
            combined[(rec["year"], rec["drug_code"])] = rec
    for rec in d176:
        if rec["year"] > D77_PREFERRED_THROUGH:
            combined[(rec["year"], rec["drug_code"])] = rec
    return sorted(combined.values(), key=lambda r: (r["year"], r["drug_code"]))


def write_csv(records: list[dict], out_path: Path) -> None:
    years = sorted({r["year"] for r in records})
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "drug_code", "drug_name", "deaths", "provisional"])
        for rec in records:
            writer.writerow([
                rec["year"],
                rec["drug_code"],
                rec["drug_name"],
                "" if rec["deaths"] is None else int(rec["deaths"]),
                str(rec["provisional"]).lower(),
            ])
    print(f"  ✓ {out_path.name}  ({len(records)} rows  |  years {years[0]}–{years[-1]})")


def read_csv(path: Path) -> list[dict]:
    """Read a previously-written drug-deaths CSV back into records."""
    records = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            deaths = row["deaths"].strip()
            records.append({
                "year": int(row["year"]),
                "drug_code": row["drug_code"],
                "drug_name": row["drug_name"],
                "deaths": None if deaths == "" else int(deaths),
                "provisional": row["provisional"].strip().lower() == "true",
            })
    return records


def print_summary(records: list[dict]) -> None:
    code_to_name = {code: name for _, (code, name) in WONDER_LABEL_TO_CODE.items()}
    drugs = sorted(code_to_name.keys())
    years = sorted({r["year"] for r in records})
    lookup = {(r["year"], r["drug_code"]): r for r in records}

    col_w = 12
    header = f"{'Year':<6}" + "".join(f"{code_to_name.get(d, d)[:col_w]:>{col_w}}" for d in drugs)
    print(header)
    print("-" * len(header))
    for yr in years:
        row = f"{yr:<6}"
        for d in drugs:
            rec = lookup.get((yr, d))
            if rec is None:
                val = "—"
            elif rec["deaths"] is None:
                val = "Supp."
            else:
                val = f"{int(rec['deaths']):,}"
            row += f"{val:>{col_w}}"
        prov = " *" if any(lookup.get((yr, d), {}).get("provisional") for d in drugs) else ""
        print(row + prov)
    print("\n* provisional")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh-final",
        action="store_true",
        help="Re-query WONDER for the final 1999–2020 data instead of reusing "
             "the cached snapshot (use only if CDC restates the historical series).",
    )
    args = parser.parse_args()

    client = WonderClient(timeout=120)
    print("Fetching drug deaths by substance from CDC WONDER …\n")

    final_cache = OUTPUT_DIR / FINAL_CACHE_CSV
    d77_from_cache = final_cache.exists() and not args.refresh_final

    d77_records: list[dict] = []
    d176_records: list[dict] = []

    # D77 (final, 1999–2020) — load the cached snapshot when we have one; only
    # hit WONDER when the cache is missing or --refresh-final was requested.
    if d77_from_cache:
        d77_records = read_csv(final_cache)
        yrs = sorted({r["year"] for r in d77_records})
        print(
            f"  → [D77] reusing cache {final_cache.name} "
            f"({len(d77_records)} rows  |  years {yrs[0]}–{yrs[-1]})",
            flush=True,
        )
    else:
        d77_records = run_query(
            client, "D77", QUERIES_DIR / "drug-deaths-by-year-1999-2020-req.xml", False
        )
        print(f"  (waiting {RATE_LIMIT_SLEEP}s for rate limit …)", flush=True)
        time.sleep(RATE_LIMIT_SLEEP)

    # D176 (provisional, 2021+) — always re-fetched; these counts get revised.
    d176_records = run_query(
        client, "D176", QUERIES_DIR / "drug-deaths-by-year-2018-2024-req.xml", True
    )

    # Validate each half independently. A partial failure (e.g. one query
    # hitting a WONDER 429 and returning []) must abort rather than silently
    # write a truncated CSV — otherwise the merged output loses an entire era
    # of data with no error. See the D77-drops-out truncation bug.
    problems: list[str] = []

    d77_years = {r["year"] for r in d77_records}
    if not d77_records:
        problems.append("D77 (final, 1999–2020) returned no rows")
    elif D77_PREFERRED_THROUGH not in d77_years:
        problems.append(
            f"D77 (final) is missing year {D77_PREFERRED_THROUGH}; "
            f"got {min(d77_years)}–{max(d77_years)}"
        )

    d176_years = {r["year"] for r in d176_records}
    if not d176_records:
        problems.append("D176 (provisional, 2021+) returned no rows")
    elif not any(y > D77_PREFERRED_THROUGH for y in d176_years):
        problems.append(
            f"D176 (provisional) has no year past {D77_PREFERRED_THROUGH}; "
            f"got {min(d176_years)}–{max(d176_years)}"
        )

    if problems:
        print(
            "\nAborting — incomplete fetch, refusing to write a truncated CSV:",
            file=sys.stderr,
        )
        for p in problems:
            print(f"  • {p}", file=sys.stderr)
        print("Check errors above (WONDER rate-limits with HTTP 429).", file=sys.stderr)
        sys.exit(1)

    print(f"\nMerging: D77 for 1999–{D77_PREFERRED_THROUGH}, D176 for {D77_PREFERRED_THROUGH + 1}+")
    merged = merge(d77_records, d176_records)
    print(f"Total merged rows: {len(merged)}\n")

    print("\nWriting output …")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Persist the final snapshot when it came fresh from WONDER (and validated),
    # so future runs can reuse it without re-querying.
    if not d77_from_cache:
        write_csv([r for r in d77_records if r["year"] <= D77_PREFERRED_THROUGH], final_cache)
    write_csv(merged, OUTPUT_DIR / OUTPUT_CSV)

    print("\n── Deaths by substance and year (all intents, MCD) ──────────────────")
    print_summary(merged)
    print("\nDone.")


if __name__ == "__main__":
    main()
