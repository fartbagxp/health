# cdc_open

Python SDK and CLI for [data.cdc.gov](https://data.cdc.gov) — U.S. public health statistics via the Socrata SODA API.

14 datasets covering mortality, birth, COVID-19, disability, nutrition, and county/city health indicators.

## Setup

```bash
# Optional: set a CDC app token to raise rate limits (1,000 → 20,000 req/hr)
# Register at data.cdc.gov → sign in → Developer Settings → Create New App Token
# Use the "App Token" string only — the secret token is for OAuth writes, not needed here
export CDC_DATA_APP_TOKEN=your_app_token_here

# Required for `analyze` command only
export ANTHROPIC_API_KEY=your_key_here
```

A `.env` file in the project root is loaded automatically.

---

## CLI

### List datasets

```bash
uv run python -m cdc_open list
uv run python -m cdc_open list -f json
```

```bash
KEY                       DATASET ID   YEARS          NAME
--------------------------------------------------------------------------------
leading_death             bi63-dtpu    1999–2017      Leading Causes of Death
life_expectancy           w9j2-ggv5    1900–2018      Life Expectancy
mortality_rates           489q-934x    2020–present   Provisional Mortality Rates
places_county             swc5-untb    Current        PLACES: County Health
places_city               dxpw-cm5u    Current        PLACES: City Health
...
```

### Raw SODA query

Query any dataset directly using [Socrata SODA syntax](https://dev.socrata.com/docs/queries/).

```bash
# Top causes of death in Ohio in 2010
uv run python -m cdc_open query bi63-dtpu \
  --where "year='2010' AND state='Ohio'" \
  --order "deaths DESC" \
  --limit 5 \
  -f table

# Age-adjusted heart disease death rate over time
uv run python -m cdc_open query 6rkc-nb2q \
  --where "leading_causes='Heart Disease'" \
  --order "year ASC" \
  -f csv > heart_disease.csv

# County obesity rates in Texas
uv run python -m cdc_open query swc5-untb \
  --where "stateabbr='TX' AND measureid='OBESITY'" \
  --select "locationname, data_value, totalpopulation" \
  --order "data_value DESC" \
  --limit 20 \
  -f table

# Weekly deaths in 2023 (all states)
uv run python -m cdc_open query r8kw-7aab \
  --where "group='By Week' AND year='2023'" \
  --order "end_date DESC" \
  --limit 50 \
  -f json
```

Output formats: `json` (default), `csv`, `table`.

## Testing

Run the integration test.

```bash
uv run pytest tests/test_cdc_open.py -m integration -v
```

### Analyze — LLM-powered question answering

Ask a natural language question. Claude picks the right tool(s), fetches real data, and synthesizes an answer.

```bash
uv run python -m cdc_open analyze "What were the top 5 causes of death in the US in 2015?"

uv run python -m cdc_open analyze "Compare obesity rates across southern states"

uv run python -m cdc_open analyze "How did life expectancy differ between Black and White Americans in 2010?"

uv run python -m cdc_open analyze "Which states had the highest drug overdose death rates in 2014?"

uv run python -m cdc_open analyze "Show excess mortality trends during COVID-19 in New York"

# Verbose: see which tools Claude calls and how many rows are returned
uv run python -v analyze "Compare preterm birth rates by race/ethnicity"

# Dump the raw fetched data alongside the analysis
uv run python -m cdc_open analyze "Opioid overdose trends in Appalachia" \
  --dump-data --dump-format csv
```

---

## Python SDK

### Direct query functions

```python
from cdc_open.sdk import (
    get_leading_causes_of_death,
    get_life_expectancy,
    get_mortality_rates,
    get_places_county_health,
    get_places_city_health,
    get_weekly_deaths,
    get_disability_data,
    get_drug_overdose_data,
    get_nutrition_obesity_data,
    get_historical_death_rates,
    get_birth_indicators,
    get_covid_data,
    query_dataset,
)

# Leading causes of death in a state/year
rows = get_leading_causes_of_death(state="West Virginia", year=2014)

# Life expectancy trends by race
rows = get_life_expectancy(race="Black", sex="Both Sexes")

# Most current mortality data (updated weekly)
rows = get_weekly_deaths(state="California", year=2023)

# County-level obesity rates for a state
rows = get_places_county_health(state="MS", measure="OBESITY")

# Drug overdose death rates — all states, all years
rows = get_drug_overdose_data(sex="Both Sexes")

# Historical heart disease death rates since 1950
rows = get_historical_death_rates(cause="Heart Disease", start_year=1950)

# Raw SODA query — full flexibility
rows = query_dataset(
    dataset_id="bi63-dtpu",
    where="year = '2015' AND state = 'United States'",
    order="deaths DESC",
    limit=20,
)
```

Each function returns a `list[dict]`, ready for use with `pandas`, `csv`, or JSON output.

```python
import pandas as pd
from cdc_open.sdk import get_places_county_health

df = pd.DataFrame(get_places_county_health(state="NY", measure="DIABETES"))
print(df[["locationname", "data_value"]].sort_values("data_value", ascending=False))
```

### LLM tool-calling integration

`tools.py` exposes all functions as [Anthropic API tool_use](https://docs.anthropic.com/en/docs/tool-use) definitions.

```python
import anthropic
from cdc_open.tools import TOOLS, execute_tool

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    tools=TOOLS,
    messages=[{"role": "user", "content": "Which states have the highest rates of cognitive disability?"}],
)

# Execute tool calls returned by Claude
for block in response.content:
    if block.type == "tool_use":
        rows = execute_tool(block.name, block.input)
        print(f"{block.name}: {len(rows)} rows")
```

---

## Available datasets

| Key                      | Dataset ID  | Coverage     | Description                               |
| ------------------------ | ----------- | ------------ | ----------------------------------------- |
| `leading_death`          | `bi63-dtpu` | 1999–2017    | Leading causes of death by state          |
| `life_expectancy`        | `w9j2-ggv5` | 1900–2018    | Life expectancy by race and sex           |
| `mortality_rates`        | `489q-934x` | 2020–present | Provisional quarterly death rates         |
| `places_county`          | `swc5-untb` | Current      | County health indicators (30+ measures)   |
| `places_city`            | `dxpw-cm5u` | Current      | City health indicators (pop. > 50k)       |
| `covid_cases`            | `pwn4-m3yp` | 2020–2023    | Weekly COVID-19 cases and deaths          |
| `covid_conditions`       | `hk9y-quqm` | 2020–2023    | COVID-19 deaths by contributing condition |
| `weekly_deaths`          | `r8kw-7aab` | 2020–present | Weekly deaths by state (updated weekly)   |
| `disability`             | `s2qv-b27b` | Current      | Disability prevalence by type and state   |
| `weekly_deaths_by_cause` | `muzy-jte6` | 2020–2023    | Weekly deaths by cause                    |
| `drug_overdose_state`    | `xbxb-epbu` | 1999–2016    | Drug overdose mortality by state          |
| `nutrition_obesity`      | `hn4x-zwk7` | Current      | Obesity, inactivity, nutrition by state   |
| `death_rates_historical` | `6rkc-nb2q` | 1900–2017    | Historical death rates for major causes   |
| `birth_indicators`       | `76vv-a7x8` | Current      | Quarterly birth indicators by race        |

## PLACES measure IDs

Common measures for `get_places_county_health` and `get_places_city_health`:

| ID           | Measure                   |
| ------------ | ------------------------- |
| `OBESITY`    | Adult obesity             |
| `DIABETES`   | Diabetes                  |
| `CSMOKING`   | Current smoking           |
| `BPHIGH`     | High blood pressure       |
| `DEPRESSION` | Depression                |
| `SLEEP`      | Short sleep duration      |
| `BINGE`      | Binge drinking            |
| `LPA`        | Physical inactivity       |
| `ACCESS2`    | No health insurance       |
| `FOODINSECU` | Food insecurity           |
| `LONELINESS` | Loneliness                |
| `HOUSINSECU` | Housing insecurity        |
| `CHD`        | Coronary heart disease    |
| `STROKE`     | Stroke                    |
| `COPD`       | COPD                      |
| `CASTHMA`    | Asthma                    |
| `MHLTH`      | Poor mental health days   |
| `PHLTH`      | Poor physical health days |
