"""
Bulk-download all CDC Open datasets to data/raw/cdc_open/<key>.json

Usage:
    uv run python -m cdc_open.download
"""

import json
import sys
from pathlib import Path

from cdc_open.datasets import DATASETS
from cdc_open.sdk import query_dataset

# Large enough to capture full datasets; PLACES county/city are the biggest (~3k–5k rows)
_DEFAULT_LIMIT = 50_000
_OUT_DIR = Path("data/raw/cdc_open")


def download_all(out_dir: Path = _OUT_DIR, limit: int = _DEFAULT_LIMIT) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    ok, failed = 0, []

    for key, ds in DATASETS.items():
        print(f"  fetching {key} ({ds.id}) ...", end=" ", flush=True)
        try:
            rows = query_dataset(ds.id, limit=limit)
            path = out_dir / f"{key}.json"
            path.write_text(json.dumps(rows, indent=2))
            print(f"{len(rows)} rows -> {path}")
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
