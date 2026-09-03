"""
Sync one PLACES release/geography into the public Dolt database.

Usage:
    uv run python -m places.sync --geo county --release 2025
    uv run python -m places.sync --all --release 2025
    uv run python -m places.sync --geo tract --release 2025 --force
    uv run python -m places.sync --family nmf --all      # Non-Medical Factors
    uv run python -m places.sync --family both --all     # all seven portal pages

Order of operations, and why:

  1. Compare Socrata's `rowsUpdatedAt` against release_meta FIRST. PLACES is an
     annual product, so on almost every scheduled run this is where the job
     ends -- for the cost of one metadata request, transferring none of the
     ~1.4GB.
  2. Stream the export to disk, then stream that file into normalized CSVs.
  3. Import dimensions before facts, so a fact row never references a measure
     or location that isn't there yet.
  4. Record release_meta last. It is the marker that the release landed, so it
     must not be written until everything else has succeeded -- a job that dies
     mid-import leaves release_meta untouched and the next run redoes the work.

The Non-Medical Factors family (--family nmf) runs the same four steps against
its own fact table and its own ledger, nmf_release_meta, keyed by ACS period
rather than release year. See places.datasets for why the two cannot share.
"""

import argparse
import csv
import datetime as dt
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

from places.client import PlacesClient
from places.datasets import (
    GEO_LEVELS,
    NMF_PERIOD,
    NmfDataset,
    PlacesDataset,
    dataset,
    nmf_dataset,
)
from places.dolt import DoltError, DoltHubClient
from places.transform import PRIMARY_KEYS, split, split_nmf

RAW_DIR = Path("data/raw/places")
SCHEMA = Path(__file__).parent / "schema.sql"

# Dimensions first -- facts reference them.
IMPORT_ORDER = ["category", "measure", "location", "location_population", "measurement"]
NMF_IMPORT_ORDER = [
    "category",
    "measure",
    "nmf_location",
    "nmf_location_population",
    "nmf_measurement",
]

# These describe the measures themselves, not a geography, so every geography
# ships identical copies -- and both families write them, PLACES contributing
# 40 measures across 6 categories and Non-Medical Factors 9 more under a 7th.
# Only the first sync of a release needs to load them; the merged tables are 49
# and 7 rows, small enough to read back whole and compare.
SHARED_DIMENSIONS = {"category", "measure"}


def _utc(ts: int) -> str:
    return dt.datetime.fromtimestamp(ts, dt.UTC).strftime("%Y-%m-%d %H:%M:%S")


def _parse_dt(value: str) -> dt.datetime | None:
    """Parse a DATETIME as DoltHub renders it.

    Compared as datetimes rather than strings: the API may hand back
    '2025-12-04 10:35:06', an ISO 'T' separator, or a trailing 'Z', and a
    string mismatch here would silently re-download the whole release on every
    run.
    """
    text = (value or "").strip().replace("T", " ").removesuffix("Z").strip()
    if not text:
        return None
    text = text.split(".", 1)[0]  # drop fractional seconds
    try:
        # Socrata's rowsUpdatedAt is UTC and DoltHub stores what we wrote, so
        # both sides are UTC; stamping it here keeps the comparison aware.
        return dt.datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.UTC)
    except ValueError:
        return None


def needs_sync(dolt: DoltHubClient, ds: PlacesDataset, rows_updated_at: int) -> bool:
    """True when CDC has republished since the last successful ingest."""
    if not dolt.table_exists("release_meta"):
        return True
    rows = dolt.sql(
        "select rows_updated_at from release_meta "
        f"where release_year = {ds.release} and geo_level = '{ds.geo_level}' limit 1"
    )
    if not rows:
        return True
    recorded = _parse_dt(str(rows[0]["rows_updated_at"]))
    if recorded is None:
        return True  # unparseable marker -- re-sync rather than skip blindly
    return recorded != _parse_dt(_utc(rows_updated_at))


