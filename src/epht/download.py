"""
Archive curated EPHT measures as small state-level CSVs under data/raw/epht/.

Each registered measure is fetched at the plain State stratification level (one
row per state per year) and written as CSV. A hard size guard skips any file
that would exceed the archive cap so an unexpectedly large measure can never
land a big blob in the repo.

Requires EPHT_API_TOKEN for reliable runs -- the API rate-limits unauthenticated
requests with HTTP 429 (get a free key at https://ephtracking.cdc.gov/apihelp).

Usage:
    EPHT_API_TOKEN=... uv run python -m epht.download
"""

from __future__ import annotations

import csv
import io
import os
import sys
from pathlib import Path

from epht.datasets import MEASURES
from epht.sdk import get_state_series

_OUT_DIR = Path("data/raw/epht")
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB archive cap


def _records_to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    seen: dict[str, None] = {}
    for row in rows:
        seen.update(dict.fromkeys(row.keys()))
    out = io.StringIO()
    writer = csv.DictWriter(
        out, fieldnames=list(seen), extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def download_all(out_dir: Path = _OUT_DIR) -> None:
    if not os.environ.get("EPHT_API_TOKEN"):
        print(
            "  note: EPHT_API_TOKEN not set -- the API will rate-limit "
            "unauthenticated requests (HTTP 429).",
            file=sys.stderr,
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    ok, skipped, failed = 0, [], []

    for key, m in MEASURES.items():
        print(f"  fetching {key} (measure {m.measure_id}) ...", end=" ", flush=True)
        try:
            rows = get_state_series(m.measure_id)
            csv_text = _records_to_csv(rows)
            size = len(csv_text.encode())
            if size > _MAX_BYTES:
                print(f"SKIP -- {size/1048576:.1f}MB over {_MAX_BYTES/1048576:.0f}MB cap")
                skipped.append((key, size))
                continue
            if not rows:
                print("0 rows (nothing written)")
                failed.append((key, "no data returned"))
                continue
            path = out_dir / f"{key}.csv"
            path.write_text(csv_text)
            print(f"{len(rows)} rows, {size/1024:.0f}KB -> {path}")
            ok += 1
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: {exc}")
            failed.append((key, exc))

    print(f"\nDone: {ok} ok, {len(skipped)} skipped (too big), {len(failed)} failed.")
    for key, size in skipped:
        print(f"  SKIPPED {key}: {size/1048576:.1f}MB", file=sys.stderr)
    if failed:
        for key, exc in failed:
            print(f"  FAILED {key}: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    download_all()
