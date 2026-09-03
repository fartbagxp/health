# Data Catalog

A verified inventory of every CDC data resource across the three-repo pipeline:
[`pulse-code`](https://github.com/fartbagxp/pulse-code) (explore), then
**`health`** (archive), then
[`health-charts`](https://github.com/fartbagxp/health-charts) (visualize). It
records each source's live status, refresh cadence, and where it lands.

**How to read this page:**

- **Source system:** the upstream CDC/NCHS/NCI program and its API.
- **Registry:** the Python module in `health/src/` that defines the datasets.
- **Archive:** where the scheduled job commits CSVs under `health/data/`.
- **Charted:** whether `health-charts` renders it today.
- **Activity:** taken from the latest data date in the committed archive and the
  GitHub Actions schedule, checked 2026-08-24.

---

## The pipeline at a glance

```
pulse-code  →  health  →  health-charts
(explore)      (archive)   (visualize)
```

| Repo | Role | What it holds |
| ---- | ---- | ------------- |
| **`pulse-code`** | Exploration CLI (`pulse`) | Standalone `requests`-only reimplementations of eight of health's nine source clients (all but EPHT), plus **59** saved CDC WONDER XML queries. Nothing is archived; it holds ad hoc, one-off queries and an LLM XML query builder. |
| **`health`** | Scheduled archive | The full ingestion stack (`pandas`/`lxml`/`playwright`). Five GitHub Actions jobs fetch on a schedule and commit CSVs to `data/raw/` and `data/processed/`. This is the source of truth. |
| **`health-charts`** | Dashboard | A SvelteKit site that reads the committed CSVs directly from `raw.githubusercontent.com` at page load. **50** visible chart series (54 defined, 4 hidden). Copies no data. |

**Query graduates to archive:** 23 of `pulse-code`'s 59 saved WONDER queries have a
matching `fetch_*.py` script here. The rest stay exploration-only for now.

---

## Source systems

Ten upstream systems are wired up. Six feed the scheduled archive. Three
(**GRASP**, **NSSP**, **NIS**) are query-only in `pulse`/`health` and are **not**
committed to `data/`. **EPHT** is cataloged with a working discovery client, but
its archiver is not scheduled yet (see section 9). **PLACES** is the one source
too large to commit at all: it is mirrored into a public Dolt database, with
only small derived slices tracked here (see section 10).

| # | System | Module | API | Datasets | Archived? | Schedule (UTC) | Verified latest data |
| - | ------ | ------ | --- | -------- | --------- | -------------- | -------------------- |
| 1 | **CDC WONDER** | `wonder` | XML-over-HTTPS | 26 datasets, 49 XML query templates, 9 fetch scripts, 13 CSVs | ✅ `data/raw/wonder/` | Sat 16:00, weekly | 2024 (annual source) |
| 2 | **CDC Open Data** (Socrata) | `cdc_open` | data.cdc.gov SODA | 68 Socrata + 1 composite + 3 WCMS | ✅ `data/raw/cdc_open/`, `data/processed/cdc_open/` | Sat 14:00, weekly | **2026-08** (weekly series current) |
| 3 | **NCHS DQS** (Health, US) | `nchs_dqs` | data.cdc.gov SODA | 28 across 17 topics | ✅ `data/raw/dqs/` | Sat 15:00, weekly | 2024 (annual source) |
| 4 | **WISQARS** | `wisqars` | data.cdc.gov SODA | 5 | ✅ `data/raw/wisqars/` | Sat 15:00, weekly | 2026-03 (provisional monthly) |
| 5 | **NCI SEER** | `seer` | SEER\*Explorer JSON | 70+ cancer sites | ✅ `data/raw/seer/` | 1st of month 15:00 | 2024 (annual source) |
| 6 | **ATSDR GRASP / FluView** | `grasp` | gis.cdc.gov + CMU Delphi | 4 (hantavirus, ILINet, clinical labs, FluSurv-NET) | ❌ live-only | on demand | live |
| 7 | **NSSP** (ED visits) | `nssp` | CMU Delphi Epidata | 4 pathogens (COVID/flu/RSV/combined) | ❌ live-only | on demand | live |
| 8 | **NIS** (immunization) | `nis` | CDC FTP fixed-width `.dat` | NIS-Child + NIS-Teen | ❌ live-stream | on demand | live |
| 9 | **EPHT** (environmental tracking) | `epht` | ephtracking.cdc.gov REST/JSON | 867 measures; 8 curated for state-level archive | 🚧 discovery ✅, archive pending token | not yet scheduled | live |
| 10 | **CDC PLACES** | `places` | data.cdc.gov bulk export | 4 geographies x 49 measures, 2 families (~7.9M rows) | ✅ Dolt `fartbagxp/cdc-places` + `data/processed/places/` | 1st of month 17:00 | 2025 release + ACS 2017-2021 |

### Who collects it, and how

The center and collection method behind each system (health-charts renders the
same taxonomy per chart from `src/lib/sources.js`):

| System | CDC center | How it's collected |
| ------ | ---------- | ------------------ |
| CDC WONDER | NCHS | Vital records (birth/death certificates) plus notifiable-disease case counts |
| CDC Open Data (Socrata) | Multi-center portal | Varies by dataset: hospital/facility reporting (NHSN), surveys (NIS, PLACES/BRFSS), wastewater (NWSS), vital records (NVSS), lab surveillance (RESP-NET, BEAM, measles/NNDSS), model-based nowcast (CFA) |
| NCHS DQS | NCHS | Vital records, national surveys (NHANES/NHIS), and CMS expenditure accounts |
| WISQARS | NCIPC (Injury Prevention & Control) | Compiled from NVSS death certificates and related systems |
| NCI SEER | **NCI (NIH)**, not CDC | Population-based cancer registries |
| ATSDR GRASP / FluView | ATSDR platform; NCIRD data | Outpatient ILINet and clinical-lab influenza surveillance |
| NSSP | CSELS / OPHDST | Syndromic emergency-department visit reporting |
| NIS | NCIRD (Immunization Services Div.) | Random-digit-dial and panel telephone survey |
| EPHT | NCEH (National Center for Environmental Health) | Environmental monitoring plus linked health records |
| CDC PLACES | NCCDPHP (Chronic Disease Prevention & Health Promotion) | Two products: small-area estimates modeled from BRFSS responses (40 measures), and Non-Medical Factor Measures derived from the 5-year American Community Survey (9 measures) |

> **Activity verdict.** All five scheduled jobs are healthy. Weekly respiratory,
> wastewater, measles, and NHSN archives are current through mid-August 2026. The
> annual sources (WONDER, DQS, SEER) correctly sit at 2024, the newest full year
> those programs have released. GRASP, NSSP, and NIS carry no staleness risk
> because they are fetched live, not stored.

---

## 1. CDC WONDER (`data/raw/wonder/`)

CDC's public query system (mortality, births, natality, VAERS, environmental),
back to 1968 via an unauthenticated XML API. 49 saved XML query templates live in
`src/wonder/queries/`; 9 are wrapped in `fetch_*.py` scripts that run weekly and
commit a CSV.

| Archived CSV | Charted as | Coverage |
| ------------ | ---------- | -------- |
| `births-by-year-1995-2002.csv` / `-2003-2006.csv` / `-2007-2024.csv` | U.S. Annual Births | 1995-2024 |
| `mortality-total-by-year.csv` | U.S. Annual Deaths | 1979-2024 |
| `mortality-top5-causes-by-year.csv` | Deaths: circulatory / cancer / respiratory | 1979-2024 |
| `deaths-by-place-of-death.csv` | Deaths by place of death | 2018-2024 (monthly) |
| `drug-deaths-by-year.csv` / `-by-month.csv` | Drug overdose deaths by type | 1999-2024 |
| `fentanyl-deaths-by-month.csv` | (component of overdose series) | 1999-2024 |
| `maternal-mortality-by-year.csv` / `-by-state-year.csv` | U.S. Maternal Mortality | 1999-present |
| `tick-borne-diseases-by-year.csv` | Lyme Disease Cases | 2016-present |
| `obesity-diabetes-deaths-by-year.csv` | (collected) | 1999-2024 |

Exploration-only in `pulse-code` (no archive yet): cancer and AIDS by state, fetal
deaths by cause/race, PM2.5 by state/year, STD and TB cases, unintentional
injuries, plus demographic slices of COVID, opioid, and maternal mortality.

## 2. CDC Open Data (Socrata) (`data/raw/cdc_open/`, `data/processed/cdc_open/`)

The largest registry: **68** `data.cdc.gov` datasets, plus **1** multi-year
composite (state life expectancy) and **3** CDC WCMS measles JSON endpoints. 16
are charted today; 10 are disabled in the bulk downloader because they exceed
GitHub's file-size limit at full resolution and nothing charts them yet (still
queryable live).

**Charted (16):** life expectancy, provisional mortality rates, historical death
rates, quarterly birth indicators, NWSS wastewater (COVID/flu/RSV/measles/H5),
respiratory % of deaths, nursing-home respiratory and vaccination (NHSN), weekly
respiratory vaccination (NIS-ACM), SchoolVaxView kindergarten coverage, weekly and
annual measles, and BEAM foodborne isolates.

**Backlog (collected but not yet charted):** leading causes of death, PLACES
county/city, disability, NHANES measured obesity, VSRR overdose, NNDSS measles and
STI tables (chlamydia/gonorrhea/syphilis), HAI/AMR (MRSA, CRE/CRAB/ESBL, C. diff,
candidemia), ARI activity, RESP-LENS, NVSN pediatric positivity, and cumulative
RSV/COVID hospitalization estimates. Run `cdc-open list --uncharted` for the full
list.

**Disabled (over GitHub size limit, uncharted):** `covid_conditions`, `rsv_net`,
`covid_net`, `drug_overdose_county`, `nssp_ed_visits`, `resp_coverage_adults`,
`covid_coverage_adults`, `nndss_weekly`, `chronic_disease_indicators`. Each stays
queryable via `cdc_open query <id>`. (`epidemic_trends_rt` is also skipped by the
bulk downloader but is charted; see below.)

### Near-real-time and forecasting (CFA)

The datasets closest to real time, added because they lead the survey and hospital
archives rather than lag them:

| Series | Dataset | How it's kept small | Charted as |
| ------ | ------- | ------------------- | ---------- |
| **CFA Epidemic Trends nowcast** | `5dqz-y4ea` (~520k rows full) | `fetch_epidemic_trends.py` pulls only the latest `as_of` snapshot (~4.4k rows) and accumulates a national daily rollup (`processed/epidemic_trends_national.csv`) | "Epidemic Growth Nowcast" (share of states with a rising COVID/flu/RSV trajectory) |
| **Mpox wastewater** | `xpxn-rzgz` (~297k rows full) | fetched fresh, rolled up by `aggregate` to a national weekly median (~5 KB) | "Mpox Wastewater Signal" |
| **NWSS public COVID metric** | `2ew6-ywp6` (~837k rows full) | `aggregate_nwss_metric()` produces a national weekly-median activity percentile (~3 KB) | "COVID-19 Wastewater Activity Level" |

The CFA nowcast (`5dqz-y4ea`) refreshes several times a week; the wastewater
series refresh weekly. Raw pulls are git-ignored; only the small rollups commit.

## 3. NCHS DQS (Health, United States) (`data/raw/dqs/`)

A unified query layer over CDC's national surveys (NHANES, NHIS, NHAMCS, NVSS,
NPALS, NHCS, plus BLS/CMS/MTF). **28** datasets sharing one tidy Socrata schema,
across 17 topics. Only **3** are charted (`drug_overdose_by_type.csv`,
`low_birthweight_by_state.csv`, `national_health_spending.csv`); the other 25 are
the backlog: chronic disease and risk factors, nutrition, oral health, disability,
self-reported health, the health-care system (beds, ED visits, utilization),
workforce, spending, and long-term care.

