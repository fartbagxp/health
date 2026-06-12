"""
Bulk-download all CDC Open datasets to data/raw/cdc_open/<key>.csv

Usage:
    uv run python -m cdc_open.download
"""

import csv
import io
import json
import os
import sys
import time
from pathlib import Path

import requests

from cdc_open.datasets import COMPOSITE_DATASETS, DATASETS, WCMS_DATASETS

_BASE_URL = "https://data.cdc.gov/resource"
_DEFAULT_LIMIT = 50_000
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


def download_all(out_dir: Path = _OUT_DIR, limit: int = _DEFAULT_LIMIT) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    ok, failed = 0, []

    headers = {"Accept": "text/csv"}
    app_token = os.environ.get("CDC_DATA_APP_TOKEN")
    if app_token:
        headers["X-App-Token"] = app_token

    for key, ds in DATASETS.items():
        print(f"  fetching {key} ({ds.id}) ...", end=" ", flush=True)
        try:
            params: dict = {"$limit": limit}
            if ds.soql_where:
                params["$where"] = ds.soql_where
            resp = _fetch_with_retry(
                f"{_BASE_URL}/{ds.id}.csv",
                params=params,
                headers=headers,
            )
            path = out_dir / f"{key}.csv"
            path.write_text(resp.text)
            row_count = resp.text.count("\n") - 1  # subtract header row
            print(f"{row_count} rows -> {path}")
            ok += 1
        except Exception as exc:
            failed.append((key, exc))

    for key, ds in COMPOSITE_DATASETS.items():
        print(f"  fetching {key} ({len(ds.sources)} sources) ...", end=" ", flush=True)
        try:
            all_rows: list[dict] = []
            for year, sid in ds.sources:
                resp = _fetch_with_retry(
                    f"https://data.cdc.gov/resource/{sid}.json",
                    params={"$limit": limit},
                    headers={"Accept": "application/json"},
                )
                for row in resp.json():
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
