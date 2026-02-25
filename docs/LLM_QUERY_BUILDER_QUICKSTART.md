# LLM Query Builder - Quick Start

## What It Does

Converts a natural language description into a complete CDC WONDER XML query using Claude,
then executes it against the CDC WONDER API. The builder:

- Selects the right dataset automatically
- Merges your query intent onto a validated base template (all boilerplate handled)
- Enforces CDC WONDER constraint rules (e.g. AAR disabled when grouping by age)

## Setup

```bash
cp .env.sample .env
# Add: ANTHROPIC_API_KEY='your-anthropic-api-key'
```

## Usage

### Build and execute in one step

```bash
uv run python -m wonder query "opioid deaths by year 2018-2024" -f csv
```

### Save the query XML for reference

```bash
uv run python -m wonder query "opioid deaths by year 2018-2024" --save-xml query.xml -f csv
```

### Generate query XML only (no API call)

```bash
uv run python -m wonder build "opioid deaths by year 2018-2024" -o query.xml
```

### Python API

```python
from wonder.llm_query_builder import LLMQueryBuilder

builder = LLMQueryBuilder()
request = builder.build_query("opioid overdose deaths by year 2018-2024")
print(request.to_xml())
```

## Example Prompts

See `src/wonder/README.md` for a full catalog of 33+ example queries across all datasets.

A few to get started:

```bash
# Deaths by cause and year (D176, most recent data)
uv run python -m wonder query "COVID-19 deaths by year 2020-2023" -f csv
uv run python -m wonder query "firearm deaths by state 2020-2022" -f csv
uv run python -m wonder query "drug overdose deaths by race and sex 2018-2023" -f csv

# Long-term trends (D157, 1999-2023)
uv run python -m wonder query "cancer death rates 1999 to 2023, group by year and sex, dataset D157" -f csv

# Historical (D77, 1979-1998)
uv run python -m wonder query "HIV/AIDS deaths by year 1982-1998, dataset D77" -f csv
```

## Supported Datasets

| Dataset  | Label                          | Years        |
| -------- | ------------------------------ | ------------ |
| **D176** | Provisional Mortality          | 2018–present |
| **D157** | Final Mortality                | 2018–2023    |
| **D77**  | Multiple Cause of Death        | 1999–2020    |
| **D8**   | VAERS (Vaccine Adverse Events) | 1990–present |

**Note on D8:** Due to a CDC server-side bug, VAERS queries cannot be executed via the XML API.
Use `wonder build` to generate the XML and submit it via the web interface.

## Verified Working Queries

For direct execution without LLM:

```bash
uv run python -m wonder run src/wonder/queries/opioid-overdose-deaths-2018-2024-req.xml -f csv
```

Verified queries in `src/wonder/queries/`:

| File                                              | What it queries                           |
| ------------------------------------------------- | ----------------------------------------- |
| `opioid-overdose-deaths-2018-2024-req.xml`        | Opioid deaths by year                     |
| `covid-deaths-by-race-2020-2023-req.xml`          | COVID deaths by Hispanic origin + year    |
| `heart-vs-cancer-by-sex-2018-2023-req.xml`        | Heart disease & cancer by sex + year      |
| `unintentional-injuries-by-age-2018-2023-req.xml` | External-cause deaths by age group + year |
| `racial-mortality-gap-2018-2023-req.xml`          | All-cause deaths by race + year           |
| `infant-mortality-2018-2023-req.xml`              | Infant deaths by year                     |

## Components

- `src/wonder/llm_query_builder.py` — Core implementation
- `src/wonder/templates/` — Base XML templates (D176, D157, D77, D8)
- `src/wonder/queries/` — Verified working XML files
- `src/wonder/README.md` — Query catalog
- `docs/LLM_QUERY_BUILDER.md` — Full documentation
