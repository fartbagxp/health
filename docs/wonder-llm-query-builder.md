# Wonder Query Builder

The query builder calls Claude to turn plain English into a CDC WONDER API request. It picks the right dataset, maps your intent to grouping variables and filters, merges overrides onto a validated base template, and enforces WONDER constraint rules before sending.

See [wonder.md](wonder.md) for setup and usage. This document covers architecture, parameter details, and troubleshooting.

## Architecture

### Components

**`WonderRequest`** (`src/wonder/llm_query_builder.py`) — Pydantic model representing a WONDER query. Serializes to the XML format CDC WONDER expects.

**`LLMQueryBuilder`** (`src/wonder/llm_query_builder.py`) — Converts natural language to a `WonderRequest` via LLM tool calling. Loads `topics_mapping.json` to pick a dataset, loads the matching `query_params_D*.json`, merges LLM overrides onto the base template, and enforces post-merge constraints.

**Base templates** (`src/wonder/templates/`) — Neutral XML for each supported dataset. All boilerplate intact; query-specific values set to `*All*` / `*None*`. Covers D176, D157, D77, D8.

**`build_wonder_query` tool** — The LLM tool schema. Produces only overrides (`B_*`, `F_*`, mode selectors); the code merges them onto the template.

### How It Works

```bash
User Query (Natural Language)
    ↓
LLM Analyzes Intent
    ↓
Identifies Dataset (from topics_mapping.json)
    ↓
Loads Query Parameters (from query_params_D*.json)
    ↓
LLM Maps Intent → Override Parameters (B_*, F_*, O_* mode selectors)
    ↓
Calls build_wonder_query Tool
    ↓
Constraint rules applied (e.g. AAR disabled when grouping by age)
    ↓
Overrides merged onto base template (all boilerplate preserved)
    ↓
Returns complete WonderRequest (ready to execute)
    ↓
Execute via WonderClient
```

## Supported Datasets