## 4. WISQARS (`data/raw/wisqars/`)

Fatal injury, firearm, suicide, homicide, and overdose data. **5** datasets:
`injury_mortality` (1999-2016), and the mapping series `injury_national` /
`injury_state` / `injury_county` / `injury_census_tract` (2019-present). Charted:
national monthly rates (drug OD, suicide, homicide, firearm) plus a
WISQARS+WONDER `suicide_by_sex` blend.

## 5. NCI SEER (`data/raw/seer/`)

Cancer incidence and U.S. mortality by site, sex, race, and age back to 1975, via
the JSON endpoints SEER\*Explorer itself uses. Archived: `mortality_by_year.csv`,
`mortality_by_age.csv`, `mortality_by_year_age.csv`. Charted: cancer deaths by
type (7 sites) and by sex (lung, colorectal, pancreas, liver). Monthly refresh
because SEER re-releases annually.

> **Known upstream drift.** The SEER snapshot dropped the combined Leukemia site
> in favor of narrow myeloid subtypes with no aggregate total, so the
> `cancer-sex-leukemia` chart matches zero rows and is hidden until the aggregate
> returns.

## 6-8. Live-only sources (GRASP, NSSP, NIS)

Queryable through `pulse`/`health` but **not** committed to `data/`:

- **GRASP / FluView:** hantavirus cases, ILINet ILI %, WHO/NREVSS clinical-lab
  flu positivity, and FluSurv-NET hospitalization rates (via CMU Delphi).
