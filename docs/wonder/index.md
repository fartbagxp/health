# CDC WONDER

[CDC WONDER](https://wonder.cdc.gov/) is CDC's public query system for mortality, births, natality, environmental, and vaccine adverse event data. It has a web interface and an unauthenticated XML API.

This module wraps that API with an **LLM query builder** — describe what you want in plain English, and Claude picks the right dataset, generates the XML, and enforces WONDER's constraint rules.

## Setup

```bash
cp .env.sample .env
# add: ANTHROPIC_API_KEY='sk-ant-...'
uv sync
```

## The three commands

```bash
# LLM-powered: natural language → XML → result
uv run python -m wonder query "drug overdose deaths by state 2020-2023" -f csv

# Run a pre-built XML query file directly (no LLM needed)
uv run python -m wonder run src/wonder/queries/covid-deaths-by-race-2020-2023-req.xml -f csv

# Build XML without executing (inspect or save it)
uv run python -m wonder build "firearm deaths by state 2022" > my-query.xml
```

## Choosing the right dataset

WONDER splits data across datasets by year range and data type. The LLM picks automatically based on your prompt, but knowing the map helps when you need a specific time window.

### Mortality — which dataset for which years?

```
Need years...        Use dataset(s)
─────────────────────────────────────────────────────────────────────────
2018–present         D176  Provisional Mortality (updates weekly)
2018–2023            D157  Final Mortality, Single Race (confirmed)
1999–2020            D77   Multiple Cause of Death (ICD-10, bridged race)
1999–2020            D76   Underlying Cause of Death (like D77, UCD only)
1979–1998            D16   Compressed Mortality (ICD-9)
1968–1978            D74   Compressed Mortality (ICD-8)

For 1979–present you need three datasets: D16 + D77 + D176.
See → Multi-Year Queries for the merge pattern.
```

!!! tip "D176 vs D157"
D176 (Provisional) publishes within weeks of death; D157 (Final) is confirmed 2–3 years later. For exploratory work use D176. For publications use D157 when the years are available.

### Natality — births

| Dataset | Years        | Notes                          |
| ------- | ------------ | ------------------------------ |
| D192    | 2023–present | Provisional, updates monthly   |
| D66     | 2007–2024    | Default for recent births      |
| D149    | 2016–2024    | Expanded race/ethnicity detail |
| D27     | 2003–2006    |                                |
| D10     | 1995–2002    |                                |

### Infant mortality

| Dataset | Years                |
| ------- | -------------------- |
| D69     | 2007–2023            |
| D159    | 2017–2023 (expanded) |
| D31     | 2003–2006            |
| D18     | 1999–2002            |
| D23     | 1995–1998            |

### Environmental

| Dataset | What                                 | Years     |
| ------- | ------------------------------------ | --------- |
| D104    | Heat wave days                       | 1981–2010 |
| D60     | Air temperature & heat index (NLDAS) | 1979–2011 |
| D73     | PM2.5 fine particulate matter        | 2003–2011 |
| D80     | Daily sunlight                       | 1979–2011 |
| D81     | Daily precipitation                  | 1979–2011 |

## Writing prompts that work

Be specific: name the cause with its ICD chapter, the years, and how you want results grouped.

```bash
# Too vague — LLM has to guess what "opioid" means
uv run python -m wonder query "opioid deaths"

# Specific — everything the LLM needs
uv run python -m wonder query \
  "opioid overdose deaths 2018-2024 by year, age-adjusted rate per 100,000"

# Add the dataset explicitly when you need a specific year range
uv run python -m wonder query \
  "HIV deaths by year 1982-1998, dataset D77"
```

**Include in your prompt:**

- Cause of death + ICD chapter if you know it (`drug overdose`, `T40.0–T40.6`)
- Year range (`2018-2023`, `1999 to 2020`)
- How to group results (`by year`, `by state and year`, `by race and sex`)
- Metric wanted (`deaths`, `crude rate`, `age-adjusted rate`)
- Dataset if non-default (`dataset D157`, `dataset D77`)

## Common queries to try

```bash
# Current data (D176, 2018–present)
uv run python -m wonder query "COVID-19 deaths by year 2020-2023" -f csv
uv run python -m wonder query "firearm deaths by state 2020-2022" -f csv
uv run python -m wonder query "drug overdose deaths by race and sex 2018-2023" -f csv
uv run python -m wonder query "maternal mortality by race 2018-2023, age-adjusted rate"
uv run python -m wonder query "suicide deaths by sex 2018-2024, age-adjusted rate"

# Long-term trend (cross-dataset)
# See Multi-Year Queries for the pattern to collect 1979–2024

# Final data (D157, 1999–2023)
uv run python -m wonder query \
  "cancer death rates 1999 to 2023, group by year and sex, dataset D157" -f csv

# Historical (D77/D16)
uv run python -m wonder query "HIV/AIDS deaths by year 1982-1998, dataset D77" -f csv
```

## Key limitations

| Limit                  | Detail                                                                                                                                                                    |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Rate limit**         | ≥15 seconds between API requests. Scripts must `time.sleep(15)` in loops.                                                                                                 |
| **75,000 cell cap**    | WONDER rejects queries whose result would exceed 75,000 cells. Break large state × year × cause queries into smaller pieces.                                              |
| **Suppressed values**  | Counts below 10 appear as "Suppressed" — small populations and rare causes drop out.                                                                                      |
| **AAR + age grouping** | Age-adjusted rates can't be computed when grouping by age. The builder disables AAR automatically.                                                                        |
| **Mode selectors**     | `O_ucd`, `O_age`, `O_race` must match your active `F_*` filter, or the filter is silently ignored. The builder sets these — but if results look wrong, verify they match. |
| **VAERS (D8)**         | The XML API has a server-side bug for D8. Use `wonder build` to generate XML, submit manually via the VAERS web interface.                                                |
