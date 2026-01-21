"""
LLM-Powered CDC WONDER Query Builder

This module uses an LLM with tool calling to convert natural language queries
into structured WONDER API requests. It leverages the topics_mapping.json and
query_params files to intelligently select datasets and build valid queries.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()


class WonderParameter(BaseModel):
    """Single query parameter with one or more values"""
    name: str = Field(..., description="Parameter name (e.g., B_1, F_D176.V1, M_1)")
    values: List[str] = Field(..., description="List of values for this parameter")


class WonderRequest(BaseModel):
    """
    Structured WONDER API request matching the XML schema.
    This represents the complete set of parameters sent to CDC WONDER.
    """
    dataset_id: str = Field(..., description="CDC WONDER dataset ID (e.g., D176)")
    parameters: List[WonderParameter] = Field(
        default_factory=list,
        description="List of all query parameters"
    )

    def to_dict(self) -> Dict[str, Union[str, List[str]]]:
        """Convert to dictionary format used by WonderClient"""
        result = {}
        for param in self.parameters:
            if len(param.values) == 1:
                result[param.name] = param.values[0]
            else:
                result[param.name] = param.values
        return result


class QueryIntent(BaseModel):
    """User's query intent parsed by the LLM"""
    description: str = Field(..., description="Natural language description of what data is requested")
    health_topics: List[str] = Field(default_factory=list, description="Identified health topics")
    time_period: Optional[str] = Field(None, description="Time period if specified")
    geography: Optional[str] = Field(None, description="Geographic scope if specified")
    grouping_dimensions: List[str] = Field(default_factory=list, description="How to group the results")
    filters: Dict[str, List[str]] = Field(default_factory=dict, description="Specific filters to apply")


