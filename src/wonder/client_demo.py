#!/usr/bin/env python3
"""
CDC WONDER Client Demo

This script demonstrates how to use the WonderClient to query CDC WONDER data.

Run with: uv run python examples/wonder_client_demo.py
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.wonder.client import WonderClient, QueryBuilder


def demo_query_from_file():
    """Demo: Execute a pre-built query from XML file"""
    print("=" * 70)
    print("Demo 1: Execute Query from File")
    print("=" * 70)

    client = WonderClient()

    # Execute the opioid query
    query_file = "src/wonder/queries/All Opioid Overdose Deaths of U.S. Residents by Year in Years 2018-2024-req.xml"

    print(f"\nExecuting query from: {query_file}")
    print("This may take a few seconds...")

    response = client.execute_query_file(query_file)

    # Get metadata
    metadata = client.get_dataset_metadata(response)
    print(f"\nDataset: {metadata.get('label')}")
    print(f"Vintage: {metadata.get('vintage')}")

    # Parse to array format
    table = client.parse_response_to_arrays(response)

    print(f"\nResults ({len(table)} rows):")
    print("-" * 70)
    for row in table:
        print(f"  {row}")


def demo_query_builder():
    """Demo: Build and execute a custom query using QueryBuilder"""
    print("\n\n")
    print("=" * 70)
    print("Demo 2: Build Custom Query with QueryBuilder")
    print("=" * 70)

    client = WonderClient()

    # Build a query for deaths by year, 2020-2022
    params = (
        QueryBuilder(dataset_id="D176")
        .group_by("D176.V1-level1", slot=1)  # Group by Year
        .measures(["D176.M1", "D176.M2", "D176.M3"])  # Deaths, Population, Crude Rate
        .filter("F_D176.V1", ["2020", "2021", "2022"])  # Years 2020-2022
        .filter("F_D176.V9", "*All*")  # All states
        .filter("F_D176.V2", "*All*")  # All months
        .filter("F_D176.V10", "*All*")  # All regions
        .filter("F_D176.V27", "*All*")  # All HHS regions
        .filter("F_D176.V77", "*All*")  # All occurrence regions
        .filter("F_D176.V79", "*All*")  # All occurrence states
        .filter("F_D176.V80", "*All*")  # All occurrence census regions
        .filter("F_D176.V100", "*All*")  # All residence urbanization
        .option("O_rate_per", "100000")  # Per 100,000 population
        .option("O_show_totals", "true")  # Show totals
        .option("O_javascript", "on")  # Enable javascript
        .option("O_precision", "1")  # 1 decimal place
        .option("O_timeout", "300")  # 5 minute timeout
        .option("O_V1_fmode", "freg")  # Regular filter mode
        .option("O_V2_fmode", "freg")
        .option("O_V9_fmode", "freg")
        .option("O_V10_fmode", "freg")
        .option("O_V27_fmode", "freg")
        .option("O_V77_fmode", "freg")
        .option("O_V79_fmode", "freg")
        .option("O_V80_fmode", "freg")
        .option("O_V100_fmode", "freg")
        .option("O_location", "D176.V9")
        .option("O_dates", "YEAR")
        .build()
    )

    print("\nBuilt query parameters:")
    print(f"  Group by: {params.get('B_1')}")
    print(f"  Measures: {[v for k, v in params.items() if k.startswith('M_')]}")
    print(f"  Years: {params.get('F_D176.V1')}")

    print("\nExecuting query...")
    print("This may take a few seconds...")

    response = client.query("D176", params)

    # Parse response
    table = client.parse_response_to_arrays(response)

    print(f"\nResults ({len(table)} rows):")
    print("-" * 70)
    for row in table:
        print(f"  {row}")


def demo_parse_to_dicts():
    """Demo: Parse response to dictionary format"""
    print("\n\n")
    print("=" * 70)
    print("Demo 3: Parse Response to Dictionaries")
    print("=" * 70)

    client = WonderClient()

    # Execute query
    query_file = "src/wonder/queries/All Opioid Overdose Deaths of U.S. Residents by Year in Years 2018-2024-req.xml"
    response = client.execute_query_file(query_file)

    # Parse to dictionary format
    rows = client.parse_response_to_dicts(response)

    print(f"\nParsed {len(rows)} rows to dictionaries")
    print("\nFirst row (2018):")
    print(json.dumps(rows[0], indent=2))

    print("\nLast row (Total):")
    print(json.dumps(rows[-1], indent=2))


def main():
    """Run all demos"""
    try:
        # Demo 1: Query from file
        demo_query_from_file()

        # Demo 2: Query builder (commented out to avoid rate limiting)
        # Uncomment if you want to test, but wait 2+ minutes between queries
        # demo_query_builder()

        # Demo 3: Parse to dictionaries
        demo_parse_to_dicts()

        print("\n" + "=" * 70)
        print("All demos completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
