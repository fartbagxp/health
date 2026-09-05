"""Shared guard against silent truncation in multi-query WONDER fetchers.

Several fetchers assemble one CSV by merging results from multiple CDC WONDER
datasets that each cover a different span of years (e.g. D77 for 1999–2020 plus
D176 for 2021+). When one of those queries fails — most commonly a WONDER
HTTP 429 rate-limit, which ``run_query()`` swallows into an empty list — a naive
"abort only if *everything* came back empty" check lets the run write a merged
CSV that is silently missing an entire era of data.

``require_complete()`` turns that partial failure into a hard, loud abort:
every source that is supposed to contribute rows must actually contribute rows
(and, optionally, reach an expected year) or the process exits non-zero without
writing anything.
"""
from __future__ import annotations

import sys


def require_complete(*sources: tuple) -> None:
    """Abort (exit 1) unless every source contributed the data it should.

    Each source is a tuple:
        (label, records)                     – ``records`` must be non-empty
        (label, records, must_include_year)  – …and must include that year

    ``records`` are dicts carrying an integer ``"year"`` key. Call this AFTER
    all queries have run and BEFORE writing any output.
    """
    problems: list[str] = []
    for spec in sources:
        label, records = spec[0], spec[1]
        must_year = spec[2] if len(spec) > 2 else None
        if not records:
            problems.append(f"{label} returned 0 rows")
            continue
        if must_year is not None:
            years = {r["year"] for r in records}
            if must_year not in years:
                problems.append(
                    f"{label} is missing year {must_year} "
                    f"(got {min(years)}–{max(years)})"
                )
    if problems:
        print(
            "\nAborting — incomplete fetch, refusing to write truncated data:",
            file=sys.stderr,
        )
        for p in problems:
            print(f"  • {p}", file=sys.stderr)
        print(
            "CDC WONDER rate-limits with HTTP 429; wait a minute and re-run.",
            file=sys.stderr,
        )
        sys.exit(1)
