"""
CDC PLACES CLI

PLACES publishes model-based estimates of 40 health measures for every county,
place, census tract and ZCTA in the country, plus 9 more ACS-derived
non-medical factors -- together the seven pages of CDC's PLACES portal. That is
~7.9M rows / ~1.7GB, far too large for this repository, so it is mirrored into
the public Dolt database fartbagxp/cdc-places and only small derived slices are
committed under data/processed/places/.

Usage:
    # What is registered, and whether CDC has published newer data
    uv run python -m places list
    uv run python -m places status

    # Mirror into Dolt (needs DOLTHUB_TOKEN)
    uv run python -m places sync --geo county
    uv run python -m places sync --all
    uv run python -m places sync --all --family both   # all seven portal pages

    # Rebuild the committed CSVs health-charts reads
    uv run python -m places derive

    # Query the published database (no credentials needed -- it is public)
    uv run python -m places query "select count(*) from measurement" -f json
"""

import argparse
import csv
import io
import json
import os
import sys

from dotenv import load_dotenv

from places.datasets import (
    GEO_LEVELS,
    NMF_DATASETS,
    NMF_PERIOD,
    PLACES_DATASETS,
    releases,
)

load_dotenv()


# ─── Commands ─────────────────────────────────────────────────────────────────


def cmd_list(args):
    rows = [
        {
            "key": key,
            "family": "places",
            "socrata_id": d.socrata_id,
            "geo_level": d.geo_level,
            "version": str(d.release),
            "rows": d.rows,
            "value_types": ",".join(d.value_types),
            "name": d.name,
        }
        for key, d in PLACES_DATASETS.items()
    ] + [
        {
            "key": key,
            "family": "nmf",
            "socrata_id": d.socrata_id,
            "geo_level": d.geo_level,
            "version": d.period,
            "rows": d.rows,
            "value_types": "Percent",
            "name": d.name,
        }
        for key, d in NMF_DATASETS.items()
    ]
    if args.format == "json":
        print(json.dumps(rows, indent=2))
        return
    print(
        f"{'KEY':<20} {'FAMILY':<7} {'ID':<12} {'GEO':<8} "
        f"{'VERSION':<10} {'ROWS':>11}  VALUE TYPES"
    )
    print("-" * 88)
    for r in rows:
        print(
            f"{r['key']:<20} {r['family']:<7} {r['socrata_id']:<12} "
            f"{r['geo_level']:<8} {r['version']:<10} {r['rows']:>11,}  "
            f"{r['value_types']}"
        )
    total = sum(r["rows"] for r in rows)
    print(
        f"\n{len(rows)} dataset(s), {total:,} rows. "
        f"PLACES release(s): {', '.join(map(str, releases()))}; "
        f"ACS period: {NMF_PERIOD}"
    )


def cmd_status(args):
    """Compare Socrata's rowsUpdatedAt against what Dolt has ingested."""
    from places.client import PlacesClient
    from places.dolt import DoltError, DoltHubClient
    from places.sync import _utc

    client = PlacesClient()
    dolt = DoltHubClient()
    # (version, geo_level) -> rows_updated_at, per family. The two ledgers are
    # separate tables: PLACES versions by release year, Non-Medical Factors by
    # ACS period.
    recorded: dict[str, dict[tuple[str, str], str]] = {"places": {}, "nmf": {}}
    for family, table, version_column in (
        ("places", "release_meta", "release_year"),
        ("nmf", "nmf_release_meta", "period"),
    ):
        try:
            if not dolt.table_exists(table):
                continue
            for row in dolt.sql(
                f"select {version_column}, geo_level, rows_updated_at "
                f"from {table} order by {version_column}, geo_level limit 1000"
            ):
                key = (str(row[version_column]), row["geo_level"])
                recorded[family][key] = row["rows_updated_at"]
        except DoltError as exc:
            print(f"(dolt unavailable for {table}: {exc})", file=sys.stderr)

    registry = [
        ("places", key, d.socrata_id, str(d.release), d.geo_level)
        for key, d in PLACES_DATASETS.items()
    ] + [
        ("nmf", key, d.socrata_id, d.period, d.geo_level)
        for key, d in NMF_DATASETS.items()
    ]

    rows = []
    for family, key, socrata_id, version, geo_level in registry:
        upstream = _utc(client.rows_updated_at(socrata_id))
        have = recorded[family].get((version, geo_level), "")
        rows.append(
            {
                "key": key,
                "family": family,
                "socrata_updated": upstream,
                "dolt_ingested": have or "-",
                "state": "ok" if have and have.startswith(upstream[:10]) else "stale",
            }
        )

    if args.format == "json":
        print(json.dumps(rows, indent=2))
        return
    print(f"{'KEY':<20} {'FAMILY':<7} {'SOCRATA UPDATED':<21} {'DOLT HAS':<21} STATE")
    print("-" * 78)
    for r in rows:
        print(
            f"{r['key']:<20} {r['family']:<7} {r['socrata_updated']:<21} "
            f"{r['dolt_ingested']:<21} {r['state']}"
        )


