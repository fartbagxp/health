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

| Key                        | Dataset                                       | ID          | Years        |
| -------------------------- | --------------------------------------------- | ----------- | ------------ |
| `leading_death`            | Leading Causes of Death                       | `bi63-dtpu` | 1999–2017    |
| `mortality_rates`          | Provisional Mortality Rates (quarterly)       | `489q-934x` | 2020–present |
| `weekly_deaths`            | Weekly Death Surveillance                     | `r8kw-7aab` | 2020–present |
| `weekly_deaths_by_cause`   | Weekly Deaths by Cause                        | `muzy-jte6` | 2020–2023    |
| `monthly_deaths_by_cause`  | Monthly Provisional Deaths by Select Cause    | `9dzk-mvmi` | 2020–present |
| `drug_overdose_state`      | Drug Poisoning Mortality by State             | `xbxb-epbu` | 1999–2016    |
| `death_rates_historical`   | Historical Death Rates by Cause               | `6rkc-nb2q` | 1900–2017    |
| `drug_overdose_vsrr`       | VSRR Provisional Drug Overdose Deaths         | `xkb8-kh2a` | 2015–present |
| `drug_overdose_county`     | VSRR County-Level Drug Overdose Deaths        | `gb4e-yj24` | 2020–present |
| `life_expectancy`          | Life Expectancy by Race and Sex               | `w9j2-ggv5` | 1900–2018    |
| `life_expectancy_by_state` | U.S. State Life Expectancy by Sex (composite) | —           | 2018–2021    |

### COVID-19

| Key                     | Dataset                                    | ID          | Years        |
| ----------------------- | ------------------------------------------ | ----------- | ------------ |
| `covid_cases`           | COVID-19 Cases & Deaths (weekly, by state) | `pwn4-m3yp` | 2020–2023    |
| `covid_conditions`      | COVID-19 Contributing Conditions           | `hk9y-quqm` | 2020–2023    |
| `pct_deaths_covid`      | Provisional % Deaths: COVID/Flu/RSV        | —           | 2020–present |
| `pct_deaths_covid_demo` | Provisional % Deaths by Demographics       | —           | 2020–present |

### Hospitalizations

| Key                     | Dataset                                            | ID          | Years        |
| ----------------------- | -------------------------------------------------- | ----------- | ------------ |
| `resp_net`              | RESP-NET: RSV/COVID/Flu Hospitalizations           | `kvib-3txy` | 2017–present |
| `rsv_net`               | RSV-NET Hospitalizations                           | `29hc-w46k` | 2018–present |
| `covid_net`             | COVID-NET Hospitalizations                         | `6jg4-xsqq` | 2020–present |
| `nhsn_hrd`              | Weekly Hospital Respiratory Data (NHSN)            | `ua7e-t2fy` | 2020–present |
| `covid_hosp_archived`   | Weekly COVID-19 Hospitalization Metrics (Archived) | `7dk4-g6vg` | 2020–2024    |
| `cumulative_rsv_hosp`   | Cumulative RSV Hospitalizations by Week            | `hmye-mqgq` | 2024–present |
| `cumulative_covid_hosp` | Cumulative COVID-19 Hospitalizations by Week       | `xnjn-rdmd` | 2024–present |

### Wastewater (NWSS)

| Key                   | Dataset                                  | ID          | Years        |
| --------------------- | ---------------------------------------- | ----------- | ------------ |
| `wastewater_covid`    | NWSS: SARS-CoV-2 wastewater surveillance | `j9g8-acpt` | 2020–present |
| `wastewater_flu`      | NWSS: Influenza A wastewater             | `ymmh-divb` | 2022–present |
| `wastewater_rsv`      | NWSS: RSV wastewater                     | `45cq-cw4i` | 2023–present |
| `wastewater_measles`  | NWSS: Measles wastewater                 | `akvg-8vrb` | 2024–present |
| `wastewater_h5`       | CDC Wastewater: Avian Influenza A (H5)   | `mtpu-urpp` | 2024–present |
| `wastewater_activity` | CDC Wastewater Viral Activity Level      | `atcp-73re` | 2023–present |

### Vaccination

