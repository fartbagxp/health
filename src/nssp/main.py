"""
NSSP CLI — query NSSP emergency department visit signals via Delphi Epidata API.

Usage:
    uv run python -m nssp query covid --geo-type state --geo-value ca
    uv run python -m nssp query influenza --geo-type nation
    uv run python -m nssp national --start 20240901
    uv run python -m nssp snapshot covid
"""

import argparse
import csv
import io
import json
import sys

from dotenv import load_dotenv

from nssp.sdk import get_ed_visits, get_national_trends, get_hhs_region_trends
from nssp.client import SIGNALS, GEO_TYPES

load_dotenv()


def _print_output(rows: list[dict], fmt: str) -> None:
    if not rows:
        print("No results.")
        return
    if fmt == "json":
        print(json.dumps(rows, indent=2, default=str))
    elif fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        print(buf.getvalue(), end="")
    else:
        cols = [
            "geo_value",
            "time_value",
            "value",
            "stderr",
            "direction",
            "sample_size",
        ]
        cols = [c for c in cols if c in rows[0]]
        widths = {
            c: max(len(c), max(len(str(r.get(c, ""))) for r in rows)) for c in cols
        }
        header = "  ".join(c.ljust(widths[c]) for c in cols)
        print(header)
        print("-" * len(header))
        for r in rows:
            print("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols))


def cmd_query(args):
    rows = get_ed_visits(
        pathogen=args.pathogen,
        geo_type=args.geo_type,
        geo_value=args.geo_value,
        start_date=args.start,
        end_date=args.end,
    )
    rows.sort(
        key=lambda r: (r.get("geo_value", ""), r.get("time_value", 0)), reverse=True
    )
    _print_output(rows, args.format)


def cmd_national(args):
    rows = get_national_trends(start_date=args.start, end_date=args.end)
    rows.sort(
        key=lambda r: (r.get("pathogen", ""), r.get("time_value", 0)), reverse=True
    )
    _print_output(rows, args.format)


def cmd_hhs(args):
    rows = get_hhs_region_trends(
        pathogen=args.pathogen,
        region=args.region,
        start_date=args.start,
        end_date=args.end,
    )
    rows.sort(key=lambda r: (r.get("geo_value", ""), r.get("time_value", 0)))
    _print_output(rows, args.format)


def main():
    parser = argparse.ArgumentParser(
        prog="nssp",
        description="Query NSSP ED visit signals via Delphi Epidata API",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    _fmt = dict(choices=["table", "json", "csv"], default="table")

    p_query = sub.add_parser("query", help="ED visit pct for a pathogen by geography")
    p_query.add_argument("pathogen", choices=list(SIGNALS), help="Pathogen signal")
    p_query.add_argument(
        "--geo-type",
        default="state",
        choices=sorted(GEO_TYPES),
        help="Geographic resolution (default: state)",
    )
    p_query.add_argument(
        "--geo-value",
        default="*",
        help="'*' for all, 'ca' for state, '06037' for county FIPS, '4' for HHS region",
    )
    p_query.add_argument("--start", metavar="YYYYWW", help="Start date")
    p_query.add_argument("--end", metavar="YYYYWW", help="End date")
    p_query.add_argument("-f", "--format", **_fmt)
    p_query.set_defaults(func=cmd_query)

    p_nat = sub.add_parser("national", help="All four pathogens at national level")
    p_nat.add_argument("--start", metavar="YYYYWW", help="Start date")
    p_nat.add_argument("--end", metavar="YYYYWW", help="End date")
    p_nat.add_argument("-f", "--format", **_fmt)
    p_nat.set_defaults(func=cmd_national)

    p_hhs = sub.add_parser("hhs", help="ED visit pct by HHS region")
    p_hhs.add_argument("pathogen", choices=list(SIGNALS))
    p_hhs.add_argument(
        "--region",
        type=int,
        choices=range(1, 11),
        metavar="1-10",
        help="HHS region number (omit for all)",
    )
    p_hhs.add_argument("--start", metavar="YYYYWW", help="Start date")
    p_hhs.add_argument("--end", metavar="YYYYWW", help="End date")
    p_hhs.add_argument("-f", "--format", **_fmt)
    p_hhs.set_defaults(func=cmd_hhs)

    args = parser.parse_args()
    try:
        args.func(args)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
