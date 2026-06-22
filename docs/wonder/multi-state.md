# All-State Queries

WONDER can return data for all 50 states (+ DC + territories) in a single request by grouping on the state variable and setting the state filter to `*All*`. This page shows how to get state-level data at scale.

## The quick path — LLM query

For a single metric across all states, just ask:

```bash
# Deaths by state — all states, no filter needed
uv run python -m wonder query \
  "drug overdose deaths by state 2018-2023, crude rate per 100,000" -f csv

uv run python -m wonder query \
  "firearm deaths by state 2020-2023, age-adjusted rate" -f csv

uv run python -m wonder query \
  "maternal mortality by state 2018-2023" -f csv
```

The LLM sets `B_1 = D176.V9-level1` (group by state) and `F_D176.V9 = *All*` automatically.

## State × year — getting both dimensions

Grouping by **state and year** together returns ~350 rows (50 states × 7 years) — well within WONDER's 75,000-cell limit. Ask for both in the same prompt:

```bash
uv run python -m wonder query \
  "drug overdose deaths by state and year 2018-2023, crude rate" -f csv

uv run python -m wonder query \
  "opioid deaths (T40.0-T40.6 MCD) by state and year 2018-2024, death counts" -f csv
```

## The 75,000-cell limit

WONDER rejects results that would exceed 75,000 cells:

```bash
cells = (states) × (years) × (other group-by dimensions)
```

Rules of thumb:

| Dimensions                                  | Approx rows | Safe?           |
| ------------------------------------------- | ----------- | --------------- |
| state only                                  | ~52         | ✅              |
| state × year (7 yr)                         | ~364        | ✅              |
| state × year × sex                          | ~728        | ✅              |
| state × year × age (10-yr groups, 12 bands) | ~4,368      | ✅              |
| state × year × ICD chapter (~20 chapters)   | ~7,280      | ✅              |
| state × county × year                       | ~100k+      | ❌ split needed |
| state × year (25 yr) × race × sex           | ~90k+       | ❌ split needed |

When you hit the limit, the solution is to **query one year at a time** and loop:

```python
import time, csv, io
from wonder.client import WonderClient

client = WonderClient()
years = list(range(1999, 2024))
all_rows = []

for i, year in enumerate(years):
    if i > 0:
        time.sleep(16)
    print(f"Querying {year}...")
    result = client.query_with_llm(
        f"drug overdose deaths by state {year}, crude rate per 100,000, dataset D77"
        if year <= 2020 else
        f"drug overdose deaths by state {year}, crude rate per 100,000, dataset D176"
    )
    for row in result:
        row["year"] = year
    all_rows.extend(result)

# Write combined CSV
with open("overdose-by-state-1999-2023.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=all_rows[0].keys())
    writer.writeheader()
    writer.writerows(all_rows)
```

!!! note "Total time for 25-year state loop"
25 queries × 16 seconds = ~6.7 minutes. Run once, save results to CSV, re-use locally.

## State names vs FIPS codes

WONDER returns state names as labels. If you need FIPS codes for merging with other datasets (Census, WISQARS, etc.), use this lookup:

```python
STATE_FIPS = {
    "Alabama": "01", "Alaska": "02", "Arizona": "04", "Arkansas": "05",
    "California": "06", "Colorado": "08", "Connecticut": "09", "Delaware": "10",
    "District of Columbia": "11", "Florida": "12", "Georgia": "13",
    "Hawaii": "15", "Idaho": "16", "Illinois": "17", "Indiana": "18",
    "Iowa": "19", "Kansas": "20", "Kentucky": "21", "Louisiana": "22",
    "Maine": "23", "Maryland": "24", "Massachusetts": "25", "Michigan": "26",
    "Minnesota": "27", "Mississippi": "28", "Missouri": "29", "Montana": "30",
    "Nebraska": "31", "Nevada": "32", "New Hampshire": "33", "New Jersey": "34",
    "New Mexico": "35", "New York": "36", "North Carolina": "37",
    "North Dakota": "38", "Ohio": "39", "Oklahoma": "40", "Oregon": "41",
    "Pennsylvania": "42", "Rhode Island": "44", "South Carolina": "45",
    "South Dakota": "46", "Tennessee": "47", "Texas": "48", "Utah": "49",
    "Vermont": "50", "Virginia": "51", "Washington": "53",
    "West Virginia": "54", "Wisconsin": "55", "Wyoming": "56",
    # Territories
    "Puerto Rico": "72",
}

# Attach FIPS to results
for row in all_rows:
    state_name = row.get("State") or row.get("state") or ""
    row["state_fips"] = STATE_FIPS.get(state_name, "")
```

