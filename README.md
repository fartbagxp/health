# Overview

This is a repository to collect and run fun experiments on various publicly available health APIs.

## Sources

| Data Source                                                           | Module          | API                     |
| --------------------------------------------------------------------- | --------------- | ----------------------- |
| [Wide-ranging ONline Data for Epidemiologic Research (WONDER)]        | `src/wonder/`   | CDC WONDER XML API      |
| [National Syndromic Surveillance Program (NSSP)]                      | `src/nssp/`     | CMU Delphi Epidata API  |
| [WISQARS Injury & Violence Data]                                       | `src/wisqars/`  | data.cdc.gov (Socrata)  |
| [National Immunization Survey (NIS)]                                  | `src/nis/`      | CDC FTP fixed-width DAT |
| [National Wastewater Surveillance System (NWSS)]                      | `src/cdc_open/` | data.cdc.gov (Socrata)  |
| [National Respiratory and Enteric Virus Surveillance System (NREVSS)] | `src/cdc_open/` | data.cdc.gov (Socrata)  |
| [National Healthcare Safety Network (NHSN)]                           | `src/cdc_open/` | data.cdc.gov (Socrata)  |
| [Children Vaccination]                                                | `src/cdc_open/` | data.cdc.gov (Socrata)  |
| [CDC Open Data (data.cdc.gov)]                                        | `src/cdc_open/` | data.cdc.gov (Socrata)  |

---

### CDC WONDER

[CDC WONDER](https://wonder.cdc.gov/) is CDC's public data query system covering mortality, births, vaccine adverse events, and more. It exposes an unauthenticated XML-over-HTTPS API. The [Wonder API](https://wonder.cdc.gov/wonder/help/wonder-api.html) accepts POST requests with XML query parameters including `accept_datause_restrictions=true`.

26 datasets are supported across mortality, infant/birth, natality, environmental, and VAERS categories. An LLM-powered query builder converts natural language into the XML query format.

The soft rate limit is a query every two minutes.

Refer to [WONDER README](src/wonder/README.md) for more information.

### NSSP — National Syndromic Surveillance Program

[NSSP](https://www.cdc.gov/nssp/) tracks the proportion of emergency department visits attributed to COVID-19, influenza, and RSV, updated weekly. This module uses the [CMU Delphi Epidata API](https://cmu-delphi.github.io/delphi-epidata/api/covidcast-signals/nssp.html) — a separate public API (no auth required) that processes and exposes NSSP signals at national, state, HHS region, and county level.

Time values use epiweek format (YYYYWW, e.g. `202518` = week 18 of 2025).

```bash
uv run python -m nssp query covid --geo-type nation --geo-value us -f table
uv run python -m nssp hhs influenza --region 4
uv run python -m nssp national --start 202401 -f csv
```

Refer to [NSSP source](src/nssp/) for more information.

### WISQARS — Web-based Injury Statistics Query and Reporting System

[WISQARS](https://wisqars.cdc.gov/) is CDC's injury data portal covering fatal and nonfatal injuries, violence, and overdose. WISQARS has no public API, but its underlying NCHS datasets are available on data.cdc.gov. 4 datasets are supported:

| Dataset              | Coverage     | Description                                             |
| -------------------- | ------------ | ------------------------------------------------------- |
| `injury_mortality`   | 1999–2016    | Fatal injury by mechanism, intent, age, race, sex       |
| `injury_national`    | 2019–present | National firearm/suicide/OD/homicide — monthly & annual |
| `injury_state`       | 2019–present | State-level firearm/suicide/OD/homicide                 |
| `injury_county`      | 2019–present | County-level firearm/suicide/OD/homicide                |

```bash
uv run python -m wisqars mortality --intent Suicide --mechanism Firearm -f csv
uv run python -m wisqars state --intent Drug_OD --year 2023 -f table
uv run python -m wisqars national --intent FA_Deaths --type year -f table
uv run python -m wisqars county --state Texas --intent FA_Deaths --year 2023
```

Refer to [WISQARS source](src/wisqars/) for more information.

### NIS — National Immunization Survey

The [NIS](https://www.cdc.gov/vaccines/imz-managers/nis/) is CDC's annual random-digit-dial telephone survey measuring childhood and adolescent vaccination coverage across the US. Two surveys are covered:

| Survey      | Ages        | Index page                                                          |
| ----------- | ----------- | ------------------------------------------------------------------- |
| **NIS-Child** | 19–35 months | https://www.cdc.gov/nis/php/datasets-child/index.html             |
| **NIS-Teen**  | 13–17 years  | https://www.cdc.gov/nis/php/datasets-teen/index.html              |

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

### CDC Open Data

[data.cdc.gov](https://data.cdc.gov) is the CDC's public open data portal, built on the Socrata platform. It exposes datasets as a standard REST/JSON API ([SODA](https://dev.socrata.com/)) — no authentication required for read access.

32 datasets are available covering mortality, birth indicators, COVID-19, respiratory surveillance, wastewater (NWSS), vaccination, disability, nutrition, overdose, notifiable diseases (NNDSS), NHSN nursing homes, NREVSS RSV, NSSP ED visits, and children's vaccination. An LLM-powered `analyze` command uses Claude to fetch and synthesize data in response to natural language questions.

```bash
uv run python -m cdc_open list
uv run python -m cdc_open analyze "Which states had the highest drug overdose death rates in 2023?"
```

Refer to [CDC Open README](src/cdc_open/README.md) for more information.

[CDC]: https://www.cdc.gov
[Wide-ranging ONline Data for Epidemiologic Research (WONDER)]: https://wonder.cdc.gov/wonder/help/wonder-api.html
[National Syndromic Surveillance Program (NSSP)]: https://www.cdc.gov/nssp/
[WISQARS Injury & Violence Data]: https://wisqars.cdc.gov/
[National Immunization Survey (NIS)]: https://www.cdc.gov/vaccines/imz-managers/nis/
[National Wastewater Surveillance System (NWSS)]: https://www.cdc.gov/nwss/about.html
[National Respiratory and Enteric Virus Surveillance System (NREVSS)]: https://www.cdc.gov/nrevss/php/dashboard/index.html
[National Healthcare Safety Network (NHSN)]: https://www.cdc.gov/nhsn/datastat/index.html
[Children Vaccination]: https://data.cdc.gov/Child-Vaccinations/Vaccination-Coverage-among-Young-Children-0-35-Mon/fhky-rtsk/about_data
[CDC Open Data (data.cdc.gov)]: https://data.cdc.gov