| Key                                 | Dataset                                              | ID          | Years        |
| ----------------------------------- | ---------------------------------------------------- | ----------- | ------------ |
| `flu_coverage_all_ages`             | NIS-Flu: Influenza Vaccination Coverage, 6+ months   | `vh55-3he6` | 2009–present |
| `resp_coverage_adults`              | NIS-FRVM: Fall Respiratory Virus Vaccination, Adults | `ee83-ukst` | 2024–present |
| `covid_coverage_adults`             | NIS-ACM: Adult COVID-19 Vaccination Coverage         | `si7g-c2bs` | 2021–present |
| `rsv_coverage_adults_60plus`        | RSV Vaccination Coverage, Adults 60+                 | `qve4-fp9c` | 2023–present |
| `adult_vaccination_coverage`        | Vaccination Coverage among Adults 18+ (BRFSS)        | `aetd-68ew` | 2008–present |
| `pregnant_vaccination_coverage`     | Vaccination Coverage among Pregnant Women            | `h7pm-wmjc` | 2012–present |
| `nursing_home_vaccination_coverage` | Vaccination Coverage among Nursing Home Residents    | `8w4j-reb4` | 2005–2021    |
| `hcp_vaccination_coverage`          | Vaccination Coverage among Health Care Personnel     | `xerk-pcm8` | 2013–2021    |
| `children_vaccination`              | Vaccination Coverage: Young Children (0–35 months)   | `fhky-rtsk` | 2011–2022    |
| `flu_vaccine_doses`                 | Weekly Cumulative Flu Vaccine Doses Distributed      | `k87d-gv3u` | 2009–present |
| `resp_vaccination`                  | Weekly Respiratory Virus Vaccination Coverage        | `5c6r-xi2t` | 2023–present |

### Population health

| Key                          | Dataset                                        | ID          | Years        |
| ---------------------------- | ---------------------------------------------- | ----------- | ------------ |
| `places_county`              | PLACES: County Health Indicators               | `swc5-untb` | Current      |
| `places_city`                | PLACES: City Health Indicators                 | `dxpw-cm5u` | Current      |
| `disability`                 | Disability Prevalence by State (BRFSS)         | `s2qv-b27b` | Current      |
| `nutrition_obesity`          | Nutrition, Physical Activity & Obesity (BRFSS) | `hn4x-zwk7` | Current      |
| `chronic_disease_indicators` | U.S. Chronic Disease Indicators (CDI)          | `hksd-2xuw` | 2001–present |
| `birth_indicators`           | Quarterly Birth Indicators                     | `76vv-a7x8` | Current      |
| `rsv_positivity`             | RSV Test Positivity (NREVSS)                   | `3cxc-4k8q` | 2020–present |
| `nrevss_rsv_historic`        | NREVSS RSV Lab Data (Historical)               | `52kb-ccu2` | 2010–2020    |

### Surveillance

| Key                        | Dataset                                           | ID          | Years        |
| -------------------------- | ------------------------------------------------- | ----------- | ------------ |
| `nssp_ed_visits`           | NSSP ED Visit Trajectories                        | `rdmq-nq56` | 2022–present |
| `ari_activity_state`       | Acute Respiratory Illness Activity Level by State | `f3zz-zga5` | 2024–present |
| `resp_ed_conditions`       | Respiratory Conditions Treated in ED              | `v58w-vynu` | 2023–present |
| `resp_lens`                | RESP-LENS: Respiratory Virus Lab Positivity (ED)  | `ch5i-63ve` | 2021–2024    |
| `nvsn_pathogen_positivity` | NVSN Viral Pathogen Positivity in Children        | `kipu-qxy8` | 2017–present |
| `nursing_home_resp`        | NHSN Nursing Home Pathogens & Vaccination         | `tscn-ryh9` | 2024–present |
| `epidemic_trends_rt`       | CDC Epidemic Trends and Rt                        | `5dqz-y4ea` | 2020–present |

### Healthcare-Associated Infections (HAI) & Antimicrobial Resistance

Data from CDC's Emerging Infections Program (EIP) and related surveillance networks. Annual case rates, not individual-level records.

| Key              | Dataset                                | ID          | Years        |
| ---------------- | -------------------------------------- | ----------- | ------------ |
| `hai_mrsa`       | HAICViz: Invasive MRSA/MSSA            | `ssz5-s49e` | 2005–2021    |
| `hai_amr`        | HAICViz: AMR (CRAB, CRE, ESBL)         | `v4tm-h8pe` | 2012–present |
| `hai_cdiff`      | HAICViz: C. difficile (CDI)            | `abgz-qs4g` | 2011–present |
| `hai_candidemia` | HAICViz: Candidemia (Invasive Candida) | `34p9-h4us` | 2009–present |