## Handling suppressed values

States with small populations or rare causes return "Suppressed" instead of a count (NCHS suppresses values < 10). Handle them explicitly:

```python
def safe_float(val):
    """Return float or None for Suppressed/Missing/Not Applicable."""
    if val is None:
        return None
    s = str(val).strip()
    if s in ("Suppressed", "Missing", "Not Applicable", ""):
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None

# Filter to only rows with usable data
usable = [r for r in all_rows if safe_float(r.get("Deaths")) is not None]
suppressed = [r for r in all_rows if safe_float(r.get("Deaths")) is None]
print(f"{len(suppressed)} suppressed rows out of {len(all_rows)}")
```

## Full script: drug overdose deaths by state and year, 1999–2024

This pattern covers the entire ICD-10 era for mortality:

```python
"""
Drug overdose deaths by state and year, 1999–2024.

Uses two datasets:
  D77  — 1999–2020 (final data, ICD-10)
  D176 — 2021–2024 (provisional)

Queries each year individually (avoids cell-count limit).
"""
import csv
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from wonder.client import WonderClient  # noqa: E402

client = WonderClient(timeout=120)

# Define year→dataset mapping
def dataset_for_year(year: int) -> str:
    if year <= 2020:
        return "D77"
    return "D176"

years = list(range(1999, 2025))
all_rows = []

for i, year in enumerate(years):
    if i > 0:
        time.sleep(16)

    dataset = dataset_for_year(year)
    print(f"  {year} ({dataset})...", end=" ", flush=True)

    prompt = (
        f"drug overdose deaths (ICD V_D77.V25 = D1 all drug-induced) "
        f"by state {year}, crude rate per 100,000, dataset {dataset}"
    )

    try:
        rows = client.query_with_llm(prompt, output_format="csv")
    except Exception as e:
        print(f"ERROR: {e}")
        rows = []

    for row in rows:
        row["year"] = year
        row["dataset"] = dataset

    all_rows.extend(rows)
    print(f"{len(rows)} rows")

# Write output
out = PROJECT_ROOT / "data" / "raw" / "wonder" / "overdose-by-state-1999-2024.csv"
if all_rows:
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_rows[0].keys())
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\nWrote {len(all_rows)} rows to {out.name}")
```

## Cross-referencing with WISQARS

WISQARS covers 2019–present at state, county, and census-tract level. For state-level firearm or overdose data, WISQARS and WONDER can complement each other:

```python
# WONDER: firearm deaths 1999–2024, all states, by year
uv run python -m wonder query \
  "firearm deaths by state and year 1999-2024, crude rate, dataset D77 for 1999-2020 and D176 after"

# WISQARS: 2019–present with more geographic granularity
uv run python -m wisqars state --intent FA_Deaths --year 2023 -f csv
uv run python -m wisqars county --state Texas --intent FA_Deaths --year 2023 -f csv
```

## HHS regions instead of states

If 50-state granularity is too detailed, group by HHS region (10 regions):

```bash
uv run python -m wonder query \
  "drug overdose deaths by HHS region and year 2018-2024, crude rate"
```

The LLM sets `B_1 = D176.V27-level1` (HHS region grouping). You can also use census region (`D176.V10`) for the 4 Census Bureau regions or 9 divisions.

## County-level data

WONDER supports county grouping (`B_1 = D176.V9-level2`), but the 75,000-cell limit bites hard at this granularity (~3,200 counties × years × cause). Best practice: filter to a single state:

```bash
uv run python -m wonder query \
  "drug overdose deaths by county in Texas 2018-2023, crude rate"

# Or build the XML and target state filter
uv run python -m wonder build \
  "drug overdose deaths by county in Ohio 2020-2023, crude rate" \
  > ohio-county-overdose.xml
uv run python -m wonder run ohio-county-overdose.xml -f csv
```

For county-level data 2019–present at national scale, WISQARS is easier — it's designed for sub-state geography and doesn't have the cell limit problem.
