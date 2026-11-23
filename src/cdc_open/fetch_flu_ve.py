"""
Scrape CDC's seasonal influenza vaccine effectiveness (VE) estimates.

Source: "CDC Seasonal Flu Vaccine Effectiveness Studies"
https://www.cdc.gov/flu-vaccines-work/php/effectiveness-studies/index.html

The page carries one row per season (2004-05 onward) from the U.S. Flu VE
Network: adjusted overall VE against medically attended, lab-confirmed
influenza, its 95% CI, patient count, study sites, and the citation. CDC
publishes it only as an HTML table (no Socrata dataset), so it's scraped.

The table is found by its header ("Adjusted Overall VE"), not its position:
the page also has a horizontal chart-data table with the same numbers for
2009-10 onward only.

Footnote markers on the season cell are turned into flags:
    ††  preliminary estimate (latest seasons)
    †   2008-09 only: estimate never published
    *   2004-05..2010-11: network also enrolled inpatients
    **  2020-21: not estimated (too little flu circulating); row kept with
        empty values so charts show a gap rather than interpolating

cdc.gov's Akamai front end rejects curl's default client but serves
requests' default headers fine, so plain requests is used.

Output: data/raw/cdc_open/flu_vaccine_effectiveness.csv

    uv run python -m cdc_open.fetch_flu_ve
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://www.cdc.gov/flu-vaccines-work/php/effectiveness-studies/index.html"
_OUT_DIR = Path("data/raw/cdc_open")
_TIMEOUT = 60

FIELDS = [
    "season",
    "season_start_year",
    "ve_pct",
    "ci_low",
    "ci_high",
    "patients",
    "study_sites",
    "reference",
    "preliminary",
    "published",
    "includes_inpatients",
]

_SEASON_RE = re.compile(r"(\d{4})\s*[–-]\s*(\d{2})")


def _num(text: str) -> int | None:
    text = text.replace(",", "").strip()
    try:
        return int(text)
    except ValueError:
        return None


def parse_ve_table(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    table = None
    for t in soup.find_all("table"):
        header = [
            c.get_text(" ", strip=True) for c in t.find("tr").find_all(["th", "td"])
        ]
        if any("Adjusted Overall VE" in h for h in header) and any(
            "Season" in h for h in header
        ):
            table = t
            break
    if table is None:
        raise ValueError("VE table (header 'Adjusted Overall VE') not found on page")

    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
        if len(cells) < 6:
            continue
        season_raw, reference, sites, patients, ve, ci = cells[:6]
        m = _SEASON_RE.search(season_raw)
        if not m:
            continue
        markers = season_raw[m.end() :].replace(" ", "")

        ci_parts = [p.strip() for p in ci.split(",")]
        ci_low, ci_high = (
            (_num(ci_parts[0]), _num(ci_parts[1]))
            if len(ci_parts) == 2
            else (None, None)
        )

        rows.append(
            {
                "season": f"{m.group(1)}-{m.group(2)}",
                "season_start_year": int(m.group(1)),
                "ve_pct": _num(ve),
                "ci_low": ci_low,
                "ci_high": ci_high,
                "patients": _num(patients),
                "study_sites": "" if sites.lower() == "n/a" else sites,
                "reference": "" if reference.lower() == "n/a" else reference,
                "preliminary": "††" in markers,
                # A lone † (not part of ††) marks the unpublished 2008-09 row.
                "published": _num(ve) is not None
                and "†" not in markers.replace("††", "")
                and reference.lower() != "unpublished",
                # Single * (not ** / ***) = inpatients also enrolled.
                "includes_inpatients": re.fullmatch(r"\*(?!\*).*", markers) is not None,
            }
        )

    if not rows:
        raise ValueError("VE table found but no season rows parsed")
    return sorted(rows, key=lambda r: r["season_start_year"])


def fetch_flu_ve(out_dir: Path = _OUT_DIR) -> list[dict]:
    resp = requests.get(URL, timeout=_TIMEOUT)
    resp.raise_for_status()
    rows = parse_ve_table(resp.text)

    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "flu_vaccine_effectiveness.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: "" if v is None else v for k, v in r.items()})
    return rows


def main() -> None:
    print("  fetching flu vaccine effectiveness ...", end=" ", flush=True)
    rows = fetch_flu_ve()
    print(
        f"{len(rows)} seasons ({rows[0]['season']}..{rows[-1]['season']}) -> "
        f"{_OUT_DIR / 'flu_vaccine_effectiveness.csv'}"
    )


if __name__ == "__main__":
    main()
