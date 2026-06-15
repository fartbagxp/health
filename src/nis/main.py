"""
NIS CLI — stream and aggregate CDC National Immunization Survey data.

Usage
-----
    # List available years
    uv run python -m nis list child
    uv run python -m nis list teen

    # Stream raw respondent records (no storage)
    uv run python -m nis stream child 2022 -f csv
    uv run python -m nis stream teen 2022 --state CA -f json

    # State-level UTD rates for all vaccines
    uv run python -m nis rates child 2022 -f table
    uv run python -m nis rates teen 2022 --vaccines P_UTDHPV13 P_UTDTDAP -f csv

    # National-level UTD summary
    uv run python -m nis national child 2022
    uv run python -m nis national teen 2022 --vaccines P_UTDHPV13

Notes
-----
The SAS codebook is fetched first (~50 KB), then the DAT file is streamed.
DAT files are large (50–200 MB); streaming begins immediately but may take
several minutes over a slow connection.
"""

import argparse
import csv
import io
import json
import sys
from typing import Any

from nis.datasets import CHILD_VAX_COLS, TEEN_VAX_COLS
from nis.sdk import get_national_rates, get_vaccination_rates, list_years, stream_records


# ── Commands ───────────────────────────────────────────────────────────────────


def cmd_list(args: argparse.Namespace) -> None:
    years = list_years(args.survey)
    print(f"Available years for NIS-{args.survey.capitalize()}: {years[0]}–{years[-1]}")
    print("  " + "  ".join(str(y) for y in years))


def cmd_stream(args: argparse.Namespace) -> None:
    vaccines = set(args.vaccines) if args.vaccines else None
    try:
        gen = stream_records(args.survey, args.year, state=args.state, columns=vaccines)
        rows = list(gen) if args.limit else gen
        if args.limit:
            rows = rows[: args.limit]
        _output(rows, args.format)
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_rates(args: argparse.Namespace) -> None:
    vaccines = args.vaccines if args.vaccines else None
    try:
        rows = get_vaccination_rates(args.survey, args.year, state=args.state, vaccines=vaccines)
        _output(rows, args.format)
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_national(args: argparse.Namespace) -> None:
    vaccines = args.vaccines if args.vaccines else None
    try:
        result = get_national_rates(args.survey, args.year, vaccines=vaccines)
        _output([result], args.format)
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


# ── Output helpers ─────────────────────────────────────────────────────────────


def _output(rows: list[dict[str, Any]], fmt: str) -> None:
    if not rows:
        print("No results.", file=sys.stderr)
        return
    if fmt == "json":
        print(json.dumps(rows, indent=2))
    elif fmt == "csv":
        keys = list(rows[0].keys())
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
        print(buf.getvalue(), end="")
    elif fmt == "table":
        keys = list(rows[0].keys())
        widths = {k: max(len(str(k)), max(len(str(r.get(k, ""))) for r in rows)) for k in keys}
        header = "  ".join(str(k).ljust(widths[k]) for k in keys)
        print(header)
        print("-" * len(header))
        for row in rows:
            print("  ".join(str(row.get(k, "")).ljust(widths[k]) for k in keys))
    else:
        print(f"Unknown format: {fmt}", file=sys.stderr)
        sys.exit(1)


# ── CLI entry point ────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="nis",
        description="CDC National Immunization Survey (NIS) CLI — stream fixed-width DAT files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    lp = subparsers.add_parser("list", help="List available years for a survey")
    lp.add_argument("survey", choices=["child", "teen"])
    lp.set_defaults(func=cmd_list)

    # stream
    sp = subparsers.add_parser("stream", help="Stream raw respondent records")
    sp.add_argument("survey", choices=["child", "teen"])
    sp.add_argument("year", type=int)
    sp.add_argument("--state", metavar="STATE",
                    help="Filter by state: FIPS code ('06'), postal ('CA'), or full name ('California')")
    sp.add_argument("--vaccines", nargs="+", metavar="VAR",
                    help="Column names to include (default: all vaccination + geo + hesitancy columns)")
    sp.add_argument("--limit", type=int, metavar="N",
                    help="Return at most N records (buffered into memory)")
    sp.add_argument("-f", "--format", choices=["json", "csv", "table"], default="csv")
    sp.set_defaults(func=cmd_stream)

    # rates
    rp = subparsers.add_parser("rates", help="State-level UTD vaccination rates")
    rp.add_argument("survey", choices=["child", "teen"])
    rp.add_argument("year", type=int)
    rp.add_argument("--state", metavar="STATE",
                    help="Limit to one state")
    rp.add_argument("--vaccines", nargs="+", metavar="VAR",
                    help="UTD column names to aggregate (default: all)")
    rp.add_argument("-f", "--format", choices=["json", "csv", "table"], default="table")
    rp.set_defaults(func=cmd_rates)

    # national
    np_ = subparsers.add_parser("national", help="National-level UTD vaccination rates")
    np_.add_argument("survey", choices=["child", "teen"])
    np_.add_argument("year", type=int)
    np_.add_argument("--vaccines", nargs="+", metavar="VAR",
                     help="UTD column names to aggregate (default: all)")
    np_.add_argument("-f", "--format", choices=["json", "csv", "table"], default="table")
    np_.set_defaults(func=cmd_national)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