- **NSSP:** weekly % of ED visits for COVID/flu/RSV at nation/state/HHS/county
  (via CMU Delphi). County flu/COVID/RSV is reachable here with `--geo-type county`.
- **NIS:** NIS-Child (19-35 mo) and NIS-Teen (13-17 yr) vaccination microdata,
  streamed from fixed-width `.dat` files without touching disk.

## 9. EPHT: Environmental Public Health Tracking (`epht`)

CDC's environmental-health data API (`ephtracking.cdc.gov`), covering 867 measures
across 27 content areas (air and water quality, heat, childhood lead, asthma,
birth outcomes, and more) at national, state, and county level. The `epht` module
wraps the discovery-then-fetch REST API:

```bash
uv run python -m epht content-areas            # 27 content areas
uv run python -m epht measures --search asthma # search the 867 measures
uv run python -m epht registry                 # the curated archive set (8 measures)
uv run python -m epht fetch pm25_annual_avg    # one measure, state-level
```

**Status.** Discovery (content areas, measure search, geographic types,
stratification levels) is verified and working. The archival path
(`epht.download`, state-level series under a 5 MB guard) is implemented against
CDC's documented `getCoreHolder` contract but **not yet verified end-to-end**: the
API rate-limits unauthenticated requests (HTTP 429), so a scheduled job needs a
free `EPHT_API_TOKEN` from <https://ephtracking.cdc.gov/apihelp>. It is
deliberately **not** wired into a GitHub Actions workflow yet, to avoid a
scheduled run committing empty files before a token-backed verification pass
confirms which curated measures return state-level data (some measures are
county-only). The curated registry is a starting set, not a final one.

