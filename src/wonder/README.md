# WONDER

[CDC WONDER](https://wonder.cdc.gov/) is CDC's public data query system — mortality, births, vaccine adverse events. It has a web interface and an XML API you can POST queries to.

This module adds a natural-language front end. You describe what you want; an LLM turns it into the XML. Dataset parameters are scraped from the WONDER web interface and saved to `data/raw/wonder/`. Base templates live in `src/wonder/templates/`.

## Module layout

```
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
- [Architecture & troubleshooting](../../docs/wonder-llm-query-builder.md) — how the LLM builder works, mode selectors, known issues
- [Examples](../../docs/wonder-examples.md) — worked examples with real results
- [Adding a dataset template](../../docs/wonder-api-template.md) — how to scrape and wire up a new dataset

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
