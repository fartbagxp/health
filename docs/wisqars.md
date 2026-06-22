# WISQARS

[WISQARS](https://wisqars.cdc.gov/) (Web-based Injury Statistics Query and Reporting System) tracks injury and violence deaths at national, state, county, and census-tract level. The `wisqars` module queries the WISQARS API and underlying Socrata datasets.

No API key required.

---

## Datasets

| Command     | Coverage                                               | Source                     |
| ----------- | ------------------------------------------------------ | -------------------------- |
| `mortality` | Fatal injuries by mechanism/intent/demographics        | 1999–2016 (Socrata)        |
| `national`  | Firearm, suicide, homicide, overdose deaths — national | 2019–present (WISQARS API) |
| `state`     | State-level injury/violence data                       | 2019–present (WISQARS API) |
| `county`    | County-level injury/violence data                      | 2019–present (WISQARS API) |
| `tract`     | Census-tract-level data                                | 2022–present (WISQARS API) |
| `query`     | Raw SODA query against any WISQARS dataset             | —                          |

---

## National data (2019–present)

```bash
# All firearm deaths, by year
uv run python -m wisqars national --intent FA_Deaths --period year -f table

# Firearm homicides monthly, 2023
uv run python -m wisqars national --intent FA_Homicide --period month --year 2023 -f csv

# All suicide deaths, trailing twelve months
uv run python -m wisqars national --intent All_Suicide --period TTM -f table

# Drug overdose deaths by year
uv run python -m wisqars national --intent Drug_OD --period year -f table
```

**Intent codes for national/state/county:**

| Code           | Description                   |
| -------------- | ----------------------------- |
| `FA_Deaths`    | All firearm deaths            |
| `FA_Homicide`  | Firearm homicides             |
| `FA_Suicide`   | Firearm suicides              |
| `All_Homicide` | All homicides (any mechanism) |
| `All_Suicide`  | All suicides (any mechanism)  |
| `Drug_OD`      | Drug overdose deaths          |

---

## State-level data (2019–present)

```bash
# All states, all firearm deaths, 2023
uv run python -m wisqars state --intent FA_Deaths --year 2023 -f table

# One state
uv run python -m wisqars state --state Texas --intent FA_Deaths --year 2023 -f table
uv run python -m wisqars state --state 48 --intent FA_Deaths --year 2023   # FIPS

# Drug overdose, all states, trailing 12 months
uv run python -m wisqars state --intent Drug_OD --year TTM -f csv
```

---

## County-level data (2019–present)

```bash
# All counties in Ohio, firearm deaths, 2023
uv run python -m wisqars county --state Ohio --intent FA_Deaths --year 2023 -f table

# Specific county by partial name match
uv run python -m wisqars county --state Texas --county Harris --intent Drug_OD --year 2023

# All US counties (large output — pipe to CSV)
uv run python -m wisqars county --intent FA_Deaths --year 2023 -f csv > fa-deaths-county-2023.csv
```

---

## Census-tract level (2022–present)

The most granular data available. Only two intents supported at tract level:

```bash
# All census tracts in Cook County, IL
uv run python -m wisqars tract --state Illinois --intent All_Homicide --year 2022

# Specific tract by GEOID partial match
uv run python -m wisqars tract --state CA --tract 06037 --intent Drug_OD --year 2022
```

!!! note
Census-tract data is only available starting 2022.

---

## Legacy mortality data (1999–2016)

The older `mortality` command queries the Socrata-backed dataset with different intent/mechanism vocabulary:

```bash
# Unintentional firearm deaths, all ages, 2010
uv run python -m wisqars mortality \
  --intent Unintentional --mechanism Firearm --year 2010 -f table

# All suicide deaths, female, 2005-2010
uv run python -m wisqars mortality \
  --intent Suicide --sex Female -f csv

# Poisoning deaths (covers most overdoses) 1999–2016
uv run python -m wisqars mortality \
  --mechanism Poisoning --intent Unintentional -f csv
```

**Intent choices (mortality):** `All Intentions`, `Unintentional`, `Suicide`, `Homicide`, `Undetermined`, `Legal intervention/war`

**Mechanism choices (mortality):** `All Mechanisms`, `Firearm`, `Poisoning`, `Fall`, `Motor vehicle traffic`, `Suffocation`, `Drowning`, `Cut/pierce`, `Fire/hot object or substance`, `All Other Transport`, `All Other Specified`, `Unspecified`

---

## Raw SODA query

```bash
# List available WISQARS Socrata datasets
uv run python -m wisqars list

# Raw query against a specific dataset
uv run python -m wisqars query <dataset_id> \
  --where "state_name='Texas' AND year='2023'" \
  --select "state_name,deaths,crude_rate" \
  -f csv
```

---

## Python SDK

```python
from wisqars.sdk import (
    get_national_data,
    get_state_data,
    get_county_data,
    get_census_tract_data,
    get_mortality,
)

# National firearm deaths by year
rows = get_national_data(intent="FA_Deaths", period="year")

# All states, 2023
rows = get_state_data(intent="FA_Deaths", year="2023")

# Ohio counties
rows = get_county_data(state="Ohio", intent="Drug_OD", year="2023")

# Cook County census tracts
rows = get_census_tract_data(state="Illinois", intent="All_Homicide", year="2022")
```

---

## Combining WISQARS and WONDER

WISQARS (2019–present) complements WONDER (1999–present) at sub-state geography:

```python
# WONDER: firearm deaths by state and year, 1999–2024 (50 years, national picture)
# WISQARS: firearm deaths by county, 2019–present (local picture)

# Typical workflow:
# 1. Use WONDER for long trends and state-level comparisons
# 2. Use WISQARS for county/tract breakdowns within a state
# 3. Merge on state name + year where both overlap (2019–2020)
```
