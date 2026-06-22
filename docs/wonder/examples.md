# Example Gallery

Worked examples for WONDER queries. Copy-paste any prompt directly into:

```bash
uv run python -m wonder query "<prompt>" -f csv
```

---

## Datasets we've already fetched

These datasets are committed to `data/raw/wonder/`. Run the corresponding scripts to refresh them.

### Mortality by year and cause — 1979–2024

**File:** `data/raw/wonder/mortality-total-by-year.csv` (46 rows)  
**File:** `data/raw/wonder/mortality-top5-causes-by-year.csv` (230 rows)  
**Script:** `src/wonder/queries/fetch_mortality_by_year.py`  
**Sources:** D16 (1979–1998, ICD-9) + D77 (1999–2020, ICD-10) + D176 (2021–2024, provisional)

```bash
uv run python src/wonder/queries/fetch_mortality_by_year.py
```

Produces two files: total deaths per year, and the top-5 ICD chapters per year in long format. Uses the D16 hierarchical row parser (year only appears on first sub-row per year group) and flat parsers for D77/D176. On overlap years (2018–2020), takes `max()` — D77 final data wins.

Sample output:
```
year,total_deaths
1979,1913841
1999,2391399
2019,2854838
2020,3383729
2021,3458697
2022,3279857
2023,3090964
2024,3072666
```

---

### Maternal mortality (national) — 1999–2024

**File:** `data/raw/wonder/maternal-mortality-by-year.csv` (26 rows)  
**Script:** `src/wonder/queries/fetch_maternal_mortality.py`  
**Sources:** D76 (1999–2017) + D158 (2018–2024)

```bash
uv run python src/wonder/queries/fetch_maternal_mortality.py
```

Filters UCD to O00–O99 (Pregnancy, childbirth and the puerperium) + A34 (Obstetrical tetanus). Merges datasets: D76 for 1999–2017, D158 preferred from 2018 onward. The crude rate column uses total population as denominator — join with birth counts to compute the true maternal mortality ratio (per 100,000 live births).

!!! warning "Pregnancy checkbox artifact"
    States adopted the 2003 revised death certificate (which added a pregnancy checkbox) on a rolling schedule 2003–2017. The apparent rise in maternal deaths through the 2000s is partly a measurement change, not a real increase. Interpret pre-2018 trends with caution.

Sample output:
```
year,deaths,population,crude_rate_per_100k_pop
1999,406,279040168,0.1
2010,799,309326295,0.3
2019,754,328239523,0.2
2021,1205,331893745,0.4
2023,1056,334914895,0.3
```

---

### Maternal mortality by state and year — 1999–2024

**File:** `data/raw/wonder/maternal-mortality-by-state-year.csv` (1,260 rows)  
**Script:** `src/wonder/queries/scrape_maternal_mortality_by_state.py`  
**Sources:** D76 + D158 (same as national, but state-grouped)

The WONDER XML API blocks state-level grouping for all mortality datasets ("only national data available via web service"). This script uses **Playwright** to interact with the WONDER web UI instead, which does allow state breakdowns.

```bash
# Requires playwright installed and browsers downloaded
uv run playwright install chromium
uv run python src/wonder/queries/scrape_maternal_mortality_by_state.py
```

Many state-year cells are suppressed (death count < 10). The CSV includes both suppressed and unsuppressed rows — filter before analysis:

```python
import csv

with open("data/raw/wonder/maternal-mortality-by-state-year.csv") as f:
    rows = list(csv.DictReader(f))

# Only rows where deaths is a real number
usable = [r for r in rows if r["deaths"].strip() not in ("", "Suppressed")]
print(f"{len(usable)} / {len(rows)} rows have usable death counts")
```

---

### Births by year — 1995–2024

**Files:**
- `data/raw/wonder/births-by-year-1995-2002.csv` (8 rows, D10)
- `data/raw/wonder/births-by-year-2003-2006.csv` (4 rows, D27)
- `data/raw/wonder/births-by-year-2007-2024.csv` (18 rows, D66)

**XML queries:** `src/wonder/queries/births-by-year-*-req.xml`

Run the three epochs sequentially with a 16-second sleep:

