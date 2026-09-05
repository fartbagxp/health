"""Reusable on-disk cache for the immutable "final" half of a WONDER fetch.

CDC WONDER's final datasets (e.g. D77, 1999–2020) never change, so re-querying
them on every run only wastes time and re-exposes the historical data to loss
when a query is rate-limited (HTTP 429). These helpers persist the final records
once and read them back, so later runs merge the cached snapshot with a freshly
fetched provisional tail instead of hitting WONDER again.

The cache stores raw fetch records — the same dicts a fetcher's merge() consumes
— one per row, with light type coercion on read so booleans and nullable numbers
round-trip. Each fetcher declares its own columns and per-column types.
"""
from __future__ import annotations

import csv
from pathlib import Path


def write_final_cache(records: list[dict], path: Path, fieldnames: list[str]) -> None:
    """Write ``records`` (already filtered to the final years) to ``path``.

    ``None`` becomes an empty cell and booleans become ``true``/``false`` so the
    file matches the fetchers' own CSV conventions.
    """
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            row = {}
            for k in fieldnames:
                v = rec.get(k)
                if isinstance(v, bool):
                    v = str(v).lower()
                elif v is None:
                    v = ""
                row[k] = v
            writer.writerow(row)


def read_final_cache(
    path: Path,
    *,
    int_fields: tuple[str, ...] = (),
    nullable_int_fields: tuple[str, ...] = (),
    nullable_float_fields: tuple[str, ...] = (),
    bool_fields: tuple[str, ...] = (),
) -> list[dict]:
    """Read a cache written by :func:`write_final_cache` back into typed records.

    Any column not named in a ``*_fields`` argument is left as a string.
    """
    records: list[dict] = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            rec: dict = dict(row)
            for k in int_fields:
                rec[k] = int(rec[k])
            for k in nullable_int_fields:
                s = (rec[k] or "").strip()
                rec[k] = None if s == "" else int(s)
            for k in nullable_float_fields:
                s = (rec[k] or "").strip()
                rec[k] = None if s == "" else float(s)
            for k in bool_fields:
                rec[k] = (rec[k] or "").strip().lower() == "true"
            records.append(rec)
    return records
