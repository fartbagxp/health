# CDC WONDER API Guide

## Overview

CDC WONDER (Wide-ranging ONline Data for Epidemiologic Research) is a comprehensive public health database provided by the CDC. It includes an unauthenticated Application Programmatic Interface (API) for accessing birth (natality), death (mortality), cancer, infectious disease, vaccination, environmental health, and population statistics.

- [**Official Documentation**](https://wonder.cdc.gov/wonder/help/wonder-api.html)

## Quick Start

```python
from src.wonder.client import WonderClient, QueryBuilder

# Method 1: Execute a pre-built query from file
client = WonderClient()
response = client.execute_query_file("src/wonder/queries/your-query.xml")
table = client.parse_response_to_arrays(response)

# Method 2: Build a custom query
params = (
    QueryBuilder(dataset_id="D176")
    .group_by("D176.V1-level1")  # Group by Year
    .measures(["D176.M1", "D176.M2"])  # Deaths, Population
    .filter("F_D176.V1", ["2020", "2021"])  # Years 2020-2021
    .option("O_rate_per", "100000")
    .build()
)
response = client.query("D176", params)
table = client.parse_response_to_arrays(response)
```

## API Characteristics

1. **Non-standard XML-based protocol**: Uses custom XML format over HTTPS
2. **Unauthenticated access**: No API keys or authentication required
3. **Data use agreement**: Requires sending `accept_datause_restrictions: true` parameter
4. **Rate limiting**: Soft limit of one query every two minutes
5. **Dataset-specific endpoints**: Each dataset (D1-D250+) has its own endpoint and parameters

## Request Parameters

CDC WONDER uses a complex parameter system organized into several categories:

### Parameter Categories

#### B Parameters - Group By Controls

Define how results are grouped and organized.

- `B_1` through `B_5`: Up to 5 grouping dimensions
- Values reference dataset variables (e.g., `D176.V1-level1` for Year)
- Use `*None*` when a grouping slot is not needed

**Example:**

```python
params = {
    "B_1": "D176.V1-level1",  # Group by Year
    "B_2": "*None*",           # No secondary grouping
}
```

**Common grouping variables:**

- `D176.V1-level1`: Year
- `D176.V2-level1`: Month
- `D176.V9-level1`: Residence State
- `D176.V9-level2`: Residence County
- `D176.V5`: Age Groups
- `D176.V7`: Gender

#### M Parameters - Measure Controls

Specify which statistics to include in results.

**Common measures (vary by dataset):**

- `D176.M1`: Deaths (count)
- `D176.M2`: Population
- `D176.M3`: Crude Rate
- `D176.M9`: Age-Adjusted Rate

**Example:**

```python
params = {
    "M_1": "D176.M1",  # Deaths
    "M_2": "D176.M2",  # Population
    "M_3": "D176.M3",  # Crude Rate
}
```

#### F Parameters - Filter Values

Define which values to include for filterable dimensions.

**Common filter parameters:**

- `F_D176.V1`: Year filter
- `F_D176.V2`: Month filter
- `F_D176.V9`: State filter
- `F_D176.V13`: ICD-10 Cause of Death codes
- `F_D176.V25`: Underlying Cause of Death
- `F_D176.V5`: Age groups

**Example:**

```python
params = {
    "F_D176.V1": ["2020", "2021", "2022"],  # Specific years
    "F_D176.V9": "*All*",                    # All states
    "F_D176.V13": ["T40.1", "T40.4"],       # Specific ICD codes
}
```

#### V Parameters - Variable Values

Additional value specifications for variables.

**Example:**

```python
params = {
    "V_D176.V5": "*All*",  # All age groups
    "V_D176.V7": "*All*",  # All genders
    "V_D176.V42": "*All*", # All races
}
```

#### O Parameters - Output Options

Control output format, calculations, and display settings.

**Important O parameters:**

- `O_rate_per`: Rate calculation base (e.g., `"100000"` for per 100K)
- `O_show_totals`: Show totals row (`"true"` or `"false"`)
- `O_precision`: Decimal precision (e.g., `"1"`)
- `O_aar`: Age-adjusted rate type (`"aar_std"`, `"aar_none"`)
- `O_aar_pop`: Standard population for age adjustment (e.g., `"0000"` for 2000 US standard)
- `O_javascript`: Compatibility setting (set to `"on"`)
- `O_timeout`: Query timeout in seconds (e.g., `"300"`)
- `O_location`: Location variable reference (e.g., `"D176.V9"`)
- `O_dates`: Date grouping (`"YEAR"`, `"MONTH"`, `"QUARTER"`)
- `O_V#_fmode`: Filter mode (`"freg"` = regular, `"fadv"` = advanced)

**Example:**

```python
params = {
    "O_rate_per": "100000",
    "O_show_totals": "true",
    "O_precision": "1",
    "O_aar": "aar_std",
    "O_javascript": "on",
}
```

#### Misc Parameters

Required boilerplate parameters:

```python
params = {
    "dataset_code": "D176",
    "action-Send": "Send",
    "stage": "request",
}
```

### Complete Parameter Example

```python
params = {
    # Group By
    "B_1": "D176.V1-level1",  # Year
    "B_2": "*None*",
    "B_3": "*None*",
    "B_4": "*None*",
    "B_5": "*None*",

    # Measures
    "M_1": "D176.M1",  # Deaths
    "M_2": "D176.M2",  # Population
    "M_3": "D176.M3",  # Crude Rate

    # Filters
    "F_D176.V1": ["2020", "2021", "2022"],
    "F_D176.V9": "*All*",
    "F_D176.V2": "*All*",

    # Options
    "O_rate_per": "100000",
    "O_show_totals": "true",
    "O_precision": "1",
    "O_javascript": "on",
    "O_V1_fmode": "freg",
    "O_V9_fmode": "freg",

    # Required
    "dataset_code": "D176",
    "action-Send": "Send",
    "stage": "request",
}
```

## Response Format

The API returns XML with a data table structure:

```xml
<data-table show-all-labels="false">
    <r>
        <c l="2018"/>
        <c v="46,802"/>
        <c v="327,167,434"/>
        <c v="14.3"/>
        <c v="14.6" a="c"><l v="(14.4 - 14.7)"/></c>
        <c v="10.2%"/>
    </r>
    <r>
        <c c="1"/>
        <c dt="460,929"/>
        <c dt="2,319,902,172"/>
        <c dt="19.9"/>
        <c dt="20.2" a="c"><l v="(20.2 - 20.3)"/></c>
        <c dt="100.0%"/>
    </r>
</data-table>
```

### Response Cell Attributes

Each `<c>` (cell) element can have:

- **`l`**: Label (text value, used for row headers like "2018")
- **`v`**: Value (data value like "46,802")
- **`c`**: Column indicator (e.g., `c="1"` for totals column)
- **`dt`**: Data total (appears in totals row)
- **`a`**: Attribute type (e.g., `a="c"` indicates confidence interval)
- **Nested `<l>`**: Sub-label (e.g., confidence intervals like "(14.4 - 14.7)")

### Parsing Response Data

The WonderClient provides three methods to parse responses:

#### 1. Parse to Arrays (Simplest)

```python
table = client.parse_response_to_arrays(response)
# Returns: [
#   ['2018', 46802.0, 327167434.0, 14.3, 14.6, '10.2%'],
#   ['2019', 49860.0, 328239523.0, 15.2, 15.5, '10.8%'],
#   ...
# ]
```

#### 2. Parse to ResponseRow Objects (Most Detailed)

```python
rows = client.parse_response_table(response)
for row in rows:
    for cell in row.cells:
        print(f"Label: {cell.label}, Value: {cell.value}")
        print(f"Numeric: {cell.get_numeric_value()}")
        print(f"Sub-label: {cell.sub_label}")
```

#### 3. Parse to Dictionaries (Structured)

```python
rows = client.parse_response_to_dicts(response)
# Returns list of dicts with cell details
```

## Understanding Query Parameters

### Finding Available Parameters

Each dataset has unique parameters. Parameter definitions are stored in:

```markdown
data/raw/wonder/query_params_D###.json
```

Example structure:

```json
{
  "dataset_id": "D176",
  "page_title": "Provisional Mortality Statistics, 2018 through Last Week Request Form",
  "summary": {
    "total_selects": 47,
    "total_inputs": 201,
    "total_textareas": 29
  },
  "parameters": {
    "selects": [
      {
        "name": "B_1",
        "label": "Group Results By",
        "options": [
          { "value": "D176.V1-level1", "text": "Year" },
          { "value": "D176.V9-level1", "text": "Residence State" }
        ]
      }
    ]
  }
}
```

### Common Variable Codes by Dataset Type

#### Mortality Datasets (D76, D176, D77)

- **V1**: Year/Date
- **V2**: Month
- **V5**: Age Groups (e.g., "15-24", "25-34")
- **V7**: Gender ("M", "F")
- **V9/V10**: Location (State, County, Census Region)
- **V13**: ICD-10 Cause of Death codes
- **V17**: Hispanic Origin
- **V25**: Underlying Cause of Death (UCD)
- **V42**: Race
- **V79/V80**: Death Occurrence Location

#### ICD-10 Codes (for mortality queries)

Common cause of death codes:

- **T40.0**: Opium
- **T40.1**: Heroin
- **T40.2**: Other opioids
- **T40.3**: Methadone
- **T40.4**: Other synthetic narcotics (e.g., fentanyl)
- **T40.6**: Other and unspecified narcotics
- **C00-C97**: Malignant neoplasms (cancer)
- **I00-I99**: Circulatory diseases
- **J00-J99**: Respiratory diseases

#### Natality (Birth) Datasets (D66, D149)

- **V1**: Year
- **V2**: Month
- **V3**: Weekday
- **V4**: Birth Weight
- **V7**: Gender of Infant
- **V8**: Plurality (single, twin, triplet, etc.)
- **V9**: Location
- **V21**: Maternal Age
- **V27**: Maternal Race

## Using QueryBuilder

The `QueryBuilder` class simplifies parameter construction:

```python
from src.wonder.client import QueryBuilder, WonderClient

# Build query
params = (
    QueryBuilder(dataset_id="D176")
    .group_by("D176.V1-level1", slot=1)      # Primary grouping
    .group_by("D176.V9-level1", slot=2)      # Secondary grouping
    .measures(["D176.M1", "D176.M2", "D176.M3"])
    .filter("F_D176.V1", ["2020", "2021"])
    .filter("F_D176.V9", "*All*")
    .option("O_rate_per", "100000")
    .option("O_show_totals", "true")
    .build()
)

# Execute
client = WonderClient()
response = client.query("D176", params)
table = client.parse_response_to_arrays(response)
```

## Working with Pre-built Queries

The repository includes pre-built queries in `src/wonder/queries/`:

```python
# List available queries
import os
queries = os.listdir("src/wonder/queries")
print(queries)

# Execute a query
client = WonderClient()
response = client.execute_query_file(
    "src/wonder/queries/All Opioid Overdose Deaths of U.S. Residents by Year in Years 2018-2024-req.xml"
)
```

## Dataset Catalog

Available datasets are cataloged in `data/raw/wonder/topics_mapping.json`, organized by topic:

- **Mortality**: General death statistics (D76, D77, D176, etc.)
- **Birth & Natality**: Birth statistics (D66, D149, etc.)
- **Cancer**: Cancer incidence and mortality (D52, D53, etc.)
- **Infectious Diseases**: AIDS, TB, STD surveillance
- **Vaccinations**: VAERS adverse event data
- **Environmental Health**: Climate and environmental data
- **Population Estimates**: Demographics and projections

## Best Practices

### 1. Rate Limiting

Wait at least 2 minutes between queries to avoid overloading CDC servers.

### 2. Error Handling

```python
try:
    response = client.query("D176", params)
    table = client.parse_response_to_arrays(response)
except RuntimeError as e:
    print(f"Query failed: {e}")
except ValueError as e:
    print(f"Parse error: {e}")
```

### 3. Handling Suppressed Values

CDC suppresses small counts (< 10) for privacy:

```python
for row in table:
    if "Suppressed" in str(row):
        # Handle suppressed data
        pass
```

### 4. Age-Adjusted Rates

Use age-adjusted rates when comparing populations with different age distributions:

```python
params = (
    QueryBuilder(dataset_id="D176")
    .option("O_aar", "aar_std")
    .option("O_aar_pop", "0000")  # 2000 US standard population
    .option("O_aar_enable", "true")
    .build()
)
```

### 5. Checking Dataset Vintage

Always check the dataset vintage to understand data recency:

```python
metadata = client.get_dataset_metadata(response)
print(f"Data vintage: {metadata.get('vintage')}")
```

## Common Issues & Solutions

### Issue: Query Too Complex

**Error**: "Query result exceeds maximum allowed size"

**Solution**: Add more filters or reduce grouping dimensions

```python
# Instead of grouping by county
.group_by("D176.V9-level2")  # County - may be too large

# Group by state
.group_by("D176.V9-level1")  # State - smaller result set
```

### Issue: Invalid Parameter Value

**Error**: "Invalid parameter value for F_D176.V1"

**Solution**: Check valid values in `query_params_D176.json`

```python
# Load parameter definitions
import json
with open('data/raw/wonder/query_params_D176.json') as f:
    param_defs = json.load(f)

# Find valid options for a parameter
for select in param_defs['parameters']['selects']:
    if select['name'] == 'B_1':
        print("Valid options:", [opt['value'] for opt in select['options']])
```

### Issue: No Data Returned

**Possible causes**:

1. Filters are too restrictive (no matching records)
2. Date range is outside dataset coverage
3. Invalid ICD codes or other filter values

**Solution**: Start with broad filters, then narrow down

```python
# Start broad
.filter("F_D176.V9", "*All*")  # All states
.filter("F_D176.V1", "*All*")  # All years

# Then narrow
.filter("F_D176.V9", ["06"])   # Just California
.filter("F_D176.V1", ["2020"]) # Just 2020
```

## Example Queries

### Example 1: Opioid Deaths by Year

```python
params = (
    QueryBuilder(dataset_id="D176")
    .group_by("D176.V1-level1")  # By Year
    .measures(["D176.M1", "D176.M2", "D176.M3"])
    .filter("F_D176.V1", ["2018", "2019", "2020", "2021", "2022", "2023", "2024"])
    .filter("F_D176.V13", ["T40.6"])  # Opioid ICD code
    .filter("F_D176.V9", "*All*")
    .option("O_rate_per", "100000")
    .build()
)
```

### Example 2: Cancer Deaths by State, 2020

```python
params = (
    QueryBuilder(dataset_id="D76")
    .group_by("D76.V9-level1")  # By State
    .measures(["D76.M1", "D76.M2", "D76.M3"])
    .filter("F_D76.V1", ["2020"])
    .filter("F_D76.V2", ["C00-C97"])  # All cancers
    .option("O_rate_per", "100000")
    .build()
)
```

### Example 3: Birth Statistics by Month, 2022

```python
params = (
    QueryBuilder(dataset_id="D149")
    .group_by("D149.V2-level1")  # By Month
    .measures(["D149.M1"])  # Birth count
    .filter("F_D149.V1", ["2022"])
    .filter("F_D149.V9", "*All*")
    .build()
)
```

## Additional Resources

- [**Official API Docs**](https://wonder.cdc.gov/wonder/help/wonder-api.html)
- [**API Examples**](https://wonder.cdc.gov/wonder/help/api-examples/)
- [**ICD-10 Codes**](https://www.cdc.gov/nchs/icd/icd-10-cm.htm)
- [**Community Resource**](https://github.com/alipphardt/cdc-wonder-api)

## Support

For issues with this client:

1. Check parameter definitions in `data/raw/wonder/query_params_D###.json`
2. Review example queries in `src/wonder/queries/`
3. Verify dataset ID and vintage in `data/raw/wonder/topics_mapping.json`
4. Test with CDC WONDER web interface first to understand expected behavior