```bash
uv run python -m wonder run \
  src/wonder/queries/births-by-year-1995-2002-req.xml -f csv \
  > data/raw/wonder/births-by-year-1995-2002.csv

sleep 16

uv run python -m wonder run \
  src/wonder/queries/births-by-year-2003-2006-req.xml -f csv \
  > data/raw/wonder/births-by-year-2003-2006.csv

sleep 16

uv run python -m wonder run \
  src/wonder/queries/births-by-year-2007-2024-req.xml -f csv \
  > data/raw/wonder/births-by-year-2007-2024.csv
```

To merge into a single series:
```python
import csv
from pathlib import Path

files = [
    "births-by-year-1995-2002.csv",
    "births-by-year-2003-2006.csv",
    "births-by-year-2007-2024.csv",
]
all_rows = []
for fname in files:
    with open(f"data/raw/wonder/{fname}") as f:
        rows = [r for r in csv.DictReader(f) if r.get("Year", "").strip().isdigit()]
        all_rows.extend(rows)

all_rows.sort(key=lambda r: int(r["Year"]))
# all_rows: [{"Year": "1995", "Births": "3900089.0"}, ...]
```

Births peaked in 2007 (4,316,233) and have fallen steadily; 2023 saw 3,596,017 births.

---

### Tick-borne diseases — 2016–2023

**File:** `data/raw/wonder/tick-borne-diseases-by-year.csv` (128 rows)  
**Script:** `src/wonder/queries/fetch_tick_borne_diseases.py`  
**Source:** D130 — NNDSS Annual Summary Data

```bash
uv run python src/wonder/queries/fetch_tick_borne_diseases.py
```

Covers: Lyme disease, babesiosis, ehrlichiosis/anaplasmosis (4 subtypes), spotted fever rickettsiosis, tularemia, Powassan virus. Long format: one row per (year, disease) pair including confirmed/probable/total breakdowns.

```python
import csv
from collections import defaultdict

with open("data/raw/wonder/tick-borne-diseases-by-year.csv") as f:
    rows = list(csv.DictReader(f))

# Lyme disease totals by year
lyme = {r["year"]: int(r["cases"]) for r in rows if r["disease"] == "Lyme disease, Total"}
for year in sorted(lyme):
    print(f"{year}: {lyme[year]:,} Lyme disease cases")
```

Sample totals (Lyme disease confirmed + probable combined):

| Year | Lyme | Babesiosis | Spotted fever | Anaplasmosis |
|---|---|---|---|---|
| 2016 | 36,429 | 1,910 | 4,269 | 4,151 |
| 2019 | 34,945 | 2,418 | 5,207 | 7,225 |
| 2022 | 62,006 | 3,427 | 8,232 | 9,074 |
| 2023 | 62,473 | 3,427 | 7,248 | 9,538 |

---

### Saved XML queries for reuse

These XML files are committed so you can run them without the LLM:

| File | What it fetches |
|---|---|
| `mortality-by-year-cause-1979-1998-req.xml` | All-cause + ICD-9 chapter, D16 |
| `mortality-by-year-cause-1999-2020-req.xml` | All-cause + ICD-10 chapter, D77 |
| `mortality-by-year-cause-2021-2024-req.xml` | All-cause + ICD-10 chapter, D176 |
| `maternal-mortality-by-year-1999-2020-req.xml` | O00–O99 national by year, D76 |
| `maternal-mortality-by-year-2018-2024-req.xml` | O00–O99 national by year, D158 |
| `births-by-year-1995-2002-req.xml` | Births by year, D10 |
| `births-by-year-2003-2006-req.xml` | Births by year, D27 |
| `births-by-year-2007-2024-req.xml` | Births by year, D66 |
| `covid-deaths-by-race-2020-2023-req.xml` | COVID deaths × race, D176 |
| `opioid-overdose-deaths-2018-2024-req.xml` | T40.0–T40.6 UCD, D176 |
| `infant-mortality-2018-2023-req.xml` | Infant mortality by race, D69 |
| `racial-mortality-gap-2018-2023-req.xml` | All-cause deaths × race, D176 |
| `heart-vs-cancer-by-sex-2018-2023-req.xml` | Heart disease vs cancer × sex, D176 |
| `unintentional-injuries-by-age-2018-2023-req.xml` | Unintentional injuries × age, D176 |
| `tick-borne-diseases-by-year-2016-2023-req.xml` | NNDSS tick-borne diseases, D130 |

