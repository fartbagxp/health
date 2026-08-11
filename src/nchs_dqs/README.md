# nchs_dqs

Python SDK and CLI for the [NCHS Data Query System (DQS)](https://www.cdc.gov/nchs/dqs/) — CDC/NCHS's unified query layer over the "Health, United States" report family.

DQS draws from the national surveys (NHANES, NHIS, NHAMCS, NVSS, NPALS, NHCS) and publishes each topic as a Socrata dataset on [data.cdc.gov](https://data.cdc.gov) with a `DQS ...` title. Every dataset shares one tidy schema:

```
topic · subtopic · classification · group · subgroup
      · estimate_type · time_period · estimate · estimate_lci · estimate_uci
```

`classification = 'Total'` is the all-persons row; other classifications are demographic, geographic, or socioeconomic cuts. Because the schema is uniform, one `query` verb covers all 28 datasets. `group` is a SoQL reserved word — backtick-quote it in a `$select`.

28 datasets are registered (see `datasets.py`), spanning mortality, natality, chronic disease and risk factors (NHANES), nutrition, oral health, disability, self-reported health (NHIS), substance use, the health-care system (beds, ED visits, utilization), workforce, spending, and long-term care. Not all are wired into a chart yet — `list --uncharted` shows the backlog.

## Setup

```bash
# Optional: raise Socrata rate limits (1,000 → 20,000 req/hr)
export CDC_DATA_APP_TOKEN=your_app_token_here
```

A `.env` file in the project root is loaded automatically.

## CLI

### List datasets

```bash
uv run python -m nchs_dqs list
uv run python -m nchs_dqs list -f json
uv run python -m nchs_dqs list --charted      # only datasets health-charts renders
uv run python -m nchs_dqs list --uncharted    # collected-ready but not yet charted (the backlog)
```

```
KEY                          DATASET ID   YEARS        SURVEY     CHARTED  NAME
--------------------------------------------------------------------------------------------------------------
drug-overdose-deaths         rdjz-vn2n    2018–2024    NVSS       yes      Drug overdose death rates, by drug type...
low-birthweight              ga7k-kycn    2014–2023    NVSS       yes      Low birthweight live births, by state
national-health-spending     s57w-7gbe    1960–2024    CMS/NHEA   yes      National health spending
...
```

### Raw SODA query

```bash
uv run python -m nchs_dqs query low-birthweight --where "classification='Geographic Characteristic'" -f csv
uv run python -m nchs_dqs query rdjz-vn2n --where "classification='Total'" --limit 500 -f json
```

Accepts a registry key (`low-birthweight`) or a Socrata ID (`ga7k-kycn`), plus `--where`, `--select`, `--group`, `--order`, `--limit`.

### National trend

```bash
uv run python -m nchs_dqs trend national-health-spending -f csv
uv run python -m nchs_dqs trend cholesterol-adults -e "mg/dL, age adjusted" -f csv
```

`trend` filters to the all-persons `Total` series and sorts oldest→newest. `-e/--estimate-type` narrows to one measure when a dataset publishes several (e.g. crude vs. age-adjusted).

## Archiving into health-charts

`fetch_dqs.py` writes the charted slices to `data/raw/dqs/`, run weekly by `.github/workflows/update_dqs.yml`:

| CSV | Dataset | Shape |
| --- | --- | --- |
| `national_health_spending.csv` | `s57w-7gbe` | Annual line, 1960–present (per-capita, billions, % GDP) |
| `drug_overdose_by_type.csv` | `rdjz-vn2n` | Age-adjusted rate per 100k, by opioid type, 2018–present |
| `low_birthweight_by_state.csv` | `ga7k-kycn` | One row per state, latest year (choropleth) |

```bash
uv run python -m nchs_dqs.fetch_dqs
```

The `charted` flag in `datasets.py` marks these three; the other 25 are the backlog of series we could add next.
