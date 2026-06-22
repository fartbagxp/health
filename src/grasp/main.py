"""
GRASP CLI — query ATSDR/CDC GRASP disease APIs.

Usage:
    uv run python -m grasp list
    uv run python -m grasp hantavirus cases --outcome Dead -f table
    uv run python -m grasp hantavirus by-year -f table
    uv run python -m grasp hantavirus by-state -f table
    uv run python -m grasp fluview ili data --region nat ca tx --epiweeks 202001-202026
    uv run python -m grasp fluview ili by-region --epiweeks 202001-202026
    uv run python -m grasp fluview clinical data --region nat --epiweeks 202001-202026
    uv run python -m grasp flusurv data --location network_all --season 2019-20
    uv run python -m grasp flusurv by-season --location CA -f table
    uv run python -m grasp flusurv by-location --season 2019-20 -f table
"""

import argparse
import csv
import io
import json
import sys

from dotenv import load_dotenv

from grasp.datasets import DATASETS, FLUSURV_LOCATIONS
from grasp.sdk import (
    get_fluview_clinical,
    get_fluview_ili,
    get_flusurv_net,
    get_hantavirus_cases,
    summarize_fluview_ili_by_region,
    summarize_flusurv_by_location,
    summarize_flusurv_by_season,
    summarize_hantavirus_by_state,
    summarize_hantavirus_by_year,
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
        print(f"{key:25s}  {ds.years:20s}  {ds.name}")


# ── hantavirus ─────────────────────────────────────────────────────────────────


def cmd_hanta_cases(args):
    rows = get_hantavirus_cases(
        state_fips=args.state_fips,
        state_name=args.state,
        outcome=args.outcome,
        year=args.year,
    )
    _print_output(rows, args.format)


def cmd_hanta_by_year(args):
    _print_output(summarize_hantavirus_by_year(), args.format)


def cmd_hanta_by_state(args):
    _print_output(summarize_hantavirus_by_state(), args.format)


# ── fluview ────────────────────────────────────────────────────────────────────


def cmd_fluview_ili_data(args):
    rows = get_fluview_ili(
        regions=args.region or None,
        epiweeks=args.epiweeks,
    )
    _print_output(rows, args.format)


def cmd_fluview_ili_by_region(args):
    rows = summarize_fluview_ili_by_region(epiweeks=args.epiweeks)
    _print_output(rows, args.format)


def cmd_fluview_clinical_data(args):
    rows = get_fluview_clinical(
        regions=args.region or None,
        epiweeks=args.epiweeks,
    )
    _print_output(rows, args.format)


# ── flusurv ────────────────────────────────────────────────────────────────────


def cmd_flusurv_data(args):
    locations = args.location if args.location else None
    rows = get_flusurv_net(
        locations=locations,
        epiweeks=args.epiweeks,
        season=args.season,
    )
    if args.format == "table" and rows:
        keep = ["location", "season", "epiweek", "rate_overall",
                "rate_age_0", "rate_age_1", "rate_age_2", "rate_age_3", "rate_age_4",
                "rate_flu_a", "rate_flu_b"]
        rows = [{k: r.get(k) for k in keep if k in r} for r in rows]
    _print_output(rows, args.format)


def cmd_flusurv_by_season(args):
    _print_output(summarize_flusurv_by_season(location=args.location or "network_all"), args.format)


def cmd_flusurv_by_location(args):
    rows = summarize_flusurv_by_location(epiweeks=args.epiweeks, season=args.season)
    _print_output(rows, args.format)


# ── argument parser ────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        prog="grasp",
        description="Query ATSDR/CDC GRASP disease APIs (gis.cdc.gov/grasp)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    _fmt = dict(choices=["table", "json", "csv"], default="table")

    sub.add_parser("list", help="List available GRASP datasets").set_defaults(func=cmd_list)

    # ── hantavirus ─────────────────────────────────────────────────────────────
    p_hanta = sub.add_parser("hantavirus", help="Hantavirus case data (pre-1993–present)")
    hanta_sub = p_hanta.add_subparsers(dest="subcommand", required=True)

    p_cases = hanta_sub.add_parser("cases", help="Individual case records")
    p_cases.add_argument("--state", metavar="STATE", help="State name (e.g. 'New Mexico')")
    p_cases.add_argument("--state-fips", metavar="FIPS", help="2-digit FIPS code (e.g. '35')")
    p_cases.add_argument("--outcome", choices=["Alive", "Dead", "Unknown"], metavar="OUTCOME")
    p_cases.add_argument("--year", metavar="YEAR", help="4-digit year or 'Before 1993'")
    p_cases.add_argument("-f", "--format", **_fmt)
    p_cases.set_defaults(func=cmd_hanta_cases)

    p_year = hanta_sub.add_parser("by-year", help="Case counts and deaths by year")
    p_year.add_argument("-f", "--format", **_fmt)
    p_year.set_defaults(func=cmd_hanta_by_year)

    p_state_h = hanta_sub.add_parser("by-state", help="Case counts and deaths by state")
    p_state_h.add_argument("-f", "--format", **_fmt)
    p_state_h.set_defaults(func=cmd_hanta_by_state)

    # ── fluview ────────────────────────────────────────────────────────────────
    p_fluview = sub.add_parser(
        "fluview",
        help="FluView ILINet and WHO/NREVSS clinical lab data (via Delphi Epidata)",
    )
    fluview_sub = p_fluview.add_subparsers(dest="subcommand", required=True)

    # fluview ili
    p_ili = fluview_sub.add_parser("ili", help="ILINet influenza-like illness activity (1997-98–present)")
    ili_sub = p_ili.add_subparsers(dest="ili_subcommand", required=True)

    _region_help = (
        "Region code(s). 'nat' = national, 'hhs1'..'hhs10' = HHS regions, "
        "'cen1'..'cen9' = census regions, or lowercase 2-letter state (e.g. 'ca', 'tx'). "
        "Default: nat"
    )
    _epiweek_help = "Epiweek range YYYYWW e.g. '202001-202526' or single '202001'"

    p_ili_data = ili_sub.add_parser("data", help="Weekly ILI records")
    p_ili_data.add_argument("--region", nargs="+", metavar="REGION", help=_region_help)
    p_ili_data.add_argument("--epiweeks", metavar="RANGE", help=_epiweek_help)
    p_ili_data.add_argument("-f", "--format", **_fmt)
    p_ili_data.set_defaults(func=cmd_fluview_ili_data)

    p_ili_region = ili_sub.add_parser("by-region", help="Peak/avg wILI across nat+HHS+census regions")
    p_ili_region.add_argument("--epiweeks", metavar="RANGE", help=_epiweek_help)
    p_ili_region.add_argument("-f", "--format", **_fmt)
    p_ili_region.set_defaults(func=cmd_fluview_ili_by_region)

    # fluview clinical
    p_clin = fluview_sub.add_parser(
        "clinical",
        help="WHO/NREVSS clinical lab flu test positivity (2016-17–present)",
    )
    clin_sub = p_clin.add_subparsers(dest="clin_subcommand", required=True)

    p_clin_data = clin_sub.add_parser("data", help="Weekly clinical lab records")
    p_clin_data.add_argument("--region", nargs="+", metavar="REGION", help=_region_help)
    p_clin_data.add_argument("--epiweeks", metavar="RANGE", help=_epiweek_help)
    p_clin_data.add_argument("-f", "--format", **_fmt)
    p_clin_data.set_defaults(func=cmd_fluview_clinical_data)

    # ── flusurv ────────────────────────────────────────────────────────────────
    valid_locs = sorted(FLUSURV_LOCATIONS.keys())
    p_flu = sub.add_parser("flusurv", help="FluSurv-NET hospitalization rates (2009-10–present)")
    flu_sub = p_flu.add_subparsers(dest="subcommand", required=True)

    p_flu_data = flu_sub.add_parser("data", help="Weekly hospitalization rate records")
    p_flu_data.add_argument(
        "--location", nargs="+", metavar="LOC",
        help=f"Location code(s). Valid: {', '.join(valid_locs)}. Default: network_all",
    )
    p_flu_data.add_argument("--epiweeks", metavar="RANGE", help=_epiweek_help)
    p_flu_data.add_argument("--season", metavar="SEASON", help="Filter by season e.g. '2019-20'")
    p_flu_data.add_argument("-f", "--format", **_fmt)
    p_flu_data.set_defaults(func=cmd_flusurv_data)

    p_flu_season = flu_sub.add_parser("by-season", help="Peak/avg rates per season for a location")
    p_flu_season.add_argument(
        "--location", metavar="LOC", default="network_all",
        help=f"Location code. Valid: {', '.join(valid_locs)}. Default: network_all",
    )
    p_flu_season.add_argument("-f", "--format", **_fmt)
    p_flu_season.set_defaults(func=cmd_flusurv_by_season)

    p_flu_loc = flu_sub.add_parser("by-location", help="Compare peak/avg rates across all locations")
    p_flu_loc.add_argument("--epiweeks", metavar="RANGE", help="Restrict to an epiweek range")
    p_flu_loc.add_argument("--season", metavar="SEASON", help="Filter by season e.g. '2019-20'")
    p_flu_loc.add_argument("-f", "--format", **_fmt)
    p_flu_loc.set_defaults(func=cmd_flusurv_by_location)

    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
