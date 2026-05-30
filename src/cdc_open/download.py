"""
Bulk-download all CDC Open datasets to data/raw/cdc_open/<key>.csv

Usage:
    uv run python -m cdc_open.download
"""

import os
import sys
import time
from pathlib import Path

import requests

from cdc_open.datasets import DATASETS

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
            resp = _fetch_with_retry(
                f"{_BASE_URL}/{ds.id}.csv",
                params={"$limit": limit},
                headers=headers,
            )
            path = out_dir / f"{key}.csv"
            path.write_text(resp.text)
            row_count = resp.text.count("\n") - 1  # subtract header row
            print(f"{row_count} rows -> {path}")
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
