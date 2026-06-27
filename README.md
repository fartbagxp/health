# Overview

[![Deploy Docs](https://github.com/fartbagxp/health/actions/workflows/docs.yml/badge.svg)](https://github.com/fartbagxp/health/actions/workflows/docs.yml)
[![Update CDC Open Data](https://github.com/fartbagxp/health/actions/workflows/update_cdc_open.yml/badge.svg)](https://github.com/fartbagxp/health/actions/workflows/update_cdc_open.yml)
[![Update WONDER](https://github.com/fartbagxp/health/actions/workflows/update_wonder.yml/badge.svg)](https://github.com/fartbagxp/health/actions/workflows/update_wonder.yml)
[![Update WISQARS](https://github.com/fartbagxp/health/actions/workflows/update_wisqars.yml/badge.svg)](https://github.com/fartbagxp/health/actions/workflows/update_wisqars.yml)
[![Datasets](https://img.shields.io/badge/datasets-70-4c9be8)](https://fartbagxp.github.io/health/)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-8a2be2)](https://fartbagxp.github.io/health/)

This is a repository to collect and run fun experiments on various publicly available health APIs.

**[Documentation site →](https://fartbagxp.github.io/health/)**

## Sources

| Data Source                                                           | Module          | API                           |
| --------------------------------------------------------------------- | --------------- | ----------------------------- |
| [Wide-ranging ONline Data for Epidemiologic Research (WONDER)]        | `src/wonder/`   | CDC WONDER XML API            |
| [National Syndromic Surveillance Program (NSSP)]                      | `src/nssp/`     | CMU Delphi Epidata API        |
| [WISQARS Injury & Violence Data]                                      | `src/wisqars/`  | data.cdc.gov (Socrata)        |
| [ATSDR GRASP Disease APIs]                                            | `src/grasp/`    | gis.cdc.gov/grasp (REST/JSON) |
| [National Immunization Survey (NIS)]                                  | `src/nis/`      | CDC FTP fixed-width DAT       |
| [National Wastewater Surveillance System (NWSS)]                      | `src/cdc_open/` | data.cdc.gov (Socrata)        |
| [National Respiratory and Enteric Virus Surveillance System (NREVSS)] | `src/cdc_open/` | data.cdc.gov (Socrata)        |
| [National Healthcare Safety Network (NHSN)]                           | `src/cdc_open/` | data.cdc.gov (Socrata)        |
| [Children Vaccination]                                                | `src/cdc_open/` | data.cdc.gov (Socrata)        |
| [CDC Open Data (data.cdc.gov)]                                        | `src/cdc_open/` | data.cdc.gov (Socrata)        |
| [CDC BEAM (Bacteria, Enterics, Ameba, and Mycotics)]                  | `src/cdc_open/` | data.cdc.gov (Socrata)        |

---

### CDC WONDER — [docs](https://fartbagxp.github.io/health/wonder/)

[CDC WONDER](https://wonder.cdc.gov/) is CDC's public data query system covering mortality, births, vaccine adverse events, and more. It exposes an unauthenticated XML-over-HTTPS API. The [Wonder API](https://wonder.cdc.gov/wonder/help/wonder-api.html) accepts POST requests with XML query parameters including `accept_datause_restrictions=true`.

26 datasets are supported across mortality, infant/birth, natality, environmental, and VAERS categories. An LLM-powered query builder converts natural language into the XML query format.

The soft rate limit is a query every two minutes.

Refer to [WONDER README](src/wonder/README.md) for more information.

### NSSP — National Syndromic Surveillance Program — [docs](https://fartbagxp.github.io/health/nssp/)

[NSSP](https://www.cdc.gov/nssp/) tracks the proportion of emergency department visits attributed to COVID-19, influenza, and RSV, updated weekly. This module uses the [CMU Delphi Epidata API](https://cmu-delphi.github.io/delphi-epidata/api/covidcast-signals/nssp.html) — a separate public API (no auth required) that processes and exposes NSSP signals at national, state, HHS region, and county level.

Time values use epiweek format (YYYYWW, e.g. `202518` = week 18 of 2025).

```bash
uv run python -m nssp query covid --geo-type nation --geo-value us -f table
uv run python -m nssp hhs influenza --region 4
uv run python -m nssp national --start 202401 -f csv
```

Refer to [NSSP source](src/nssp/) for more information.

### WISQARS — Web-based Injury Statistics Query and Reporting System — [docs](https://fartbagxp.github.io/health/wisqars/)

[WISQARS](https://wisqars.cdc.gov/) is CDC's injury data portal covering fatal and nonfatal injuries, violence, and overdose. WISQARS has no public API, but its underlying NCHS datasets are available on data.cdc.gov. 5 datasets are supported:

| Dataset               | Coverage     | Description                                                              |
| --------------------- | ------------ | ------------------------------------------------------------------------ |
| `injury_mortality`    | 1999–2016    | Fatal injury by mechanism, intent, age, race, sex                        |
| `injury_national`     | 2019–present | National firearm/suicide/OD/homicide — monthly & annual                  |
| `injury_state`        | 2019–present | State-level firearm/suicide/OD/homicide                                  |
| `injury_county`       | 2019–present | County-level firearm/suicide/OD/homicide                                 |
| `injury_census_tract` | 2022–present | Census-tract-level homicide & drug OD via Bayesian small-area estimation |

Firearm (`FA_Deaths`, `FA_Homicide`, `FA_Suicide`) and gunshot wound fatality data are available through the mapping datasets at national, state, county, and census-tract granularity. The `injury_mortality` dataset additionally supports filtering by `mechanism = 'Firearm'` across all intent categories from 1999–2016. Nonfatal injury counts are not available via a public API — use the [WISQARS interactive tool](https://wisqars.cdc.gov/) for nonfatal queries.

```bash
uv run python -m wisqars mortality --intent Suicide --mechanism Firearm -f csv
uv run python -m wisqars state --intent Drug_OD --year 2023 -f table
uv run python -m wisqars national --intent FA_Deaths --type year -f table
uv run python -m wisqars county --state Texas --intent FA_Deaths --year 2023
uv run python -m wisqars tract --state Texas --intent All_Homicide --year 2022
```

Refer to [WISQARS source](src/wisqars/) for more information.

### ATSDR GRASP — Geographic Research, Analysis, and Services Program — [docs](https://fartbagxp.github.io/health/grasp/)

[GRASP](https://gis.cdc.gov/grasp/) is a suite of disease-specific REST APIs maintained by ATSDR and hosted at `gis.cdc.gov/grasp/`. Each application exposes a `GetData_JSON` endpoint returning patient-level or aggregate records as JSON. No authentication or API key is required. Data is fetched in full and cached locally for 24 hours.

All four datasets are sourced via the [CMU Delphi Epidata API](https://cmu-delphi.github.io/delphi-epidata/) (fluview/flusurv endpoints), which pulls directly from CDC GRASP and provides a clean REST interface. No authentication required.

| Dataset            | Coverage         | Description                                                                       |
| ------------------ | ---------------- | --------------------------------------------------------------------------------- |
| `hantavirus`       | pre-1993–present | Patient-level cases: onset date, state FIPS, and outcome                          |
| `fluview_ili`      | 1997-98–present  | Weekly ILINet outpatient ILI % by nat/HHS region/census region/state (via Delphi) |
| `fluview_clinical` | 2016-17–present  | Weekly WHO/NREVSS clinical lab flu test positivity by region (via Delphi)         |
| `flusurv_net`      | 2009-10–present  | Weekly flu hospitalization rates by age, race, sex, and flu type (via Delphi)     |

**Hantavirus:** All ~890 confirmed US cases from CDC's Viral Special Pathogens Branch via NNDSS. Each record includes `IllnessOnsetDate`, `StateFIPS`, and `Outcome` (Alive/Dead/Unknown). Overall case fatality rate ~35%.

**FluView ILINet:** Weekly influenza-like illness percentage from CDC's outpatient surveillance network. Regions: `nat` (national), `hhs1`–`hhs10` (HHS), `cen1`–`cen9` (census), or any 2-letter lowercase state code. Fields include `wili` (weighted ILI %), `ili`, patient/provider counts, and age-stratified ILI counts.

**FluView Clinical Labs:** Weekly WHO/NREVSS clinical laboratory flu test positivity. Same region coverage as ILINet. Fields: `total_specimens`, `total_a`, `total_b`, `percent_positive`, `percent_a`, `percent_b`.

**FluSurv-NET:** Weekly lab-confirmed hospitalization rates per 100,000. 3 surveillance networks (`network_all`, `network_eip`, `network_ihsp`) + 12 states (CA, CO, CT, GA, MD, MI, MN, NM, OH, OR, TN, UT). Per-record rates by age (`rate_age_0`=0–4 yr through `rate_age_7`=85+ yr), race/ethnicity, sex, and flu type (A/B).

```bash
uv run python -m grasp list

# Hantavirus
uv run python -m grasp hantavirus cases --outcome Dead -f table
uv run python -m grasp hantavirus by-year -f table
uv run python -m grasp hantavirus by-state -f table

# FluView ILI (ILINet outpatient)
uv run python -m grasp fluview ili data --region nat ca tx --epiweeks 202001-202026
uv run python -m grasp fluview ili by-region --epiweeks 201940-202020 -f table

# FluView Clinical Labs (WHO/NREVSS)
uv run python -m grasp fluview clinical data --region nat hhs1 hhs2 --epiweeks 202001-202026

# FluSurv-NET hospitalizations
uv run python -m grasp flusurv by-season --location network_all -f table
uv run python -m grasp flusurv by-location --season 2019-20 -f table
uv run python -m grasp flusurv data --location CA OH --epiweeks 202001-202020 -f csv
```

**Python SDK:**

```python
from grasp.sdk import get_hantavirus_cases, summarize_hantavirus_by_year, summarize_hantavirus_by_state

cases = get_hantavirus_cases(state_name="New Mexico", outcome="Dead")
by_year = summarize_hantavirus_by_year()
# [{'year': 'Before 1993', 'cases': 4, 'deaths': 3}, {'year': '1993', 'cases': 27, ...}, ...]

from grasp.sdk import get_fluview_ili, summarize_fluview_ili_by_region

# National + state ILI for 2019-20 season
ili = get_fluview_ili(regions=["nat", "ca", "tx"], epiweeks="201940-202020")
# [{'region': 'ca', 'epiweek': 201940, 'wili': 2.1, 'ili': 2.1, ...}, ...]

# Peak/avg wILI across all national/HHS/census regions
summary = summarize_fluview_ili_by_region(epiweeks="201940-202020")
# [{'region': 'cen7', 'peak_wili': 13.49, 'avg_wili': 6.3, 'weeks': 33}, ...]

from grasp.sdk import get_fluview_clinical

lab = get_fluview_clinical(regions=["nat", "hhs1"], epiweeks="202001-202026")
# [{'region': 'hhs1', 'epiweek': 202001, 'percent_positive': 18.2, ...}, ...]

from grasp.sdk import get_flusurv_net, summarize_flusurv_by_season, summarize_flusurv_by_location

records = get_flusurv_net(locations=["CA", "OH", "network_all"], season="2024-25")
summary = summarize_flusurv_by_season(location="CA")
# [{'season': '2009-10', 'location': 'CA', 'peak_rate': 3.2, 'avg_rate': 0.71, 'weeks': 30}, ...]
by_loc = summarize_flusurv_by_location(season="2019-20")
# [{'location': 'CT', 'name': 'Connecticut', 'peak_rate': 14.2, 'avg_rate': 3.43, ...}, ...]
```

### NIS — National Immunization Survey — [docs](https://fartbagxp.github.io/health/nis/)

The [NIS](https://www.cdc.gov/vaccines/imz-managers/nis/) is CDC's annual random-digit-dial telephone survey measuring childhood and adolescent vaccination coverage across the US. Two surveys are covered:

| Survey        | Ages         | Index page                                            |
| ------------- | ------------ | ----------------------------------------------------- |
| **NIS-Child** | 19–35 months | https://www.cdc.gov/nis/php/datasets-child/index.html |
| **NIS-Teen**  | 13–17 years  | https://www.cdc.gov/nis/php/datasets-teen/index.html  |

Data are distributed as **fixed-width ASCII `.dat` files** (50–200 MB each) with accompanying SAS and R import programs. This module is a pure-Python replacement — it fetches the SAS codebook to derive column positions, then streams the `.dat` file without writing anything to disk.

**Geographic scope of public-use files:** national and state level. County-level identifiers are suppressed and require [CDC Research Data Center](https://www.cdc.gov/rdc/) access.

**Vaccines tracked (NIS-Child):** DTaP, MMR, Polio, Hib, PCV, HepB, HepA, Varicella, Rotavirus, Influenza, and combined series (4:3:1, 7-vaccine).

**Vaccines tracked (NIS-Teen):** Tdap, MCV4 (meningococcal), HPV, HepA, HepB, Influenza, Meningococcal B.

**Hesitancy columns:** `SHOT_HES` (both surveys), `NOT_SURE_VACC` (teen).

```bash
# List available years
uv run python -m nis list child        # 2011–2022
uv run python -m nis list teen

# Stream raw respondent records — no storage; values are raw SAS codes
uv run python -m nis stream child 2022 --limit 10 -f json
uv run python -m nis stream teen 2022 --state CA -f csv

# State-level UTD rates (unweighted %; use PROVWT_D/PROVWT_C for survey-weighted estimates)
uv run python -m nis rates child 2022 -f table
uv run python -m nis rates teen 2022 --vaccines P_UTDHPV13 P_UTDTDAP -f csv

# National summary
uv run python -m nis national child 2022
uv run python -m nis national teen 2022 --vaccines P_UTDHPV13
```

**Python SDK:**

```python
from nis.sdk import list_years, stream_records, get_vaccination_rates, get_national_rates

# Stream respondent-level microdata (never touches disk)
for rec in stream_records("child", 2022, state="California"):
    mmr_utd = rec["P_UTDMMX"]        # '1' = UTD, '0' = not UTD, '' = unknown
    state_fips = rec["RETEILI"]
    weight = rec["PROVWT_D"]          # survey weight for representative estimates

# Aggregate UTD rates by state
rows = get_vaccination_rates("child", 2022)
# rows[0] → {'state_fips': '01', 'state_name': 'Alabama', 'P_UTDMMX_pct': 91.3, ...}

# National rates
nat = get_national_rates("teen", 2022, vaccines=["P_UTDHPV13", "P_UTDTDAP"])
print(nat["P_UTDHPV13_pct"])   # % of teens with completed HPV series
```

---

### CDC Open Data — [docs](https://fartbagxp.github.io/health/cdc-open/)

[data.cdc.gov](https://data.cdc.gov) is the CDC's public open data portal, built on the Socrata platform. It exposes datasets as a standard REST/JSON API ([SODA](https://dev.socrata.com/)) — no authentication required for read access.

32 datasets are available covering mortality, birth indicators, COVID-19, respiratory surveillance, wastewater (NWSS), vaccination, disability, nutrition, overdose, notifiable diseases (NNDSS), NHSN nursing homes, NREVSS RSV, NSSP ED visits, and children's vaccination. An LLM-powered `analyze` command uses Claude to fetch and synthesize data in response to natural language questions.

```bash
uv run python -m cdc_open list
uv run python -m cdc_open analyze "Which states had the highest drug overdose death rates in 2023?"
```

Refer to [CDC Open README](src/cdc_open/README.md) for more information.

### CDC BEAM — Bacteria, Enterics, Ameba, and Mycotics

[BEAM](https://www.cdc.gov/beam/dashboard/index.html) is CDC's interactive dashboard for enteric pathogen surveillance. It tracks lab-confirmed human, animal, and food isolates for five pathogens — Campylobacter, Salmonella, Shigella, STEC (Shiga toxin-producing E. coli), and Vibrio — reported monthly by state health labs since 2018.

The raw dataset (`jbhn-e8xn`) has ~200k rows of state-level isolate records. `fetch_beam.py` aggregates these to a national monthly totals CSV keyed by `(date, pathogen)`.

```bash
uv run python -m cdc_open.fetch_beam
# → data/raw/cdc_open/beam_foodborne.csv
```

Data sourced from the [BEAM Dashboard – Report Data](https://data.cdc.gov/Foodborne-Waterborne-and-Related-Diseases/BEAM-Dashboard-Report-Data/jbhn-e8xn) Socrata dataset.

[CDC]: https://www.cdc.gov
[Wide-ranging ONline Data for Epidemiologic Research (WONDER)]: https://wonder.cdc.gov/wonder/help/wonder-api.html
[National Syndromic Surveillance Program (NSSP)]: https://www.cdc.gov/nssp/
[WISQARS Injury & Violence Data]: https://wisqars.cdc.gov/
[ATSDR GRASP Disease APIs]: https://gis.cdc.gov/grasp/
[National Immunization Survey (NIS)]: https://www.cdc.gov/vaccines/imz-managers/nis/
[National Wastewater Surveillance System (NWSS)]: https://www.cdc.gov/nwss/about.html
[National Respiratory and Enteric Virus Surveillance System (NREVSS)]: https://www.cdc.gov/nrevss/php/dashboard/index.html
[National Healthcare Safety Network (NHSN)]: https://www.cdc.gov/nhsn/datastat/index.html
[Children Vaccination]: https://data.cdc.gov/Child-Vaccinations/Vaccination-Coverage-among-Young-Children-0-35-Mon/fhky-rtsk/about_data
[CDC Open Data (data.cdc.gov)]: https://data.cdc.gov
[CDC BEAM (Bacteria, Enterics, Ameba, and Mycotics)]: https://www.cdc.gov/beam/dashboard/index.html
