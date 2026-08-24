# Data Catalog

A single, verified inventory of every CDC data resource across the three-repo
pipeline — [`pulse-code`](https://github.com/fartbagxp/pulse-code) (explore) →
**`health`** (archive) → [`health-charts`](https://github.com/fartbagxp/health-charts)
(visualize) — with each source's live status, refresh cadence, and where it lands.

!!! info "How to read this page" - **Source system** — the upstream CDC/NCHS/NCI program and its API. - **Registry** — the Python module in `health/src/` that defines the datasets. - **Archive** — where the scheduled job commits CSVs under `health/data/`. - **Charted** — whether `health-charts` renders it today. - **Activity** — verified from the latest data date in the committed archive
and the GitHub Actions schedule, checked **2026-08-24**.

---

## The pipeline at a glance

```bash
pulse-code  →  health  →  health-charts
(explore)      (archive)   (visualize)
```

| Repo                | Role                      | What it holds                                                                                                                                                                                                 |
| ------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`pulse-code`**    | Exploration CLI (`pulse`) | Standalone `requests`-only reimplementations of the same eight source clients, plus **59** saved CDC WONDER XML queries. Nothing is archived — it's for ad-hoc, one-off queries and an LLM XML query builder. |
| **`health`**        | Scheduled archive         | The full ingestion stack (`pandas`/`lxml`/`playwright`). Five GitHub Actions jobs fetch on a schedule and commit CSVs to `data/raw/` and `data/processed/`. This is the source of truth.                      |
| **`health-charts`** | Dashboard                 | A SvelteKit site that reads the committed CSVs directly from `raw.githubusercontent.com` at page load. **~46** visible chart series (50 defined, 4 hidden). Copies no data.                                   |

**Query graduates to archive:** 23 of `pulse-code`'s 59 saved WONDER queries have a
matching `fetch_*.py` script here. The rest are exploration-only for now.

---

## Source systems

Eight live upstream systems feed the archive. Five are on a scheduled job; three
(**GRASP**, **NSSP**, **NIS**) are query-only in `pulse`/`health` and are **not**
committed to `data/` — they're fetched live on demand.

| #   | System                            | Module     | API                           | Datasets                                                         | Archived?                                           | Schedule (UTC)     | Verified latest data                |
| --- | --------------------------------- | ---------- | ----------------------------- | ---------------------------------------------------------------- | --------------------------------------------------- | ------------------ | ----------------------------------- |
| 1   | **CDC WONDER**                    | `wonder`   | XML-over-HTTPS                | 26 datasets · 49 XML query templates · 9 fetch scripts · 13 CSVs | ✅ `data/raw/wonder/`                               | Sat 16:00, weekly  | 2024 (annual source)                |
| 2   | **CDC Open Data** (Socrata)       | `cdc_open` | data.cdc.gov SODA             | 68 Socrata + 1 composite + 3 WCMS                                | ✅ `data/raw/cdc_open/`, `data/processed/cdc_open/` | Sat 14:00, weekly  | **2026-08** (weekly series current) |
| 3   | **NCHS DQS** (Health, US)         | `nchs_dqs` | data.cdc.gov SODA             | 28 across 17 topics                                              | ✅ `data/raw/dqs/`                                  | Sat 15:00, weekly  | 2024 (annual source)                |
| 4   | **WISQARS**                       | `wisqars`  | data.cdc.gov SODA             | 5                                                                | ✅ `data/raw/wisqars/`                              | Sat 15:00, weekly  | 2026-03 (provisional monthly)       |
| 5   | **NCI SEER**                      | `seer`     | SEER\*Explorer JSON           | 70+ cancer sites                                                 | ✅ `data/raw/seer/`                                 | 1st of month 15:00 | 2024 (annual source)                |
| 6   | **ATSDR GRASP / FluView**         | `grasp`    | gis.cdc.gov + CMU Delphi      | 4 (hantavirus, ILINet, clinical labs, FluSurv-NET)               | ❌ live-only                                        | —                  | live                                |
| 7   | **NSSP** (ED visits)              | `nssp`     | CMU Delphi Epidata            | 4 pathogens (COVID/flu/RSV/combined)                             | ❌ live-only                                        | —                  | live                                |
| 8   | **NIS** (immunization)            | `nis`      | CDC FTP fixed-width `.dat`    | NIS-Child + NIS-Teen                                             | ❌ live-stream                                      | —                  | live                                |
| 9   | **EPHT** (environmental tracking) | `epht`     | ephtracking.cdc.gov REST/JSON | 867 measures; 8 curated for state-level archive                  | 🚧 discovery ✅, archive pending token              | not yet scheduled  | live                                |

### Who collects it, and how

The center and collection method behind each system (health-charts renders the
same taxonomy per chart from `src/lib/sources.js`):

| System                  | CDC center                                      | How it's collected                                                                                                                                                                                        |
| ----------------------- | ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CDC WONDER              | NCHS                                            | Vital records (birth/death certificates) + notifiable-disease case counts                                                                                                                                 |
| CDC Open Data (Socrata) | Multi-center portal                             | Varies by dataset — hospital/facility reporting (NHSN), surveys (NIS, PLACES/BRFSS), wastewater (NWSS), vital records (NVSS), lab surveillance (RESP-NET, BEAM, measles/NNDSS), model-based nowcast (CFA) |
| NCHS DQS                | NCHS                                            | Vital records + national surveys (NHANES/NHIS) + CMS expenditure accounts                                                                                                                                 |
| WISQARS                 | NCIPC (Injury Prevention & Control)             | Compiled from NVSS death certificates + related systems                                                                                                                                                   |
| NCI SEER                | **NCI (NIH)** — not CDC                         | Population-based cancer registries                                                                                                                                                                        |
| ATSDR GRASP / FluView   | ATSDR platform; NCIRD data                      | Outpatient ILINet + clinical-lab influenza surveillance                                                                                                                                                   |
| NSSP                    | CSELS / OPHDST                                  | Syndromic emergency-department visit reporting                                                                                                                                                            |
| NIS                     | NCIRD (Immunization Services Div.)              | Random-digit-dial & panel telephone survey                                                                                                                                                                |
| EPHT                    | NCEH (National Center for Environmental Health) | Environmental monitoring + linked health records                                                                                                                                                          |

!!! note "Activity verdict"
All five scheduled jobs are **healthy**. Weekly respiratory, wastewater,
measles, and NHSN archives are current through mid-August 2026; the annual
sources (WONDER, DQS, SEER) correctly sit at 2024, which is the newest full
year those programs have released. GRASP/NSSP/NIS carry no staleness risk
because they're fetched live, not stored.

---

## 1 · CDC WONDER — `data/raw/wonder/`

CDC's public query system (mortality, births, natality, VAERS, environmental),
back to 1968 via an unauthenticated XML API. 49 saved XML query templates live in
`src/wonder/queries/`; 9 are wrapped in `fetch_*.py` scripts that run weekly and
commit a CSV.

| Archived CSV                                                         | Charted as                                 | Coverage            |
| -------------------------------------------------------------------- | ------------------------------------------ | ------------------- |
| `births-by-year-1995-2002.csv` / `-2003-2006.csv` / `-2007-2024.csv` | U.S. Annual Births                         | 1995–2024           |
| `mortality-total-by-year.csv`                                        | U.S. Annual Deaths                         | 1979–2024           |
| `mortality-top5-causes-by-year.csv`                                  | Deaths: circulatory / cancer / respiratory | 1979–2024           |
| `deaths-by-place-of-death.csv`                                       | Deaths by place of death                   | 2018–2024 (monthly) |
| `drug-deaths-by-year.csv` / `-by-month.csv`                          | Drug overdose deaths by type               | 1999–2024           |
| `fentanyl-deaths-by-month.csv`                                       | (component of overdose series)             | 1999–2024           |
| `maternal-mortality-by-year.csv` / `-by-state-year.csv`              | U.S. Maternal Mortality                    | 1999–present        |
| `tick-borne-diseases-by-year.csv`                                    | Lyme Disease Cases                         | 2016–present        |
| `obesity-diabetes-deaths-by-year.csv`                                | (collected)                                | 1999–2024           |

Exploration-only in `pulse-code` (no archive yet): cancer & AIDS by state, fetal
deaths by cause/race, PM2.5 by state/year, STD & TB cases, unintentional injuries,
plus demographic slices of COVID, opioid, and maternal mortality.

## 2 · CDC Open Data (Socrata) — `data/raw/cdc_open/`, `data/processed/cdc_open/`

The largest registry: **65** `data.cdc.gov` datasets, **1** multi-year composite
(state life expectancy), and **3** CDC WCMS measles JSON endpoints. **16** are
charted today; **10** are deliberately disabled in the bulk downloader because
they exceed GitHub's file-size limit at full resolution and nothing charts them
yet (still queryable live).

**Charted (16):** life expectancy, provisional mortality rates, historical death
rates, quarterly birth indicators, NWSS wastewater (COVID/flu/RSV/measles/H5),
respiratory % of deaths, nursing-home respiratory + vaccination (NHSN), weekly
respiratory vaccination (NIS-ACM), SchoolVaxView kindergarten coverage, weekly &
annual measles, and BEAM foodborne isolates.

**Backlog — collected but not yet charted:** leading causes of death, PLACES
county/city, disability, NHANES measured obesity, VSRR overdose, NNDSS measles &
STI tables (chlamydia/gonorrhea/syphilis), HAI/AMR (MRSA, CRE/CRAB/ESBL, C. diff,
candidemia), ARI activity, RESP-LENS, NVSN pediatric positivity, cumulative
RSV/COVID hospitalization estimates, and more. Run `cdc-open list --uncharted`.

**Disabled (over GitHub size limit, uncharted):** `covid_conditions`, `rsv_net`,
`covid_net`, `drug_overdose_county`, `nssp_ed_visits`, `resp_coverage_adults`,
`covid_coverage_adults`, `nndss_weekly`, `chronic_disease_indicators`. Each stays
queryable via `cdc_open query <id>`. (`epidemic_trends_rt` is also skipped by the
bulk downloader but _is_ charted — see below.)

### Near-real-time & forecasting (CFA)

The datasets closest to real time, added because they lead the survey/hospital
archives rather than lag them:

| Series                          | Dataset                       | How it's kept small                                                                                                                                               | Charted as                                                                         |
| ------------------------------- | ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| **CFA Epidemic Trends nowcast** | `5dqz-y4ea` (~520k rows full) | `fetch_epidemic_trends.py` pulls only the latest `as_of` snapshot (~4.4k rows) and accumulates a national daily rollup (`processed/epidemic_trends_national.csv`) | "Epidemic Growth Nowcast" — share of states with a rising COVID/flu/RSV trajectory |
| **Mpox wastewater**             | `xpxn-rzgz` (~297k rows full) | fetched fresh, rolled up by `aggregate` to a national weekly median (~5 KB)                                                                                       | "Mpox Wastewater Signal"                                                           |
| **NWSS public COVID metric**    | `2ew6-ywp6` (~837k rows full) | `aggregate_nwss_metric()` → national weekly-median activity percentile (~3 KB)                                                                                    | "COVID-19 Wastewater Activity Level"                                               |

The CFA nowcast (`5dqz-y4ea`) refreshes several times a week; the wastewater
series refresh weekly. Raw pulls are git-ignored; only the small rollups commit.

## 3 · NCHS DQS (Health, United States) — `data/raw/dqs/`

A unified query layer over CDC's national surveys (NHANES, NHIS, NHAMCS, NVSS,
NPALS, NHCS, plus BLS/CMS/MTF). **28** datasets sharing one tidy Socrata schema,
across 17 topics. Only **3** are charted (`drug_overdose_by_type.csv`,
`low_birthweight_by_state.csv`, `national_health_spending.csv`); the other 25 are
the backlog — chronic disease & risk factors, nutrition, oral health, disability,
self-reported health, the health-care system (beds, ED visits, utilization),
workforce, spending, and long-term care.

## 4 · WISQARS — `data/raw/wisqars/`

Fatal injury, firearm, suicide, homicide, and overdose data. **5** datasets:
`injury_mortality` (1999–2016), and the mapping series `injury_national` /
`injury_state` / `injury_county` / `injury_census_tract` (2019–present). Charted:
national monthly rates (drug OD, suicide, homicide, firearm) plus a
WISQARS+WONDER `suicide_by_sex` blend.

## 5 · NCI SEER — `data/raw/seer/`

Cancer incidence and U.S. mortality by site, sex, race, and age back to 1975, via
the JSON endpoints SEER\*Explorer itself uses. Archived: `mortality_by_year.csv`,
`mortality_by_age.csv`, `mortality_by_year_age.csv`. Charted: cancer deaths by
type (7 sites) and by sex (lung, colorectal, pancreas, liver). Monthly refresh
because SEER re-releases annually.

!!! warning "Known upstream drift"
The SEER snapshot dropped the combined **Leukemia** site in favor of narrow
myeloid subtypes with no aggregate total, so the `cancer-sex-leukemia` chart
matches zero rows and is hidden until the aggregate returns.

## 6–8 · Live-only sources (GRASP, NSSP, NIS)

Queryable through `pulse`/`health` but **not** committed to `data/`:

- **GRASP / FluView** — hantavirus cases, ILINet ILI %, WHO/NREVSS clinical-lab
  flu positivity, FluSurv-NET hospitalization rates (via CMU Delphi).
- **NSSP** — weekly % of ED visits for COVID/flu/RSV at nation/state/HHS/county
  (via CMU Delphi). County flu/COVID/RSV is reachable here with `--geo-type county`.
- **NIS** — NIS-Child (19–35 mo) and NIS-Teen (13–17 yr) vaccination microdata,
  streamed from fixed-width `.dat` files without touching disk.

## 9 · EPHT — Environmental Public Health Tracking (`epht`)

CDC's environmental-health data API (`ephtracking.cdc.gov`), covering 867
measures across 27 content areas — air and water quality, heat, childhood lead,
asthma, birth outcomes, and more — at national/state/county level. The `epht`
module wraps the discovery-then-fetch REST API:

```bash
uv run python -m epht content-areas            # 27 content areas
uv run python -m epht measures --search asthma # search the 867 measures
uv run python -m epht registry                 # the curated archive set (8 measures)
uv run python -m epht fetch pm25_annual_avg    # one measure, state-level
```

**Status.** Discovery (content areas, measure search, geographic types,
stratification levels) is verified and working. The archival path
(`epht.download`, state-level series under a 5 MB guard) is implemented against
CDC's documented `getCoreHolder` contract but **not yet verified end-to-end**:
the API rate-limits unauthenticated requests (HTTP 429), so a scheduled job needs
a free `EPHT_API_TOKEN` from <https://ephtracking.cdc.gov/apihelp>. It is
deliberately **not** wired into a GitHub Actions workflow yet, to avoid a
scheduled run committing empty files before a token-backed verification pass
confirms which curated measures return state-level data (some measures are
county-only). The curated registry is a starting set, not a final one.

---

## State, county & local

Every source above is federal. Two research catalogs survey what's available below
the state line; nothing in either is downloaded (by design — `data/` is already
~352 MB). See [State & Local Sources](local.md) (endpoints verified against live
data) and [State Health Data Portals](state-portals.md) (all 50 states + DC).

---

## Candidate sources — external cross-check

Cross-referenced against the **[Federal Data Terminations Tracker](https://dataindex.us/terminations-tracker/)**
(Federation of American Scientists; 375 entries as of 2026-08-17) to find CDC
resources the pipeline doesn't yet cover — and to flag which upstream programs
have been cut. **None** of the following are in the repo today.

| Source                                          | Agency   | Status                                                                            | API?                                                 | Verdict                                                                                                                                                                                  |
| ----------------------------------------------- | -------- | --------------------------------------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **NCHS Rapid Surveys System (RSS)**             | CDC/NCHS | Active (gender-identity items removed)                                            | ✅ Socrata `p89x-xx88`                               | ✅ **Ingested** as `cdc_open` `rapid_surveys` (1.7 MB, enabled). Quarterly national health estimates.                                                                                    |
| **Environmental Public Health Tracking (EPHT)** | CDC      | Active (some elements removed)                                                    | ✅ REST/JSON `ephtracking.cdc.gov/apigateway/api/v1` | 🚧 **In progress** — `epht` module. Air/water quality, climate & health, childhood lead, asthma, cancer at national/state/county. API is rate-limited without a (free) `EPHT_API_TOKEN`. |
| **Sudden Death in the Young Registry**          | CDC      | Active (SO/GI items removed)                                                      | Registry/limited                                     | Niche; low priority.                                                                                                                                                                     |
| **PRAMS** (Pregnancy Risk Assessment)           | CDC      | **Partially terminated** — national weighting/publication ceased; states continue | Fragmented                                           | Not a clean national source anymore. Skip.                                                                                                                                               |
| **DAWN** (Drug Abuse Warning Network)           | SAMHSA   | **Terminated (2025)**                                                             | Historical only                                      | Not a live source. Historical archive only.                                                                                                                                              |
| **VACS** (Violence Against Children & Youth)    | CDC      | **Terminated** (never fully fielded)                                              | —                                                    | Not viable.                                                                                                                                                                              |
| **CPS Food Security Supplement**                | USDA     | **Terminated**                                                                    | —                                                    | Out of scope (not CDC).                                                                                                                                                                  |

!!! tip "Recommended next ingests"
**EPHT** (new environmental-health domain, clean REST API) and **RSS** (drops
straight into `cdc_open` as a Socrata ID). Both are active and API-backed.
The terminated programs (DAWN, VACS, PRAMS national) are worth noting in
documentation as gaps that will not refill, not as ingest targets.

---

_Counts and dates verified 2026-08-24 against the working tree: `cdc_open`
registry (65 + 1 + 3), DQS (28/17 topics), WISQARS (5), GRASP (4), WONDER (49 XML
/ 9 fetch / 13 CSV), and `health-charts` config (50 series, 4 hidden). Latest
committed data dates sampled from the archived CSVs._