Run any of them with:
```bash
uv run python -m wonder run src/wonder/queries/<filename>.xml -f csv
```

---

## Mortality — recent (D176, provisional)

```bash
# Overall trends
uv run python -m wonder query \
  "all-cause deaths by year 2018-2024, crude rate"

uv run python -m wonder query \
  "life expectancy proxy: all-cause age-adjusted death rate by year 2018-2024"

# COVID-19
uv run python -m wonder query \
  "COVID-19 deaths by year 2020-2024, crude rate and death count"

uv run python -m wonder query \
  "COVID-19 deaths by race and ethnicity 2020-2023"

uv run python -m wonder query \
  "COVID-19 deaths by age group 2020-2023"

uv run python -m wonder query \
  "COVID-19 deaths by state 2020-2022, crude rate per 100,000"

# Overdose
uv run python -m wonder query \
  "drug overdose deaths by year 2018-2024, age-adjusted rate"

uv run python -m wonder query \
  "opioid overdose deaths (T40.0-T40.6) by state and year 2018-2024"

uv run python -m wonder query \
  "synthetic opioid deaths (T40.4) by year 2018-2024, death count"

uv run python -m wonder query \
  "stimulant overdose deaths (T43.6 cocaine + T43.62 psychostimulants) by year 2018-2024"

# Firearm
uv run python -m wonder query \
  "firearm deaths by year 2018-2024, age-adjusted rate"

uv run python -m wonder query \
  "firearm suicide deaths (X72-X74) by state 2018-2023, crude rate"

uv run python -m wonder query \
  "firearm homicide deaths (X93-X95) by race and sex 2018-2023"

uv run python -m wonder query \
  "firearm deaths by intent (suicide, homicide, unintentional) 2020-2023"

# Maternal / infant
uv run python -m wonder query \
  "maternal mortality (O00-O99) by year 2018-2024, crude rate per 100,000 live births"

uv run python -m wonder query \
  "maternal mortality by race and ethnicity 2018-2023"

uv run python -m wonder query \
  "infant mortality by state 2018-2023, crude rate per 1,000 live births"

# Suicide
uv run python -m wonder query \
  "suicide deaths by sex 2018-2024, age-adjusted rate"

uv run python -m wonder query \
  "suicide deaths by age group 2018-2023"

uv run python -m wonder query \
  "suicide deaths by method (firearm vs non-firearm) by year 2018-2024"

# Cardiovascular
uv run python -m wonder query \
  "heart disease deaths by race and sex 2018-2023, age-adjusted rate"

uv run python -m wonder query \
  "stroke deaths by state 2020-2023, age-adjusted rate"
```

---

## Mortality — final data (D157, 1999–2023)

Use D157 when you need confirmed (non-provisional) data with expanded race categories.

```bash
uv run python -m wonder query \
  "cancer death rates by year 1999-2023, age-adjusted, dataset D157"

uv run python -m wonder query \
  "lung cancer deaths by sex 1999-2023, age-adjusted rate, dataset D157"

uv run python -m wonder query \
  "HIV/AIDS deaths by year 1999-2023, dataset D157"

uv run python -m wonder query \
  "Alzheimer deaths by sex and year 2010-2023, dataset D157"

uv run python -m wonder query \
  "diabetes deaths by race 2010-2023, age-adjusted, dataset D157"
```

---

## Mortality — ICD-10 era (D77, 1999–2020)

D77 uses bridged-race categories (5 groups). Covers the full ICD-10 era with final data.

```bash
uv run python -m wonder query \
  "opioid deaths by year 1999-2020, dataset D77"

uv run python -m wonder query \
  "firearm deaths by state 2010-2020, crude rate, dataset D77"

uv run python -m wonder query \
  "suicide deaths by age group and sex 2000-2020, dataset D77"

uv run python -m wonder query \
  "infant mortality by race 1999-2020, dataset D77"
```

