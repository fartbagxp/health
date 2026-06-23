"""
U.S. Suicide Deaths by Sex, 1999–2024

Combines three sources into data/raw/wisqars/suicide_by_sex.csv:
  1. data/raw/wisqars/injury_mortality.csv  — 1999–2016 (NCHS/WISQARS Socrata)
  2. CDC WONDER D77  — 2017–2020 (UCD X60-X84, Y87.0, grouped by year × sex)
  3. CDC WONDER D176 — 2021–2024 (same filter, provisional)

Output columns:
  year, sex, deaths, population, crude_rate

Sex values: "Male", "Female", "Both sexes"

Usage:
    uv run python src/wonder/queries/fetch_suicide_by_sex.py
"""

import csv
import sys
import time
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from wonder.client import WonderClient  # noqa: E402

QUERIES_DIR = Path(__file__).parent
OUTPUT_PATH = PROJECT_ROOT / "data" / "raw" / "wisqars" / "suicide_by_sex.csv"
INJURY_MORTALITY_PATH = PROJECT_ROOT / "data" / "raw" / "wisqars" / "injury_mortality.csv"

RATE_LIMIT_SLEEP = 16


# ── Source 1: derive 1999-2016 from injury_mortality.csv ─────────────────────

def load_injury_mortality() -> list[dict]:
    """Sum age-specific suicide deaths and population by year × sex (1999-2016)."""
    totals: dict[tuple, dict] = defaultdict(lambda: {"deaths": 0, "population": 0})
    with open(INJURY_MORTALITY_PATH) as f:
        for row in csv.DictReader(f):
            if (
                row["injury_intent"] != "Suicide"
                or row["race"] != "All races"
                or row["injury_mechanism"] != "All Mechanisms"
            ):
                continue
            key = (int(row["year"]), row["sex"])
            totals[key]["deaths"] += int(row["deaths"]) if row["deaths"] else 0
            totals[key]["population"] += int(row["population"]) if row["population"] else 0

    records = []
    for (year, sex), v in totals.items():
        rate = v["deaths"] / v["population"] * 100_000 if v["population"] else 0
        records.append({"year": year, "sex": sex, "deaths": v["deaths"],
                        "population": v["population"], "crude_rate": round(rate, 2)})
    years = sorted({r["year"] for r in records})
    print(f"  injury_mortality.csv: {len(records)} rows  |  years {years[0]}–{years[-1]}")
    return records


# ── Source 2 & 3: parse flat WONDER responses (Year × Sex grouping) ───────────

def _is_year(label: str) -> bool:
    s = label.strip()
    return len(s) == 4 and s.isdigit() and 1900 <= int(s) <= 2099


SEX_LABELS = {"Male", "Female", "Both sexes"}


def parse_wonder_by_sex(client: WonderClient, xml: str, year_range: str) -> list[dict]:
    """
    Parse a WONDER response grouped by Year (B_1) × Sex (B_2).

    Cell layout per data row:
        cell[0].label — Year
        cell[1].label — Sex ("Male", "Female", "Both sexes")
        cell[2].value — Deaths
        cell[3].value — Population
        cell[4].value — Crude Rate
    """
    rows = client.parse_response_table(xml)
    records = []
    current_year: int | None = None

    for row in rows:
        if row.is_total:
            continue
        cells = row.cells
        if len(cells) < 3:
            continue

        c0 = (cells[0].label or "").strip()
        c1 = (cells[1].label or "").strip() if len(cells) > 1 else ""

        # WONDER sometimes emits hierarchical rows where the year appears only on
        # the first sub-row; subsequent sub-rows shift left (sex in cell[0]).
        if _is_year(c0):
            current_year = int(c0)
            sex_label = c1
            deaths_cell = cells[2] if len(cells) > 2 else None
            pop_cell = cells[3] if len(cells) > 3 else None
            rate_cell = cells[4] if len(cells) > 4 else None
        elif c0 in SEX_LABELS:
            # Continuation: [sex, deaths, pop, rate, ...]
            if current_year is None:
                continue
            sex_label = c0
            deaths_cell = cells[1] if len(cells) > 1 else None
            pop_cell = cells[2] if len(cells) > 2 else None
            rate_cell = cells[3] if len(cells) > 3 else None
        else:
            continue

        if sex_label not in SEX_LABELS:
            continue

        deaths = deaths_cell.get_numeric_value() if deaths_cell else None
        population = pop_cell.get_numeric_value() if pop_cell else None
        crude_rate_raw = rate_cell.get_numeric_value() if rate_cell else None

        if deaths is None:
            continue

        crude_rate = (
            crude_rate_raw if crude_rate_raw is not None
            else (deaths / population * 100_000 if population else 0)
        )

        records.append({
            "year": current_year,
            "sex": sex_label,
            "deaths": int(deaths),
            "population": int(population) if population else 0,
            "crude_rate": round(crude_rate, 2),
        })

    years = sorted({r["year"] for r in records})
    rng = f"{years[0]}–{years[-1]}" if years else "none"
    print(f"    {len(records)} rows  |  years {rng}")
    return records