---

## 10. CDC PLACES (`data/processed/places/` + Dolt)

Small-area estimates of 49 measures for every US county, place, census tract and
ZCTA — all seven pages of CDC's PLACES data portal.

Two CDC products, mirrored as two families. **PLACES proper** is 40 measures
modeled from BRFSS, in six categories: Health Outcomes (12 measures),
Prevention (7), Disability (7), Health-Related Social Needs (7), Health Risk
Behaviors (4), Health Status (3). **Non-Medical Factor Measures** is the
seventh page: 9 measures derived from the 5-year American Community Survey,
under `categoryid` `SDOH`.

**The one source too large to commit.** Together, ~7.9M rows / ~1.7 GB:

| Geography | PLACES ID | Rows | Export | Non-Medical ID | Rows |
| --------- | --------- | ---- | ------ | -------------- | ---- |
| County | `swc5-untb` | 229,298 | 53 MB | `i6u4-y3g4` | 28,287 |
| Place | `eav7-hnsx` | 2,150,438 | ~460 MB | `edkk-ze78` | 268,389 |
| Census tract | `cwsq-ngmh` | 3,047,284 | 694 MB | `e539-uadk` | 751,509 |
| ZCTA | `qnzd-25i4` | 1,171,563 | 224 MB | `bumh-rgsq` | 291,024 |

