"""
CDC Open Data CLI

Access health statistics from data.cdc.gov via the Socrata SODA API.

Usage:
    # List available datasets
    uv run python -m cdc_open list

    # Raw SODA query against a dataset
    uv run python -m cdc_open query bi63-dtpu --where "year='2015' AND state='New York'" -f csv

    # Ask a question — LLM picks the right tool(s), fetches data, synthesizes answer
    uv run python -m cdc_open analyze "What were the top 5 leading causes of death in Ohio in 2010?"
    uv run python -m cdc_open analyze "Compare obesity rates across southern states"
"""

from cdc_open.datasets import DATASETS
from cdc_open.sdk import query_dataset
from cdc_open.tools import TOOLS, execute_tool

import argparse
import csv
import io
import json
import os
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()

# ─── Commands ─────────────────────────────────────────────────────────────────


def cmd_list(args):
    """List all available datasets."""
    rows = [
        {
            "key": key,
            "id": ds.id,
            "name": ds.name,
            "years": ds.years,
            "description": ds.description,
        }
        for key, ds in DATASETS.items()
    ]
    if args.format == "json":
        print(json.dumps(rows, indent=2))
    else:
        print(f"{'KEY':<25} {'DATASET ID':<12} {'YEARS':<14} NAME")
        print("-" * 80)
        for r in rows:
            print(f"{r['key']:<25} {r['id']:<12} {r['years']:<14} {r['name']}")
            if args.verbose:
                print(f"  {r['description']}")


def cmd_query(args):
    """Execute a raw SODA query against a dataset."""
    try:
        rows = query_dataset(
            dataset_id=args.dataset_id,
            where=args.where,
            select=args.select,
            group=args.group,
            order=args.order,
            limit=args.limit,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not rows:
        print("No results found.", file=sys.stderr)
        return

    _output_rows(rows, args.format)


def cmd_analyze(args):
    """Use Claude to answer a health data question by calling the appropriate tools."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "Error: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr
        )
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    model = args.model

    if args.verbose:
        print(f"Analyzing: {args.question}", file=sys.stderr)
        print(f"Model: {model}", file=sys.stderr)

    messages = [{"role": "user", "content": args.question}]

    system = (
        "You are a public health data analyst with access to CDC Open Data (data.cdc.gov). "
        "Use the provided tools to fetch the relevant data, then provide a clear, "
        "concise analysis answering the user's question. "
        "When you have the data, synthesize findings in plain language with key numbers. "
        "Always cite the dataset and year range used."
    )

    # Agentic tool-calling loop
    all_tool_results: list[dict] = []

    while True:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        if args.verbose:
            print(f"[stop_reason: {response.stop_reason}]", file=sys.stderr)

        # Collect assistant response into messages
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Extract final text response
            for block in response.content:
                if hasattr(block, "text"):
                    print(block.text)
            break

        if response.stop_reason != "tool_use":
            print(f"Unexpected stop reason: {response.stop_reason}", file=sys.stderr)
            break

        # Execute tool calls
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input

            if args.verbose:
                print(
                    f"[tool call: {tool_name}({json.dumps(tool_input)})]",
                    file=sys.stderr,
                )

            try:
                rows = execute_tool(tool_name, tool_input)
                result_text = json.dumps(rows[: args.max_rows])
                if len(rows) > args.max_rows:
                    result_text = (
                        json.dumps(rows[: args.max_rows])
                        + f"\n... ({len(rows) - args.max_rows} more rows truncated)"
                    )
                all_tool_results.extend(rows)
                if args.verbose:
                    print(f"  → {len(rows)} rows", file=sys.stderr)
            except Exception as e:
                result_text = f"Error: {e}"
                if args.verbose:
                    print(f"  → error: {e}", file=sys.stderr)

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                }
            )

        messages.append({"role": "user", "content": tool_results})

    # Optionally dump raw data
    if args.dump_data and all_tool_results:
        print("\n--- Raw Data ---", file=sys.stderr)
        _output_rows(all_tool_results, args.dump_format, file=sys.stderr)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _output_rows(rows: list[dict], format: str, file=None):
    out = file or sys.stdout
    if format == "json":
        print(json.dumps(rows, indent=2), file=out)
    elif format == "csv":
        if not rows:
            return
        fieldnames = list(rows[0].keys())
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        print(buf.getvalue(), end="", file=out)
    elif format == "table":
        if not rows:
            return
        keys = list(rows[0].keys())
        col_widths = {
            k: max(len(k), max((len(str(r.get(k, ""))) for r in rows), default=0))
            for k in keys
        }
        header = "  ".join(k.ljust(col_widths[k]) for k in keys)
        print(header, file=out)
        print("-" * len(header), file=out)
        for row in rows:
            print(
                "  ".join(str(row.get(k, "")).ljust(col_widths[k]) for k in keys),
                file=out,
            )
    else:
        print(f"Unknown format: {format}", file=sys.stderr)
        sys.exit(1)


# ─── CLI entry point ──────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        prog="cdc-open",
        description="CDC Open Data CLI — query health statistics from data.cdc.gov",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    list_parser = subparsers.add_parser("list", help="List available datasets")
    list_parser.add_argument(
        "-f",
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )
    list_parser.set_defaults(func=cmd_list)

    # query
    query_parser = subparsers.add_parser(
        "query",
        help="Raw SODA query against a dataset",
        description="Execute a Socrata SODA query against any data.cdc.gov dataset",
    )
    query_parser.add_argument("dataset_id", help="Socrata dataset ID, e.g. 'bi63-dtpu'")
    query_parser.add_argument("--where", metavar="CLAUSE", help="SODA $where clause")
    query_parser.add_argument("--select", metavar="COLS", help="SODA $select clause")
    query_parser.add_argument("--group", metavar="COLS", help="SODA $group clause")
    query_parser.add_argument("--order", metavar="COL", help="SODA $order clause")
    query_parser.add_argument(
        "--limit", type=int, default=200, help="Max rows (default: 200)"
    )
    query_parser.add_argument(
        "-f",
        "--format",
        choices=["json", "csv", "table"],
        default="json",
        help="Output format (default: json)",
    )
    query_parser.set_defaults(func=cmd_query)

    # analyze
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Ask a question — LLM fetches and analyzes the data",
        description="Use Claude to answer a public health question by querying the relevant CDC datasets",
    )
    analyze_parser.add_argument(
        "question", help="Natural language question about public health data"
    )
    analyze_parser.add_argument(
        "--model",
        default="claude-sonnet-4-6",
        help="Claude model ID (default: claude-sonnet-4-6)",
    )
    analyze_parser.add_argument(
        "--max-rows",
        type=int,
        default=500,
        dest="max_rows",
        help="Max rows per tool result passed to LLM (default: 500)",
    )
    analyze_parser.add_argument(
        "--dump-data",
        action="store_true",
        dest="dump_data",
        help="Dump raw fetched data to stderr after the analysis",
    )
    analyze_parser.add_argument(
        "--dump-format",
        choices=["json", "csv", "table"],
        default="json",
        dest="dump_format",
        help="Format for --dump-data (default: json)",
    )
    analyze_parser.set_defaults(func=cmd_analyze)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
