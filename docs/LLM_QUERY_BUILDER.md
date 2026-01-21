# LLM-Powered CDC WONDER Query Builder

Convert natural language queries into structured CDC WONDER API requests using an LLM with tool calling.

## Overview

The LLM Query Builder uses Claude (via Anthropic API) to intelligently convert your plain English questions into properly formatted CDC WONDER queries. It automatically:

- Selects the appropriate dataset based on your health topic
- Identifies the correct query parameters
- Builds valid XML requests
- Handles complex multi-dimensional queries

## Quick Start

### Configuration

Set your Anthropic API key in `.env` file (recommended):

```bash
# Copy the sample file
cp .env.sample .env

# Edit .env and add your API key
# ANTHROPIC_API_KEY='your-anthropic-api-key'
```

The `.env` file is automatically loaded when you import the module. Alternatively, you can export the API key as an environment variable:

```bash
export ANTHROPIC_API_KEY='your-anthropic-api-key'
```

## Architecture

### Core Components

1. **WonderRequest Model** (`src/wonder/llm_query_builder.py`)

   - Pydantic model representing a structured WONDER query
   - Matches the XML schema expected by CDC WONDER API
   - Contains dataset ID and list of parameters

2. **LLMQueryBuilder Class** (`src/wonder/llm_query_builder.py`)

   - Main query building engine
   - Uses Anthropic's Claude with tool calling
   - Loads topics mapping and query parameters
   - Iteratively builds queries through LLM conversation

3. **Tool Schema: build_wonder_query**
   - LLM tool that constructs WonderRequest objects
   - Validates parameter names and values
   - Follows WONDER parameter conventions (B*, F*, M*, O*, V\_)

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
LLM Maps Intent → Parameters
    ↓
Calls build_wonder_query Tool
    ↓
Returns WonderRequest
    ↓
Execute via WonderClient (optional)
```

## Usage

### Python API

```python
from wonder.llm_query_builder import LLMQueryBuilder
from wonder.client import WonderClient

# Initialize builder
builder = LLMQueryBuilder()

# Build query from natural language
request = builder.build_query(
    "Show me opioid overdose deaths by year from 2018 to 2024"
)

# Inspect the generated request
print(f"Dataset: {request.dataset_id}")
print(f"Parameters: {len(request.parameters)}")

# Convert to dict for WonderClient
params = request.to_dict()

# Execute query
client = WonderClient()
response = client.query(request.dataset_id, params)

# Parse results
rows = WonderClient.parse_response_table(response)
for row in rows:
    print(row)
```

### CLI Tool

```bash
# Set your API key
export ANTHROPIC_API_KEY='your-key-here'

# Single query mode
python scripts/query_wonder.py "Show me opioid deaths by year 2020-2023"

# Execute the query
python scripts/query_wonder.py "Cancer mortality by state" --execute

# Verbose output
python scripts/query_wonder.py "Birth rates by age" --verbose

