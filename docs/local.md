# State, County & Local Sources

Every source wired into this repo today is federal, and federal surveillance mostly stops at the state line. WONDER mortality goes to county but suppresses small cells; NNDSS reports national and state totals; NIS suppresses county entirely. If the question is "what is happening in _my_ county," the federal tier answers it only for a handful of measures.

This page is a survey, not an implementation. Nothing here is downloaded yet. `data/` is already 352 MB against a 358 MB `.git`, so the point is to work out what is worth ingesting before ingesting it. See [Ingestion strategy](#ingestion-strategy) for the size constraint that should govern that call.

Everything below was probed against a live endpoint, which limits it to about a dozen portals. For the wider view, [State Health Data Portals](state-portals.md) lists the official portal for all 50 states and DC and groups them by the software behind them, which is the faster way to find a source this page has not reached yet.

## Verification legend

Every endpoint below was probed on 2026-08-02, then re-probed after the network allowlist was widened.

| Mark | Meaning                                                                                    |
| ---- | ------------------------------------------------------------------------------------------ |
| ✅   | Called it, got data back. Dataset IDs and column names are copied from the live response   |
| ⚠️   | Known-good pattern, but the domain is outside the network allowlist, so confirm before use |
| ❌   | No machine-readable endpoint exists; manual extraction only                                |

---

## Tier 1: Federal APIs that already go below the state line

The highest-value tier, because these need no new client code. Every ✅ Socrata row is reachable with the existing `cdc_open` downloader by adding a `Dataset` entry to `src/cdc_open/datasets.py`.

| Source                    | Finest geography | ID / endpoint                                | Status  |
| ------------------------- | ---------------- | -------------------------------------------- | ------- |
| CDC PLACES                | **Census tract** | `cwsq-ngmh` (tract), `swc5-untb` (county)    | ✅ done |
| NSSP ED visits via Delphi | **County**       | `api.delphi.cmu.edu/epidata/covidcast`       | ✅      |
| Lyme disease public-use   | **County FIPS**  | `x5j9-wybp` (2022–23), `qtbi-xd4i` (2008–21) | ✅      |
| WISQARS injury            | **Census tract** | already wired, `src/wisqars/`                | ✅      |
| EPHT Tracking Network     | **County**       | `ephtracking.cdc.gov/apigateway/api/v1`      | ✅      |
| NORS outbreaks            | State            | `5xkq-dg7x`                                  | ✅      |
| BEAM enteric pathogens    | State            | already wired, `fetch_beam.py`               | ✅      |
| openFDA food enforcement  | Firm city/state  | `api.fda.gov/food/enforcement.json`          | ✅      |
| NNDSS weekly notifiable   | State            | `x9gk-5huc`                                  | ✅      |
| State Cancer Profiles     | **County**       | `statecancerprofiles.cancer.gov`             | ✅      |
| County Health Rankings    | **County**       | `countyhealthrankings.org` (CSV)             | ✅      |

Two more county-level sources come from state-published ArcGIS layers and have no federal equivalent: Kansas DHE's alpha-gal and lone star tick layer, and Missouri DHSS's tick disease rates. Both are covered under [Alpha-gal syndrome](#alpha-gal-syndrome-the-hard-case).

### CDC PLACES: the single best local-health dataset

Small-area estimates for 49 measures (chronic disease, prevention, health behaviors, disability, and ACS-derived non-medical factors) at census tract, ZCTA, county, and place level, covering the whole country. Nothing else gets this close to a national county-and-below health profile.

> **Now implemented.** PLACES is the `places` module — but note it broke the rule
> at the top of this page: it was far too large to add as a `cdc_open` registry
> entry. All eight datasets together are ~7.9M rows / ~1.7 GB, so they are
> mirrored into the public Dolt database `fartbagxp/cdc-places` and only
> county-level slices are committed. See [PLACES](places.md).

```bash
curl "https://data.cdc.gov/resource/cwsq-ngmh.json?\$limit=1"
```

```
{ "year": "2023", "stateabbr": "AL", "countyname": "Jefferson",
  "countyfips": "01073", "locationname": "01073010900",
  "datasource": "BRFSS", "category": "Disability",
  "measure": "Any disability among adults", "data_value": "44.9",
  "low_confidence_limit": "40.7", "high_confidence_limit": "49.0",
  "totalpopulation": "4719" }
```

These are modeled estimates, not counts, and that distinction matters more than it might look. A tract-level PLACES value is BRFSS survey data projected onto census demographics, so it describes the _expected_ prevalence for a population like that one, not observed cases. Carry `low_confidence_limit` and `high_confidence_limit` through to any chart. At tract level the intervals are wide enough to change conclusions.

It is also the largest ingestion risk on the page. The tract file is roughly 60k tracts × 40 measures, well past GitHub's 100 MB limit, so it would need the `enabled=False` treatment or a filtered `soql_where` on a single state.

### Delphi covidcast: county-level COVID, flu and RSV

The repo already talks to Delphi for `nssp` and `grasp`. Its metadata endpoint reports which signals carry county geography, which beats guessing:

```bash
curl -s "https://api.delphi.cmu.edu/epidata/covidcast/meta"
```

Sources exposing county-level signals, counted from that response:

| Source                | County signals | Notes                                    |
| --------------------- | -------------- | ---------------------------------------- |
| `fb-survey`           | 324            | Facebook symptom survey, ended June 2022 |
| `google-symptoms`     | 22             | Symptom search volume                    |
| `jhu-csse`            | 12             | COVID cases/deaths, archived             |
| `usa-facts`           | 12             | COVID cases/deaths, archived             |
| `nssp`                | 8              | **ED visits for COVID/flu/RSV, current** |
| `chng`                | 6              | Change Healthcare outpatient claims      |
| `hospital-admissions` | 6              | Claims-based admissions                  |
| `doctor-visits`       | 2              | Outpatient visit percentage              |

Only `nssp` and `google-symptoms` are still actively updated; the rest are pandemic-era archives. The existing `src/nssp/` module already accepts `--geo-type county`, so county COVID/flu/RSV ED-visit data is reachable today with no new code.

### Lyme disease with county geography

```bash
curl "https://data.cdc.gov/resource/x5j9-wybp.json?\$limit=1"
```

```
{ "year": "2022", "state": "AK", "fips": "Suppressed",
  "case_status": "Confirmed", "sex": "Suppressed",
  "age_cat_yrs": "20+", "frequency": "2" }
```

Note `"fips": "Suppressed"` in that first row. County FIPS is present but redacted wherever counts are small enough to risk re-identification, which in low-incidence states covers most rows. The dataset is genuinely county-level in high-incidence areas like the Northeast and upper Midwest, and effectively state-level everywhere else. A companion line-listed series (`9mtj-y2ba`, `abzs-b3gw`) has per-case records but no geography at all, so the tradeoff is explicit and you cannot have both.

### EPHT (Environmental Public Health Tracking)

County-level environmental health indicators across 20+ content areas: asthma, childhood lead poisoning, cancer, COPD, birth defects, air quality, heat. Structured as a browsable hierarchy rather than a flat table.

```bash
# Content areas → indicators → measures → data
curl "https://ephtracking.cdc.gov/apigateway/api/v1/contentareas/json"
curl "https://ephtracking.cdc.gov/apigateway/api/v1/indicators/3"     # 3 = Asthma
curl "https://ephtracking.cdc.gov/apigateway/api/v1/measures/3"
curl "https://ephtracking.cdc.gov/apigateway/api/v1/getCoreHolder/90/2/ALL/ALL/2020/0/0"
```

Two things cost real time here. The `/json` suffix is inconsistent: `contentareas/json` requires it, while `indicators/{id}` and `measures/{id}` reject it with `"Invalid Call from API"`. Follow the shape above rather than assuming a uniform convention.

The other is rate limiting. Roughly six unauthenticated calls in quick succession returns `429 "Server has serviced too many non-token requests"`. Any real ingestion needs an API token from CDC, stored the way `CDC_DATA_APP_TOKEN` already is in `update_cdc_open.yml`.

### NORS: foodborne and waterborne outbreaks

66,713 outbreak records back to 1971, and the only national outbreak dataset with an actual API.

```
{ "year": "1971", "month": "2", "state": "California", "primary_mode": "Water",
  "etiology": "Copper", "etiology_status": "Confirmed", "setting": "Restaurant",
  "illnesses": "2", "deaths": "0", "water_type": "Community" }
```

`state` is the finest geography available. Outbreaks are attributed to the reporting state health department, not to a county or a venue. For sub-state foodborne signal you need either local restaurant inspections (Tier 2 below) or `openFDA` recall distribution patterns. At roughly 67k rows this is small enough to ingest without any size concern, which makes it a strong first candidate.

---

## Tier 2: State and local open data portals

A large share of state and county health portals run Socrata, the same platform as `data.cdc.gov`. That means the `cdc_open` client's pagination, `$where` filtering and CSV export all work against them unchanged. Only the base URL differs, and `Dataset` already has a `base_url` field for exactly this.

### Discovering portals programmatically

Rather than hardcoding a portal list that will rot, the Socrata Discovery API searches every Socrata domain at once:

```bash
# What health data exists, and on which domains?
curl "https://api.us.socrata.com/api/catalog/v1?q=covid&limit=100"

# Scope to one portal
curl "https://api.us.socrata.com/api/catalog/v1?domains=health.data.ny.gov&q=influenza&only=dataset"
```

Tallying domains across queries for covid, influenza, cancer, foodborne and tick produced the portal ranking below. Every dataset ID was then fetched directly and returned live rows.

### Verified state portals

| Portal                  | Topic      | ID          | Dataset                                                                 |
| ----------------------- | ---------- | ----------- | ----------------------------------------------------------------------- |
| `health.data.ny.gov`    | Tick       | `vzbp-i2d4` | Deer Tick Surveillance: Adults, **by county**                           |
| `health.data.ny.gov`    | Tick       | `kibp-u2ip` | Deer Tick Surveillance: Nymphs, by county                               |
| `health.data.ny.gov`    | Tick       | `sy3m-5gti` | Risk of Infected Blacklegged Tick Encounter, w/ polygons                |
| `health.data.ny.gov`    | Flu        | `jr8b-6gh6` | Influenza Lab-Confirmed Cases **by county**, 2009 onward                |
| `health.data.ny.gov`    | Cancer     | `y2hp-qjpb` | Deaths Due to Cancer by Site, Sex, Age                                  |
| `health.data.ny.gov`    | Foodborne  | `2hcc-shji` | Food Service Establishment Inspections, 2005 onward                     |
| `data.pa.gov`           | Flu        | `mrpb-ugjv` | Influenza + RSV Case Counts **by county**, 2025–26                      |
| `data.pa.gov`           | COVID      | `kayn-sjhx` | COVID Hospitalizations, weekly by county                                |
| `data.pa.gov`           | Mortality  | `smxk-2cca` | Deaths aggregated at state/county level, 1990 onward                    |
| `data.delaware.gov`     | Cancer     | `dp2v-5sfv` | Cancer Incidence                                                        |
| `data.delaware.gov`     | Flu        | `46y5-s57v` | Influenza Cases                                                         |
| `data.delaware.gov`     | Flu        | `m96q-uzzi` | Influenza **wastewater** viral activity                                 |
| `opendata.maryland.gov` | Cancer     | `yg8i-6p9m` | Age-Adjusted Cancer Incidence by Jurisdiction                           |
| `opendata.maryland.gov` | COVID      | `ntd2-dqpx` | COVID Cases **by ZIP code**                                             |
| `data.ct.gov`           | Notifiable | `4rss-apm8` | Reportable Disease Case List **by county**                              |
| `data.ct.gov`           | COVID      | `28fr-iqnx` | COVID Tests/Cases/Deaths **by town** (archived)                         |
| `healthdata.tn.gov`     | COVID      | `en4s-cm4i` | COVID Cases and Outcomes by County, 2020–24                             |
| `healthdata.tn.gov`     | Cancer     | `mgff-jwis` | Average Annual Lung Cancer Cases, 2001–2020                             |
| `data.ny.gov`           | COVID      | `xdss-u53e` | Statewide COVID Testing **by county** (serves via `health.data.ny.gov`) |
| `healthdata.gov`        | Hospital   | `g62h-syeh` | HHS hospital capacity & staffing shortages by state                     |

`data.chhs.ca.gov` (California Health & Human Services) runs CKAN rather than Socrata, and has the strongest county-level infectious disease coverage found anywhere. See [Tier 3](#ckan-portals-california-and-others).

New York's tick surveillance is the standout. It is county-level entomological data, not case counts, but the tick population itself, tested for pathogens:

```
{ "year": "2008", "county": "Albany", "total_sites_visited": "1",
  "total_ticks_collected": "314", "adult_density": "200", "total_tested": "52",
  "b_burgdorferi": "57.700", "a_phagocytophilum": "1.900", "b_microti": "0" }
```

Those are infection-prevalence percentages by pathogen. Nothing federal comes close to that resolution, and because it measures the vector rather than the patient it leads human cases rather than lagging them.

### Verified county and city portals

| Portal                         | Topic      | ID          | Dataset                                       |
| ------------------------------ | ---------- | ----------- | --------------------------------------------- |
| `data.cityofchicago.org`       | Flu        | `8vvr-jv2g` | Influenza Risk Level **by ZIP code**          |
| `data.cityofchicago.org`       | Flu        | `6xmk-qk57` | Influenza Surveillance Weekly                 |
| `data.cityofchicago.org`       | COVID      | `qwib-edaw` | COVID-like illness ED visits                  |
| `data.cityofchicago.org`       | Foodborne  | `4ijn-s7e5` | Food Inspections                              |
| `data.cityofnewyork.us`        | Flu        | `2nwg-uqyg` | ED Visits for Influenza-like Illness          |
| `data.cityofnewyork.us`        | Foodborne  | `43nn-pn8j` | DOHMH Restaurant Inspection Results           |
| `data.lacity.org`              | COVID      | `fvye-93wd` | **Neighborhood-level** COVID data             |
| `data.kingcounty.gov`          | Foodborne  | `r878-4sxa` | Food Establishment Inspections                |
| `datacatalog.cookcountyil.gov` | Mortality  | `r5wk-nc2x` | Suburban Cook County selected causes of death |
| `data.napacounty.gov`          | COVID/Flu  | `n5fh-b3q8` | **Wastewater** levels and trends              |
| `data.montgomerycountymd.gov`  | Foodborne  | `5pue-gfbe` | Food Inspections                              |
| `data.ramseycountymn.gov`      | Infectious | `iw4p-s622` | Infectious Disease Summary                    |

Restaurant inspections are the most consistently available local health dataset in the country. Nearly every large county publishes them, usually with lat/long, and they lead foodborne risk in a way NORS does not, since NORS only records outbreaks after somebody investigates one. Local wastewater monitoring is also spreading fast: Napa County and Delaware both publish their own series independent of the federal NWSS feed the repo already collects.

The archive problem is visible in the table above. Much of the COVID-era state data is marked ARCHIVE or stopped updating in 2023–24. Treat anything COVID-related from a state portal as a historical record rather than a live feed, and check `rowsUpdatedAt` before putting it on a dashboard.

---

## Tier 3: Non-Socrata portals

Both platforms below are now fetchable end to end, though each took a detour to get there. CKAN needs a second hop through a short-lived signed URL, and ArcGIS hides its data behind a layer index that has to be enumerated first.

### CKAN portals (California and others)

✅ Catalog verified. CKAN powers `data.ca.gov` and, more usefully, `data.chhs.ca.gov` (California Health & Human Services), which is where the state's actual health data lives. 87 datasets matched a county communicable-disease query alone:

```bash
curl "https://data.chhs.ca.gov/api/3/action/package_search?q=county+communicable+disease&rows=4"
curl "https://data.chhs.ca.gov/api/3/action/package_show?id=03e61434-7db8-4a53-a3e2-1d4d36d6848d"
```

Standouts, all county-level: Infectious Diseases by Disease, County, Year, and Sex (2001–2023), Vaccine Preventable Disease Cases by County and Year, STDs by Disease, County, Year, and Sex, and County Health Status Profiles.

✅ Downloads verified. CKAN hands back metadata with a resource URL rather than the data, and that URL `302`s to a pre-signed `s3.amazonaws.com` link:

```
https://data.chhs.ca.gov/dataset/<pkg>/resource/<res>/download/<file>.csv
  → 302 → https://s3.amazonaws.com/og-production-open-data-.../<file>.csv?X-Amz-...
```

That redirect is a pre-signed URL with an 86400-second expiry, so it cannot be cached and replayed later. Any ingestion has to resolve the CKAN resource immediately before each download. The two-hop, short-lived-URL pattern is more involved than the Socrata path and is not something the `cdc_open` client does today.

Infectious Diseases by Disease, County, Year, and Sex was fetched end to end: 13 MB, 199,125 rows, covering 52 reportable diseases across all 59 California counties, 2001–2023, stratified by sex, with population denominators and confidence intervals.

```
"Disease","County","Year","Sex","Cases","Population","Rate","Lower_95__CI","Upper_95__CI"
Lyme Disease,Alameda,2001,Female,2,746596,0.268*,0.032,0.968
```

It is the richest local dataset on the page. All six tickborne conditions (Anaplasmosis, Babesiosis, Ehrlichiosis, Lyme, Spotted Fever Rickettsiosis, Tularemia) sit in the same file as the major foodborne ones (Campylobacteriosis, Salmonellosis, Cryptosporidiosis, Cyclosporiasis, Vibrio, botulism variants), with 23 years of history and real denominators rather than raw counts.

Two parsing notes. `Rate` carries a trailing `*` on statistically unstable values (`0.268*`), so the column is text and needs stripping before it will cast to float. And `Sex` includes a `Total` row alongside `Female` and `Male`, so summing without filtering double-counts.

`catalog.data.gov` is reachable but no longer exposes a CKAN action API; `/api/3/action/*` returns `404` across the board. Use the Socrata discovery API or ArcGIS Hub for cross-agency search instead.

### ArcGIS Hub / FeatureServer

✅ Discovery verified. `hub.arcgis.com` is the best way to find state and county health GIS data, and it indexes far more than expected, with 25,244 hits for "tick surveillance" alone. Filtering by type is essential, since most results are dashboards and web maps rather than queryable data:

```bash
curl "https://hub.arcgis.com/api/v3/datasets?q=blacklegged+tick&filter\[type\]=Feature+Service"
```

The ArcGIS Online search API turned out to be the better tool, because it supports field-scoped queries that Hub does not:

```bash
curl "https://www.arcgis.com/sharing/rest/search?q=%22Alpha-Gal%22+AND+type%3A%22Feature+Service%22&f=json&num=20"
curl "https://www.arcgis.com/sharing/rest/search?q=owner%3AJonny.Rogers.ADH+AND+type%3A%22Feature+Service%22&f=json"
```

Searching by `owner:` is the trick that pays off. Once one useful layer turns up, its publisher usually has a whole catalogue behind it. Arkansas DoH (`Jonny.Rogers.ADH`) alone exposes 122 feature services, including county-aggregated tickborne, chlamydia, gonorrhea, syphilis and rabies series.

These queries surfaced the finds relevant to the tickborne question:

| Dataset                              | Publisher     | Host         | Why it matters                                                  |
| ------------------------------------ | ------------- | ------------ | --------------------------------------------------------------- |
| Tick Diseases Annual Cases per 100k  | Missouri DHSS | `gis.mo.gov` | County tick disease rates in a **top-five alpha-gal state** ✅  |
| _A. americanum_ Pop Status           | Kansas DHE    | `services9`  | **Lone star tick** status + AGS county classification           |
| `Suspected_Cases_of_AGS_WFL1`        | Kansas DHE    | `services9`  | A layer dedicated purely to **suspected alpha-gal cases**       |
| `ADH_Tickborne_County_Year_Agg`      | Arkansas DoH  | `services5`  | County × year tickborne aggregation, another top-five AGS state |
| Kansas Risky Tick Habitats           | Kansas        | `services2`  | Habitat-level exposure risk                                     |
| _I. scapularis_ Distribution         | Kansas DHE    | `services9`  | Blacklegged tick distribution                                   |
| NCI County Lung / Colon Cancer Rates | NCI           | `services7`  | County cancer rates as feature layers                           |

Arkansas DoH also runs Alpha-Gal Syndrome by Month dashboards in both CONFIRMED and SUSPECTED variants, which implies an ongoing monthly state surveillance series rather than the frozen 2022 MMWR snapshot. Finding the feature service behind those dashboards is the most promising open thread here.

✅ Data retrieval verified. Feature services live on numbered hosts (`services1` through `services9.arcgis.com`), the unnumbered `services.arcgis.com`, or state-run servers like `gis.mo.gov`. The query pattern:

```bash
curl "https://services9.arcgis.com/<org>/arcgis/rest/services/<layer>/FeatureServer/0/query\
?where=1%3D1&outFields=*&returnGeometry=false&resultRecordCount=2000&f=json"
```

Running that against real services taught a few things. Enumerate layers first: a FeatureServer root (`?f=json`) lists its layers and tables, and the interesting one is rarely layer 0. On the Kansas service, layer 0 is a state boundary and the alpha-gal data sits in layers 1 and 3.

Pagination behaves as documented. `resultOffset` and `resultRecordCount` against `maxRecordCount` (2000 on both services tested) paged Missouri's 2,399 records cleanly as 2000 + 399. Pass `returnGeometry=false` unless you need the shapes, since county polygons dwarf the attributes and the tabular layer is usually all you want.

Server-side aggregation is available too. `returnCountOnly`, `returnDistinctValues` and `outStatistics` all work, so you can profile a dataset without downloading it, which suits a repo watching its own size.

One dead end worth recording: vector tile services are not a data source. Vermont's cancer incidence layers on `tiles.arcgis.com` report `"capabilities": "TilesOnly,Tilemap"`, meaning pre-rendered map tiles with no query endpoint and no attribute access. Anything published only as a `VectorTileServer` is a picture, not a dataset. Look for a sibling FeatureServer instead.

---

## Alpha-gal syndrome (the hard case)

This one gets its own section because the obvious sources all fail and the one that works sits somewhere nobody would think to look.

Alpha-gal syndrome is not nationally notifiable. It is absent from NNDSS, has no `data.cdc.gov` dataset (a Socrata catalog search for "alpha-gal" across all domains returns exactly one result, an unrelated HHS innovation-challenge record), and has no CDC API of any kind. Searching CDC's own properties for it returns nothing usable.

County-level data does exist, republished by a state health department as a GIS layer covering four states. That is the finding of this section, and it was reachable only through ArcGIS rather than any health-data catalog.

What exists instead:

| Source                                 | Geography        | Format                   | Status |
| -------------------------------------- | ---------------- | ------------------------ | ------ |
| **AGS + lone star tick status (KDHE)** | County, 4 states | **ArcGIS FeatureServer** | ✅     |
| Tick disease rates (MO DHSS)           | County           | **ArcGIS FeatureServer** | ✅     |
| Tick vector surveillance (NY)          | County           | **Socrata API**          | ✅     |
| MMWR 72(30) county distribution        | County           | Choropleth figure only   | ❌     |
| Commercial lab testing (Viracor)       | County           | Proprietary              | ❌     |
| State surveillance (e.g. Maine)        | State            | Reports                  | ❌     |

The 2023 MMWR "[Geographic Distribution of Suspected Alpha-gal Syndrome Cases](https://www.cdc.gov/mmwr/volumes/72/wr/mm7230a2.htm)" is the county-level source everyone cites. It counted 233,521 suspected cases in 2017–2022, but derived them from one commercial laboratory's IgE test orders (Eurofins Viracor). The geography therefore reflects where that lab's testing was ordered, not where the disease is, and counties with high case counts may simply be counties with clinicians who know to test. Arkansas, Kentucky, Missouri, Tennessee and Virginia led on cases per capita.

The article itself has no county table. The full text was retrieved from PubMed Central and parsed: it contains exactly one table, breaking 295,400 test results down by age group, sex and year, with no geography. There are no supplementary files, and the county distribution appears only as a rendered choropleth. As a source, the MMWR is a dead end.

### But the county data is published elsewhere ✅

Kansas DHE republishes the MMWR county classification as an ArcGIS feature layer, and it is queryable:

```bash
BASE=https://services9.arcgis.com/Q6wTdPdCh608iNrJ/arcgis/rest/services/A__americanum_Pop_Status_WFL1/FeatureServer
curl "$BASE/3/query?where=1%3D1&outFields=*&returnGeometry=false&f=json"
```

372 counties across Kansas, Missouri, Arkansas and Oklahoma, each row carrying alpha-gal burden and lone star tick status side by side:

```
{ "State_Prop": "Kansas", "StateAbbrv": "KS", "Cnty_FIPS": 20001,
  "Cnty_Prop": "Allen ", "AGS_Status": "High", "AGS_Num": 4,
  "AGS_NoTest": 0, "AGS_NoCase": 0, "AGS_LT11": 0, "AGS_1187": 0, "AGS_GT87": 1,
  "AAPop_Status": "Reported", "AAPop_Est": 0, "AAPop_Rptd": 1 }
```

The `AGS_*` flags are the MMWR's own tertiles, and its footnote gives the units precisely: counties were assigned to "low (<11 suspected AGS cases per 1M PPY), medium (11–87), and high (>87)". So these are rates per million person-years binned into thirds, not case counts. Layer 1 carries the same attributes joined to county polygons; layer 3 is the flat table.

| Field                                                | Meaning                             | Counties       |
| ---------------------------------------------------- | ----------------------------------- | -------------- |
| `AGS_Status` / `AGS_GT87`                            | High: >87 cases per 1M person-years | 187            |
| `AGS_1187`                                           | Medium: 11–87                       | 118            |
| `AGS_LT11`                                           | Low: <11                            | 6              |
| `AGS_NoCase`                                         | Tested, no cases found              | 46             |
| `AGS_NoTest`                                         | No testing performed                | 15             |
| `AAPop_Status` = Established / Reported / No Records | Lone star tick population status    | 142 / 33 / 197 |

Two limits keep this honest. It covers four states, not the nation, so it is a regional slice of the MMWR rather than a replacement for it. And it inherits every bias of the original: the underlying geography still reflects where one commercial lab's tests were ordered, which makes `AGS_NoTest` and `AGS_NoCase` statements about surveillance rather than about absence of disease.

Even so, this is the closest thing to county-level alpha-gal data in machine-readable form, and it puts the syndrome and its vector in the same row, which is exactly the join the question implies.

### Vector surveillance more broadly

Alpha-gal is transmitted primarily by the lone star tick (_Amblyomma americanum_), so vector data measures exposure risk rather than diagnosis. For a condition this badly under-diagnosed, that may be the more honest signal.

Missouri DHSS publishes Tick Diseases Annual Cases per 100k ✅ at county level, and it is fetchable:

```bash
curl "https://gis.mo.gov/arcgis/rest/services/DHSS/Tick_Diseases_Annual_Cases_per_100k/FeatureServer/0/query\
?where=1%3D1&outFields=NAME,YEAR,DISEASE,Cases,CaseRate&returnGeometry=false&f=json"
```

2,399 records covering 2009–2021 for Anaplasmosis, Ehrlichiosis, Lyme, Spotted Fever Rickettsiosis and Tularemia, with `CaseRate` per 100k. Ehrlichiosis is itself lone-star-transmitted, making it a same-vector proxy in a top-five AGS state. Suppression is the limitation: only 537 of the 2,399 rows carry a real value, and the other 78% read `Suppressed (Less than 5 cases)`, so coverage by county, year and disease is sparse outside the higher-incidence counties.

New York's `vzbp-i2d4` is still the richest vector dataset overall, though its program tracks the blacklegged tick, the Lyme vector, rather than the lone star.

One thing already in the repo is worth connecting here. `src/wonder/queries/fetch_tick_borne_diseases.py` collects national tickborne case counts from NNDSS (D130) for babesiosis, ehrlichiosis, Lyme, spotted fever, tularemia and Powassan, by year and disease, with no geographic breakdown and with alpha-gal absent because it is not notifiable. Adding state grouping to that existing query is a smaller change than any new source on this page.

---

## Cancer below the state line

The repo's SEER module covers national incidence and mortality by site. County-level cancer runs through a different system.

State Cancer Profiles ✅ is the NCI/CDC joint system and the standard source for county cancer rates. It has no documented API, but its interactive tables accept an `output=1` parameter that returns CSV, the same undocumented-but-public arrangement the `seer` module already relies on. Both the incidence and mortality endpoints were confirmed working:

```bash
# County incidence, all cancer sites, Alabama (stateFIPS=01)
curl "https://statecancerprofiles.cancer.gov/incidencerates/index.php?stateFIPS=01\
&areatype=county&cancer=001&race=00&sex=0&age=001&stage=999&year=0&type=incd&output=1"

# County mortality, same parameters with a different path and type
curl "https://statecancerprofiles.cancer.gov/deathrates/index.php?stateFIPS=01\
&areatype=county&cancer=001&race=00&sex=0&age=001&year=0&type=death&output=1"
```

The response is CSV behind a few header lines naming the cohort and period:

```
Incidence Rate Report for Alabama by County
"All Cancer Sites (All Stages^), 2018-2022"
"All Races (includes Hispanic), Both Sexes, All Ages"

County,FIPS,2023 Rural-Urban Continuum Codes,Age-Adjusted Incidence Rate - cases
per 100,000,Lower 95% CI,Upper 95% CI,CI*Rank,...,Average Annual Count,Recent Trend,...
"Crenshaw County(2)",01041,Rural,566.6,516.7,620.4,1,1,8,104,rising,2.9,1.7,4.2
"Lowndes County(2)",01085,Urban,532.8,477.4,593.4,2,1,27,75,stable,1.0,-0.3,2.4
```

For county cancer this is as good as it gets: FIPS, age-adjusted rate with confidence intervals, a rank with its own CI, average annual count, rural/urban continuum code, and a directional 5-year trend. `areatype=county` is the parameter that matters. `cancer=001` is all sites, and the site codes follow the same NCI scheme the `seer` module uses.

Three practical notes. Queries run one state at a time, because `stateFIPS` does not accept `ALL` for county output, so a national county file means 51 requests. The leading header lines and the trailing footnote block both need stripping before the CSV parses. And since the parameter set is undocumented it can change without notice, so anything built on it needs a schema assertion on every run. The `risk/` endpoint for screening and risk-factor data uses a different parameter set than the one tried here and needs its own reverse-engineering.

County Health Rankings ✅ publishes a single national county-level CSV covering every ranked measure:

```bash
curl -O "https://www.countyhealthrankings.org/sites/default/files/media/document/analytic_data2025_v2.csv"
```

13 MB, one row per county, with `5-digit FIPS Code` as the join key. Each measure arrives as a family of columns: raw value, numerator, denominator, CI low and high, a suppression flag, and separate estimates stratified by race (AIAN, Asian, Black, Hispanic, White). For a ranking product that is unusually honest about its own uncertainty.

The catch is that the source is ending. CHR&R funding stops in December 2026; the program published a partial refresh in March 2026 instead of its usual annual release, and is migrating to a community-run open-source project. Treat the analytic file as a fixed historical asset to archive once rather than a recurring feed. For a repo already fighting its own size, that shape is a feature.

CDC WONDER offers `D43` (NPCR incidence) and `D53` (cancer mortality), both already documented in [Dataset Reference](wonder/datasets.md). NPCR covers around 97% of the US population against SEER's 48%, which makes it the better denominator for state comparisons, though county-level cells suppress aggressively.

State cancer registries publish their own data, often at finer granularity than the federal rollups. Maryland's `yg8i-6p9m` and Delaware's `dp2v-5sfv` above are examples. Every state has a registry; only some publish via an API.

---

## Network access

Development here runs behind a network allowlist, so "unreachable" and "does not exist" are easy to confuse. A blocked domain fails instantly with `curl` exit 7 and no HTTP status, while a real outage times out or returns a code. Everything below was classified on that basis on 2026-08-02.

### Host availability is not stable

Allowlisted hosts flap, and that turned out to matter more than which hosts were on the list. Over a single working session, `services.arcgis.com`, `services1` and `services9` each served real data and then returned connection-refused 3/3 within minutes, while `hub`, `www`, `tiles` and `gis.mo.gov` stayed up throughout. `data.chhs.ca.gov` went blocked, then reachable, then served a 13 MB download.

That has three consequences for anything built here. Retry aggressively: `curl --retry 3 --retry-all-errors --retry-delay 3` wrapped in an outer attempt loop is what got California's file down, where a single-shot fetch would have reported failure. Never write a source off from one probe, either. Every ❌ on this page rests on repeated checks plus a reason (no endpoint exists, WAF `403`, tiles-only capability) rather than on a single refused connection. And snapshot the catalog whenever a window opens, since discovery hosts have been the most stable; record service URLs while you can reach them instead of assuming they will be there when you need to fetch.

| Host group                         | Observed behaviour                                           |
| ---------------------------------- | ------------------------------------------------------------ |
| `hub` / `www` / `tiles.arcgis.com` | Stable throughout; discovery and search are dependable       |
| `services*.arcgis.com`             | Intermittent; served data in one window, refused in the next |
| `gis.mo.gov`, `s3.amazonaws.com`   | Stable once opened                                           |
| `data.chhs.ca.gov`                 | Flapped, then downloaded 13 MB cleanly                       |

Wildcards are worth a warning. `*.arcgis.com` does not behave like a supported pattern: subdomains open and close independently rather than together, so each needs listing individually and none can be assumed from a sibling.

### Reachable but WAF-blocked, so allowlisting will not help

`www.cdc.gov`, `wonder.cdc.gov` and `www.fsis.usda.gov` all resolve and connect, then return `403` to non-browser clients. That is the origin's own bot protection rather than the allowlist, so adding them changes nothing. The WONDER API at `wonder.cdc.gov/controller/datarequest` accepts POSTs normally, which is why `src/wonder/` works; only the HTML pages are protected. FSIS therefore has no usable recall API from here, leaving openFDA as the only machine-readable recall source.

### Now reachable

`hub.arcgis.com`, `www.arcgis.com`, `tiles.arcgis.com`, `gis.mo.gov`, `s3.amazonaws.com`, `catalog.data.gov` (reachable, though its CKAN action API is gone and `/api/3/action/*` returns `404`), `data.ca.gov`, `data.chhs.ca.gov`, `healthdata.gov`, `opendata.maryland.gov`, `data.ramseycountymn.gov`, `pmc.ncbi.nlm.nih.gov`, `statecancerprofiles.cancer.gov`, `www.countyhealthrankings.org`, and the Tier 2 Socrata portals. `services*.arcgis.com` is intermittent per the section above.

`data.ny.gov` resolves and its health datasets work, because resource requests `302` to `health.data.ny.gov`, which is already allowlisted. Its `/api/views/*` metadata paths still fail.

Two further traps when classifying a host. `api.us.socrata.com` refuses HEAD but serves GET, so a HEAD-based probe reports a false block. And a bare-hostname check can succeed while real paths fail on the same host. Probe with a GET against a real path.

## Ingestion strategy

`data/` is 352 MB and `.git` is 358 MB, and the CDC Open workflow (`.github/workflows/update_cdc_open.yml`) already carries a safety net that drops files over 95 MB before they can wedge a push. Adding a local tier naively, 50 states across several topics, would make that permanently worse, because git history does not shrink.

Four constraints are worth applying before adding anything.

Filter at the source rather than after. `Dataset.soql_where` already exists and pushes the filter server-side, so a PLACES query scoped to one state is a few MB where the national tract file is not committable at all.

Prefer aggregates to microdata. `fetch_beam.py` is the pattern to copy: it pulls roughly 200k state-level rows and commits a national monthly rollup instead of the raw file. Most local sources should land in `data/processed/` rather than `data/raw/`.

Pick depth over breadth. One or two states covered well is more useful, and far cheaper, than every state covered shallowly. New York and Pennsylvania have the strongest verified coverage across tick, flu, cancer and mortality.

Check for staleness before wiring anything up. Socrata exposes `rowsUpdatedAt` in its metadata, and a dataset last updated in 2023 belongs in an archive note rather than a scheduled workflow.

Ranked by value per megabyte, the first candidates are:

1. **County NSSP** via the installed `nssp` module. Zero new code, zero new storage, current data.
2. **NORS** (~67k rows). National outbreak history with no local equivalent, small enough to ignore size concerns.
3. **NY tick surveillance.** County-level vector data with pathogen prevalence, and nothing federal matches it.
4. **State Cancer Profiles.** County cancer incidence and mortality, though a national file costs 51 requests.
5. **County Health Rankings.** One 13 MB archival snapshot, worth taking before the program ends.
6. **Kansas DHE alpha-gal + lone star tick layer.** 372 rows, trivially small, and the only machine-readable county-level AGS data found anywhere.
7. **Missouri DHSS tick disease rates.** 2,399 rows, county × year × disease.

The ArcGIS sources are small enough that size is a non-issue. They rank below the others only because they cover four states rather than the nation.

California's county infectious disease series deserves separate mention. At 13 MB and 199,125 rows it is the largest single candidate here, but it covers 52 diseases across 59 counties and 23 years, with denominators and confidence intervals, and it puts tickborne and foodborne conditions in the same file. Per megabyte it is the best value on the page, and it would sit comfortably under the 95 MB workflow guard. If only one new source gets wired up, this is the one to argue for.
