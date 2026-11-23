"""
Persist FluView WHO/NREVSS clinical-lab influenza percent positive as a CSV
for health-charts.

Pulls weekly specimen and positive counts from the CMU Delphi Epidata API for
the nation and the nine Census divisions, then sums divisions into the four
Census regions. Percent positive is recomputed from the summed counts
(positives / specimens) rather than averaging division percentages, so a
small division can't skew its region.

Output: data/processed/grasp/flu_percent_positive.csv
    week_end, region, total_specimens, total_positive, percent_positive

    uv run python -m grasp.export
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from grasp.client import fluview_clinical_fetch

_OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "processed" / "grasp"

# Delphi fluview_clinical starts with the 2016-17 season.
_START_EPIWEEK = 201640

# Census divisions (Delphi cen1..cen9) → Census regions.
DIVISION_REGION = {
    "cen1": "Northeast",  # New England
    "cen2": "Northeast",  # Middle Atlantic
    "cen3": "Midwest",  # East North Central
    "cen4": "Midwest",  # West North Central
    "cen5": "South",  # South Atlantic
    "cen6": "South",  # East South Central
    "cen7": "South",  # West South Central
    "cen8": "West",  # Mountain
    "cen9": "West",  # Pacific
}


def mmwr_week_end(epiweek: int) -> date:
    """Saturday ending MMWR week YYYYWW. Week 1 is the first Sun–Sat week
    with at least four days in the year, i.e. the one containing Jan 4."""
    year, week = divmod(epiweek, 100)
    jan4 = date(year, 1, 4)
    week1_start = jan4 - timedelta(days=(jan4.weekday() + 1) % 7)
    return week1_start + timedelta(weeks=week - 1, days=6)


def _fetch_region(region: str, epiweeks: str) -> list[dict]:
    # One region per request: all regions at once can exceed Delphi's row cap
    # (result=2, silently truncated).
    return fluview_clinical_fetch([region], epiweeks)


def export_flu_percent_positive(out_dir: Path = _OUT_DIR) -> int:
    epiweeks = f"{_START_EPIWEEK}-{date.today().year + 1}53"

    # (epiweek, region) -> [specimens, positives]
    totals: dict[tuple[int, str], list[int]] = defaultdict(lambda: [0, 0])
    for code, region in [("nat", "National"), *DIVISION_REGION.items()]:
        for row in _fetch_region(code, epiweeks):
            specimens = row.get("total_specimens")
            if specimens is None:
                continue
            positives = (row.get("total_a") or 0) + (row.get("total_b") or 0)
            t = totals[(int(row["epiweek"]), region)]
            t[0] += int(specimens)
            t[1] += int(positives)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "flu_percent_positive.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(
            [
                "week_end",
                "region",
                "total_specimens",
                "total_positive",
                "percent_positive",
            ]
        )
        for (epiweek, region), (specimens, positives) in sorted(totals.items()):
            if specimens == 0:
                continue
            writer.writerow(
                [
                    mmwr_week_end(epiweek).isoformat(),
                    region,
                    specimens,
                    positives,
                    round(positives / specimens * 100, 3),
                ]
            )
    return len(totals)


if __name__ == "__main__":
    print("  exporting flu_percent_positive ...", end=" ", flush=True)
    n = export_flu_percent_positive()
    print(f"{n} weekly points -> {_OUT_DIR / 'flu_percent_positive.csv'}")
