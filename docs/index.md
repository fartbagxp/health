# US Health Data APIs

A Python toolkit for querying CDC surveillance and public health datasets — no API keys needed for most sources.

## Quick Start

```bash
git clone https://github.com/boris/health
cd health
cp .env.sample .env          # add ANTHROPIC_API_KEY for WONDER LLM queries
uv sync
```

## Data Sources

| Source                            | Module     | What it covers                                  | Years        |
| --------------------------------- | ---------- | ----------------------------------------------- | ------------ |
| [CDC WONDER](wonder/index.md)     | `wonder`   | Mortality, births, natality, environment, VAERS | 1968–present |
| [ATSDR GRASP / FluView](grasp.md) | `grasp`    | Flu hospitalizations, ILI activity, hantavirus  | 1997–present |
| [WISQARS](wisqars.md)             | `wisqars`  | Injury, firearm, overdose deaths by geography   | 1999–present |
| [NSSP](nssp.md)                   | `nssp`     | Emergency dept. visits for COVID/flu/RSV        | 2020–present |
| [NIS](nis.md)                     | `nis`      | Childhood & teen vaccination coverage           | 2011–present |
| [CDC Open Data](cdc-open.md)      | `cdc_open` | 30+ datasets: overdose, NHSN, NWSS, wastewater  | varies       |
| [SEER](seer.md)                   | `seer`     | Cancer incidence/mortality by site, sex, age    | 1975–present |

Federal surveillance mostly stops at the state line. Two research catalogs cover what is available below it, and nothing in either is collected yet. [State & Local Sources](local.md) goes deep on the endpoints that have been verified against live data: county and census-tract figures for cancer, COVID, flu, tickborne disease and foodborne outbreaks. [State Health Data Portals](state-portals.md) goes wide, listing the official portal for all 50 states and DC and grouping them by the software behind them.

## One-liners

```bash
# WONDER — natural language → CDC API
uv run python -m wonder query "drug overdose deaths by state 2020-2023" -f csv
uv run python -m wonder query "maternal mortality by race 2018-2023, age-adjusted rate"

# GRASP — FluSurv-NET hospitalizations
uv run python -m grasp flusurv by-season --location network_all -f table
uv run python -m grasp fluview ili data --region nat --epiweeks 202001-202520

# WISQARS — firearm deaths by state
uv run python -m wisqars state --intent FA_Deaths --year 2023 -f table

# NSSP — ED visit % for influenza
uv run python -m nssp hhs influenza --region 4

# NIS — childhood vaccination coverage
uv run python -m nis rates child 2022 -f table

# CDC Open Data — leading causes of death
uv run python -m cdc_open query bi63-dtpu --where "year='2021'" -f csv

# SEER — cancer mortality by site/sex/race
uv run python -m seer mortality --site 55 --sex female -f csv
```

## Setup Notes

Most sources need no credentials. WONDER's LLM query builder requires an Anthropic API key (`ANTHROPIC_API_KEY` in `.env`). The WONDER XML API itself is unauthenticated.

WONDER enforces a **15-second rate limit** between requests — scripts that loop over many queries must sleep between calls. See [Multi-Year Queries](wonder/multi-year.md) for a production-ready pattern.
