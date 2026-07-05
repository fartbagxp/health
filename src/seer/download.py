"""
Refresh the bundled SEER*Explorer catalog and data snapshots under data/raw/seer/.

Usage:
    uv run python -m seer.download            # catalog + mortality data snapshots
    uv run python -m seer.download --catalog-only
"""

import argparse
import csv
import json
import time
from pathlib import Path

from seer.catalog import AGE_RANGE, cancer_sites
from seer.client import SeerClient
from seer.sdk import get_mortality_by_age, get_mortality_trend

_OUT_DIR = Path("data/raw/seer")
_CATALOG_PATH = _OUT_DIR / "var_formats.json"
_MORTALITY_BY_YEAR_PATH = _OUT_DIR / "mortality_by_year.csv"
_MORTALITY_BY_AGE_PATH = _OUT_DIR / "mortality_by_age.csv"
_MORTALITY_BY_YEAR_AGE_PATH = _OUT_DIR / "mortality_by_year_age.csv"
_REQUEST_DELAY = 0.5  # seconds between requests, polite to seer.cancer.gov


def download_catalog(out_path: Path = _CATALOG_PATH) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = SeerClient().get_var_formats()
    out_path.write_text(json.dumps(data, indent=2))
    n_sites = len(data.get("VariableFormats", {}).get("site", {}))
    print(f"Fetched {n_sites} cancer sites -> {out_path}")


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Some sites (e.g. histology subtypes) return extra dimension columns
    # (stage, subtype, rate_type) that ordinary sites don't, so the fieldname
    # set must be the union across all rows, not just the first.
    fieldnames: list[str] = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, restval="")
        writer.writeheader()
        writer.writerows(rows)


def download_mortality_by_year(out_path: Path = _MORTALITY_BY_YEAR_PATH) -> None:
    """U.S. mortality rate/count by year, for every cataloged cancer site, split by sex."""
    rows = []
    sites = cancer_sites()
    for code in sites:
        try:
            rows.extend(get_mortality_trend(site=code, compare_by="sex"))
        except Exception as exc:
            print(f"  WARNING: site {code} ({sites[code]}) failed: {exc}")
        time.sleep(_REQUEST_DELAY)
    _write_csv(out_path, rows)
    print(
        f"Fetched {len(rows)} mortality-by-year rows across {len(sites)} sites -> {out_path}"
    )


def download_mortality_by_age(out_path: Path = _MORTALITY_BY_AGE_PATH) -> None:
    """U.S. mortality rate/count by age group, for every cataloged cancer site, split by sex."""
    rows = []
    sites = cancer_sites()
    for code in sites:
        try:
            rows.extend(get_mortality_by_age(site=code, compare_by="sex"))
        except Exception as exc:
            print(f"  WARNING: site {code} ({sites[code]}) failed: {exc}")
        time.sleep(_REQUEST_DELAY)
    _write_csv(out_path, rows)
    print(
        f"Fetched {len(rows)} mortality-by-age rows across {len(sites)} sites -> {out_path}"
    )


def download_mortality_by_year_age(out_path: Path = _MORTALITY_BY_YEAR_AGE_PATH) -> None:
    """U.S. mortality rate/count by year within each (coarse) age band, for
    every cataloged cancer site, split by sex.

    Unlike download_mortality_by_age (fine ~5-year age groups pooled over a
    single recent multi-year window), this crosses year with SEER's broader
    age-band filter (e.g. <15, 15-39, 40-64, 65-74, 75+, ...) so each row is a
    single calendar year x age band x sex combination. SEER's rates-by-age
    view only supports fine age groups pooled over a period, not per-year, so
    this coarser banding is the finest year x age x sex breakdown available.
    """
    rows = []
    sites = cancer_sites()
    # Codes "6" (Ages < 65) and "11" (Ages <40) are in the AGE_RANGE catalog
    # but aren't valid filters for this trend endpoint — the server silently
    # falls back to "All Ages" instead of filtering, so they're excluded here
    # to avoid fetching (and storing) redundant/misleading duplicate rows.
    _INVALID_YEAR_TREND_AGE_CODES = {"6", "11"}
    age_ranges = {
        code: label
        for code, label in AGE_RANGE.items()
        if code != "1" and code not in _INVALID_YEAR_TREND_AGE_CODES
    }
    for site_code in sites:
        for age_code in age_ranges:
            try:
                rows.extend(
                    get_mortality_trend(
                        site=site_code, age_range=age_code, compare_by="sex"
                    )
                )
            except Exception as exc:
                print(
                    f"  WARNING: site {site_code} ({sites[site_code]}) "
                    f"age {age_code} ({age_ranges[age_code]}) failed: {exc}"
                )
            time.sleep(_REQUEST_DELAY)
    _write_csv(out_path, rows)
    print(
        f"Fetched {len(rows)} mortality-by-year-age rows across {len(sites)} "
        f"sites x {len(age_ranges)} age bands -> {out_path}"
    )


def download_all(out_dir: Path = _OUT_DIR) -> None:
    download_catalog(out_dir / "var_formats.json")
    download_mortality_by_year(out_dir / "mortality_by_year.csv")
    download_mortality_by_age(out_dir / "mortality_by_age.csv")
    download_mortality_by_year_age(out_dir / "mortality_by_year_age.csv")


def main():
    parser = argparse.ArgumentParser(
        description="Refresh bundled SEER catalog and data snapshots"
    )
    parser.add_argument(
        "--catalog-only",
        action="store_true",
        help="Only refresh the cancer-site/vocabulary catalog, skip data snapshots",
    )
    args = parser.parse_args()

    if args.catalog_only:
        download_catalog()
    else:
        download_all()


if __name__ == "__main__":
    main()