---

## Births / natality

```bash
# Recent births (D66 default, 2007–2024)
uv run python -m wonder query \
  "births by year 2010-2024, birth count and birth rate"

uv run python -m wonder query \
  "teen births (mothers aged 15-19) by state 2018-2023"

uv run python -m wonder query \
  "preterm births by race 2018-2023, percent of births"

uv run python -m wonder query \
  "low birth weight by state 2018-2023"

uv run python -m wonder query \
  "C-section delivery rate by state 2018-2023"

# Expanded race detail (D149, 2016–2024)
uv run python -m wonder query \
  "births by race and ethnicity 2016-2023, dataset D149"
```

---

## Multi-year — cross-epoch patterns

These queries span multiple datasets and require looping. See [Multi-Year Queries](multi-year.md) for the full merge pattern.

```bash
# Collect 1999–2024 in two shots (D77 then D176)
# Year 1: D77 1999–2020
uv run python -m wonder query \
  "drug overdose deaths by year 1999-2020, dataset D77" -f csv > overdose-d77.csv

sleep 16

# Year 2: D176 2021–2024
uv run python -m wonder query \
  "drug overdose deaths by year 2021-2024, dataset D176" -f csv > overdose-d176.csv

# Then merge the two CSVs in pandas / polars / awk
```

---

## All-state queries

See [All-State Queries](multi-state.md) for the cell-limit workaround patterns.

```bash
# State × year — within cell limit
uv run python -m wonder query \
  "firearm deaths by state and year 2018-2024" -f csv

uv run python -m wonder query \
  "drug overdose deaths by state and year 2018-2024, crude rate" -f csv

# State only (single metric snapshot)
uv run python -m wonder query \
  "suicide death rate by state 2020-2022, age-adjusted" -f csv

uv run python -m wonder query \
  "maternal mortality rate by state 2018-2023" -f csv
```

---

## Race and ethnicity breakdowns

```bash
uv run python -m wonder query \
  "all-cause deaths by race and Hispanic origin 2018-2023, age-adjusted rate"

uv run python -m wonder query \
  "COVID-19 deaths by race 2020-2022, crude rate per 100,000"

uv run python -m wonder query \
  "firearm homicide deaths by race 2018-2023, age-adjusted rate"

uv run python -m wonder query \
  "infant mortality by race 2018-2023, infant mortality rate"
```

---

## Age-specific queries

```bash
uv run python -m wonder query \
  "deaths by 10-year age group 2020-2023, crude rate"

uv run python -m wonder query \
  "overdose deaths in adults 25-44 by year 2015-2024"

uv run python -m wonder query \
  "firearm deaths in ages 0-17 by state 2018-2023"

uv run python -m wonder query \
  "cardiovascular deaths in ages 35-64 by sex 2018-2023, age-adjusted"
```

---

## Environment and NLDAS

```bash
uv run python -m wonder query \
  "heat wave days per year by state 1981-2010, dataset D104"

uv run python -m wonder query \
  "days with max temperature above 90F by state 1979-2011, dataset D60"

uv run python -m wonder query \
  "average PM2.5 by county in California 2003-2011, dataset D73"
```

---

## Pediatric causes

```bash
uv run python -m wonder query \
  "leading causes of death in ages 1-4 by year 2018-2023"

uv run python -m wonder query \
  "unintentional injury deaths in children under 18 by state 2018-2023"

uv run python -m wonder query \
  "SIDS deaths (R95) by year 2010-2023"

uv run python -m wonder query \
  "drowning deaths (W65-W74) in ages 0-14 by state 2018-2023"
```

---

## Building XML queries for reuse

For any query you run repeatedly, save the XML so you don't need the LLM:

```bash
# Build and save
uv run python -m wonder build \
  "drug overdose deaths by state 2024, crude rate" \
  > src/wonder/queries/overdose-by-state-2024-req.xml

# Run from file (no LLM needed)
uv run python -m wonder run \
  src/wonder/queries/overdose-by-state-2024-req.xml -f csv

# Update just the year — edit the XML file:
# <F_D176.V1 value="2024"/> → <F_D176.V1 value="2025"/>
```
