# CDC WONDER

[CDC WONDER](https://wonder.cdc.gov/) is CDC's public data query system covering mortality, births, vaccine adverse events, cancer, and more. It has a web interface and an XML API.

This repo's primary interface is an LLM query builder: describe what you want in plain English, and Claude picks the right dataset, generates the XML, and enforces constraint rules automatically.

- [CLI reference](../src/wonder/README.md)
- [Architecture & troubleshooting](wonder_llm_query_builder.md)
- [Worked examples](wonder_examples.md)
- [Official API docs](https://wonder.cdc.gov/wonder/help/wonder-api.html)

## Setup

```bash
cp .env.sample .env
# Add: ANTHROPIC_API_KEY='your-anthropic-api-key'
```

## Supported Datasets

| Dataset | Label                         | Years        | Notes                       |
| ------- | ----------------------------- | ------------ | --------------------------- |
| D176    | Provisional Mortality         | 2018–present | Most recent; updates weekly |
| D157    | Final Mortality (Single Race) | 2018–2023    | Confirmed statistics        |
| D77     | Multiple Cause of Death       | 1999–2020    | Historical; bridged race    |
| D8      | VAERS                         | 1990–present | See D8 note below           |

For topics outside these four, the builder attempts a query without template merging — manual review may be needed. Full dataset catalog: `data/raw/wonder/topics_mapping.json`.

## Writing Effective Prompts

Be specific. Name the cause of death (with its ICD chapter if you know it), the years, and how you want results grouped.

```bash
# Too vague
uv run python -m wonder query "opioid deaths"

# Better
uv run python -m wonder query "opioid overdose deaths 2018-2024 by year, age-adjusted rate"
```

A few starting points:

```bash
# Recent data (D176, 2018–present)
uv run python -m wonder query "COVID-19 deaths by year 2020-2023" -f csv
uv run python -m wonder query "firearm deaths by state 2020-2022" -f csv
uv run python -m wonder query "drug overdose deaths by race and sex 2018-2023" -f csv

# Long-term trends (D157, 1999–2023)
uv run python -m wonder query "cancer death rates 1999 to 2023, group by year and sex, dataset D157" -f csv

# Historical (D77, 1979–1998)
uv run python -m wonder query "HIV/AIDS deaths by year 1982-1998, dataset D77" -f csv
```

See [wonder_examples.md](wonder_examples.md) for 33 worked examples with real results.

## Gotchas

### Rate limit

At least 15 seconds between API requests.

### Mode selectors

Several `O_*` parameters tell WONDER which filter sub-section is active. If they don't match your `F_*` filter, the filter is silently ignored and you get all-cause data back with no error. The builder sets these automatically, but if results look wrong, verify that `O_ucd`, `O_age`, `O_race` match your query intent. See [wonder_llm_query_builder.md](wonder_llm_query_builder.md#mode-selectors) for the full table.

### D8 VAERS Bug

The XML API endpoint for VAERS always returns a server error. Use `wonder build` to generate the XML, then submit it manually via the [VAERS web interface](https://wonder.cdc.gov/vaers.html). Also: VAERS counts are reports, not confirmed adverse events.

### AAR and Age Grouping

Age-adjusted rates can't be computed when grouping by age. The builder disables AAR automatically when any `B_*` slot contains an age variable.

### Suppressed Values

CDC suppresses counts below 10 for privacy. These appear as "Suppressed" in results.

## Parameter Reference

A WONDER request is a flat collection of parameters in several families. With template merging, the base template handles all boilerplate; the LLM only produces `B_*`, `F_*`, and key `O_*` overrides.

### B — Group by (up to 5 dimensions)

```bash
B_1 = D176.V1-level1   # Group by Year
B_2 = *None*           # Unused slot
```

Common grouping variables (D176):

| Value            | Meaning             |
| ---------------- | ------------------- |
| `D176.V1-level1` | Year                |
| `D176.V9-level1` | Residence State     |
| `D176.V9-level2` | Residence County    |
| `D176.V5`        | Ten-year age groups |
| `D176.V7`        | Gender              |
| `D176.V42`       | Race                |

### M — Measures

```bash
M_1 = D176.M1   # Deaths
M_2 = D176.M2   # Population
M_3 = D176.M3   # Crude rate
M_9 = D176.M9   # Age-adjusted rate
```

### F — Filter Values

```bash
F_D176.V1  = ["2020", "2021"]    # Specific years
F_D176.V13 = ["T40.1", "T40.4"] # ICD-10 codes (multiple cause)
F_D176.V2  = "*All*"             # All ICD chapters (underlying cause)
F_D176.V9  = "*All*"             # All states
```

`F_D176.V25` (Drug/Alcohol Induced Causes) takes cause-group codes like `D1` (all drug-induced) or `A1` (all alcohol-induced) — not ICD-10 codes.

### V — Variable Selectors

```bash
V_D176.V5  = *All*   # All age groups
V_D176.V7  = *All*   # All genders
V_D176.V42 = *All*   # All races
```

### O — Output options

```bash
O_rate_per    = 100000   # Per 100k
O_aar         = aar_std  # Use standard AAR
O_aar_pop     = 0000     # 2000 US standard population
O_show_totals = true
O_precision   = 1
```

Mode selectors — must match your active `F_*` filter:

| Parameter | Controls                                | Example                                                 |
| --------- | --------------------------------------- | ------------------------------------------------------- |
| `O_ucd`   | Which underlying-cause filter is active | `D176.V2` for ICD chapters, `D176.V25` for drug/alcohol |
| `O_age`   | Which age grouping is active            | `D176.V5` ten-year, `D176.V51` five-year                |
| `O_race`  | Which race variable is active           | `D176.V42` Single Race 6, `D176.V43` Single Race 15     |

### Common ICD-10 Codes

| Codes              | Cause                                       |
| ------------------ | ------------------------------------------- |
| T40.0–T40.4, T40.6 | Opioids (heroin, fentanyl, methadone, etc.) |
| C00–C97            | Malignant neoplasms (cancer)                |
| I00–I99            | Circulatory disease (heart disease, stroke) |
| J00–J99            | Respiratory disease                         |
| X60–X84            | Intentional self-harm (suicide)             |
| V01–Y89            | External causes (injuries, accidents)       |
| U00–U99            | COVID-19 and other special purposes         |

## Response Format

The API returns XML:

```xml
<data-table>
    <r>
        <c l="2018"/>                               <!-- label (row header) -->
        <c v="46,802"/>                             <!-- deaths -->
        <c v="327,167,434"/>                        <!-- population -->
        <c v="14.3"/>                               <!-- crude rate -->
        <c v="14.6" a="c"><l v="(14.4-14.7)"/></c> <!-- AAR + CI -->
    </r>
</data-table>
```

Cell attributes: `l` label, `v` value, `dt` totals-row value, `a="c"` confidence interval.

Parsing:

```python
from wonder.client import WonderClient

client = WonderClient()
response = client.query_from_xml(dataset_id, xml)
table = client.parse_response_to_arrays(response)  # [[label, val, ...], ...]
```

## Advanced: Direct Python API

The `QueryBuilder` class lets you build queries without the LLM. Useful when you know exactly what parameters you want.

```python
from src.wonder.client import WonderClient, QueryBuilder

params = (
    QueryBuilder(dataset_id="D176")
    .group_by("D176.V1-level1")
    .measures(["D176.M1", "D176.M2", "D176.M3"])
    .filter("F_D176.V1", ["2020", "2021"])
    .option("O_rate_per", "100000")
    .build()
)

client = WonderClient()
response = client.query("D176", params)
table = client.parse_response_to_arrays(response)
```

Valid parameter values for each dataset are in `data/raw/wonder/query_params_D*.json`.