def sync_one(
    geo_level: str,
    release: int,
    dolt: DoltHubClient,
    client: PlacesClient,
    work_dir: Path,
    force: bool = False,
    keep_raw: bool = False,
) -> bool:
    """Sync one geography. Returns True if anything was imported."""
    ds = dataset(geo_level, release)
    print(f"\n{ds.geo_level} {ds.release} ({ds.socrata_id}) -- {ds.name}")

    updated = client.rows_updated_at(ds.socrata_id)
    print(f"  socrata rowsUpdatedAt: {_utc(updated)}")
    if not force and not needs_sync(dolt, ds, updated):
        print("  up to date, nothing to do")
        return False

    raw = RAW_DIR / f"{ds.geo_level}_{ds.release}.csv"
    if raw.exists():
        print(f"  reusing {raw} ({raw.stat().st_size:,} bytes)")
    else:
        print("  downloading ...", end=" ", flush=True)
        size = client.download(ds.socrata_id, raw)
        print(f"{size:,} bytes")

    out = work_dir / f"{ds.geo_level}_{ds.release}"
    print("  transforming ...", end=" ", flush=True)
    result = split(
        client.read_csv(raw),
        geo_level=ds.geo_level,
        release=ds.release,
        out_dir=out,
        expected_rows=ds.rows,
    )
    print(", ".join(f"{k}={v:,}" for k, v in result.counts.items()))

    print("  schema ...")
    dolt.apply_schema(SCHEMA)

    for table in IMPORT_ORDER:
        path = result.paths[table]
        # Re-importing an unchanged shared dimension is pure waste -- and
        # DoltHub's poll endpoint answers 500 for the resulting no-op job, so
        # it is waste that also breaks the run.
        if table in SHARED_DIMENSIONS and _already_loaded(dolt, table, path):
            print(f"  {table}: unchanged, skipping")
            continue
        print(
            f"  importing {table} ({path.stat().st_size / 1e6:.1f} MB) ...",
            end=" ",
            flush=True,
        )
        # v1alpha1 uploads carry no commit message; DoltHub writes its own.
        chunks = dolt.import_csv(path, table=table, primary_keys=PRIMARY_KEYS[table])
        print(f"ok{f' ({chunks} chunks)' if chunks > 1 else ''}")

    _record_release(dolt, ds, updated, result.counts["measurement"], out)

    # Only now discard the raw export. Deleting it right after the transform
    # saved a few hundred MB of runner disk but cost a full re-download on any
    # later failure -- and 234MB of ZCTA was thrown away exactly that way.
    # Peak usage is raw + transformed (~840MB at tract), which a runner with
    # ~14GB free absorbs comfortably.
    if not keep_raw:
        raw.unlink(missing_ok=True)
    shutil.rmtree(out, ignore_errors=True)
    print(f"  done -- {result.counts['measurement']:,} measurements")
    return True


def _already_loaded(dolt: DoltHubClient, table: str, path: Path) -> bool:
    """True when every row in the CSV is already in `table` with these values.

    A subset test, not an equality test, because `measure` and `category` are
    shared between the PLACES and Non-Medical Factors families: the PLACES CSV
    holds 40 measures, the ACS one holds 9, and the table ends up with 49. An
    equality test would call both of them "changed" forever and fire a no-op
    import on every run -- which DoltHub answers with a 500 on the job poll,
    turning pure waste into a failed sync. Since every import is an upsert,
    "all my rows are already there" is exactly the right skip condition.
    """
    try:
        existing = dolt.sql(f"select * from {table} limit 1000")
    except DoltError:
        return False
    with path.open(newline="") as f:
        wanted = list(csv.DictReader(f))
    if not wanted or len(existing) >= 1000:
        # At the row cap we cannot know what we did not see; re-import instead
        # of skipping on incomplete evidence.
        return False
    columns = sorted(wanted[0])

    def normalize(rows):
        return {tuple((c, str(r.get(c) or "").strip()) for c in columns) for r in rows}

    return normalize(wanted) <= normalize(existing)


def nmf_needs_sync(dolt: DoltHubClient, ds: NmfDataset, rows_updated_at: int) -> bool:
    """True when CDC has republished this ACS period since the last ingest."""
    if not dolt.table_exists("nmf_release_meta"):
        return True
    rows = dolt.sql(
        "select rows_updated_at from nmf_release_meta "
        f"where period = '{ds.period}' and geo_level = '{ds.geo_level}' limit 1"
    )
    if not rows:
        return True
    recorded = _parse_dt(str(rows[0]["rows_updated_at"]))
    if recorded is None:
        return True  # unparseable marker -- re-sync rather than skip blindly
    return recorded != _parse_dt(_utc(rows_updated_at))


def sync_nmf_one(
    geo_level: str,
    period: str,
    dolt: DoltHubClient,
    client: PlacesClient,
    work_dir: Path,
    force: bool = False,
    keep_raw: bool = False,
) -> bool:
    """Sync one Non-Medical Factors geography. Returns True if it imported.

    Deliberately a sibling of sync_one() rather than a parameterization of it.
    The two share a shape but not much else -- different version key (ACS
    period vs release year), different fact table, different ledger -- and the
    conditionals needed to fold them together cost more than the duplication.
    """
    ds = nmf_dataset(geo_level, period)
    print(f"\n[nmf] {ds.geo_level} {ds.period} ({ds.socrata_id}) -- {ds.name}")

    updated = client.rows_updated_at(ds.socrata_id)
    print(f"  socrata rowsUpdatedAt: {_utc(updated)}")
    if not force and not nmf_needs_sync(dolt, ds, updated):
        print("  up to date, nothing to do")
        return False

    raw = RAW_DIR / f"nmf_{ds.geo_level}_{ds.period}.csv"
    if raw.exists():
        print(f"  reusing {raw} ({raw.stat().st_size:,} bytes)")
    else:
        print("  downloading ...", end=" ", flush=True)
        size = client.download(ds.socrata_id, raw)
        print(f"{size:,} bytes")

    out = work_dir / f"nmf_{ds.geo_level}_{ds.period}"
    print("  transforming ...", end=" ", flush=True)
    result = split_nmf(
        client.read_csv(raw),
        geo_level=ds.geo_level,
        period=ds.period,
        out_dir=out,
        expected_rows=ds.rows,
    )
    print(", ".join(f"{k}={v:,}" for k, v in result.counts.items()))

    print("  schema ...")
    dolt.apply_schema(SCHEMA)

    for table in NMF_IMPORT_ORDER:
        path = result.paths[table]
        if table in SHARED_DIMENSIONS and _already_loaded(dolt, table, path):
            print(f"  {table}: unchanged, skipping")
            continue
        print(
            f"  importing {table} ({path.stat().st_size / 1e6:.1f} MB) ...",
            end=" ",
            flush=True,
        )
        chunks = dolt.import_csv(path, table=table, primary_keys=PRIMARY_KEYS[table])
        print(f"ok{f' ({chunks} chunks)' if chunks > 1 else ''}")

    _record_nmf_release(dolt, ds, updated, result.counts["nmf_measurement"], out)

    if not keep_raw:
        raw.unlink(missing_ok=True)
    shutil.rmtree(out, ignore_errors=True)
    print(f"  done -- {result.counts['nmf_measurement']:,} measurements")
    return True