def cmd_doctor(args):
    """Check the pieces sync needs, and say precisely what is wrong."""
    from places.client import PlacesClient
    from places.dolt import DoltError, DoltHubClient

    ok = True

    token = os.environ.get("CDC_DATA_APP_TOKEN")
    print(
        f"[{'ok' if token else '--'}] CDC_DATA_APP_TOKEN  "
        f"{'set' if token else 'unset (optional; raises rate limits)'}"
    )

    try:
        PlacesClient().rows_updated_at(PLACES_DATASETS["county_2025"].socrata_id)
        print("[ok] data.cdc.gov         reachable")
    # A doctor command that crashes tells you nothing. Any failure whatsoever
    # is a finding to print beside the other checks, not an exception to raise.
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"[XX] data.cdc.gov         {exc}")

    dolt = DoltHubClient()
    label = f"{dolt.owner}/{dolt.database}"
    try:
        db = dolt.check_database()
        if db["empty"]:
            state = "empty, no commits yet"
        else:
            tables = dolt.sql("show tables")
            state = f"{len(tables)} table(s)" if tables else "no tables yet"
        print(f"[ok] {label}   exists ({state})")
    except DoltError as exc:
        ok = False
        print(f"[XX] {label}   {exc}")

    try:
        scope = dolt.check_token()
        branches = ", ".join(scope["branches"]) or "no branches yet"
        print(
            f"[ok] DOLTHUB_TOKEN        valid, writes to {scope['scope']} ({branches})"
        )
    except DoltError as exc:
        ok = False
        for i, line in enumerate(str(exc).splitlines()):
            prefix = "[XX] DOLTHUB_TOKEN        " if i == 0 else "     "
            print(f"{prefix}{line.strip()}")

    print("\nReady to sync." if ok else "\nNot ready -- fix the [XX] items above.")
    sys.exit(0 if ok else 1)


def cmd_sync(args):
    from places.sync import main as sync_main

    argv = [
        "--release",
        str(args.release),
        "--period",
        args.period,
        "--family",
        args.family,
    ]
    if args.all:
        argv.append("--all")
    else:
        argv += ["--geo", args.geo]
    if args.force:
        argv.append("--force")
    sys.argv = ["places.sync", *argv]
    sync_main()


def cmd_derive(args):
    from places.derive import derive

    derive(args.release, period=args.period)


def cmd_query(args):
    from places.dolt import DoltError, DoltHubClient

    try:
        rows = DoltHubClient().sql(args.sql)
    except DoltError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    if not rows:
        print("No results found.", file=sys.stderr)
        return
    _print(rows, args.format)


# ─── Output ───────────────────────────────────────────────────────────────────


def _print(rows: list[dict], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(rows, indent=2))
        return
    columns = list(rows[0])
    if fmt == "csv":
        out = io.StringIO()
        writer = csv.DictWriter(
            out, fieldnames=columns, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
        print(out.getvalue(), end="")
        return
    widths = {
        c: max(len(c), max(len(str(r.get(c, ""))) for r in rows)) for c in columns
    }
    print("  ".join(c.ljust(widths[c]) for c in columns))
    print("  ".join("-" * widths[c] for c in columns))
    for r in rows:
        print("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in columns))


# ─── Entry point ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="places", description="CDC PLACES -- mirror to Dolt, slice for charts"
    )
    parser.add_argument(
        "-f", "--format", choices=["table", "csv", "json"], default="table"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="show the dataset registry").set_defaults(func=cmd_list)
    sub.add_parser("status", help="compare Socrata against Dolt").set_defaults(
        func=cmd_status
    )
    sub.add_parser("doctor", help="check credentials and connectivity").set_defaults(
        func=cmd_doctor
    )

    p = sub.add_parser("sync", help="mirror a release into DoltHub")
    p.add_argument("--geo", choices=GEO_LEVELS)
    p.add_argument("--all", action="store_true")
    p.add_argument(
        "--family",
        choices=("places", "nmf", "both"),
        default="places",
        help="places = the 6 BRFSS categories; nmf = Non-Medical Factors (ACS)",
    )
    p.add_argument("--release", type=int, default=2025)
    p.add_argument("--period", default=NMF_PERIOD)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("derive", help="rebuild the committed CSV slices")
    p.add_argument("--release", type=int, default=2025)
    p.add_argument("--period", default=NMF_PERIOD)
    p.set_defaults(func=cmd_derive)

    p = sub.add_parser("query", help="run SQL against the public Dolt database")
    p.add_argument("sql")
    p.set_defaults(func=cmd_query)

    args = parser.parse_args()
    if args.command == "sync" and not args.geo and not args.all:
        parser.error("sync: pass --geo <level> or --all")
    args.func(args)


if __name__ == "__main__":
    main()
