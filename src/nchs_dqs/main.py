"""
NCHS Data Query System (DQS) CLI

Query the "Health, United States" datasets (NHANES / NHIS / NHAMCS / NVSS /
NPALS / NHCS) on data.cdc.gov. All datasets share one tidy schema, so a single
`query` verb covers every one; `trend` is the all-persons national series.

Usage:
    # List the DQS dataset registry
    uv run python -m nchs_dqs list
    uv run python -m nchs_dqs list --charted      # only what health-charts renders
    uv run python -m nchs_dqs list --uncharted    # the backlog

    # Raw SODA query ('classification=Total' is the all-persons row)
    uv run python -m nchs_dqs query rdjz-vn2n --where "classification='Total'" -f csv

    # All-persons national trend, oldest→newest
    uv run python -m nchs_dqs trend national-health-spending -f csv
"""

import argparse
import csv
import io
import json
import sys

from dotenv import load_dotenv

from nchs_dqs.datasets import DATASETS, dataset
from nchs_dqs.sdk import query_dataset, trend

load_dotenv()


# ─── Commands ─────────────────────────────────────────────────────────────────


def cmd_list(args):
    rows = [
        {
            "key": key,
            "id": d.id,
            "years": d.years,
            "survey": d.survey,
            "topic": d.topic,
            "charted": d.charted,
            "name": d.name,
        }
        for key, d in DATASETS.items()
    ]
    if args.charted:
        rows = [r for r in rows if r["charted"]]
    elif args.uncharted:
        rows = [r for r in rows if not r["charted"]]

    if args.format == "json":
        print(json.dumps(rows, indent=2))
        return

    print(f"{'KEY':<28} {'DATASET ID':<12} {'YEARS':<12} {'SURVEY':<10} {'CHARTED':<8} NAME")
    print("-" * 110)
    for r in rows:
        charted = "yes" if r["charted"] else ""
        print(f"{r['key']:<28} {r['id']:<12} {r['years']:<12} {r['survey']:<10} {charted:<8} {r['name']}")
    if args.uncharted:
        print(f"\n{len(rows)} uncharted dataset(s) — collected-ready but not yet in health-charts.")


def cmd_query(args):
    ds = dataset(args.dataset_id)
    socrata_id = ds.id if ds else args.dataset_id
    if ds:
        print(f"Querying {socrata_id} ({ds.name})", file=sys.stderr)
    try:
        rows = query_dataset(
            dataset_id=socrata_id,
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


def cmd_trend(args):
    ds = dataset(args.dataset_id)
    socrata_id = ds.id if ds else args.dataset_id
    if ds:
        print(f"Trend {socrata_id} ({ds.name})", file=sys.stderr)
    try:
        rows = trend(socrata_id, estimate_type=args.estimate_type, limit=args.limit)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    if not rows:
        print("No 'Total' rows found — try `query` with a --where filter.", file=sys.stderr)
        sys.exit(1)
    _output_rows(rows, args.format)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _output_rows(rows: list[dict], format: str):
    if format == "json":
        print(json.dumps(rows, indent=2))
    elif format == "csv":
        fieldnames = list(rows[0].keys())
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        print(buf.getvalue(), end="")
    elif format == "table":
        keys = list(rows[0].keys())
        widths = {k: max(len(k), max((len(str(r.get(k, ""))) for r in rows), default=0)) for k in keys}
        header = "  ".join(k.ljust(widths[k]) for k in keys)
        print(header)
        print("-" * len(header))
        for r in rows:
            print("  ".join(str(r.get(k, "")).ljust(widths[k]) for k in keys))
    else:
        print(f"Unknown format: {format}", file=sys.stderr)
        sys.exit(1)


# ─── CLI entry point ──────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        prog="dqs",
        description="NCHS Data Query System CLI — Health, United States datasets on data.cdc.gov",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    list_parser = subparsers.add_parser("list", help="List the DQS dataset registry")
    list_parser.add_argument("-f", "--format", choices=["table", "json"], default="table")
    charted_group = list_parser.add_mutually_exclusive_group()
    charted_group.add_argument("--charted", action="store_true", help="Only datasets health-charts renders")
    charted_group.add_argument("--uncharted", action="store_true", help="Only the collected-but-uncharted backlog")
    list_parser.set_defaults(func=cmd_list)

    # query
    query_parser = subparsers.add_parser("query", help="Raw SODA query against a DQS dataset")
    query_parser.add_argument("dataset_id", help="Registry key (e.g. low-birthweight) or Socrata ID")
    query_parser.add_argument("--where", metavar="CLAUSE", help="SODA $where clause")
    query_parser.add_argument("--select", metavar="COLS", help="SODA $select clause (backtick-quote `group`)")
    query_parser.add_argument("--group", metavar="COLS", help="SODA $group clause")
    query_parser.add_argument("--order", metavar="COL", help="SODA $order clause")
    query_parser.add_argument("--limit", type=int, default=200, help="Max rows (default: 200)")
    query_parser.add_argument("-f", "--format", choices=["json", "csv", "table"], default="json")
    query_parser.set_defaults(func=cmd_query)

    # trend
    trend_parser = subparsers.add_parser("trend", help="All-persons national trend, oldest→newest")
    trend_parser.add_argument("dataset_id", help="Registry key or Socrata ID")
    trend_parser.add_argument("-e", "--estimate-type", dest="estimate_type", help="Narrow to one measure")
    trend_parser.add_argument("--limit", type=int, default=1000)
    trend_parser.add_argument("-f", "--format", choices=["json", "csv", "table"], default="table")
    trend_parser.set_defaults(func=cmd_trend)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