# Interactive mode
python scripts/query_wonder.py --interactive
```

### Example Queries

**Simple Mortality Query:**

```
"Show me opioid overdose deaths by year from 2018 to 2024"
```

**Geographic Analysis:**

```
"Compare infant mortality rates by state for 2020-2023"
```

**Multi-Dimensional:**

```
"I want to analyze cancer mortality trends:
- By year (2015-2022)
- Grouped by age group and sex
- For lung cancer specifically
- Show both death counts and age-adjusted rates"
```

**Birth Statistics:**

```
"Birth rates by age of mother in California from 2015 to 2020"
```

## WonderRequest Schema

The `WonderRequest` model follows this structure:

```python
{
    "dataset_id": "D176",  # CDC WONDER dataset ID
    "parameters": [
        {
            "name": "B_1",              # Group by year
            "values": ["D176.V1-level1"]
        },
        {
            "name": "F_D176.V1",        # Filter: years
            "values": ["2018", "2019", "2020", "2021", "2022", "2023", "2024"]
        },
        {
            "name": "F_D176.V25",       # Filter: drug/alcohol induced causes
            "values": ["T40.0", "T40.1", "T40.2", "T40.3", "T40.4"]
        },
        {
            "name": "M_1",              # Measure: deaths
            "values": ["D176.M1"]
        },
        {
            "name": "dataset_code",     # Required metadata
            "values": ["D176"]
        },
        {
            "name": "action-Send",      # Required action
            "values": ["Send"]
        },
        {
            "name": "stage",            # Required stage
            "values": ["request"]
        }
    ]
}
```

### Parameter Conventions

| Prefix | Purpose                       | Example                       |
| ------ | ----------------------------- | ----------------------------- |
| `B_*`  | Group By (up to 5 dimensions) | `B_1`, `B_2`, `B_3`           |
| `M_*`  | Measures to include           | `M_1`, `M_2`, `M_3`           |
| `F_*`  | Filter values                 | `F_D176.V1`, `F_D176.V25`     |
| `V_*`  | Variable-specific values      | `V_D176.V5`                   |
| `O_*`  | Output options                | `O_rate_per`, `O_show_totals` |
| `VM_*` | Values for adjusted rates     | `VM_D176.M6_D176.V10`         |

### Special Values

- `*All*` - Include all values for this parameter
- `*None*` - Empty slot (for unused Group By positions)

## Data Sources

The LLM Query Builder relies on scraped CDC WONDER metadata:

1. **topics_mapping.json** (`data/raw/wonder/`)

   - Maps 169 datasets to health topics and categories
   - Provides dataset IDs, URLs, years, and topics
   - Used for dataset selection

2. **query_params_D\*.json** (`data/raw/wonder/`)
   - Detailed parameter definitions for each dataset
   - Includes all form elements (selects, inputs, textareas)
   - Contains labels, values, and option lists
   - 169 files (one per dataset)

## Configuration

### Environment Variables

- `ANTHROPIC_API_KEY` - Required. Your Anthropic API key.

### Initialization Options

```python
builder = LLMQueryBuilder(
    api_key="your-key",           # Override API key
    data_dir=Path("/custom/path") # Override data directory
)
```

## Advanced Usage

### Custom System Prompts

The LLM uses a system prompt that includes:

- Available datasets summary
- Dataset parameter details (on request)
- Parameter naming conventions
- Query building process

### Iterative Query Building

The builder engages in a conversation with the LLM:

1. User provides natural language intent
2. LLM analyzes and requests dataset parameters
3. System provides parameter details
4. LLM builds query using `build_wonder_query` tool
5. Returns structured WonderRequest

### Integration with WonderClient

```python
# Build query
request = builder.build_query("your query here")

# Convert to WonderClient format
params = request.to_dict()

# Execute
client = WonderClient()
response_xml = client.query(request.dataset_id, params)

# Parse response
rows = WonderClient.parse_response_table(response_xml)
dicts = WonderClient.parse_response_to_dicts(response_xml)
arrays = WonderClient.parse_response_to_arrays(response_xml)
```

## Output Files

When using the CLI tool, files are saved to `output/`:

- `last_query_request.json` - Full WonderRequest object
- `last_query_params.json` - Parameters dict for WonderClient
- `last_query_response.xml` - Response XML (if executed)

## Examples

See `examples/llm_query_example.py` for comprehensive examples:

```bash
python examples/llm_query_example.py
```

This runs four example scenarios:

1. Basic mortality query
2. Complex multi-dimensional query
3. Geographic analysis
4. Full integration with execution

## Limitations

1. **Dataset Coverage**: Limited to 169 scraped datasets
2. **Parameter Validation**: LLM may generate invalid parameter combinations
3. **API Costs**: Each query requires LLM API calls
4. **Rate Limits**: Subject to Anthropic API rate limits

## Troubleshooting

**Error: No query parameters found for dataset**

- Dataset hasn't been scraped yet
- Check `data/raw/wonder/query_params_D*.json` exists

**Error: ANTHROPIC_API_KEY not set**

- Copy `.env.sample` to `.env`: `cp .env.sample .env`
- Edit `.env` and add your key: `ANTHROPIC_API_KEY='your-key'`
- Or export as environment variable: `export ANTHROPIC_API_KEY='your-key'`

**LLM didn't build query**

- Query may be too ambiguous
- Try providing more specific intent
- Check LLM response for clarifying questions

**Invalid parameter values**

- LLM may hallucinate parameter values
- Verify against `query_params_D*.json` for your dataset
- Add validation logic if needed

## Future Enhancements

- [ ] Parameter validation against query_params schemas
- [ ] Support for chaining multiple queries
- [ ] Automatic result visualization
- [ ] Query templates and caching
- [ ] Support for other LLM providers
- [ ] Web interface

## Related Files

- `src/wonder/llm_query_builder.py` - Main implementation
- `src/wonder/client.py` - WonderClient for execution
- `scripts/query_wonder.py` - CLI tool
- `examples/llm_query_example.py` - Usage examples
- `data/raw/wonder/topics_mapping.json` - Dataset mappings
- `data/raw/wonder/query_params_D*.json` - Parameter definitions

## License

Same as parent project.
