# cdc_open

Python SDK and CLI for [data.cdc.gov](https://data.cdc.gov) — U.S. public health statistics via the Socrata SODA API.

52 datasets covering mortality, birth, COVID-19, flu, RSV, vaccination coverage, wastewater surveillance, injury, disability, nutrition, and county/city health indicators.

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
    get_wastewater_data,
    get_resp_net_hospitalizations,
    get_rsv_hospitalizations,
    get_covid_net_hospitalizations,
    get_resp_deaths_pct,
    get_resp_deaths_pct_demo,
    get_rsv_positivity,
    get_nursing_home_resp,
    get_resp_vaccination,
    get_flu_vaccine_doses,
    get_drug_overdose_counts,
    get_drug_overdose_county,
    get_nndss_weekly,
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

# Wastewater surveillance — SARS-CoV-2 signal in New York, last 30 samples
rows = get_wastewater_data(pathogen="sars_cov2", state="NY", limit=30)

# Influenza A wastewater detections nationally since Oct 2024
rows = get_wastewater_data(pathogen="flu_a", start_date="2024-10-01", detected_only=True)

# Measles wastewater signal (2024–present)
rows = get_wastewater_data(pathogen="measles", limit=200)

# RESP-NET: all three networks, current season
rows = get_resp_net_hospitalizations(season="2024-25", age_group="Overall")

# RSV hospitalization rates by age group
rows = get_rsv_hospitalizations(season="2024-25", age_category="0-5 months")

# COVID-NET hospitalization rates — 65+ age group, all states
rows = get_covid_net_hospitalizations(age_category="65-74 years")

# Weekly % of deaths from flu nationally
rows = get_resp_deaths_pct(pathogen="Influenza")

# COVID-19 death % by race/ethnicity in a state
rows = get_resp_deaths_pct_demo(pathogen="COVID-19", demographic_type="Race/Ethnicity", state="California")

# RSV test positivity nationally since Sept 2024
rows = get_rsv_positivity(level="National", start_date="2024-09-01")

# Nursing home RSV cases and vaccination rates
rows = get_nursing_home_resp(jurisdiction="National")

# COVID-19 vaccination coverage by state
rows = get_resp_vaccination(vaccine="COVID-19", geographic_level="State")

# Flu vaccine supply rollout for current season
rows = get_flu_vaccine_doses(season="2024-2025")

# Monthly fentanyl/synthetic opioid deaths in Ohio
rows = get_drug_overdose_counts(state="OH", indicator="Synthetic Opioids")

# County-level overdose deaths in West Virginia
rows = get_drug_overdose_county(state="WV", year="2023")

# Weekly measles cases by state (NNDSS)
rows = get_nndss_weekly(disease="Measles", year="2024")

# Pertussis outbreak tracking
rows = get_nndss_weekly(disease="Pertussis", state="California")

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

### Mortality & chronic disease

| Key                      | Dataset ID  | Coverage     | Description                                          |
| ------------------------ | ----------- | ------------ | ---------------------------------------------------- |
| `leading_death`          | `bi63-dtpu` | 1999–2017    | Leading causes of death by state                     |
| `life_expectancy`        | `w9j2-ggv5` | 1900–2018    | Life expectancy by race and sex                      |
| `mortality_rates`        | `489q-934x` | 2020–present | Provisional quarterly death rates                    |
| `death_rates_historical` | `6rkc-nb2q` | 1900–2017    | Historical death rates for major causes              |
| `weekly_deaths`          | `r8kw-7aab` | 2020–present | Weekly deaths by state: COVID/flu/pneumonia (weekly) |
| `weekly_deaths_by_cause` | `muzy-jte6` | 2020–2023    | Weekly deaths by cause                               |
| `covid_conditions`       | `hk9y-quqm` | 2020–2023    | COVID-19 deaths by contributing condition            |

### County / city health

| Key                 | Dataset ID  | Coverage | Description                             |
| ------------------- | ----------- | -------- | --------------------------------------- |
| `places_county`     | `swc5-untb` | Current  | County health indicators (30+ measures) |
| `places_city`       | `dxpw-cm5u` | Current  | City health indicators (pop. > 50k)     |
| `disability`        | `s2qv-b27b` | Current  | Disability prevalence by type and state |
| `nutrition_obesity` | `hn4x-zwk7` | Current  | Obesity, inactivity, nutrition by state |

### COVID-19

| Key                     | Dataset ID  | Coverage     | Description                                               |
| ----------------------- | ----------- | ------------ | --------------------------------------------------------- |
| `covid_cases`           | `pwn4-m3yp` | 2020–2023    | Weekly COVID-19 cases and deaths by state                 |
| `covid_hosp_archived`   | `7dk4-g6vg` | 2020–2024    | Weekly hospital admissions and bed utilization (archived) |
| `cumulative_covid_hosp` | `xnjn-rdmd` | 2024–present | Preliminary cumulative COVID-19 hospitalization estimates |
| `covid_net`             | `6jg4-xsqq` | 2020–present | COVID-NET hospitalization rates by state/age (weekly)     |
| `epidemic_trends_rt`    | `5dqz-y4ea` | 2020–present | Estimated Rt and epidemic trend category for COVID/flu    |

### Flu & RSV surveillance

| Key                        | Dataset ID  | Coverage     | Description                                                     |
| -------------------------- | ----------- | ------------ | --------------------------------------------------------------- |
| `ari_activity_state`       | `f3zz-zga5` | 2024–present | State-level ARI activity labels — FluView ILI map equivalent    |
| `resp_ed_conditions`       | `v58w-vynu` | 2023–present | Weekly % ED visits by respiratory condition + age group         |
| `resp_lens`                | `ch5i-63ve` | 2021–2024    | RESP-LENS % positivity for 9 viruses by HHS region (ED network) |
| `nvsn_pathogen_positivity` | `kipu-qxy8` | 2017–present | % positivity for 9 pathogens in children with ARI (NVSN)        |
| `resp_net`                 | `kvib-3txy` | 2017–present | RESP-NET hospitalization rates: RSV/COVID/Flu (weekly)          |
| `rsv_net`                  | `29hc-w46k` | 2018–present | RSV-NET RSV hospitalization rates (weekly)                      |
| `rsv_positivity`           | `3cxc-4k8q` | 2020–present | RSV NAAT test positivity by HHS region (NREVSS, weekly)         |
| `nrevss_rsv_historic`      | `52kb-ccu2` | 2010–2020    | Historical RSV lab data by HHS region (NREVSS)                  |
| `cumulative_rsv_hosp`      | `hmye-mqgq` | 2024–present | Preliminary cumulative RSV hospitalization estimates            |

### NHSN hospital data

| Key                 | Dataset ID  | Coverage     | Description                                                          |
| ------------------- | ----------- | ------------ | -------------------------------------------------------------------- |
| `nhsn_hrd`          | `ua7e-t2fy` | 2020–present | Weekly COVID/flu/RSV new admissions, inpatients, ICU by jurisdiction |
| `nursing_home_resp` | `tscn-ryh9` | 2024–present | Nursing home COVID/Flu/RSV cases + vaccination (weekly)              |

### Deaths by pathogen

| Key                    | Dataset ID  | Coverage     | Description                                             |
| ---------------------- | ----------- | ------------ | ------------------------------------------------------- |
| `resp_deaths_pct`      | `4bc2-bbpq` | 2020–present | Provisional % deaths: COVID/Flu/RSV nationally (weekly) |
| `resp_deaths_pct_demo` | `53g5-jf7x` | 2020–present | Provisional % deaths by age/sex/race/state (weekly)     |

### Vaccination

| Key                                 | Dataset ID  | Coverage     | Description                                                    |
| ----------------------------------- | ----------- | ------------ | -------------------------------------------------------------- |
| `resp_vaccination`                  | `5c6r-xi2t` | 2023–present | Weekly flu/COVID-19/RSV coverage, children + adults, by state  |
| `flu_vaccine_doses`                 | `k87d-gv3u` | 2009–present | Cumulative flu vaccine doses distributed nationally (weekly)   |
| `flu_coverage_all_ages`             | `vh55-3he6` | 2009–present | NIS-Flu monthly flu coverage, all ages 6+, by state/age/race   |
| `resp_coverage_adults`              | `ee83-ukst` | 2024–present | NIS-FRVM monthly COVID/flu/RSV coverage among adults, by state |
| `covid_coverage_adults`             | `si7g-c2bs` | 2021–present | NIS-ACM monthly COVID-19 coverage + vaccine confidence, adults |
| `rsv_coverage_adults_60plus`        | `qve4-fp9c` | 2023–present | Weekly cumulative RSV coverage, adults 60+, by jurisdiction    |
| `adult_vaccination_coverage`        | `aetd-68ew` | 2008–present | BRFSS annual coverage: pneumococcal, shingles, tetanus, adults |
| `pregnant_vaccination_coverage`     | `h7pm-wmjc` | 2012–present | Annual flu + Tdap coverage among pregnant women, by state      |
| `nursing_home_vaccination_coverage` | `8w4j-reb4` | 2005–2021    | Annual flu + pneumococcal coverage, nursing home residents     |
| `hcp_vaccination_coverage`          | `xerk-pcm8` | 2013–2021    | Annual flu coverage among health care personnel, by state      |
| `children_vaccination`              | `fhky-rtsk` | 2011–2022    | NIS-Child coverage for children 0–35 months (DTaP, MMR, flu…)  |

### Wastewater surveillance (NWSS / NHSN)

| Key                   | Dataset ID  | Coverage     | Description                                                                    |
| --------------------- | ----------- | ------------ | ------------------------------------------------------------------------------ |
| `wastewater_covid`    | `j9g8-acpt` | 2020–present | NWSS raw RNA concentrations: SARS-CoV-2 (weekly)                               |
| `wastewater_flu`      | `ymmh-divb` | 2022–present | NWSS raw RNA concentrations: Influenza A (weekly)                              |
| `wastewater_measles`  | `akvg-8vrb` | 2024–present | NWSS raw RNA concentrations: Measles (weekly)                                  |
| `wastewater_rsv`      | `45cq-cw4i` | 2023–present | NWSS raw RNA concentrations: RSV (weekly)                                      |
| `wastewater_activity` | `atcp-73re` | 2023–present | NWSS viral activity level scores (Very Low→Very High) for SARS-CoV-2/Flu A/RSV |
| `wastewater_h5`       | `mtpu-urpp` | 2024–present | Avian Influenza A (H5) wastewater concentrations (weekly)                      |

### Drug overdose

| Key                    | Dataset ID  | Coverage     | Description                                        |
| ---------------------- | ----------- | ------------ | -------------------------------------------------- |
| `drug_overdose_vsrr`   | `xkb8-kh2a` | 2015–present | VSRR provisional OD deaths by state/drug (monthly) |
| `drug_overdose_county` | `gb4e-yj24` | 2020–present | VSRR county-level OD death counts (quarterly)      |
| `drug_overdose_state`  | `xbxb-epbu` | 1999–2016    | Drug overdose mortality rates by state/race/sex    |

### ED & surveillance

| Key              | Dataset ID  | Coverage     | Description                                                    |
| ---------------- | ----------- | ------------ | -------------------------------------------------------------- |
| `nssp_ed_visits` | `rdmq-nq56` | 2022–present | NSSP weekly % ED visits for COVID/flu/RSV with trend direction |
| `nndss_weekly`   | `x9gk-5huc` | 2014–present | NNDSS weekly notifiable disease cases (~100 diseases)          |
| `nndss_measles`  | `x9gk-5huc` | 2014–present | NNDSS weekly measles cases (imported & indigenous) by state    |

### Measles (CDC page charts)

These three datasets are fetched directly from the CDC measles data page
(`cdc.gov/measles/data-research/`) rather than data.cdc.gov. They power
the interactive charts on that page and are updated weekly.

| Key                       | Coverage     | Description                                                         |
| ------------------------- | ------------ | ------------------------------------------------------------------- |
| `measles_annual_history`  | 1962–present | Annual national case counts; powers the annotated history chart     |
| `measles_annual_cases`    | 1985–present | Annual national cases with two filter views (1985-Present, 2000-Present) |
| `measles_weekly_cases`    | 2022–present | Weekly national cases by rash onset date                            |

### Birth & demographics

| Key                | Dataset ID  | Coverage | Description                        |
| ------------------ | ----------- | -------- | ---------------------------------- |
| `birth_indicators` | `76vv-a7x8` | Current  | Quarterly birth indicators by race |

## Wastewater surveillance (NWSS)

Four datasets from the [National Wastewater Surveillance System (NWSS)](https://www.cdc.gov/nwss/) track RNA concentrations of pathogens at US wastewater treatment plants. All are updated every Friday.

| Key column                        | Description                                                                          |
| --------------------------------- | ------------------------------------------------------------------------------------ |
| `state_territory`                 | Two-letter state/territory abbreviation                                              |
| `sample_collect_date`             | Date sample was collected at the treatment plant                                     |
| `counties_served` / `county_fips` | County(-ies) whose sewage flows to this site                                         |
| `population_served`               | Estimated persons contributing to the sample                                         |
| `pcr_target_detect`               | `yes` / `no` — whether pathogen RNA was detected                                     |
| `pcr_target_avg_conc`             | Concentration back-calculated to pre-concentration basis                             |
| `pcr_target_flowpop_lin`          | Flow-population-normalized concentration — **best metric for cross-site comparison** |

Use `get_wastewater_data(pathogen=...)` with `pathogen` set to `"sars_cov2"`, `"flu_a"`, `"measles"`, or `"rsv"`.

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
