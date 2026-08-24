"""
EPHT CLI — browse and query CDC's Environmental Public Health Tracking Network.

Usage:
    uv run python -m epht content-areas
    uv run python -m epht measures --search "pm2.5"
    uv run python -m epht measures --search asthma -f table
    uv run python -m epht registry                     # curated archive set
    uv run python -m epht fetch pm25_annual_avg -f csv # one measure, state-level
    EPHT_API_TOKEN=... uv run python -m epht.download   # archive all curated
"""

import argparse
import csv
import io
import json
import sys

from dotenv import load_dotenv

from epht import client
from epht.datasets import MEASURES
from epht.sdk import get_state_series, search_measures

load_dotenv()


def _print(rows: list[dict], fmt: str) -> None:
    if not rows:
        print("No results.")
        return
    if fmt == "json":
        print(json.dumps(rows, indent=2, default=str))
    elif fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        print(buf.getvalue(), end="")
    else:
        cols = list(rows[0].keys())
        widths = {c: max(len(str(c)), max(len(str(r.get(c, ""))) for r in rows)) for c in cols}
        line = "  ".join(str(c).ljust(widths[c]) for c in cols)
        print(line[:160])
        print("-" * min(len(line), 160))
        for r in rows:
            print("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols)[:160])


def main() -> None:
    parser = argparse.ArgumentParser(prog="epht", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("content-areas", help="list EPHT content areas")

    p_meas = sub.add_parser("measures", help="search the ~867 EPHT measures")
    p_meas.add_argument("--search", required=True, help="substring of measure/area/indicator name")
    p_meas.add_argument("-f", "--format", default="table", choices=["table", "csv", "json"])

    sub.add_parser("registry", help="list the curated measures this repo archives")

    p_fetch = sub.add_parser("fetch", help="fetch one measure's state-level series")
    p_fetch.add_argument("key", help="registry key (see `registry`) or a numeric measure ID")
    p_fetch.add_argument("-f", "--format", default="table", choices=["table", "csv", "json"])

    args = parser.parse_args()

    if args.cmd == "content-areas":
        rows = [{"id": c.get("id"), "name": c.get("name")} for c in client.content_areas()]
        _print(sorted(rows, key=lambda r: r["name"] or ""), "table")

    elif args.cmd == "measures":
        hits = search_measures(args.search)
        rows = [
            {
                "measureId": m.get("measureId"),
                "contentArea": m.get("contentAreaName"),
                "indicator": m.get("indicatorName"),
                "measure": m.get("measureName"),
            }
            for m in hits
        ]
        _print(rows, args.format)

    elif args.cmd == "registry":
        rows = [
            {
                "key": m.key,
                "measureId": m.measure_id,
                "contentArea": m.content_area,
                "unit": m.unit,
                "charted": m.charted,
                "name": m.name,
            }
            for m in MEASURES.values()
        ]
        _print(rows, "table")

    elif args.cmd == "fetch":
        if args.key in MEASURES:
            measure_id = MEASURES[args.key].measure_id
        elif args.key.isdigit():
            measure_id = int(args.key)
        else:
            print(f"unknown measure key '{args.key}' (see `epht registry`)", file=sys.stderr)
            sys.exit(2)
        rows = get_state_series(measure_id)
        _print(rows, args.format)


if __name__ == "__main__":
    main()