### Notifiable Diseases (NNDSS)

Weekly provisional case counts from the National Notifiable Diseases Surveillance System. The `nndss_weekly` key covers all ~100 diseases; the others are filtered views.

| Key                   | Dataset                          | ID          | Years        |
| --------------------- | -------------------------------- | ----------- | ------------ |
| `nndss_weekly`        | NNDSS Weekly Notifiable Diseases | `x9gk-5huc` | 2014–present |
| `nndss_measles`       | NNDSS Weekly Measles Cases       | `x9gk-5huc` | 2014–present |
| `nndss_sti_chlamydia` | NNDSS Table 1G: Chlamydia        | `hwyy-s2tt` | 2014–present |
| `nndss_sti_gonorrhea` | NNDSS Table 1M: Gonorrhea        | `vx8v-gfyf` | 2014–present |
| `nndss_sti_syphilis`  | NNDSS Table 1HH: Syphilis        | `6ie8-bpiy` | 2014–present |

### Foodborne Pathogens (BEAM)

CDC's [BEAM Dashboard](https://data.cdc.gov/resource/jbhn-e8xn) tracks isolates of _Bacteria, Enterics, Ameba, and Mycotics_ — primarily Campylobacter, Salmonella, Shigella, STEC, and Vibrio — by month, state, source type (Human/Animal/Food), source site, and serotype.

| Key           | Dataset                      | ID          | Years        |
| ------------- | ---------------------------- | ----------- | ------------ |
| `beam_report` | BEAM Dashboard – Report Data | `jbhn-e8xn` | 2018–present |

**Pre-aggregated CSV**: `fetch_beam.py` pulls human isolates and writes a flat national monthly CSV to `data/raw/cdc_open/beam_foodborne.csv` (columns: `date`, `pathogen`, `isolates`).

```bash
# Re-fetch the pre-aggregated national monthly CSV
uv run python -m cdc_open.fetch_beam

# Raw query: all source types, by state
uv run python -m cdc_open query beam_report \
  --select "year,month,state,source_type,pathogen,sum(number_of_isolates)" \
  --where "pathogen='Salmonella'" \
  --order "year,month,state" -f csv

# Human isolates only, all pathogens
uv run python -m cdc_open query beam_report \
  --where "source_type='Human'" \
  --select "year,month,pathogen,serotype_species,number_of_isolates" \
  --order "year DESC,month DESC" -f table
```

### WCMS Visualization Endpoints

CDC chart endpoints that back interactive graphs on CDC disease pages. Accessed via `cdc_open` using the WCMS dataset keys. Not on data.cdc.gov — these are internal JSON feeds.

| Key                      | Dataset                             | Years        |
| ------------------------ | ----------------------------------- | ------------ |
| `measles_annual_history` | Measles Annual Cases (1962–present) | 1962–present |
| `measles_annual_cases`   | Measles Annual Cases (1985–present) | 1985–present |
| `measles_weekly_cases`   | Measles Weekly Cases by Rash Onset  | 2022–present |

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
uv run python -m cdc_open query wastewater_covid \
  --where "state_territory='California'" \
  --order "sample_collect_date DESC" --limit 100 -f table

# VSRR provisional overdose deaths, latest 12 months
uv run python -m cdc_open query drug_overdose_vsrr \
  --where "indicator='Number of Deaths'" \
  --order "year DESC,month DESC" --limit 200 -f csv

# BEAM foodborne pathogens: human Salmonella isolates by state
uv run python -m cdc_open query beam_report \
  --where "source_type='Human' AND pathogen='Salmonella'" \
  --select "year,month,state,serotype_species,number_of_isolates" \
  --order "year DESC,month DESC" -f table

# HAI: MRSA case rates by year
uv run python -m cdc_open query hai_mrsa \
  --order "yearname DESC" --limit 50 -f table

# NNDSS: measles cases by state, current year
uv run python -m cdc_open query nndss_measles \
  --where "year='2025'" \
  --order "week DESC" -f table
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
