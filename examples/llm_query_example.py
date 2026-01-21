"""
Example usage of the LLM-powered CDC WONDER query builder.

This script demonstrates how to:
1. Convert natural language queries into structured WONDER requests
2. Execute the queries against CDC WONDER API
3. Parse and display the results

Requirements:
- Set ANTHROPIC_API_KEY in .env file (copy from .env.sample)
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wonder.llm_query_builder import LLMQueryBuilder, WonderRequest  # This loads .env
from wonder.client import WonderClient


def example_1_basic_query():
    """Example 1: Simple mortality query"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Opioid Overdose Query")
    print("="*80)

    # Initialize the LLM query builder
    builder = LLMQueryBuilder()

    # Natural language query
    intent = "Show me opioid overdose deaths by year from 2018 to 2024"
    print(f"\nQuery: {intent}")

    # Build the structured request
    print("\nBuilding query with LLM...")
    request = builder.build_query(intent)

    # Display the generated request
    print(f"\nGenerated Request:")
    print(f"  Dataset: {request.dataset_id}")
    print(f"  Parameters: {len(request.parameters)}")
    for param in request.parameters:
        values_str = ", ".join(param.values[:3])
        if len(param.values) > 3:
            values_str += f", ... (+{len(param.values) - 3} more)"
        print(f"    {param.name}: [{values_str}]")

    # Execute the query (optional - uncomment to run)
    # client = WonderClient()
    # response = client.query(request.dataset_id, request.to_dict())
    # print("\nQuery executed successfully!")
    # print(response[:500] + "..." if len(response) > 500 else response)


def example_2_complex_query():
    """Example 2: Complex query with multiple dimensions"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Complex Multi-Dimensional Query")
    print("="*80)

    builder = LLMQueryBuilder()

    intent = """
    I want to analyze cancer mortality trends:
    - By year (2015-2022)
    - Grouped by age group and sex
    - For lung cancer specifically
    - Show both death counts and age-adjusted rates
    """
    print(f"\nQuery: {intent}")

    print("\nBuilding query with LLM...")
    request = builder.build_query(intent)

    print(f"\nGenerated Request:")
    print(f"  Dataset: {request.dataset_id}")
    print(f"  Parameters: {len(request.parameters)}")
    for param in request.parameters[:15]:  # Show first 15 params
        values_str = ", ".join(param.values[:2])
        if len(param.values) > 2:
            values_str += f", ... (+{len(param.values) - 2} more)"
        print(f"    {param.name}: [{values_str}]")


def example_3_geographic_query():
    """Example 3: Geographic analysis"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Geographic Analysis")
    print("="*80)

    builder = LLMQueryBuilder()

    intent = "Compare infant mortality rates by state for 2020-2023"
    print(f"\nQuery: {intent}")

    print("\nBuilding query with LLM...")
    request = builder.build_query(intent)

    print(f"\nGenerated Request:")
    print(f"  Dataset: {request.dataset_id}")
    print(f"  Parameters: {len(request.parameters)}")
    for param in request.parameters[:15]:
        values_str = ", ".join(param.values[:2])
        if len(param.values) > 2:
            values_str += f", ... (+{len(param.values) - 2} more)"
        print(f"    {param.name}: [{values_str}]")


def example_4_integration_with_client():
    """Example 4: Full integration - build and execute query"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Full Integration with WonderClient")
    print("="*80)

    # Check if user wants to actually execute
    print("\nThis example will execute a real query against CDC WONDER.")
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Skipped.")
        return

    builder = LLMQueryBuilder()
    client = WonderClient()

    intent = "Total deaths in the US by month for 2023"
    print(f"\nQuery: {intent}")

    # Build query
    print("\nBuilding query...")
    request = builder.build_query(intent)

    print(f"  Dataset: {request.dataset_id}")
    print(f"  Parameters: {len(request.parameters)}")

    # Execute query
    print("\nExecuting query...")
    try:
        response_xml = client.query(request.dataset_id, request.to_dict())

        # Parse response
        from wonder.client import WonderClient
        rows = WonderClient.parse_response_table(response_xml)

        print(f"\nReceived {len(rows)} rows")
        print("\nFirst 10 rows:")
        for i, row in enumerate(rows[:10], 1):
            cells_str = " | ".join([
                cell.label or cell.value or "-"
                for cell in row.cells[:5]  # Show first 5 cells
            ])
            print(f"  {i}. {cells_str}")

    except Exception as e:
        print(f"\nError executing query: {e}")


def main():
    """Run all examples"""
    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not found")
        print("\nPlease set your API key in .env file:")
        print("  1. Copy .env.sample to .env:  cp .env.sample .env")
        print("  2. Edit .env and set:  ANTHROPIC_API_KEY='your-key-here'")
        print("\nAlternatively, export as environment variable:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        return

    print("CDC WONDER LLM Query Builder Examples")
    print("=" * 80)

    try:
        example_1_basic_query()
        example_2_complex_query()
        example_3_geographic_query()
        example_4_integration_with_client()

        print("\n" + "="*80)
        print("Examples completed!")
        print("="*80)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