| Dataset  | Label                         | Years        | Notes                                                                  |
| -------- | ----------------------------- | ------------ | ---------------------------------------------------------------------- |
| **D176** | Provisional Mortality         | 2018–present | Most recent data; updates weekly                                       |
| **D157** | Final Mortality (Single Race) | 2018–2023    | Confirmed statistics; race via Single Race                             |
| **D77**  | Multiple Cause of Death       | 1999–2020    | Broader year range; race via bridged race                              |
| **D8**   | VAERS                         | 1990–present | Counts reports, not rates; see [D8 Limitations](#d8-vaers-limitations) |

For topics not in these four datasets, the builder falls back to generating parameters without template merging (may require manual review).

## Parameter Families

A working CDC WONDER request requires parameters from all of the following families.
With template merging, the base template handles all boilerplate automatically.
The LLM only needs to produce `B_*`, `F_*`, and key `O_*` overrides.

| Family           | Purpose                                    | Example                          | Handled by                        |
| ---------------- | ------------------------------------------ | -------------------------------- | --------------------------------- |
| `B_*`            | Group By (up to 5 dimensions)              | `B_1 = D176.V1-level1`           | LLM                               |
| `M_*`            | Measures to include                        | `M_1 = D176.M1` (deaths)         | Template                          |
| `F_*`            | Filter values                              | `F_D176.V1 = ["2020","2021"]`    | LLM                               |
| `O_*`            | Output options and mode selectors          | `O_rate_per = 100000`            | LLM (selectors) + Template (rest) |
| `V_*`            | Per-variable display/value selectors       | `V_D176.V5 = *All*`              | Template                          |
| `I_*`            | Label display params per filter variable   | `I_D176.V1 = ""`                 | Template                          |
| `finder-stage-*` | Finder staging mode per variable           | `finder-stage-D176.V1 = codeset` | Template                          |
| `L_*`            | List selectors (MCD cause lists)           | `L_D176.V15 = *All*`             | Template                          |
| `VM_*`           | Population denominators for adjusted rates | `VM_D176.M6_D176.V42 = *All*`    | Template                          |
| `dataset_code`   | Dataset identifier                         | `dataset_code = D176`            | Template                          |
| `action-Send`    | Request action                             | `action-Send = Send`             | Template                          |
| `stage`          | Request stage                              | `stage = request`                | Template                          |

### Mode Selectors

Several `O_*` parameters are **mode selectors** that tell CDC WONDER which filter sub-section
is active. Getting these wrong causes your `F_*` filter to be silently ignored and you get
back all-cause / all-group data instead of an error.

The LLM is instructed to set these correctly; the table below is a reference.

#### D176 / D157

| Parameter    | Controls                                | Valid values                                                                                               |
| ------------ | --------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `O_ucd`      | Which underlying-cause filter is active | `{DS}.V2` (ICD codes), `{DS}.V4` (113 cause list), `{DS}.V25` (drug/alcohol), `{DS}.V12` (infant causes)   |
| `O_mcd`      | Which multiple-cause filter is active   | `{DS}.V13` (ICD codes), `{DS}.V15` (113 cause list), `{DS}.V26` (drug/alcohol), `{DS}.V16` (infant causes) |
| `O_age`      | Which age grouping is active            | `{DS}.V5` (ten-year), `{DS}.V51` (five-year), `{DS}.V52` (single-year), `{DS}.V6` (infant)                 |
| `O_race`     | Which race variable is active           | `{DS}.V42` (Single Race 6), `{DS}.V43` (Single Race 15), `{DS}.V44` (Single/Multi Race 31)                 |
| `O_location` | Which residence geography is active     | `{DS}.V9` (state), `{DS}.V10` (census region), `{DS}.V27` (HHS region)                                     |

where `{DS}` is `D176` or `D157`.

**D77 differences:** D77 has no `O_race` selector (use `V_D77.V8` for race group-by directly).

**Example:** If you filter by ICD chapter (`F_D176.V2 = I00-I99`), you must also set
`O_ucd = D176.V2`. If `O_ucd` points at a different sub-section, the ICD filter is silently
ignored and all causes are returned.

### AAR Constraints

AAR can't be used when any `B_*` slot contains an age variable (`D176.V5`, `D176.V51`, `D176.V52`, `D176.V6`). The builder enforces this automatically — sets `O_aar_enable = false` / `O_aar = aar_none` regardless of what the LLM requests. The `VM_*` population parameters required for AAR are handled by the template.

### `F_D176.V25` Values

`F_D176.V25` is the **Drug/Alcohol Induced Causes** filter. Its values are cause-group codes
like `D1`, `D2`, `D3`, `D4` — **not** ICD-10 codes. Using ICD codes (e.g., `T40.0`) here is
invalid and will produce a 500 error or silently incorrect results.

```bash
D1  = All drug-induced causes
D2  = Drug-induced: Dependent use
D3  = Drug-induced: Non-dependent use
D4  = Drug-induced: Undetermined
A1  = All alcohol-induced causes
```

To filter by specific ICD-10 codes (e.g., opioid codes T40.0–T40.6), use the MCD filter
`F_D176.V13` with the ICD codes directly, and set `O_mcd = D176.V13`.

## D8 VAERS Limitations

The VAERS dataset (D8) has a known CDC server-side bug: the XML API endpoint always returns
an error message referencing "VAERS IDs" when queried programmatically. This means `wonder query`
and `wonder run` commands for D8 queries will fail with a server error, even though the query
XML itself is correctly structured.

**Workaround:** Use `wonder build` to generate the XML, then submit it manually through the
[VAERS web interface](https://wonder.cdc.gov/vaers.html).

**VAERS reporting caveat:** VAERS counts adverse event _reports_, not confirmed causal
associations. Reports are submitted voluntarily and are not adjusted for population denominators.
Do not interpret VAERS counts as incidence or causation rates.

## Special Values

- `*All*` — include all values for this parameter
- `*None*` — empty slot (for unused group-by positions B_2 through B_5)

## Data Sources

- `data/raw/wonder/topics_mapping.json` — 169 datasets mapped to health topics, used for dataset selection
- `data/raw/wonder/query_params_D*.json` — parameter definitions for each dataset (selects, inputs, option lists)
- `src/wonder/templates/` — base XML templates (D176, D157, D77, D8)

## Limitations

1. Parameters aren't validated against `query_params_D*.json` before merging; the API call is the final check.
2. VAERS queries (D8) can't be executed via the XML API — see [D8 VAERS limitations](#d8-vaers-limitations).
3. Each `build` or `query` call makes 1–2 LLM API calls.
4. CDC WONDER requires ≥15 seconds between API requests.
5. Datasets outside D176, D157, D77, and D8 fall back to unmerged LLM output, which may need manual review.

## Troubleshooting

**HTTP 500 from CDC WONDER**

- Compare the generated XML against a verified query in `src/wonder/queries/`.
- Check that `O_ucd`, `O_age`, `O_race` match your active filters.
- Check that AAR is disabled if grouping by age (the builder does this automatically for D176/D157/D77).
- For D8, see [D8 VAERS Limitations](#d8-vaers-limitations).

**Wrong data returned (no error, but totals don't match expectations)**

- Likely a mode selector mismatch. E.g., `F_D176.V2` filter set but `O_ucd` pointing at
  a different sub-section. Verify all `O_*` mode selectors match your `F_*` filters.

**HTTP 429 from CDC WONDER**

- Rate limit hit. CDC WONDER requires at least 15 seconds between API requests.

**LLM did not call `build_wonder_query` tool**

- Query may be too ambiguous or the LLM got stuck on dataset selection.
- Try a more specific prompt naming the cause of death, years, and grouping dimensions explicitly.

**Error: No query parameters found for dataset**

- The dataset hasn't been scraped. Check `data/raw/wonder/query_params_D*.json`.

## Related Files

- `src/wonder/llm_query_builder.py` — Main implementation
- `src/wonder/templates/` — Base XML templates
- `src/wonder/client.py` — WonderClient for execution
- `src/wonder/queries/` — Verified working query XML files
- `src/wonder/README.md` — Module layout and CLI reference
- `docs/wonder.md` — User guide (setup, datasets, prompt tips, parameter reference)
- `docs/wonder-examples.md` — 33 worked examples with real results
- `data/raw/wonder/topics_mapping.json` — Dataset mappings
- `data/raw/wonder/query_params_D*.json` — Parameter definitions (169 files)
