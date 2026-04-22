"""
Bulk-download all CDC Open datasets to data/raw/cdc_open/<key>.csv

Usage:
    uv run python -m cdc_open.download
"""

import os
import sys
from pathlib import Path

import requests

from cdc_open.datasets import DATASETS

_BASE_URL = "https://data.cdc.gov/resource"
_DEFAULT_LIMIT = 50_000
_OUT_DIR = Path("data/raw/cdc_open")


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
            resp = requests.get(
                f"{_BASE_URL}/{ds.id}.csv",
                params={"$limit": limit},
                headers=headers,
                timeout=60,
            )
            resp.raise_for_status()
            path = out_dir / f"{key}.csv"
            path.write_text(resp.text)
            row_count = resp.text.count("\n") - 1  # subtract header row
            print(f"{row_count} rows -> {path}")
            ok += 1
        except Exception as exc:
            print(f"ERROR: {exc}")
            failed.append((key, exc))

    print(f"\nDone: {ok} succeeded, {len(failed)} failed.")
    if failed:
        for key, exc in failed:
            print(f"  FAILED {key}: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    download_all()
