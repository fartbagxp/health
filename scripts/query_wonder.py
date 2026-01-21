#!/usr/bin/env python3
"""
CLI tool to query CDC WONDER using natural language.

Usage:
    python scripts/query_wonder.py "Show me opioid deaths by year 2020-2023"
    python scripts/query_wonder.py --interactive

Configuration:
    Set ANTHROPIC_API_KEY in .env file (copy from .env.sample)
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wonder.llm_query_builder import LLMQueryBuilder  # This loads .env automatically
from wonder.client import WonderClient


def query_wonder(intent: str, execute: bool = False, verbose: bool = False):
    """
    Build and optionally execute a WONDER query from natural language.

    Args:
        intent: Natural language query
        execute: Whether to actually execute the query
        verbose: Show detailed output
    """
    # Initialize builder
    builder = LLMQueryBuilder()

    # Build query
    print(f"\nQuery: {intent}")
    print("\nBuilding structured request...")

    try:
        request = builder.build_query(intent)
    except Exception as e:
        print(f"Error building query: {e}")
        return None

    # Display request
    print(f"\nDataset: {request.dataset_id}")
    print(f"Parameters: {len(request.parameters)}")

    if verbose:
        print("\nDetailed Parameters:")
        for param in request.parameters:
            values_str = ", ".join(param.values[:5])
            if len(param.values) > 5:
                values_str += f", ... (+{len(param.values) - 5} more)"
            print(f"  {param.name}: [{values_str}]")

    # Save to file
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    # Save as JSON
    json_path = output_dir / "last_query_request.json"
    with open(json_path, 'w') as f:
        json.dump(request.model_dump(), f, indent=2)
    print(f"\nRequest saved to: {json_path}")

    # Save as dict for WonderClient
    dict_path = output_dir / "last_query_params.json"
    with open(dict_path, 'w') as f:
        json.dump(request.to_dict(), f, indent=2)
    print(f"Parameters saved to: {dict_path}")

    # Execute if requested
    if execute:
        print("\nExecuting query...")
        client = WonderClient()

        try:
            response_xml = client.query(request.dataset_id, request.to_dict())

            # Save response
            xml_path = output_dir / "last_query_response.xml"
            with open(xml_path, 'w') as f:
                f.write(response_xml)
            print(f"Response saved to: {xml_path}")

            # Parse and display
            rows = WonderClient.parse_response_table(response_xml)
            print(f"\nReceived {len(rows)} rows")

            if rows and verbose:
                print("\nFirst 10 rows:")
                for i, row in enumerate(rows[:10], 1):
                    cells = [cell.label or cell.value or "-" for cell in row.cells]
                    print(f"  Row {i}: {' | '.join(cells[:6])}")

            return response_xml

        except Exception as e:
            print(f"Error executing query: {e}")
            return None

    return request


def interactive_mode():
    """Interactive query building mode"""
    print("="*80)
    print("CDC WONDER LLM Query Builder - Interactive Mode")
    print("="*80)
    print("\nType your query in natural language, or 'quit' to exit.")
    print("Examples:")
    print("  - Show me opioid deaths by year from 2018 to 2024")
    print("  - Cancer mortality by state for 2020")
    print("  - Birth rates by age of mother in California 2015-2020")
    print()

    builder = LLMQueryBuilder()

    while True:
        try:
            print("\n" + "-"*80)
            intent = input("\nYour query: ").strip()

            if not intent or intent.lower() == 'quit':
                print("Goodbye!")
                break

            # Build query
            print("\nBuilding query...")
            request = builder.build_query(intent)

            print(f"\nDataset: {request.dataset_id}")
            print(f"Parameters: {len(request.parameters)}")

            # Ask if user wants details
            show_details = input("\nShow parameter details? (y/n): ").lower() == 'y'
            if show_details:
                for param in request.parameters:
                    values_str = ", ".join(param.values[:3])
                    if len(param.values) > 3:
                        values_str += f", ... (+{len(param.values) - 3} more)"
                    print(f"  {param.name}: [{values_str}]")

            # Ask if user wants to execute
            execute = input("\nExecute this query? (y/n): ").lower() == 'y'
            if execute:
                query_wonder(intent, execute=True, verbose=show_details)

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            continue


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Query CDC WONDER using natural language",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Show me opioid deaths by year 2020-2023"
  %(prog)s "Cancer mortality by state" --execute --verbose
  %(prog)s --interactive
        """
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="Natural language query (omit for interactive mode)"
    )
    parser.add_argument(
        "-e", "--execute",
        action="store_true",
        help="Execute the query against CDC WONDER"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Interactive mode"
    )

    args = parser.parse_args()

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not found")
        print("\nPlease set your API key in .env file:")
        print("  1. Copy .env.sample to .env:  cp .env.sample .env")
        print("  2. Edit .env and set:  ANTHROPIC_API_KEY='your-key-here'")
        print("\nAlternatively, export as environment variable:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)

    # Interactive mode
    if args.interactive or not args.query:
        interactive_mode()
    else:
        # Single query mode
        query_wonder(args.query, execute=args.execute, verbose=args.verbose)


if __name__ == "__main__":
    main()
