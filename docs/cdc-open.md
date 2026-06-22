# CDC Open Data

The `cdc_open` module queries 30+ CDC datasets published on [data.cdc.gov](https://data.cdc.gov/) (Socrata platform). It includes a raw query interface, a dataset registry, and an LLM-powered analysis mode.

No API key required for data queries. The LLM `analyze` command requires `ANTHROPIC_API_KEY`.

---

## Quick start

```bash
# List all available datasets
uv run python -m cdc_open list

# Query a dataset by key name
uv run python -m cdc_open query leading_death -f table

# Raw Socrata query with filter
uv run python -m cdc_open query leading_death \
  --where "year='2017' AND state='United States'" \
  -f table

# Ask a question using the LLM analyzer
uv run python -m cdc_open analyze \
  "What were the top 5 leading causes of death in 2017?"
```

---

## Dataset registry

Use these keys with `uv run python -m cdc_open query <key>`:

### Mortality

| Key                      | Dataset                                 | ID          | Years        |
| ------------------------ | --------------------------------------- | ----------- | ------------ |
| `leading_death`          | Leading Causes of Death                 | `bi63-dtpu` | 1999–2017    |
| `mortality_rates`        | Provisional Mortality Rates (quarterly) | `489q-934x` | 2020–present |
| `weekly_deaths`          | Weekly Death Surveillance               | `r8kw-7aab` | 2020–present |
| `weekly_deaths_by_cause` | Weekly Deaths by Cause                  | `muzy-jte6` | 2020–2023    |
| `drug_overdose_state`    | Drug Poisoning Mortality by State       | `xbxb-epbu` | 1999–2016    |
| `historical_death_rates` | Historical Death Rates by Cause         | —           | 1900–2017    |
| `vsrr_overdose`          | VSRR Provisional Drug Overdose Deaths   | —           | 2015–present |
| `vsrr_overdose_county`   | VSRR County-Level Drug Overdose Deaths  | —           | 2019–present |
| `life_expectancy`        | Life Expectancy by Race and Sex         | `w9j2-ggv5` | 1900–2018    |

### COVID-19

| Key                     | Dataset                                    | ID          | Years        |
| ----------------------- | ------------------------------------------ | ----------- | ------------ |
| `covid_cases`           | COVID-19 Cases & Deaths (weekly, by state) | `pwn4-m3yp` | 2020–2023    |
| `covid_conditions`      | COVID-19 Contributing Conditions           | `hk9y-quqm` | 2020–2023    |
| `pct_deaths_covid`      | Provisional % Deaths: COVID/Flu/RSV        | —           | 2020–present |
| `pct_deaths_covid_demo` | Provisional % Deaths by Demographics       | —           | 2020–present |

### Hospitalizations

| Key                | Dataset                                      | ID  | Years        |
| ------------------ | -------------------------------------------- | --- | ------------ |
| `resp_net`         | RESP-NET: RSV/COVID/Flu Hospitalizations     | —   | 2017–present |
| `rsv_net`          | RSV-NET Hospitalizations                     | —   | 2018–present |
| `covid_net`        | COVID-NET Hospitalizations                   | —   | 2020–present |
| `cumulative_rsv`   | Cumulative RSV Hospitalizations by Week      | —   | 2023–present |
| `cumulative_covid` | Cumulative COVID-19 Hospitalizations by Week | —   | 2020–present |

### Wastewater (NWSS)

| Key                | Dataset                                  | Years        |
| ------------------ | ---------------------------------------- | ------------ |
| `nwss_covid`       | NWSS: SARS-CoV-2 wastewater surveillance | 2020–present |
| `nwss_flu_a`       | NWSS: Influenza A wastewater             | 2022–present |
| `nwss_rsv`         | NWSS: RSV wastewater                     | 2023–present |
| `nwss_measles`     | NWSS: Measles wastewater                 | 2024–present |
| `nwss_h5`          | NWSS: Avian Influenza A (H5) wastewater  | 2024–present |
| `wastewater_viral` | CDC Wastewater Viral Activity Level      | 2023–present |

### Vaccination

| Key                          | Dataset                                              | Years        |
| ---------------------------- | ---------------------------------------------------- | ------------ |
| `flu_vaccine_coverage`       | NIS-Flu: Influenza Vaccination Coverage, 6+ months   | 2011–present |
| `fall_rsvax_adults`          | NIS-FRVM: Fall Respiratory Virus Vaccination, Adults | 2023–present |
| `covid_vax_adults`           | NIS-ACM: Adult COVID-19 Vaccination Coverage         | 2021–present |
| `rsv_vax_adults`             | RSV Vaccination Coverage, Adults 60+                 | 2023–present |
| `brfss_vaccination`          | Vaccination Coverage among Adults 18+ (BRFSS)        | 2012–present |
| `pregnant_vaccination`       | Vaccination Coverage among Pregnant Women            | 2012–present |
| `nursing_home_vaccination`   | Vaccination Coverage among Nursing Home Residents    | 2020–present |
| `hcp_vaccination`            | Vaccination Coverage among Health Care Personnel     | 2011–present |
| `young_children_vaccination` | Vaccination Coverage: Young Children (0–35 months)   | 2011–present |
| `weekly_flu_doses`           | Weekly Cumulative Flu Vaccine Doses Distributed      | 2020–present |
| `weekly_resp_vax`            | Weekly Respiratory Virus Vaccination Coverage        | 2023–present |

### Population health

| Key                     | Dataset                                        | ID          | Years        |
| ----------------------- | ---------------------------------------------- | ----------- | ------------ |
| `places_county`         | PLACES: County Health Indicators               | `swc5-untb` | Current      |
| `places_city`           | PLACES: City Health Indicators                 | `dxpw-cm5u` | Current      |
| `disability`            | Disability Prevalence by State (BRFSS)         | `s2qv-b27b` | Current      |
| `nutrition_obesity`     | Nutrition, Physical Activity & Obesity (BRFSS) | `hn4x-zwk7` | Current      |
| `births_quarterly`      | Quarterly Birth Indicators                     | —           | Current      |
| `rsv_test_positivity`   | RSV Test Positivity (NREVSS)                   | —           | 2018–present |
| `nrevss_rsv_historical` | NREVSS RSV Lab Data (Historical)               | —           | 2000–present |

### Surveillance

| Key                    | Dataset                                           | Years        |
| ---------------------- | ------------------------------------------------- | ------------ |
| `nssp_ed_trajectories` | NSSP ED Visit Trajectories                        | 2020–present |
| `ari_activity`         | Acute Respiratory Illness Activity Level by State | 2020–present |
| `resp_conditions_ed`   | Respiratory Conditions Treated in ED              | 2020–present |
| `resp_lens`            | RESP-LENS: Respiratory Virus Lab Positivity (ED)  | 2022–present |
| `nvsn_pathogen`        | NVSN Viral Pathogen Positivity in Children        | 2015–present |
| `nhsn_nursing`         | NHSN Nursing Home Pathogens & Vaccination         | 2020–present |
| `epidemic_trends`      | CDC Epidemic Trends and Rt                        | 2020–present |

---

## Common query patterns

```bash
# Leading causes of death, United States, all years
uv run python -m cdc_open query leading_death \
  --where "state='United States'" \
  --order "year" -f csv

# Weekly deaths: COVID + flu + pneumonia, last 52 weeks, all states
uv run python -m cdc_open query weekly_deaths \
  --where "state!='United States'" \
  --select "state,end_date,covid_19_deaths,influenza_deaths,total_deaths" \
  --order "end_date DESC" --limit 2600 -f csv

# Drug overdose deaths by state, 2000-2016
uv run python -m cdc_open query drug_overdose_state \
  --where "sex='Both sexes' AND age='All Ages'" \
  --select "year,state,death_rate" \
  --order "year,state" -f csv

# PLACES: county obesity rates in Texas
uv run python -m cdc_open query places_county \
  --where "stateabbr='TX' AND measureid='OBESITY'" \
  --select "locationname,data_value" \
  --order "data_value DESC" -f table

# NWSS wastewater COVID trends, California sites
uv run python -m cdc_open query nwss_covid \
  --where "wwtp_jurisdiction='California'" \
  --order "date DESC" --limit 100 -f table

# VSRR provisional overdose deaths, latest 12 months
uv run python -m cdc_open query vsrr_overdose \
  --where "indicator='Number of Deaths'" \
  --order "year DESC,month DESC" --limit 200 -f csv
```

---

## LLM analysis mode

The `analyze` command lets you ask natural language questions. The LLM calls `cdc_open query` as a tool internally to fetch the relevant data, then answers.

```bash
# Requires ANTHROPIC_API_KEY in .env
uv run python -m cdc_open analyze \
  "What are the top 10 causes of death in the US for the most recent year?"

uv run python -m cdc_open analyze \
  "Which states had the highest drug overdose death rates in 2015?"

uv run python -m cdc_open analyze \
  "How has COVID-19 as a percentage of weekly deaths changed over time?"

uv run python -m cdc_open analyze \
  "Which counties in Florida have the highest obesity rates?"

# Show the raw data alongside the analysis
uv run python -m cdc_open analyze \
  "What is the SARS-CoV-2 wastewater signal trend in the last 3 months?" \
  --dump-data --dump-format csv
```

---

## Python SDK

```python
from cdc_open.sdk import query_dataset, list_datasets

# List all registered datasets
for key, dataset in list_datasets().items():
    print(f"{key}: {dataset.name} ({dataset.years})")

# Query a dataset
rows = query_dataset(
    key="leading_death",
    where="state='United States'",
    order="year",
    limit=1000,
)

# Raw Socrata query by dataset ID
from cdc_open.client import CdcOpenClient
client = CdcOpenClient()
rows = client.query(
    dataset_id="bi63-dtpu",
    where="year='2017'",
    select="cause_name,deaths,age_adjusted_death_rate",
    order="deaths DESC",
    limit=20,
)
```

---

## Direct Socrata API access

For datasets not in the registry, query by Socrata ID directly:

```bash
# Any data.cdc.gov dataset by ID
uv run python -m cdc_open query bi63-dtpu \
  --where "year='2017' AND state='United States'" \
  -f table
```

Find dataset IDs at [data.cdc.gov](https://data.cdc.gov/) — the ID is the 9-character alphanumeric slug in the dataset URL (e.g. `bi63-dtpu`).
