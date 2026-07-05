"""
SEER CLI — query NCI SEER cancer incidence/mortality statistics.

Usage:
    uv run python -m seer sites
    uv run python -m seer sites --search breast
    uv run python -m seer mortality --site 55 --sex female -f csv
    uv run python -m seer mortality --site 47 --compare-by race -f csv
    uv run python -m seer incidence --site 55 --stage 104 -f csv
    uv run python -m seer by-age --site 1 -f csv
    uv run python -m seer compare-sites 55 47 66 -f csv
"""

import argparse
import csv
import io
import json
import sys

from dotenv import load_dotenv

from seer.catalog import AGE_RANGE, RACE, STAGE
from seer.sdk import (
    compare_sites_mortality,
    get_incidence_trend,
    get_mortality_by_age,
    get_mortality_trend,
    list_cancer_sites,
    search_cancer_sites,
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
        sep = "-" * min(len(header), 140)
        print(header[:140])
        print(sep)
        for r in rows:
            line = "  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols)
            print(line[:140])


def cmd_sites(args):
    sites = search_cancer_sites(args.search) if args.search else list_cancer_sites()
    for s in sites:
        print(f"{s['code']:>6}  {s['name']}")


def cmd_mortality(args):
    rows = get_mortality_trend(
        site=args.site,
        sex=args.sex,
        race=args.race,
        age_range=args.age_range,
        compare_by=args.compare_by,
        long_term=args.long_term,
    )
    _print_output(rows, args.format)


def cmd_incidence(args):
    rows = get_incidence_trend(
        site=args.site,
        sex=args.sex,
        race=args.race,
        age_range=args.age_range,
        stage=args.stage,
        compare_by=args.compare_by,
        long_term=args.long_term,
    )
    _print_output(rows, args.format)


def cmd_by_age(args):
    rows = get_mortality_by_age(
        site=args.site,
        sex=args.sex,
        race=args.race,
        compare_by=args.compare_by,
    )
    _print_output(rows, args.format)


def cmd_compare_sites(args):
    rows = compare_sites_mortality(
        sites=args.sites,
        sex=args.sex,
        race=args.race,
        age_range=args.age_range,
    )
    _print_output(rows, args.format)


def main():
    parser = argparse.ArgumentParser(
        prog="seer",
        description="Query NCI SEER cancer incidence/mortality statistics",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    _fmt = dict(choices=["table", "json", "csv"], default="table")
    _sex = dict(choices=["both", "male", "female"], default="both")
    _race = dict(choices=sorted(RACE), default="1", metavar="RACE_CODE")
    _age = dict(choices=sorted(AGE_RANGE), default="1", metavar="AGE_RANGE_CODE")
    _compare_by = dict(
        choices=["sex", "race", "age_range"], default=None, metavar="FIELD"
    )

    p_sites = sub.add_parser("sites", help="List/search the cancer site catalog")
    p_sites.add_argument(
        "--search", metavar="TEXT", help="Substring search e.g. 'breast'"
    )
    p_sites.set_defaults(func=cmd_sites)

    p_mort = sub.add_parser(
        "mortality", help="U.S. mortality rate/count by year for a cancer site"
    )
    p_mort.add_argument("--site", required=True, type=int, metavar="CODE")
    p_mort.add_argument("--sex", **_sex)
    p_mort.add_argument("--race", **_race)
    p_mort.add_argument("--age-range", dest="age_range", **_age)
    p_mort.add_argument("--compare-by", dest="compare_by", **_compare_by)
    p_mort.add_argument(
        "--long-term", action="store_true", help="1975-present instead of 2000-present"
    )
    p_mort.add_argument("-f", "--format", **_fmt)
    p_mort.set_defaults(func=cmd_mortality)

    p_inc = sub.add_parser(
        "incidence", help="SEER incidence rate/count by year for a cancer site"
    )
    p_inc.add_argument("--site", required=True, type=int, metavar="CODE")
    p_inc.add_argument("--sex", **_sex)
    p_inc.add_argument("--race", **_race)
    p_inc.add_argument("--age-range", dest="age_range", **_age)
    p_inc.add_argument(
        "--stage", choices=sorted(STAGE), default="101", metavar="STAGE_CODE"
    )
    p_inc.add_argument("--compare-by", dest="compare_by", **_compare_by)
    p_inc.add_argument(
        "--long-term", action="store_true", help="1975-present instead of 2000-present"
    )
    p_inc.add_argument("-f", "--format", **_fmt)
    p_inc.set_defaults(func=cmd_incidence)

    p_age = sub.add_parser(
        "by-age", help="U.S. mortality rate/count by age group for a cancer site"
    )
    p_age.add_argument("--site", required=True, type=int, metavar="CODE")
    p_age.add_argument("--sex", **_sex)
    p_age.add_argument("--race", **_race)
    p_age.add_argument(
        "--compare-by", dest="compare_by", choices=["sex", "race"], default=None
    )
    p_age.add_argument("-f", "--format", **_fmt)
    p_age.set_defaults(func=cmd_by_age)

    p_cmp = sub.add_parser(
        "compare-sites", help="Compare U.S. mortality trends across cancer sites"
    )
    p_cmp.add_argument("sites", type=int, nargs="+", metavar="CODE")
    p_cmp.add_argument("--sex", **_sex)
    p_cmp.add_argument("--race", **_race)
    p_cmp.add_argument("--age-range", dest="age_range", **_age)
    p_cmp.add_argument("-f", "--format", **_fmt)
    p_cmp.set_defaults(func=cmd_compare_sites)

    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
