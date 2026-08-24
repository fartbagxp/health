# Overview

[![Deploy Docs](https://github.com/fartbagxp/health/actions/workflows/docs.yml/badge.svg)](https://github.com/fartbagxp/health/actions/workflows/docs.yml)
[![Update CDC Open Data](https://github.com/fartbagxp/health/actions/workflows/update_cdc_open.yml/badge.svg)](https://github.com/fartbagxp/health/actions/workflows/update_cdc_open.yml)
[![Update WONDER](https://github.com/fartbagxp/health/actions/workflows/update_wonder.yml/badge.svg)](https://github.com/fartbagxp/health/actions/workflows/update_wonder.yml)
[![Update WISQARS](https://github.com/fartbagxp/health/actions/workflows/update_wisqars.yml/badge.svg)](https://github.com/fartbagxp/health/actions/workflows/update_wisqars.yml)
[![Update SEER](https://github.com/fartbagxp/health/actions/workflows/update_seer.yml/badge.svg)](https://github.com/fartbagxp/health/actions/workflows/update_seer.yml)
[![Update NCHS DQS](https://github.com/fartbagxp/health/actions/workflows/update_dqs.yml/badge.svg)](https://github.com/fartbagxp/health/actions/workflows/update_dqs.yml)
[![Datasets](https://img.shields.io/badge/cdc--open%20datasets-68-4c9be8)](https://fartbagxp.github.io/health/data-catalog/)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-8a2be2)](https://fartbagxp.github.io/health/)

This is a repository to collect and run fun experiments on various publicly available health APIs.

**[Documentation site →](https://fartbagxp.github.io/health/)**

## Sources

| Data Source                                                           | Module          | API                                   |
| --------------------------------------------------------------------- | --------------- | ------------------------------------- |
| [Wide-ranging ONline Data for Epidemiologic Research (WONDER)]        | `src/wonder/`   | CDC WONDER XML API                    |
| [National Syndromic Surveillance Program (NSSP)]                      | `src/nssp/`     | CMU Delphi Epidata API                |
| [WISQARS Injury & Violence Data]                                      | `src/wisqars/`  | data.cdc.gov (Socrata)                |
| [ATSDR GRASP Disease APIs]                                            | `src/grasp/`    | gis.cdc.gov/grasp (REST/JSON)         |
| [National Immunization Survey (NIS)]                                  | `src/nis/`      | CDC FTP fixed-width DAT               |
| [National Wastewater Surveillance System (NWSS)]                      | `src/cdc_open/` | data.cdc.gov (Socrata)                |
| [National Respiratory and Enteric Virus Surveillance System (NREVSS)] | `src/cdc_open/` | data.cdc.gov (Socrata)                |
| [National Healthcare Safety Network (NHSN)]                           | `src/cdc_open/` | data.cdc.gov (Socrata)                |
| [Children Vaccination]                                                | `src/cdc_open/` | data.cdc.gov (Socrata)                |
| [CDC Open Data (data.cdc.gov)]                                        | `src/cdc_open/` | data.cdc.gov (Socrata)                |
| [CDC BEAM (Bacteria, Enterics, Ameba, and Mycotics)]                  | `src/cdc_open/` | data.cdc.gov (Socrata)                |
| [SEER Cancer Statistics]                                              | `src/seer/`     | seer.cancer.gov (SEER\*Explorer JSON) |
| [NCHS Data Query System (DQS)]                                        | `src/nchs_dqs/` | data.cdc.gov (Socrata)                |
| [Environmental Public Health Tracking (EPHT)]                         | `src/epht/`     | ephtracking.cdc.gov (REST/JSON)       |

See the [Data Catalog](https://fartbagxp.github.io/health/data-catalog/) for the full, verified inventory across all systems, their CDC center, collection method, refresh cadence, and archive status.

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

68 datasets are available covering mortality, birth indicators, COVID-19, respiratory surveillance, wastewater (NWSS, including SARS-CoV-2/flu/RSV/measles/H5/mpox and the public activity-level metric), vaccination, disability, nutrition, chronic disease, overdose, notifiable diseases (NNDSS), NHSN nursing homes, NREVSS RSV, NSSP ED visits, children's vaccination, NHANES measured obesity, the NCHS Rapid Surveys System, and CFA's Epidemic Trends nowcast. An LLM-powered `analyze` command uses Claude to fetch and synthesize data in response to natural language questions. Not every dataset is wired into a chart yet — `cdc-open list --uncharted` shows what's collected but unused. Near-real-time additions (CFA Epidemic Trends, Mpox/NWSS-metric wastewater) are summarized in the [Data Catalog](https://fartbagxp.github.io/health/data-catalog/).

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

### SEER — Cancer Statistics — [docs](https://fartbagxp.github.io/health/seer/)

[SEER\*Explorer](https://seer.cancer.gov/statistics-network/explorer/) (Surveillance, Epidemiology, and End Results) is NCI's cancer statistics system. The `seer` module calls the same JSON endpoints the SEER\*Explorer web app uses to render its charts — undocumented, but public and unauthenticated. It covers 70+ cancer sites with incidence and U.S. mortality rates/counts by year, sex, race, and age group back to 1975.

```bash
uv run python -m seer sites --search breast
uv run python -m seer mortality --site 55 --sex female -f csv
uv run python -m seer mortality --site 47 --compare-by race -f csv
uv run python -m seer by-age --site 1 -f csv
uv run python -m seer compare-sites 55 47 66 -f csv
```

Refer to `uv run python -m seer.download` to refresh the bundled cancer-site catalog.

### NCHS DQS — Data Query System (Health, United States)

The [NCHS Data Query System](https://www.cdc.gov/nchs/dqs/) is CDC/NCHS's unified query layer over the "Health, United States" report family, drawing from the national surveys (NHANES, NHIS, NHAMCS, NVSS, NPALS, NHCS). Every topic is published as a Socrata dataset on data.cdc.gov sharing one tidy schema (`classification`/`group`/`subgroup`/`estimate_type`/`time_period`/`estimate` with confidence intervals), so a single `query` verb covers all 28 registered datasets. `classification = 'Total'` is the all-persons row. Coverage the other sources don't have: chronic disease and risk factors, nutrition, oral health, disability, self-reported health, the health-care system (beds, ED visits, utilization), workforce, spending, and long-term care.

```bash
uv run python -m nchs_dqs list --uncharted     # the backlog of datasets not yet charted
uv run python -m nchs_dqs trend national-health-spending -f csv
uv run python -m nchs_dqs query low-birthweight --where "classification='Geographic Characteristic'" -f csv
```

`fetch_dqs.py` archives the charted slices to `data/raw/dqs/` on a weekly schedule. Refer to [nchs_dqs README](src/nchs_dqs/README.md) for the CLI and the charted-vs-backlog dataset list.

---

## State, county & local sources ([docs](https://fartbagxp.github.io/health/local/))

Every source above is federal, and federal surveillance mostly stops at the state line. Two docs survey what is available below it. [`docs/local.md`](docs/local.md) covers endpoints verified against live data: county and census-tract figures for cancer, COVID, flu, tickborne disease, and foodborne outbreaks. [`docs/state-portals.md`](docs/state-portals.md) catalogs the official health data portal for all 50 states and DC, grouped by the software behind them, and ranks the states by how much work ingestion would take.

It is a research catalog, not a module. Nothing there is downloaded, deliberately, since `data/` is already 352MB. Endpoints were probed live on 2026-08-02 and marked verified (✅), outside the network allowlist (⚠️), or no-API (❌).

Highlights:

- **CDC PLACES** (`cwsq-ngmh`) covers 40 chronic-disease and health-behavior measures at census-tract level nationwide. Modeled estimates, not counts.
- **County COVID/flu/RSV** is already reachable with the installed `nssp` module via `--geo-type county`, so no new code and no new storage.
- **Lyme with county FIPS** (`x5j9-wybp`) has real county geography, suppressed wherever counts are small.
- **NY tick surveillance** (`vzbp-i2d4`) gives county-level tick density and pathogen infection prevalence, with no federal equivalent.
- **NORS** (`5xkq-dg7x`) holds 66,713 foodborne and waterborne outbreak records back to 1971, at state level.
- **State Cancer Profiles** returns county cancer incidence and mortality with confidence intervals, average annual counts and 5-year trends, through an undocumented `output=1` CSV export. One state per request.
- **County Health Rankings** publishes a single 13MB national county CSV keyed on FIPS. Funding ends December 2026, so archive it once rather than scheduling it.
- **State and county Socrata portals** such as `health.data.ny.gov`, `data.pa.gov` and `data.cityofchicago.org` run the same platform as `data.cdc.gov`, so the existing `cdc_open` client works against them unchanged via `Dataset.base_url`.

California's county infectious disease series (`data.chhs.ca.gov`, CKAN) is the richest local dataset found: 199,125 rows covering 52 reportable diseases across all 59 counties, 2001–2023, sex-stratified with population denominators and confidence intervals. All six tickborne conditions and the major foodborne ones sit in one 13MB file.

The doc also records the network allowlist status of every host. The finding worth knowing up front is that allowlisted hosts flap. `services*.arcgis.com` served data and then refused connections minutes later within a single session, so anything built here needs retry logic rather than single-shot fetches, and no source should be written off on one failed probe.

Alpha-gal syndrome county data exists, just not at CDC. It is not nationally notifiable, has no CDC API and no `data.cdc.gov` dataset, and [MMWR 72(30)](https://www.cdc.gov/mmwr/volumes/72/wr/mm7230a2.htm) publishes its county distribution only as a rendered map. The full text was parsed from PubMed Central to confirm that: one table, broken down by age, sex and year, no geography. Kansas DHE, however, republishes the MMWR county classification as a queryable ArcGIS layer covering 372 counties across KS, MO, AR and OK, pairing each county's alpha-gal burden with its lone star tick population status. The values are the MMWR's own tertiles, low/medium/high at <11, 11–87 and >87 suspected cases per million person-years, rather than raw counts.

---

## Related projects

This repo is the middle of a three-repo pipeline:

```
pulse-code  →  health  →  health-charts
(explore)      (archive)   (visualize)
```

- **[fartbagxp/pulse-code](https://github.com/fartbagxp/pulse-code)** — a CDC WONDER exploration CLI for one-off, ad hoc queries, with an LLM-assisted XML query builder. This repo carries 49 saved WONDER XML queries in `src/wonder/queries/`; 23 of `pulse-code`'s 59 saved queries have graduated here, each wrapped in a `fetch_*.py` script that runs on a schedule and commits the result as a CSV in `data/raw/wonder/`. That archival step is the one `pulse-code` itself doesn't do.
- **[fartbagxp/health-charts](https://github.com/fartbagxp/health-charts)** — the dashboard downstream of this repo. It fetches CSVs from `data/raw/` and `data/processed/` here directly via `raw.githubusercontent.com` at page-load time (nothing is copied into that repo) and renders them with svelteplot.

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
[SEER Cancer Statistics]: https://seer.cancer.gov/statistics-network/explorer/
[NCHS Data Query System (DQS)]: https://www.cdc.gov/nchs/dqs/
[Environmental Public Health Tracking (EPHT)]: https://ephtracking.cdc.gov/
