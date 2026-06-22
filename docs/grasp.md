# GRASP / FluView

The `grasp` module wraps CDC's GRASP surveillance data via the [CMU Delphi Epidata API](https://cmu-delphi.github.io/delphi-epidata/). Three datasets are available: FluSurv-NET hospitalization rates, FluView ILINet (influenza-like illness), and FluView WHO/NREVSS clinical lab data.

No API key required. A 24-hour cache prevents redundant fetches.

---

## FluSurv-NET — hospitalization rates

FluSurv-NET tracks laboratory-confirmed influenza hospitalizations in ~10% of the US population. Data goes back to 2009–10.

### Quick commands

```bash
# Whole-network summary by season
uv run python -m grasp flusurv by-season --location network_all -f table

# Current season, all locations ranked by peak rate
uv run python -m grasp flusurv by-location -f table

# Raw weekly data for a single location
uv run python -m grasp flusurv data --location CA --epiweeks 202001-202560 -f csv

# Specific season (e.g. 2022–23)
uv run python -m grasp flusurv data --location network_all --season 2022-23 -f table
```

### Locations

| Code | Description |
|---|---|
| `network_all` | Entire FluSurv-NET network (default) |
| `network_eip` | Emerging Infections Program (EIP) |
| `network_ihsp` | IHSP network |
| `CA` | California |
| `CO` | Colorado |
| `CT` | Connecticut |
| `GA` | Georgia |
| `MD` | Maryland |
| `MI` | Michigan |
| `MN` | Minnesota |
| `NM` | New Mexico |
| `OH` | Ohio |
| `OR` | Oregon |
| `TN` | Tennessee |
| `UT` | Utah |

### Python SDK

```python
from grasp.sdk import get_flusurv_net, summarize_flusurv_by_season, summarize_flusurv_by_location

# All data for network, full history
records = get_flusurv_net()  # defaults: location=["network_all"], all epiweeks

# Specific locations and date range
records = get_flusurv_net(
    locations=["CA", "GA"],
    epiweeks="201940-202560",
)

# Season-by-season summary for one location
by_season = summarize_flusurv_by_season("network_all")
# Returns: {"2020-21": {"peak_rate": 12.3, "avg_rate": 4.1, "weeks": 27}, ...}

# All locations ranked by peak rate, current season
by_location = summarize_flusurv_by_location(season="2023-24")
# Returns: [{"location": "GA", "location_name": "Georgia", "peak_rate": 18.2, ...}, ...]
```

### Key columns

| Column | Description |
|---|---|
| `location` | Location code (e.g. `CA`, `network_all`) |
| `epiweek` | YYYYWW format |
| `season` | Season string e.g. `2023-24` |
| `rate_overall` | Overall hospitalization rate per 100,000 |
| `rate_age_0` | Ages 0–4 |
| `rate_age_1` | Ages 5–17 |
| `rate_age_2` | Ages 18–49 |
| `rate_age_3` | Ages 50–64 |
| `rate_age_4` | Ages 65+ |
| `rate_flu_a` | Influenza A rate |
| `rate_flu_b` | Influenza B rate |

---

## FluView ILINet — influenza-like illness

ILINet tracks the percentage of outpatient visits that are influenza-like illness (ILI), reported by ~3,500 sentinel providers. Data goes back to 1997–98.

### Quick commands

```bash
# National ILI activity, last 52 weeks
uv run python -m grasp fluview ili data --region nat -f table

# All HHS + census regions, this season
uv run python -m grasp fluview ili data --region hhs1,hhs2,hhs3 --epiweeks 202440-202560 -f csv

# State-level: lowercase 2-letter code
uv run python -m grasp fluview ili data --region ca,tx,ny --epiweeks 202001-202560 -f csv

# Regional comparison, peak/avg/weeks by region
uv run python -m grasp fluview ili by-region --epiweeks 202001-202560 -f table
```

### Regions

| Code | Description |
|---|---|
| `nat` | National |
| `hhs1`–`hhs10` | HHS Region 1–10 |
| `cen1`–`cen9` | Census Region 1–9 |
| `al`, `ak`, ..., `wy` | State (lowercase 2-letter USPS code) |

### Python SDK

```python
from grasp.sdk import get_fluview_ili, summarize_fluview_ili_by_region

# National, last 2 seasons
records = get_fluview_ili(
    regions=["nat"],
    epiweeks="202340-202560",
)

# All states
records = get_fluview_ili(
    regions=["al", "ak", "az", "ar", "ca", "co", "ct"],
    epiweeks="202001-202560",
)

# Summary across all standard regions (nat + hhs + census)
summary = summarize_fluview_ili_by_region(epiweeks="202001-202560")
# Returns list sorted by peak wILI descending
```

### Key columns

| Column | Description |
|---|---|
| `region` | Region code |
| `epiweek` | YYYYWW |
| `wili` | Weighted ILI % (primary metric) |
| `ili` | Unweighted ILI % |
| `num_ili` | Number of ILI visits |
| `num_patients` | Total patient visits |
| `num_providers` | Number of reporting providers |

---

## FluView Clinical — WHO/NREVSS lab data

WHO/NREVSS clinical labs report total influenza specimens tested and positive counts by type (A and B). Data starts 2016–17.

### Quick commands

```bash
# National, last 2 seasons
uv run python -m grasp fluview clinical data --region nat --epiweeks 202340-202560 -f table

# All HHS regions
uv run python -m grasp fluview clinical data \
  --region hhs1,hhs2,hhs3,hhs4,hhs5,hhs6,hhs7,hhs8,hhs9,hhs10 \
  --epiweeks 202440-202560 -f csv
```

### Python SDK

```python
from grasp.sdk import get_fluview_clinical

records = get_fluview_clinical(
    regions=["nat"],
    epiweeks="202340-202560",
)
```

### Key columns

| Column | Description |
|---|---|
| `region` | Region code |
| `epiweek` | YYYYWW |
| `total_specimens` | Total specimens tested |
| `total_a` | Influenza A positive |
| `total_b` | Influenza B positive |
| `percent_positive` | % specimens positive |
| `percent_a` | % positive that are type A |
| `percent_b` | % positive that are type B |

---

## Hantavirus surveillance

Rare but tracked: hantavirus pulmonary syndrome (HPS) cases from GRASP.

```bash
# All cases
uv run python -m grasp hantavirus cases -f table

# Cases by year
uv run python -m grasp hantavirus by-year -f table

# Cases by state
uv run python -m grasp hantavirus by-state -f table
```

```python
from grasp.sdk import get_hantavirus_cases

cases = get_hantavirus_cases()
```

---

## Epiweek format

All time parameters use `YYYYWW` format (ISO week):
- `202501` = week 1 of 2025
- `202440-202560` = week 40 of 2024 through week 60 of 2025 (flu season span)
- `199740-202660` = full ILINet history

Flu seasons run approximately from week 40 (early October) to week 20 of the following year.
