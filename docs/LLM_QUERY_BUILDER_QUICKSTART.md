# LLM Query Builder - Quick Start

## What Was Built

An LLM-powered system that converts natural language queries into structured CDC WONDER API requests.

**Key Feature:** Ask questions in plain English, get properly formatted WONDER queries automatically.

## Components Created

### 1. Core Module: `src/wonder/llm_query_builder.py`

- **WonderRequest Model**: Pydantic model matching WONDER XML schema
- **LLMQueryBuilder Class**: Main query building engine using Claude
- **Tool Schema**: `build_wonder_query` tool for LLM to construct requests

### 2. CLI Tool: `scripts/query_wonder.py`

Interactive and single-query modes for building WONDER queries from the command line.

### 3. Examples: `examples/llm_query_example.py`

Comprehensive examples showing different query types and use cases.

### 4. Tests: `tests/test_llm_query_builder.py`

Unit tests verifying models and basic functionality (9/9 passing ✓).

### 5. Documentation: `docs/LLM_QUERY_BUILDER.md`

Complete documentation covering architecture, usage, and API reference.

## Quick Usage

### Setup

```bash
# Install dependencies (already done)
uv sync

# Set API key in .env file
cp .env.sample .env
# Edit .env and add your API key:
# ANTHROPIC_API_KEY='your-anthropic-api-key'

# Or export as environment variable
export ANTHROPIC_API_KEY='your-anthropic-api-key'
```

### Python API

```python
from wonder.llm_query_builder import LLMQueryBuilder

builder = LLMQueryBuilder()
request = builder.build_query("Show me opioid deaths by year 2020-2023")

print(f"Dataset: {request.dataset_id}")
print(f"Parameters: {len(request.parameters)}")
```

### CLI

```bash
# Single query
python scripts/query_wonder.py "Show me opioid deaths by year 2020-2023"

# Interactive mode
python scripts/query_wonder.py --interactive

# Execute query
python scripts/query_wonder.py "Cancer deaths by state" --execute --verbose
```

### Full Integration

```python
from wonder.llm_query_builder import LLMQueryBuilder
from wonder.client import WonderClient

# Build query
builder = LLMQueryBuilder()
request = builder.build_query("Birth rates by state for 2020-2023")

# Execute
client = WonderClient()
response = client.query(request.dataset_id, request.to_dict())

# Parse results
rows = WonderClient.parse_response_table(response)
for row in rows[:10]:
    print(row)
```

## How It Works

1. **User Input**: Natural language query (e.g., "opioid deaths by year")
2. **LLM Analysis**: Claude analyzes intent and selects appropriate dataset
3. **Parameter Loading**: System loads query parameters for selected dataset
4. **Query Building**: LLM maps intent to WONDER parameters using tool calling
5. **Structured Output**: Returns WonderRequest with dataset_id and parameters
6. **Execution**: Optional - execute via WonderClient and parse results

## Example Queries

```
"Show me opioid overdose deaths by year from 2018 to 2024"
"Compare infant mortality rates by state for 2020-2023"
"Birth rates by age of mother in California 2015-2020"
"Cancer mortality by age group and sex in 2022"
"COVID-19 deaths by month for 2020-2021"
```

## Architecture

```bash
User Query
    ↓
LLMQueryBuilder (uses Claude)
    ├── Loads topics_mapping.json (169 datasets)
    ├── Loads query_params_D*.json for selected dataset
    ├── LLM calls build_wonder_query tool
    └── Returns WonderRequest
         ↓
WonderClient (optional)
    ├── Converts to XML
    ├── Sends to CDC WONDER API
    └── Returns response XML
         ↓
Parse Results
    ├── parse_response_table()
    ├── parse_response_to_dicts()
    └── parse_response_to_arrays()
```

## Data Sources

The system uses scraped CDC WONDER metadata:

- **topics_mapping.json**: 169 datasets mapped to health topics
- **query_params_D\*.json**: Parameter definitions for each dataset (169 files)

## WonderRequest Structure

```python
WonderRequest(
    dataset_id="D176",
    parameters=[
        WonderParameter(name="B_1", values=["D176.V1-level1"]),  # Group by year
        WonderParameter(name="F_D176.V1", values=["2020", "2021"]),  # Filter years
        WonderParameter(name="M_1", values=["D176.M1"]),  # Measure: deaths
        WonderParameter(name="dataset_code", values=["D176"]),  # Required
        WonderParameter(name="action-Send", values=["Send"]),  # Required
        WonderParameter(name="stage", values=["request"]),  # Required
    ]
)
```

## Parameter Conventions

| Prefix | Purpose  | Example                             |
| ------ | -------- | ----------------------------------- |
| `B_*`  | Group By | `B_1="D176.V1-level1"` (by year)    |
| `M_*`  | Measures | `M_1="D176.M1"` (deaths)            |
| `F_*`  | Filters  | `F_D176.V1=["2020","2021"]` (years) |
| `O_*`  | Options  | `O_rate_per="100000"` (per capita)  |

## Dependencies Added

- `anthropic>=0.43.0` - Anthropic Claude API
- `pydantic>=2.10.6` - Data validation and models

## Testing

```bash
# Run unit tests
uv run python tests/test_llm_query_builder.py

# Run examples
uv run python examples/llm_query_example.py
```

## Next Steps

1. **Set API Key**: Get Anthropic API key and set `ANTHROPIC_API_KEY`
2. **Try Interactive Mode**: `python scripts/query_wonder.py -i`
3. **Build Your First Query**: Use natural language to query WONDER
4. **Integrate**: Use in your own scripts with the Python API

## Files Created

```
src/wonder/llm_query_builder.py          # Core implementation
scripts/query_wonder.py                  # CLI tool
examples/llm_query_example.py            # Usage examples
tests/test_llm_query_builder.py          # Unit tests
docs/LLM_QUERY_BUILDER.md                # Full documentation
docs/LLM_QUERY_BUILDER_QUICKSTART.md     # This file
```

## Support

See full documentation in `docs/LLM_QUERY_BUILDER.md` for:

- Detailed API reference
- Advanced usage patterns
- Troubleshooting guide
- Architecture details
