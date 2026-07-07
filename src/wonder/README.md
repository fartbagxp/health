# WONDER

[CDC WONDER](https://wonder.cdc.gov/) is CDC's public data query system — mortality, births, vaccine adverse events. It has a web interface and an XML API you can POST queries to.

This module adds a natural-language front end. You describe what you want; an LLM turns it into the XML. Dataset parameters are scraped from the WONDER web interface and saved to `data/raw/wonder/`. Base templates live in `src/wonder/templates/`.

## Module layout

```bash
src/wonder/
├── llm_query_builder.py  — LLM-backed query builder (primary interface)
├── client.py             — WonderClient + low-level QueryBuilder
├── __main__.py           — CLI entrypoint
├── templates/            — Base XML templates per dataset
└── queries/              — Saved working query XMLs
```

Scraped parameter definitions: `data/raw/wonder/query_params_D*.json`

## Docs

- [User guide](../../docs/wonder.md) — setup, datasets, prompt tips, parameter reference
- [Architecture & troubleshooting](../../docs/wonder_llm_query_builder.md) — how the LLM builder works, mode selectors, known issues
- [Examples](../../docs/wonder_examples.md) — worked examples with real results
- [Adding a dataset template](../../docs/wonder_api_template.md) — how to scrape and wire up a new dataset

## Saved queries

Pre-built XML queries in `queries/` that have been verified against the API.

### Natality — births per year, 1995–2024

Three datasets are needed to cover the full range because WONDER splits natality into historical epochs:

| Query file                         | Dataset               | Years     | API dataset ID |
| ---------------------------------- | --------------------- | --------- | -------------- |
| `births-by-year-1995-2002-req.xml` | Natality (historical) | 1995–2002 | D10            |
| `births-by-year-2003-2006-req.xml` | Natality (historical) | 2003–2006 | D27            |
| `births-by-year-2007-2024-req.xml` | Natality (current)    | 2007–2024 | D66            |

Each query groups by `Year` (`V20` in all three datasets) and returns the `Births` count measure (`M1`). All other filters are set to `*All*`.

**Key findings (1995–2024):**

- Peak births were in **2007 at 4,316,233** — the tail end of a decade-long rise
- The 2000s saw sustained growth, reaching ~4.1–4.3M births per year from 2003–2007
- A steady decline followed, from 4.25M in 2008 down to 3.61M in 2020 (-16% over 12 years)
- Births have been roughly flat since 2020, hovering around 3.6–3.7M through 2024
- 2024 registered 3,628,934 births — the lowest total since at least 1995

**API notes for D27 (2003–2006):** This dataset requires the full complement of base template parameters (`O_natality_archive_pops`, `O_weight`, `O_gestation`, all `V_` variable filters) to be present in the request XML. Sending a minimal subset returns a 500 error with an unfilled template message. D10 and D66 are more tolerant.

### Mortality

| Query file                                        | Topic                              | Years     |
| ------------------------------------------------- | ---------------------------------- | --------- |
| `opioid-overdose-deaths-2018-2024-req.xml`        | Opioid overdose deaths             | 2018–2024 |
| `heart-vs-cancer-by-sex-2018-2023-req.xml`        | Heart disease vs. cancer by sex    | 2018–2023 |
| `covid-deaths-by-race-2020-2023-req.xml`          | COVID-19 deaths by race            | 2020–2023 |
| `racial-mortality-gap-2018-2023-req.xml`          | Mortality gap by race              | 2018–2023 |
| `infant-mortality-2018-2023-req.xml`              | Infant mortality                   | 2018–2023 |
| `unintentional-injuries-by-age-2018-2023-req.xml` | Unintentional injury deaths by age | 2018–2023 |

### Maternal mortality — national trend (1999–2024)

Two datasets are needed to cover the full ICD-10 era:

| Query file                                     | Dataset                                 | Years     | API ID |
| ---------------------------------------------- | --------------------------------------- | --------- | ------ |
| `maternal-mortality-by-year-1999-2020-req.xml` | Underlying Cause of Death (bridged)     | 1999–2020 | D76    |
| `maternal-mortality-by-year-2018-2024-req.xml` | Underlying Cause of Death (single-race) | 2018–2024 | D158   |

ICD-10 filter: `O00–O99` (Pregnancy, childbirth and the puerperium) + `A34` (Obstetrical tetanus). Grouped by Year, national only.

Run both and merge:

```
uv run python src/wonder/queries/fetch_maternal_mortality.py
→ data/raw/wonder/maternal-mortality-by-year.csv
```

**Key findings (1999–2024):**

- Counts were ~400–800/year from 1999–2009, rising as states adopted the 2003 revised death certificate (pregnancy checkbox rollout 2003–2017 — largely measurement change, not a real increase)
- Peak in 2021 at **1,687 deaths** (COVID-era spike); declined to ~1,000 by 2023–2024
- The 2018 drop reflects the end of the checkbox rollout and a methodology reset (NCHS shifted to D158 single-race)

**API limitation — state-level data not available:** The WONDER web service returns a 500 error for any query that groups by or filters to a specific state on mortality datasets. To get state-level maternal mortality data, use the Playwright scraper:

```bash
# Prerequisites (run once — downloads the browser binary; package already in pyproject.toml)
uv run playwright install chromium

# Run — takes ~5 min; waits 90 s between the two dataset queries
uv run python src/wonder/queries/scrape_maternal_mortality_by_state.py
→ data/raw/wonder/maternal-mortality-by-state-year.csv
```

The scraper (`scrape_maternal_mortality_by_state.py`) navigates the WONDER web UI with a headless browser, sets Group By = Year × State, filters UCD = `O00–O99`, and exports both D76 (1999–2017) and D158 (2018–2024). It cannot run in the project's CI environment (requires browser libraries), so run it locally when you need fresh state-level data. Alternatively, the static **NCHS table** (2018–2022 pooled, by state) is at https://www.cdc.gov/nchs/maternal-mortality/mmr-2018-2022-state-data.pdf

**Rate note:** WONDER's crude rate column uses total population as denominator. The official maternal mortality rate (MMR) uses **live births** per 100,000 as denominator. Join with birth counts from the Natality queries (D66) to compute true MMR.

**Pregnancy checkbox caveat:** The 2003 revised U.S. Standard Certificate of Death added a pregnancy checkbox. States adopted it on a rolling schedule 2003–2017, causing a staggered artificial rise in reported counts. Pre-2018 and post-2018 figures are not directly comparable for trend analysis without adjustment.

### Obesity & diabetes as a contributing cause of death (1999–present)

| Query file                                                | Dataset | Years     |
| ---------------------------------------------------------- | ------- | --------- |
| `obesity-diabetes-deaths-by-year-1999-2020-req.xml`       | D77     | 1999–2020 |
| `obesity-diabetes-deaths-by-year-2018-2024-req.xml`       | D176    | 2018–present |

Both queries group by Year × Multiple Cause of Death (MCD) ICD-10 code and filter to `E66` (obesity, all subtypes) and `E10`–`E14` (diabetes mellitus, all subtypes/complications). MCD counts a condition if it appears *anywhere* on the death certificate — a contributing factor — not only when it's the underlying cause. This is deliberately different from `leading_death.csv` (`cdc_open`), which counts diabetes only as an **underlying** cause and essentially never counts obesity at all, since obesity is rarely the immediate cause of death.

WONDER returns the specific ICD-10 subcode on each row (e.g. `E66.0`, `E11.9` — visible as the `cd` attribute on response cells, now exposed as `ResponseCell.code` in `client.py`). Subcodes are summed into their parent category per year.

```
uv run python src/wonder/queries/fetch_obesity_diabetes_deaths.py
→ data/raw/wonder/obesity-diabetes-deaths-by-year.csv
```

**Key findings (1999–2024):**

- Obesity as a contributing cause grew roughly **5×**: 13,049 deaths in 1999 → a peak of 96,262 in 2021
- Diabetes as a contributing cause grew from 209,811 (1999) to a peak of 416,780 (2021) — roughly 2×
- Both series spike sharply in **2020–2021**, consistent with obesity and diabetes acting as major COVID-19 comorbidities
- Diabetes as a contributing cause is consistently far larger than obesity — expected, since obesity is more often the upstream driver than something coded directly on the certificate

Merge strategy: D77 (final) for 1999–2020; D176 (provisional) for 2021+, same convention as the drug-deaths queries. 2018–2019 counts match exactly between the two datasets in the overlap years, cross-validating the query; 2020 differs slightly between D77-final and D176-provisional, as expected.

## CLI usage

```bash
# Build a query from natural language, output XML
uv run python -m wonder build "opioid deaths by year 2018-2024" -o query.xml

# Run an existing query XML file
uv run python -m wonder run queries/opioid-overdose-deaths-2018-2024-req.xml

# Run an existing query XML file, output CSV
uv run python -m wonder run queries/opioid-overdose-deaths-2018-2024-req.xml -f csv

# Build and execute in one step
uv run python -m wonder query "opioid deaths by year 2018-2024" --save-xml opioid-overdose-deaths-2018-2024-req.xml
```

| Command | Description                            |
| ------- | -------------------------------------- |
| `build` | Convert natural language to WONDER XML |
| `run`   | Execute a pre-built XML query          |
| `query` | Build and run in one step              |

| Option                    | Commands   | Description                    |
| ------------------------- | ---------- | ------------------------------ |
| `-o, --output FILE`       | build      | Output file (default: stdout)  |
| `-f, --format {json,csv}` | run, query | Output format (default: json)  |
| `-t, --timeout SECONDS`   | run, query | Request timeout (default: 60s) |
| `--save-xml FILE`         | query      | Save the generated XML         |
| `-v, --verbose`           | all        | Verbose output                 |