The tract export alone is past GitHub's 100 MB hard limit. So PLACES is mirrored
into the public Dolt database
[`fartbagxp/cdc-places`](https://www.dolthub.com/repositories/fartbagxp/cdc-places)
— free at any size, versioned and diffable — and `data/raw/places/` is
gitignored. Only these derived slices are tracked:

| Archived CSV | Charted as | Coverage |
| ------------ | ---------- | -------- |
| `county_crude.csv` (114,576 rows, 4.1 MB) | county choropleth | 40 measures x 3,145 counties, crude prevalence |
| `county_ageadj.csv` (114,576 rows, 4.1 MB) | backlog | same, age-adjusted |
| `state_rollup.csv` (3,814 rows, 122 KB) | backlog | population-weighted state means |
| `nmf_county.csv` (28,278 rows, 1.3 MB) | backlog | 9 non-medical factors x 3,143 counties, with margin of error |
| `nmf_state_rollup.csv` (459 rows, 10 KB) | backlog | population-weighted state means |
| `measures.csv` (49 rows) | measure labels | the shared measure dimension, all 7 categories |

> **The mirror is ours, not CDC's.** DoltHub is a commercial service run by
> DoltHub Inc., with no affiliation to CDC. `fartbagxp/cdc-places` is a copy
> this project maintains; CDC does not publish it and is not responsible for it.
> The authoritative source is always `data.cdc.gov` — the Socrata IDs above.
> The database is named `cdc-places` for what it holds, not for who runs it.

### How it's kept small

| Full resolution | Technique | Result |
| --------------- | --------- | ------ |
| 7,937,792 rows / ~1.7 GB | Full fidelity to Dolt; only county-level slices committed | 9.4 MB tracked |
| 24 columns, 11 of them redundant per row | Normalized to fact + 4 dimension tables in Dolt | 727 MB of tract CSV → 178 MB of fact rows |

Population is constant per `(location, year)` — zero violations across all
229,298 PLACES county rows and all 28,287 Non-Medical Factors ones — and
geolocation is constant per location, so both are location attributes rather
than measurements.

**The two families keep separate fact and location tables**, sharing only
`measure` and `category`. The forcing difference is geographic, not cosmetic:
ACS 2017-2021 still uses Connecticut's retired county FIPS `09001`—`09015`
while PLACES 2025 uses the new planning regions `09110`—`09190`, so the two
do not even cover the same county universe. A county map built from one
family's FIPS will have gaps in Connecticut for the other. County names differ
too (— `Autauga County` vs `Autauga`, on 3,131 of 3,133 shared counties),
which is harmless when joining on FIPS. See [PLACES](places.md#two-families).

### Live queries

The DoltHub SQL API sends CORS headers and needs no key, so health-charts can
query it from the browser for drill-down. Two limits shape every query: a
**1000-row cap** (reported as a `RowLimit` status, not an error) and a **~55
second deadline**. A single location's measures comes back in 0.3s, but any
join against the 6.6M-row PLACES fact table exceeds the deadline — labels
have to be resolved from the 49-row `measures.csv` client-side. National-scale
chart payloads stay as committed CSVs. See [PLACES](places.md).

> **Supersedes `places_county` in `cdc_open`.** The older
> `data/processed/cdc_open/places_county.csv` covered 8 of the 40 PLACES measures,
> crude only, from a server-filtered 12 MB download. `county_crude.csv` uses the
> identical column layout and reproduces all 23,648 of its rows with no value
> differences, so the migration is a path change for health-charts rather than a
> parsing change. `places_county` should be set `enabled=False` once
> health-charts has moved.

> **`places_city` is not PLACES.** Despite the name, `dxpw-cm5u` in the
> `cdc_open` registry is *500 Cities* 2019 GIS-format data — a different,
> retired product. PLACES place-level data is `eav7-hnsx`, via Dolt.

---

## State, county and local

Every source above is federal. Two research catalogs survey what is available
below the state line; nothing in either is downloaded, by design, since `data/` is
already ~352 MB. See [State & Local Sources](local.md) (endpoints verified against
live data) and [State Health Data Portals](state-portals.md) (all 50 states + DC).

---

## Candidate sources: external cross-check

Cross-referenced against the
**[Federal Data Terminations Tracker](https://dataindex.us/terminations-tracker/)**
(Federation of American Scientists; 375 entries as of 2026-08-17) to find CDC
resources the pipeline does not yet cover, and to flag which upstream programs
have been cut. **None** of the following are in the repo today.

| Source | Agency | Status | API? | Verdict |
| ------ | ------ | ------ | ---- | ------- |
| **NCHS Rapid Surveys System (RSS)** | CDC/NCHS | Active (gender-identity items removed) | ✅ Socrata `p89x-xx88` | ✅ **Ingested** as `cdc_open` `rapid_surveys` (1.7 MB, enabled). Quarterly national health estimates. |
| **Environmental Public Health Tracking (EPHT)** | CDC | Active (some elements removed) | ✅ REST/JSON `ephtracking.cdc.gov/apigateway/api/v1` | 🚧 **In progress**: `epht` module. Air/water quality, climate and health, childhood lead, asthma, cancer at national/state/county. API is rate-limited without a (free) `EPHT_API_TOKEN`. |
| **Sudden Death in the Young Registry** | CDC | Active (SO/GI items removed) | Registry/limited | Niche; low priority. |
| **PRAMS** (Pregnancy Risk Assessment) | CDC | **Partially terminated**: national weighting/publication ceased; states continue | Fragmented | Not a clean national source anymore. Skip. |
| **DAWN** (Drug Abuse Warning Network) | SAMHSA | **Terminated (2025)** | Historical only | Not a live source. Historical archive only. |
| **VACS** (Violence Against Children & Youth) | CDC | **Terminated** (never fully fielded) | none | Not viable. |
| **CPS Food Security Supplement** | USDA | **Terminated** | none | Out of scope (not CDC). |

> **Recommended next ingests.** EPHT (a new environmental-health domain with a
> clean REST API) and RSS (drops straight into `cdc_open` as a Socrata ID). Both
> are active and API-backed. The terminated programs (DAWN, VACS, PRAMS national)
> are worth noting in documentation as gaps that will not refill, not as ingest
> targets.

---

_Counts and dates verified 2026-08-24 against the working tree: `cdc_open`
registry (68 + 1 + 3), DQS (28/17 topics), WISQARS (5), GRASP (4), WONDER (49 XML
/ 9 fetch / 13 CSV), and `health-charts` config (54 defined, 50 visible). Latest
committed data dates sampled from the archived CSVs._

_PLACES (section 10) verified 2026-08-31 against both the live exports and the
published database: all four geographies loaded into `fartbagxp/cdc-places` and
queried back at 229,298 / 2,150,438 / 3,047,284 / 1,171,563 (6,598,583 total),
with 3,145 / 29,923 / 83,522 / 32,520 locations. Age-adjusted estimates exist
only at county and place level, as CDC documents. All four 2025 datasets were
last republished by CDC in December 2025._

_Non-Medical Factors verified 2026-09-03 the same way: all four geographies
loaded and queried back at 28,287 / 268,389 / 751,509 / 291,024 (1,339,209
total) across 148,801 locations, exactly 9 measures per location at every level
with no primary-key collisions. The shared `measure` table now holds 49 rows
across 7 categories — the seven pages of CDC's portal, enumerated from the
ArcGIS Experience config itself rather than from the page. The published
database totals 7,937,792 fact rows. CDC last republished these four datasets
in October/November 2023._
