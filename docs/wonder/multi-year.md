# Multi-Year Queries

WONDER splits data into separate datasets by year range. To collect a continuous time series spanning more than one era — say, mortality from 1979 to 2024 — you query each era's dataset separately and merge the results.

## The epoch map for mortality

```bash
1968–1978   D74   Compressed Mortality (ICD-8)
1979–1998   D16   Compressed Mortality (ICD-9)
1999–2020   D77   Multiple Cause of Death (ICD-10, bridged race, final)
2018–2023   D157  Final Mortality, Single Race (ICD-10, final — overlaps D77)
2018–present D176 Provisional Mortality (ICD-10, most current)
```

For a **1979–2024** all-cause series use: D16 + D77 + D176.  
For a **1999–2024** series use: D77 + D176 (simpler, same ICD-10 era).

!!! warning "ICD-9 vs ICD-10 discontinuity"
D16 uses ICD-9 codes (pre-1999); D77 and later use ICD-10. Cause-specific time series crossing 1999 need a bridging adjustment — totals can be compared directly, but individual cause groupings differ. See [CDC ICD bridging comparability](https://www.cdc.gov/nchs/nvss/bridged_race.htm).

## Rate limit pattern

WONDER enforces **≥15 seconds between requests**. Always sleep between epoch queries.

```python
import time

RATE_LIMIT = 16  # one second of margin

for i, epoch in enumerate(epochs):
    if i > 0:
        time.sleep(RATE_LIMIT)
    result = run_query(epoch)
```

## Example: mortality by year, 1979–2024

This is the full pattern used in `src/wonder/queries/fetch_mortality_by_year.py`.

### Step 1 — save XML for each epoch

Generate XML with the LLM builder (one-time, then commit the files):

```bash
# D16: 1979–1998, ICD-9, grouped by year and ICD chapter
uv run python -m wonder build \
  "all-cause deaths by year 1979-1998 grouped by year and ICD chapter, dataset D16" \
  > src/wonder/queries/mortality-by-year-cause-1979-1998-req.xml

# D77: 1999–2020
uv run python -m wonder build \
  "all-cause deaths by year 1999-2020 grouped by year and ICD chapter, dataset D77" \
  > src/wonder/queries/mortality-by-year-cause-1999-2020-req.xml

# D176: 2021–present
uv run python -m wonder build \
  "all-cause deaths by year 2021-2024 grouped by year and ICD chapter, dataset D176" \
  > src/wonder/queries/mortality-by-year-cause-2021-2024-req.xml
```

### Step 2 — fetch and merge

```python
import time
import sys
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from wonder.client import WonderClient

QUERIES = [
    # (dataset_id, xml_path, hierarchical_rows)
    ("D16",  "mortality-by-year-cause-1979-1998-req.xml",  True),
    ("D77",  "mortality-by-year-cause-1999-2020-req.xml",  False),
    ("D176", "mortality-by-year-cause-2021-2024-req.xml",  False),
]

client = WonderClient(timeout=120)
queries_dir = PROJECT_ROOT / "src/wonder/queries"
all_records = []

for i, (dataset_id, filename, hierarchical) in enumerate(QUERIES):
    if i > 0:
        print(f"Sleeping 16s for rate limit...")
        time.sleep(16)

    xml_path = queries_dir / filename
    print(f"Querying {dataset_id}...")
    xml_result = client.execute_query_file(str(xml_path))

    if hierarchical:
        # D16 uses merged-cell rows: year only appears on the first sub-row
        records = parse_hierarchical(client, xml_result)
    else:
        records = parse_flat(client, xml_result)

    all_records.extend(records)
    print(f"  {len(records)} rows")

# Merge: keep max deaths on any overlap between datasets
merged = defaultdict(lambda: defaultdict(int))
for rec in all_records:
    y, cause, deaths = rec["year"], rec["cause"], rec["deaths"]
    merged[y][cause] = max(merged[y][cause], deaths)
```

### Step 3 — handle D16's hierarchical row format

D76 and later datasets return flat rows: every row has `[year, cause, deaths]`.  
D16 returns "merged-cell" rows: the year column only appears on the **first** sub-row for each year group; subsequent rows for the same year omit the year column.

```python
def _is_year(label: str) -> bool:
    s = label.strip()
    return len(s) == 4 and s.isdigit() and 1900 <= int(s) <= 2099

def parse_hierarchical(client, xml: str) -> list[dict]:
    """Parser for D16 merged-cell rows."""
    rows = client.parse_response_table(xml)
    records = []
    current_year = None

    for row in rows:
        if row.is_total:
            continue
        cells = row.cells
        if not cells:
            continue

        c0 = (cells[0].label or "").strip()

        if _is_year(c0):
            # First sub-row for this year: [year, cause, deaths, ...]
            current_year = int(c0)
            cause  = (cells[1].label or "").strip() if len(cells) > 1 else ""
            deaths = cells[2].get_numeric_value()  if len(cells) > 2 else None
        else:
            # Continuation sub-row: [cause, deaths, ...]
            cause  = c0
            deaths = cells[1].get_numeric_value() if len(cells) > 1 else None

        if cause and deaths is not None and current_year is not None:
            records.append({"year": current_year, "cause": cause, "deaths": int(deaths)})

    return records

def parse_flat(client, xml: str) -> list[dict]:
    """Parser for D77/D176 flat rows."""
    rows = client.parse_response_table(xml)
    records = []
    for row in rows:
        if row.is_total:
            continue
        cells = row.cells
        if len(cells) < 3:
            continue
        year_label = (cells[0].label or "").strip()
        cause      = (cells[1].label or "").strip()
        deaths     = cells[2].get_numeric_value()
        if _is_year(year_label) and cause and deaths is not None:
            records.append({"year": int(year_label), "cause": cause, "deaths": int(deaths)})
    return records
```

## Running the full mortality script

```bash
uv run python src/wonder/queries/fetch_mortality_by_year.py
```

Outputs to `data/raw/wonder/`:

- `mortality-total-by-year.csv` — total deaths per year, 1979–2024
- `mortality-top5-causes-by-year.csv` — top 5 ICD chapters per year (long format)

## Quick multi-year via the LLM (single dataset)

For queries within a single dataset epoch (≤25 years, single ICD era), just include the full year range in the prompt:

```bash
# 22 years in one shot — D157 covers this entire span
uv run python -m wonder query \
  "cancer death rates 1999-2023 by year, age-adjusted rate, dataset D157" -f csv

# 7 years in one shot on D176
uv run python -m wonder query \
  "opioid overdose deaths 2018-2024 by year, grouped by year only" -f csv
```

WONDER's `F_D176.V1` filter accepts a list of years — the LLM expands the range automatically.

## Natality across epochs

Births from 1995–2024 require three datasets:

| Dataset | Years     | Notes                                                                                          |
| ------- | --------- | ---------------------------------------------------------------------------------------------- |
| D10     | 1995–2002 |                                                                                                |
| D27     | 2003–2006 | Requires full base template — see [troubleshooting](troubleshooting.md#d27-natality-500-error) |
| D66     | 2007–2024 | Default                                                                                        |

```bash
# Pre-built XML queries for each epoch are in src/wonder/queries/
uv run python -m wonder run src/wonder/queries/births-by-year-1995-2002-req.xml
sleep 16
uv run python -m wonder run src/wonder/queries/births-by-year-2003-2006-req.xml
sleep 16
uv run python -m wonder run src/wonder/queries/births-by-year-2007-2024-req.xml
```

## Infant mortality across epochs

```
1995–1998   D23
1999–2002   D18
2003–2006   D31
2007–2023   D69 (default) or D159 (expanded race)
```

Same pattern: one XML per epoch, sleep between them, merge on Year.

## Merging results when epochs overlap

D77 ends in 2020 and D176 starts in 2018 — they overlap on 2018–2020. For totals and long-term trends, **keep the final data (D77) for overlapping years** and use D176 only for years after D77's coverage. The merge logic above uses `max()` as a pragmatic heuristic; for publication-quality work, choose the final dataset explicitly:

```python
# Prefer D157 (final) over D176 (provisional) for 2018–2023
EPOCH_PRIORITY = {
    "D157": 3,  # highest: confirmed final data
    "D77":  2,
    "D176": 1,  # lowest: provisional
    "D16":  2,
}

merged = {}
for rec in all_records:
    key = (rec["year"], rec["cause"])
    priority = EPOCH_PRIORITY.get(rec["dataset"], 0)
    if key not in merged or priority > merged[key]["priority"]:
        merged[key] = {**rec, "priority": priority}
```