def _record_nmf_release(
    dolt: DoltHubClient, ds: NmfDataset, updated: int, row_count: int, out: Path
) -> None:
    """Write the nmf_release_meta marker. Last step, deliberately."""
    path = out / "nmf_release_meta.csv"
    now = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M:%S")
    path.write_text(
        "period,geo_level,socrata_id,rows_updated_at,row_count,ingested_at\n"
        f"{ds.period},{ds.geo_level},{ds.socrata_id},{_utc(updated)},{row_count},{now}\n"
    )
    print("  recording nmf_release_meta ...", end=" ", flush=True)
    dolt.import_csv(
        path, table="nmf_release_meta", primary_keys=PRIMARY_KEYS["nmf_release_meta"]
    )
    print("ok")


def _record_release(
    dolt: DoltHubClient, ds: PlacesDataset, updated: int, row_count: int, out: Path
) -> None:
    """Write the release_meta marker. Last step, deliberately."""
    path = out / "release_meta.csv"
    now = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M:%S")
    path.write_text(
        "release_year,geo_level,socrata_id,rows_updated_at,row_count,ingested_at\n"
        f"{ds.release},{ds.geo_level},{ds.socrata_id},{_utc(updated)},{row_count},{now}\n"
    )
    print("  recording release_meta ...", end=" ", flush=True)
    dolt.import_csv(
        path, table="release_meta", primary_keys=PRIMARY_KEYS["release_meta"]
    )
    print("ok")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Sync CDC PLACES into DoltHub")
    parser.add_argument("--geo", choices=GEO_LEVELS, help="geography to sync")
    parser.add_argument("--all", action="store_true", help="sync every geography")
    parser.add_argument(
        "--family",
        choices=("places", "nmf", "both"),
        default="places",
        help="places = the 6 BRFSS categories; nmf = Non-Medical Factors (ACS)",
    )
    parser.add_argument("--release", type=int, default=2025, help="PLACES release year")
    parser.add_argument(
        "--period", default=NMF_PERIOD, help="ACS period for --family nmf"
    )
    parser.add_argument("--force", action="store_true", help="ignore release_meta")
    parser.add_argument("--keep-raw", action="store_true", help="keep the raw export")
    parser.add_argument("--work-dir", type=Path, default=Path("data/raw/places/_work"))
    args = parser.parse_args()

    if not args.geo and not args.all:
        parser.error("pass --geo <level> or --all")

    geos = list(GEO_LEVELS) if args.all else [args.geo]
    families = ("places", "nmf") if args.family == "both" else (args.family,)
    # Every unit of work up front, so one failure can be recorded and skipped
    # rather than ending the run.
    jobs = [(family, geo) for family in families for geo in geos]
    dolt = DoltHubClient()
    try:
        # Both up front: there is no point downloading 694MB to discover the
        # credential is the wrong kind at the upload step.
        dolt.check_database()
        dolt.check_token()
    except DoltError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        sys.exit(1)

    client = PlacesClient(os.environ.get("CDC_DATA_APP_TOKEN"))
    failed: list[tuple[str, Exception]] = []
    changed = 0
    for family, geo in jobs:
        label = geo if family == "places" else f"nmf/{geo}"
        try:
            if family == "places":
                did = sync_one(
                    geo,
                    args.release,
                    dolt,
                    client,
                    args.work_dir,
                    force=args.force,
                    keep_raw=args.keep_raw,
                )
            else:
                did = sync_nmf_one(
                    geo,
                    args.period,
                    dolt,
                    client,
                    args.work_dir,
                    force=args.force,
                    keep_raw=args.keep_raw,
                )
            if did:
                changed += 1
        # Deliberately blanket: one geography failing for any reason at all
        # must not sink the other seven. Every failure is collected and
        # re-reported, and the run exits non-zero, so nothing is hidden.
        except Exception as exc:  # noqa: BLE001
            failed.append((label, exc))
            print(f"  FAILED: {exc}", file=sys.stderr)

    print(f"\nDone: {changed} synced, {len(failed)} failed.")
    if failed:
        for label, exc in failed:
            print(f"  FAILED {label}: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
