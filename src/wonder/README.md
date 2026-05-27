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
