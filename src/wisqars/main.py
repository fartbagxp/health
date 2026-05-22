"""
WISQARS CLI — query CDC injury mortality and violence data.

Usage:
    uv run python -m wisqars list
    uv run python -m wisqars mortality --intent Suicide --mechanism Firearm
    uv run python -m wisqars national --intent FA_Deaths --type year
    uv run python -m wisqars state --intent Drug_OD --year 2023
    uv run python -m wisqars county --state Texas --intent FA_Deaths --year 2023
    uv run python -m wisqars query t6u2-f84c --where "intent='Drug_OD' AND type='year'"
"""

import argparse
import csv
import io
import json
import sys

from dotenv import load_dotenv

from wisqars.datasets import (
    DATASETS,
    INJURY_INTENTS,
    INJURY_MECHANISMS,
    MAPPING_INTENTS,
    MAPPING_PERIOD_TYPES,
)
from wisqars.sdk import (
    get_injury_mortality,
    get_injury_national,
    get_injury_state,
    get_injury_county,
    query_dataset,
)

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
        cols = list(rows[0].keys())
        widths = {
            c: max(len(c), max(len(str(r.get(c, ""))) for r in rows)) for c in cols
        }
        header = "  ".join(c.ljust(widths[c]) for c in cols)
        sep = "-" * min(len(header), 120)
        print(header[:120])
        print(sep)
        for r in rows:
            line = "  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols)
            print(line[:120])


def cmd_list(args):
    for key, ds in DATASETS.items():
        print(f"{key:25s} {ds.id}  {ds.years:15s}  {ds.name}")


def cmd_mortality(args):
    rows = get_injury_mortality(
        intent=args.intent,
        mechanism=args.mechanism,
        sex=args.sex,
        age=args.age,
        race=args.race,
        year=args.year,
        limit=args.limit,
    )
    _print_output(rows, args.format)


def cmd_national(args):
    rows = get_injury_national(
        intent=args.intent,
        period_type=args.type,
        year=args.year,
    )
    _print_output(rows, args.format)


def cmd_state(args):
    rows = get_injury_state(
        state=args.state,
        intent=args.intent,
        year=args.year,
        limit=args.limit,
    )
    _print_output(rows, args.format)


def cmd_county(args):
    rows = get_injury_county(
        state=args.state,
        county=args.county,
        intent=args.intent,
        year=args.year,
        limit=args.limit,
    )
    _print_output(rows, args.format)


def cmd_query(args):
    rows = query_dataset(
        dataset_id=args.dataset_id,
        where=args.where,
        select=args.select,
        order=args.order,
        limit=args.limit,
    )
    _print_output(rows, args.format)


def main():
    parser = argparse.ArgumentParser(
        prog="wisqars",
        description="Query CDC WISQARS injury mortality and violence data",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    _fmt = dict(choices=["table", "json", "csv"], default="table")
    _lim = dict(type=int, default=200)

    sub.add_parser("list", help="List available datasets").set_defaults(func=cmd_list)

    p_mort = sub.add_parser(
        "mortality", help="Fatal injury by mechanism/intent/demographics (1999-2016)"
    )
    p_mort.add_argument("--intent", choices=INJURY_INTENTS)
    p_mort.add_argument("--mechanism", choices=INJURY_MECHANISMS)
    p_mort.add_argument("--sex", choices=["Both sexes", "Male", "Female"])
    p_mort.add_argument("--age", metavar="AGE", help="e.g. 'All Ages', '25-34', '< 15'")
    p_mort.add_argument("--race", metavar="RACE")
    p_mort.add_argument("--year", type=int, metavar="YEAR", help="1999-2016")
    p_mort.add_argument("-f", "--format", **_fmt)
    p_mort.add_argument("--limit", **_lim)
    p_mort.set_defaults(func=cmd_mortality)

    p_nat = sub.add_parser(
        "national", help="National firearm/suicide/OD/homicide counts (2019-present)"
    )
    p_nat.add_argument("--intent", choices=MAPPING_INTENTS, metavar="INTENT")
    p_nat.add_argument(
        "--type",
        choices=MAPPING_PERIOD_TYPES,
        metavar="TYPE",
        help="'year', 'month', or 'TTM'",
    )
    p_nat.add_argument("--year", metavar="YEAR", help="e.g. '2023'")
    p_nat.add_argument("-f", "--format", **_fmt)
    p_nat.set_defaults(func=cmd_national)

    p_state = sub.add_parser(
        "state", help="State-level injury/violence data (2019-present)"
    )
    p_state.add_argument("--state", metavar="STATE", help="State name or 2-digit FIPS")
    p_state.add_argument("--intent", choices=MAPPING_INTENTS, metavar="INTENT")
    p_state.add_argument("--year", metavar="YEAR", help="e.g. '2023' or 'TTM'")
    p_state.add_argument("-f", "--format", **_fmt)
    p_state.add_argument("--limit", **_lim)
    p_state.set_defaults(func=cmd_state)

    p_county = sub.add_parser(
        "county", help="County-level injury/violence data (2019-present)"
    )
    p_county.add_argument("--state", metavar="STATE", help="State name or 2-digit FIPS")
    p_county.add_argument(
        "--county", metavar="COUNTY", help="County name partial match"
    )
    p_county.add_argument("--intent", choices=MAPPING_INTENTS, metavar="INTENT")
    p_county.add_argument("--year", metavar="YEAR", help="e.g. '2023' or 'TTM'")
    p_county.add_argument("-f", "--format", **_fmt)
    p_county.add_argument("--limit", **_lim)
    p_county.set_defaults(func=cmd_county)

    p_query = sub.add_parser("query", help="Raw SODA query against any WISQARS dataset")
    p_query.add_argument("dataset_id", help="Socrata dataset ID")
    p_query.add_argument("--where", metavar="CLAUSE")
    p_query.add_argument("--select", metavar="COLS")
    p_query.add_argument("--order", metavar="COL")
    p_query.add_argument("--limit", **_lim)
    p_query.add_argument("-f", "--format", **_fmt)
    p_query.set_defaults(func=cmd_query)

    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