class LLMQueryBuilder:
    """
    Builds WONDER queries using an LLM with tool calling.

    The LLM is given access to a build_wonder_query tool that it can use
    to construct valid WONDER requests based on the available datasets and
    their query parameters.
    """

    def __init__(self, api_key: Optional[str] = None, data_dir: Optional[Path] = None):
        """
        Initialize the LLM query builder.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            data_dir: Path to data/raw/wonder directory
        """
        self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.data_dir = data_dir or Path(__file__).parent.parent.parent / "data" / "raw" / "wonder"

        # Load topics mapping
        topics_path = self.data_dir / "topics_mapping.json"
        with open(topics_path) as f:
            data = json.load(f)
            self.topics_mapping = data.get("mappings", [])

        # Cache for query params
        self._query_params_cache: Dict[str, Dict] = {}

    def _load_query_params(self, dataset_id: str) -> Dict[str, Any]:
        """Load query parameters for a specific dataset"""
        if dataset_id in self._query_params_cache:
            return self._query_params_cache[dataset_id]

        params_path = self.data_dir / f"query_params_{dataset_id}.json"
        if not params_path.exists():
            raise ValueError(f"No query parameters found for dataset {dataset_id}")

        with open(params_path) as f:
            params = json.load(f)
            self._query_params_cache[dataset_id] = params
            return params

    def _get_available_datasets_summary(self) -> str:
        """Create a summary of available datasets for the LLM"""
        # Group by topic
        by_topic: Dict[str, List[Dict]] = {}
        for dataset in self.topics_mapping:
            topic = dataset.get("topic", "Unknown")
            if topic not in by_topic:
                by_topic[topic] = []
            by_topic[topic].append(dataset)

        lines = ["Available CDC WONDER Datasets:\n"]
        for topic, datasets in sorted(by_topic.items()):
            lines.append(f"\n## {topic}")
            for ds in datasets[:5]:  # Limit to first 5 per topic to save tokens
                lines.append(
                    f"- {ds['dataset_id']}: {ds.get('category', 'N/A')} "
                    f"({ds.get('years', 'N/A')})"
                )
            if len(datasets) > 5:
                lines.append(f"  ... and {len(datasets) - 5} more datasets")

        return "\n".join(lines)

    def _get_dataset_params_summary(self, dataset_id: str) -> str:
        """Create a summary of query parameters for a specific dataset"""
        params = self._load_query_params(dataset_id)

        lines = [f"Query Parameters for {dataset_id}:\n"]

        # Group parameters by type
        selects = params.get("parameters", {}).get("selects", [])
        inputs = params.get("parameters", {}).get("inputs", [])

        # Show Group By options (B_*)
        lines.append("\n### Group By Options (B_1 through B_5):")
        for select in selects:
            if select["name"].startswith("B_"):
                lines.append(f"\n{select['name']}: {select.get('label', 'N/A')}")
                for opt in select["options"][:10]:  # Limit options shown
                    lines.append(f"  - {opt['value']}: {opt['text']}")
                if len(select["options"]) > 10:
                    lines.append(f"  ... and {len(select['options']) - 10} more options")

        # Show Measures (M_*)
        lines.append("\n### Measures (M_*):")
        for inp in inputs:
            if inp["name"].startswith("M_") and inp["type"] == "input_checkbox":
                lines.append(f"  - {inp['name']}: {inp.get('label', 'N/A')}")

        # Show important filters (F_*)
        lines.append("\n### Key Filter Parameters:")
        filter_selects = [s for s in selects if s["name"].startswith("F_")]
        for select in filter_selects[:5]:  # Show first 5 filters
            lines.append(f"\n{select['name']}: {select.get('label', 'N/A')}")
            for opt in select["options"][:5]:
                lines.append(f"  - {opt['value']}: {opt['text']}")

        # Show output options (O_*)
        lines.append("\n### Output Options (O_*):")
        for select in selects:
            if select["name"].startswith("O_"):
                lines.append(f"  - {select['name']}: {select.get('label', 'N/A')}")

        return "\n".join(lines)

    def _create_build_query_tool_schema(self) -> Dict[str, Any]:
        """Create the tool schema for build_wonder_query"""
        return {
            "name": "build_wonder_query",
            "description": (
                "Build a structured CDC WONDER query request from intent. "
                "This tool converts natural language intent into a properly formatted "
                "WonderRequest with the correct dataset_id and parameters. "
                "Use this after determining which dataset to query and what parameters to use."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "The CDC WONDER dataset ID (e.g., 'D176' for Mortality)"
                    },
                    "parameters": {
                        "type": "array",
                        "description": "List of query parameters to send to WONDER",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": (
                                        "Parameter name following WONDER conventions: "
                                        "B_* for grouping, M_* for measures, F_* for filters, "
                                        "V_* for variable values, O_* for output options"
                                    )
                                },
                                "values": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": (
                                        "List of values for this parameter. "
                                        "Use '*All*' for all values, '*None*' for empty grouping slots."
                                    )
                                }
                            },
                            "required": ["name", "values"]
                        }
                    }
                },
                "required": ["dataset_id", "parameters"]
            }
        }

    def build_query(self, intent_text: str, max_tokens: int = 4096) -> WonderRequest:
        """
        Convert natural language intent into a structured WONDER query.

        Args:
            intent_text: Natural language description of the desired query
            max_tokens: Maximum tokens for LLM response

        Returns:
            WonderRequest object with dataset_id and parameters

        Example:
            >>> builder = LLMQueryBuilder()
            >>> request = builder.build_query(
            ...     "Show me opioid overdose deaths by year from 2018 to 2024"
            ... )
            >>> print(request.dataset_id)
            'D176'
        """
        # Prepare system prompt with context
        system_prompt = f"""You are a CDC WONDER query builder assistant. Your job is to convert
natural language queries into structured WONDER API requests.

{self._get_available_datasets_summary()}

Process:
1. Analyze the user's intent to determine which dataset(s) are most appropriate
2. Request the detailed parameters for the selected dataset
3. Build a complete WonderRequest using the build_wonder_query tool
4. Include all required parameters: dataset_code, action-Send, stage
5. Set Group By (B_*) parameters for requested dimensions
6. Set Measures (M_*) for requested metrics
7. Set Filters (F_*) for time periods, geography, etc.
8. Set Output Options (O_*) as appropriate

Important parameter conventions:
- B_1 through B_5: Group by dimensions (use *None* for unused slots)
- M_*: Measures to include (deaths, rates, etc.)
- F_*: Filters - use dataset-specific codes (e.g., F_D176.V1 for year)
- O_*: Output options (rate_per, show_totals, etc.)
- Always include: dataset_code, action-Send=Send, stage=request

When you need parameter details for a specific dataset, just ask and I'll provide them.
"""

        messages = [{"role": "user", "content": intent_text}]

        # Iterative conversation with the LLM
        while True:
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=max_tokens,
                system=system_prompt,
                tools=[self._create_build_query_tool_schema()],
                messages=messages
            )

            # Add assistant response to conversation
            messages.append({"role": "assistant", "content": response.content})

            # Check if we got a tool use
            tool_use_block = None
            for block in response.content:
                if block.type == "tool_use" and block.name == "build_wonder_query":
                    tool_use_block = block
                    break

            if tool_use_block:
                # LLM used the build_wonder_query tool - we're done!
                input_data = tool_use_block.input
                return WonderRequest(**input_data)

            # Check if LLM is asking for more information
            text_response = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text_response += block.text

            if response.stop_reason == "end_turn":
                # LLM might be asking for dataset parameters
                # Check if it mentions a dataset ID
                import re
                dataset_matches = re.findall(r'\b(D\d+)\b', text_response)
                if dataset_matches:
                    # Provide parameters for the first mentioned dataset
                    dataset_id = dataset_matches[0]
                    params_summary = self._get_dataset_params_summary(dataset_id)
                    messages.append({
                        "role": "user",
                        "content": params_summary
                    })
                    continue
                else:
                    # LLM responded but didn't use tool or request info
                    raise ValueError(
                        f"LLM did not build a query. Response: {text_response}"
                    )

            # If we get here, something unexpected happened
            raise ValueError(f"Unexpected response from LLM: {response}")


def main():
    """Example usage of the LLM query builder"""
    builder = LLMQueryBuilder()

    # Example queries
    examples = [
        "Show me opioid overdose deaths by year from 2018 to 2024",
        "I want to see birth rates by state for 2020-2023",
        "Cancer mortality by age group and sex in California",
    ]

    for example in examples:
        print(f"\nQuery: {example}")
        print("-" * 80)
        try:
            request = builder.build_query(example)
            print(f"Dataset: {request.dataset_id}")
            print(f"Parameters ({len(request.parameters)}):")
            for param in request.parameters[:10]:  # Show first 10
                values_str = param.values if len(param.values) <= 3 else param.values[:3] + ["..."]
                print(f"  {param.name}: {values_str}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