def run_wonder_query(client: WonderClient, query_file: Path, label: str) -> list[dict]:
    print(f"  → [{label}] {query_file.name} …", flush=True)
    try:
        xml = client.execute_query_file(str(query_file))
    except RuntimeError as exc:
        print(f"    ERROR: {exc}", file=sys.stderr)
        return []
    return parse_wonder_by_sex(client, xml, label)


# ── Merge and deduplicate ─────────────────────────────────────────────────────

def add_both_sexes(records: list[dict]) -> list[dict]:
    """For years that have Male + Female but no 'Both sexes', compute it."""
    by_year: dict[int, dict[str, dict]] = {}
    for r in records:
        by_year.setdefault(r["year"], {})[r["sex"]] = r
    extra = []
    for year, sexes in by_year.items():
        if "Both sexes" in sexes:
            continue
        if "Male" in sexes and "Female" in sexes:
            m, f = sexes["Male"], sexes["Female"]
            total_deaths = m["deaths"] + f["deaths"]
            total_pop = m["population"] + f["population"]
            rate = total_deaths / total_pop * 100_000 if total_pop else 0
            extra.append({
                "year": year,
                "sex": "Both sexes",
                "deaths": total_deaths,
                "population": total_pop,
                "crude_rate": round(rate, 2),
            })
    return records + extra


def merge(all_records: list[dict]) -> list[dict]:
    """Merge by (year, sex), keeping the last-seen value (later sources win)."""
    seen: dict[tuple, dict] = {}
    for r in all_records:
        seen[(r["year"], r["sex"])] = r
    return sorted(seen.values(), key=lambda r: (r["year"], r["sex"]))


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Building U.S. suicide deaths by sex (1999–2024) …\n")

    all_records: list[dict] = []

    # 1. Local data (1999-2016)
    print("[1/3] Loading injury_mortality.csv …")
    all_records.extend(load_injury_mortality())

    client = WonderClient(timeout=120)

    # 2. WONDER D77 (1999-2020; only 2017-2020 are new, but querying full range
    #    gives a cross-check on the 1999-2016 numbers)
    print("\n[2/3] Querying WONDER D77 (1999–2020, suicide by sex) …")
    records_d77 = run_wonder_query(
        client,
        QUERIES_DIR / "suicide-by-sex-1999-2020-req.xml",
        "D77",
    )
    all_records.extend(records_d77)

    print(f"  (waiting {RATE_LIMIT_SLEEP}s for WONDER rate limit …)", flush=True)
    time.sleep(RATE_LIMIT_SLEEP)

    # 3. WONDER D176 (2021-2024, provisional)
    print("\n[3/3] Querying WONDER D176 (2021–2024, suicide by sex) …")
    records_d176 = run_wonder_query(
        client,
        QUERIES_DIR / "suicide-by-sex-2021-2024-req.xml",
        "D176",
    )
    all_records.extend(records_d176)

    if not all_records:
        print("\nNo data returned.", file=sys.stderr)
        sys.exit(1)

    all_records = add_both_sexes(all_records)
    merged = merge(all_records)
    years = sorted({r["year"] for r in merged})
    print(f"\nMerged: {len(merged)} rows  |  years {years[0]}–{years[-1]}\n")

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "sex", "deaths", "population", "crude_rate"])
        writer.writeheader()
        writer.writerows(merged)

    print(f"✓ Wrote {OUTPUT_PATH}")

    # Preview
    print("\n── Crude rate per 100,000 (most recent 6 years) ─────────────────")
    for r in merged:
        if r["year"] >= years[-1] - 5:
            print(f"  {r['year']}  {r['sex']:<12}  {r['crude_rate']:.2f}")


if __name__ == "__main__":
    main()
