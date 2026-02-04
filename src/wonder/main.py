"""
CDC WONDER CLI Tool

Unified command-line interface for building and executing CDC WONDER queries.

Usage:
    # Build a query from natural language, output XML
    uv run python -m wonder build "opioid deaths by year 2018-2024" -o query.xml

    # Run an existing query XML file
    uv run python -m wonder run queries/opioid-overdose-deaths-2018-2024-req.xml

    # Build and execute in one step
    uv run python -m wonder query "opioid deaths by year 2018-2024" --save-xml query.xml
"""

import argparse
import json
import sys
from pathlib import Path

from wonder.client import WonderClient
from wonder.llm_query_builder import LLMQueryBuilder


def cmd_build(args):
    """Build a query from natural language and output XML"""
    if args.verbose:
        print(f"Building query from: {args.prompt}", file=sys.stderr)

    builder = LLMQueryBuilder()
    request = builder.build_query(args.prompt)
    xml = request.to_xml()

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(xml)
        if args.verbose:
            print(f"Wrote query to: {output_path}", file=sys.stderr)
    else:
        print(xml)


def cmd_run(args):
    """Run an existing query XML file"""
    query_path = Path(args.query_file)
    if not query_path.exists():
        print(f"Error: Query file not found: {query_path}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Executing query from: {query_path}", file=sys.stderr)

    client = WonderClient(timeout=args.timeout)
    response_xml = client.execute_query_file(str(query_path))

    _output_response(client, response_xml, args.format, args.verbose)


def cmd_query(args):
    """Build and execute a query in one step"""
    if args.verbose:
        print(f"Building query from: {args.prompt}", file=sys.stderr)

    builder = LLMQueryBuilder()
    request = builder.build_query(args.prompt)
    xml = request.to_xml()

    if args.save_xml:
        save_path = Path(args.save_xml)
        save_path.write_text(xml)
        if args.verbose:
            print(f"Saved query XML to: {save_path}", file=sys.stderr)

    if args.verbose:
        print(f"Executing query against dataset: {request.dataset_id}", file=sys.stderr)

    client = WonderClient(timeout=args.timeout)
    response_xml = client.query_from_xml(request.dataset_id, xml)

    _output_response(client, response_xml, args.format, args.verbose)


def _output_response(
    client: WonderClient, response_xml: str, format: str, verbose: bool
):
    """Output the response in the specified format"""
    if format == "xml":
        print(response_xml)
    elif format == "json":
        rows = client.parse_response_to_dicts(response_xml)
        print(json.dumps(rows, indent=2))
    elif format == "array":
        rows = client.parse_response_to_arrays(response_xml)
        print(json.dumps(rows, indent=2))
    else:
        print(f"Error: Unknown format: {format}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for the CLI"""
    parser = argparse.ArgumentParser(
        prog="wonder",
        description="CDC WONDER CLI Tool - Build and execute WONDER queries",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Build command
    build_parser = subparsers.add_parser(
        "build",
        help="Build a query from natural language",
        description="Convert natural language to CDC WONDER XML query format",
    )
    build_parser.add_argument(
        "prompt",
        help="Natural language query description",
    )
    build_parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Output file path (default: stdout)",
    )
    build_parser.set_defaults(func=cmd_build)

    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run an existing query XML file",
        description="Execute a pre-built CDC WONDER XML query",
    )
    run_parser.add_argument(
        "query_file",
        help="Path to XML query file",
    )
    run_parser.add_argument(
        "-f",
        "--format",
        choices=["json", "array", "xml"],
        default="json",
        help="Output format (default: json)",
    )
    run_parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=60,
        help="Request timeout in seconds (default: 60)",
    )
    run_parser.set_defaults(func=cmd_run)

    # Query command
    query_parser = subparsers.add_parser(
        "query",
        help="Build and execute a query in one step",
        description="Build a query from natural language and execute it immediately",
    )
    query_parser.add_argument(
        "prompt",
        help="Natural language query description",
    )
    query_parser.add_argument(
        "-f",
        "--format",
        choices=["json", "array", "xml"],
        default="json",
        help="Output format (default: json)",
    )
    query_parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=60,
        help="Request timeout in seconds (default: 60)",
    )
    query_parser.add_argument(
        "--save-xml",
        metavar="FILE",
        help="Save the generated XML query to file",
    )
    query_parser.set_defaults(func=cmd_query)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
