"""
Bulk-download all CDC Open datasets to data/raw/cdc_open/<key>.csv

Usage:
    uv run python -m cdc_open.download
"""

import csv
import io
import os
import sys
import time
from pathlib import Path

import requests

from cdc_open.datasets import COMPOSITE_DATASETS, DATASETS, WCMS_DATASETS

_BASE_URL = "https://data.cdc.gov/resource"
# Socrata caps a single response, so we page through with $offset instead of
# requesting one giant page. Datasets larger than this were previously being
# silently truncated to the first _PAGE_SIZE rows.
_PAGE_SIZE = 50_000
_OUT_DIR = Path("data/raw/cdc_open")
_TIMEOUT = 120
_MAX_RETRIES = 3
_RETRY_BACKOFF = [10, 30]  # seconds to wait before retry 2 and 3


def _fetch_with_retry(url: str, params: dict, headers: dict) -> requests.Response:
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        if attempt > 0:
            wait = _RETRY_BACKOFF[attempt - 1]
            print(
                f"retry {attempt}/{_MAX_RETRIES - 1} (waiting {wait}s) ...",
                end=" ",
                flush=True,
            )
            time.sleep(wait)
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=_TIMEOUT)
            resp.raise_for_status()
            return resp
        except Exception as exc:
            last_exc = exc
            print(f"ERROR: {exc}")
    raise last_exc


def _count_csv_rows(text: str) -> int:
    """Count data rows (excluding header) in CSV text, honoring quoted newlines."""
    reader = csv.reader(io.StringIO(text))
    n = sum(1 for _ in reader)
    return max(n - 1, 0)


def _fetch_csv_paginated(
    url: str, base_params: dict, headers: dict, page_size: int = _PAGE_SIZE
) -> tuple[str, int]:
    """Page through a Socrata CSV endpoint until exhausted, preserving CDC's
    exact column order and formatting. Only the first page keeps its header."""
    parts: list[str] = []
    total = 0
    offset = 0
    while True:
        params = {**base_params, "$order": ":id", "$limit": page_size, "$offset": offset}
        resp = _fetch_with_retry(url, params=params, headers=headers)
        text = resp.text
        page_rows = _count_csv_rows(text)
        if offset == 0:
            parts.append(text)
        elif page_rows:
            # Drop the header line repeated on every page (no embedded newline).
            newline = text.find("\n")
            parts.append(text[newline + 1 :] if newline != -1 else "")
        total += page_rows
        if page_rows < page_size:
            break
        offset += page_size
    return "".join(parts), total


def _fetch_json_paginated(
    url: str, base_params: dict, headers: dict, page_size: int = _PAGE_SIZE
) -> list[dict]:
    """Page through a Socrata JSON endpoint until exhausted."""
    rows: list[dict] = []
    offset = 0
    while True:
        params = {**base_params, "$order": ":id", "$limit": page_size, "$offset": offset}
        resp = _fetch_with_retry(url, params=params, headers=headers)
        page = resp.json()
        rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return rows


def _json_to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    # Union of all keys in insertion order, preserving first-seen order
    seen: dict[str, None] = {}
    for row in rows:
        seen.update(dict.fromkeys(row.keys()))
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(seen), extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def download_all(out_dir: Path = _OUT_DIR, page_size: int = _PAGE_SIZE) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    ok, failed = 0, []

    headers = {"Accept": "text/csv"}
    app_token = os.environ.get("CDC_DATA_APP_TOKEN")
    if app_token:
        headers["X-App-Token"] = app_token

    for key, ds in DATASETS.items():
        if not ds.enabled:
            print(f"  skipping {key} ({ds.id}) -- disabled, see datasets.py")
            continue
        print(f"  fetching {key} ({ds.id}) ...", end=" ", flush=True)
        try:
            base_params: dict = {}
            if ds.soql_where:
                base_params["$where"] = ds.soql_where
            base = ds.base_url or _BASE_URL
            csv_text, row_count = _fetch_csv_paginated(
                f"{base}/{ds.id}.csv",
                base_params=base_params,
                headers=headers,
                page_size=page_size,
            )
            path = out_dir / f"{key}.csv"
            path.write_text(csv_text)
            print(f"{row_count} rows -> {path}")
            ok += 1
        except Exception as exc:
            failed.append((key, exc))

    for key, ds in COMPOSITE_DATASETS.items():
        print(f"  fetching {key} ({len(ds.sources)} sources) ...", end=" ", flush=True)
        try:
            all_rows: list[dict] = []
            for year, sid in ds.sources:
                page = _fetch_json_paginated(
                    f"https://data.cdc.gov/resource/{sid}.json",
                    base_params={},
                    headers={"Accept": "application/json"},
                    page_size=page_size,
                )
                for row in page:
                    row = {"year": year, **row}
                    # Normalize geography column: area → state
                    if "area" in row and "state" not in row:
                        row["state"] = row.pop("area")
                    elif "area" in row:
                        row.setdefault("state", row.pop("area"))
                    # Normalize life expectancy column: le → leb
                    if "le" in row and not row.get("leb"):
                        row["leb"] = row.pop("le")
                    elif "le" in row:
                        row.pop("le")
                    all_rows.append(row)
            csv_text = _json_to_csv(all_rows)
            path = out_dir / f"{key}.csv"
            path.write_text(csv_text)
            print(f"{len(all_rows)} rows -> {path}")
            ok += 1
        except Exception as exc:
            failed.append((key, exc))

    for key, ds in WCMS_DATASETS.items():
        print(f"  fetching {key} (wcms) ...", end=" ", flush=True)
        try:
            resp = _fetch_with_retry(ds.url, params={}, headers={"Accept": "application/json"})
            rows = resp.json()
            csv_text = _json_to_csv(rows)
            path = out_dir / f"{key}.csv"
            path.write_text(csv_text)
            print(f"{len(rows)} rows -> {path}")
            ok += 1
        except Exception as exc:
            failed.append((key, exc))

    print(f"\nDone: {ok} succeeded, {len(failed)} failed.")
    if failed:
        for key, exc in failed:
            print(f"  FAILED {key}: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    download_all()
