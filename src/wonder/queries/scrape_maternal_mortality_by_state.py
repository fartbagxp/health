"""
CDC WONDER State-Level Maternal Mortality Scraper

The WONDER XML API (used by the rest of this project) enforces a national-only
restriction for all mortality datasets — state grouping returns a 500 error.
This script uses a headless browser (Playwright) to interact with the WONDER
web UI, which does not have that restriction.

It queries two datasets:
  D76  — Underlying Cause of Death, 1999–2020 (ICD-10, bridged-race, final)
  D158 — Underlying Cause of Death, 2018–2024 (ICD-10, single-race, final)

UCD filter applied: O00–O99 (Pregnancy, childbirth and the puerperium).
Group By: Year × State. All ages, both sexes, all races.

Merge strategy: D76 for 1999–2017; D158 for 2018+. Death counts agree in the
2018–2020 overlap when not broken out by race, so the seam is clean.

Output:
  data/raw/wonder/maternal-mortality-by-state-year.csv
    year        – calendar year
    state       – state name
    deaths      – raw maternal deaths (blank = suppressed by WONDER, n < 10)
    population  – female-population denominator (all-ages, all-races)

Suppressed cells: WONDER suppresses death counts of 1–9 for any state × year
cell. Small-birth-volume states (WY, VT, AK, ND, etc.) will have many blank
years. Pool multiple years before computing rates for those states.

Rate note: the official MMR uses LIVE BIRTHS as denominator (per 100,000).
Join with the project's natality data (births-by-year CSVs, D66) to compute
true MMR per 100,000 live births.

Prerequisites (one-time setup — downloads the browser binary):
    uv run playwright install chromium

Usage:
    uv run python src/wonder/queries/scrape_maternal_mortality_by_state.py
"""

import csv
import os
import sys
import time
from io import StringIO
from pathlib import Path

# On this host, libnspr4/libnss3/libatk/etc. are not installed system-wide.
# Stub .so files compiled from the binary's undefined-symbol list live here
# so Chrome can load without crashing.
_STUB_LIBS = Path.home() / ".local" / "lib" / "pw-stubs"
if _STUB_LIBS.is_dir():
    existing = os.environ.get("LD_LIBRARY_PATH", "")
    os.environ["LD_LIBRARY_PATH"] = f"{_STUB_LIBS}:{existing}" if existing else str(_STUB_LIBS)

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "wonder"
OUTPUT_CSV = OUTPUT_DIR / "maternal-mortality-by-state-year.csv"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# WONDER enforces a soft rate limit of ~1 query per 2 minutes on the web UI.
# We wait longer to be polite and avoid getting blocked.
RATE_LIMIT_SLEEP = 90  # seconds between queries

# D158 is preferred from 2018 onward (more current methodology)
D158_PREFERRED_FROM = 2018

DATASETS = [
    {
        "id": "D76",
        "label": "Underlying Cause of Death 1999–2020 (bridged-race)",
        "url": "https://wonder.cdc.gov/ucd-icd10.html",
        "year_group": "D76.V1-level1",
        "state_group": "D76.V9-level1",
        "ucd_filter_name": "F_D76.V2",
        "ucd_values": ["O00-O99"],
    },
    {
        "id": "D158",
        "label": "Underlying Cause of Death 2018–2024 (single-race)",
        "url": "https://wonder.cdc.gov/ucd-icd10-expanded.html",
        "year_group": "D158.V1-level1",
        "state_group": "D158.V9-level1",
        "ucd_filter_name": "F_D158.V2",
        "ucd_values": ["O00-O99"],
    },
]


# ── Form interaction ───────────────────────────────────────────────────────────


def accept_agreement(page) -> None:
    """Click the 'I Agree' button if present and wait for the form to load."""
    selectors = [
        "input[name='action-I Agree']",
        "input[value='I Agree']",
        "input[type='submit'][value*='Agree' i]",
        "button:has-text('I Agree')",
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=3000):
                btn.click()
                page.wait_for_load_state("domcontentloaded", timeout=30000)
                page.wait_for_timeout(2000)
                print("    Accepted data use agreement", flush=True)
                return
        except PlaywrightTimeout:
            continue
    print("    (no agreement button found — proceeding)", flush=True)


def set_group_by(page, slot: int, value: str) -> None:
    """Set a Group By dropdown (B_1 through B_5)."""
    name = f"B_{slot}"
    try:
        page.select_option(f"[name='{name}']", value=value, timeout=5000)
        print(f"    Set {name} = {value}", flush=True)
    except Exception as e:
        # Try by visible text (fallback)
        print(f"    {name} select_option by value failed ({e}); trying label …", flush=True)
        handle = page.locator(f"[name='{name}']")
        opts = handle.evaluate(
            "el => Array.from(el.options).map(o => ({v:o.value,t:o.text.trim()}))"
        )
        # Look for year/state in the label text
        keyword = "Year" if slot == 1 else "State"
        match = next((o for o in opts if keyword.lower() in o["t"].lower()), None)
        if match:
            page.select_option(f"[name='{name}']", value=match["v"], timeout=5000)
            print(f"    Set {name} = {match['v']} (matched '{match['t']}')", flush=True)
        else:
            raise RuntimeError(f"Could not find '{keyword}' option in {name}. Options: {opts[:10]}")


def set_ucd_filter(page, field_name: str, values: list[str]) -> None:
    """
    Set the Underlying Cause of Death filter.

    WONDER's UCD filter uses a custom multi-select in 'standard' (freg) mode.
    The <select> element is named F_D{xx}.V2 and its options are ICD-10 chapter
    ranges like 'O00-O99'.  If that select does not exist, fall back to setting
    the raw text input (textarea named I_D{xx}.V2).
    """
    # Try standard multi-select first
    sel = page.locator(f"[name='{field_name}']")
    if sel.count() > 0:
        tag = sel.evaluate("el => el.tagName")
        if tag == "SELECT":
            opts = sel.evaluate(
                "el => Array.from(el.options).map(o => ({v:o.value, t:o.text.trim()}))"
            )
            matched = [o["v"] for o in opts if o["v"] in values or any(v in o["v"] for v in values)]
            if not matched:
                # Try text-based matching for "Pregnancy"
                matched = [o["v"] for o in opts if "pregnancy" in o["t"].lower() or "O00" in o["v"]]
            if matched:
                page.select_option(f"[name='{field_name}']", value=matched, timeout=5000)
                print(f"    Set UCD filter ({field_name}) = {matched}", flush=True)
                return
            else:
                raise RuntimeError(
                    f"Could not find pregnancy option in UCD filter. Available: {opts[:10]}"
                )
        elif tag == "TEXTAREA":
            sel.fill("\n".join(values))
            print(f"    Set UCD textarea ({field_name}) = {values}", flush=True)
            return

    # Try the text input variant (I_D{xx}.V2)
    text_field = field_name.replace("F_", "I_")
    txt = page.locator(f"[name='{text_field}']")
    if txt.count() > 0:
        txt.fill(" ".join(values))
        print(f"    Set UCD text input ({text_field}) = {values}", flush=True)
        return

    raise RuntimeError(
        f"Could not find UCD filter field '{field_name}' or '{text_field}' on the form."
    )


def show_suppressed(page, dataset_id: str) -> None:
    """Enable 'Show Suppressed Values' if the checkbox exists."""
    # The checkbox might be named differently per dataset
    candidates = [
        f"[name='O_show_suppressed']",
        f"[name='O_show_suppressed'][value='true']",
        f"input[type='checkbox'][name*='suppressed' i]",
    ]
    for sel in candidates:
        el = page.locator(sel)
        if el.count() > 0:
            if not el.is_checked():
                el.check()
            print("    Show Suppressed enabled", flush=True)
            return


# ── Result parsing ─────────────────────────────────────────────────────────────


def parse_tsv_export(content: str) -> list[dict]:
    """
    Parse WONDER's exported tab-separated text.

    The export starts with a metadata/notes section, then a column-header row,
    then data rows, then a "Total" row and notes footer.
    The column header row contains "Year" and "State".
    """
    lines = content.splitlines()

    # Find the header row (contains "Year" and "State")
    header_idx = None
    for i, line in enumerate(lines):
        parts = [p.strip().strip('"') for p in line.split("\t")]
        if "Year" in parts and "State" in parts:
            header_idx = i
            break

    if header_idx is None:
        raise ValueError(
            "Could not find data table header in WONDER export. "
            f"First 300 chars: {content[:300]!r}"
        )

    headers = [p.strip().strip('"') for p in lines[header_idx].split("\t")]

    records = []
    for line in lines[header_idx + 1:]:
        if not line.strip():
            continue
        # Stop at totals/footer
        stripped = line.lstrip('"')
        if stripped.startswith("Total\t") or stripped.startswith("---"):
            break

        parts = [p.strip().strip('"') for p in line.split("\t")]
        if len(parts) < 2:
            continue

        row = dict(zip(headers, parts))

        year_str = row.get("Year", "").strip()
        state_str = row.get("State", "").strip()
        if not year_str or not year_str.isdigit():
            continue
        if not state_str or state_str in ("United States", ""):
            continue

        deaths_str = row.get("Deaths", "").strip()
        pop_str = row.get("Population", "").strip()

        SUPPRESSED = ("Suppressed", "Not Applicable", "Missing", "")
        deaths = None if deaths_str in SUPPRESSED else int(deaths_str.replace(",", ""))
        population = None if pop_str in SUPPRESSED else (
            int(pop_str.replace(",", "")) if pop_str.replace(",", "").isdigit() else None
        )

        records.append({
            "year": int(year_str),
            "state": state_str,
            "deaths": deaths,
            "population": population,
        })

    return records


def parse_html_results(html: str) -> list[dict]:
    """
    Fallback: parse the HTML data table returned by WONDER after clicking 'Send'.
    Used when the Export Results download cannot be captured.
    """
    soup = BeautifulSoup(html, "html.parser")

    # WONDER wraps the results table in a <div class="data-table"> or similar
    table = (
        soup.find("table", {"class": "data-table"})
        or soup.find("table", {"id": "DataTable"})
        or soup.find("table", {"id": "results-table"})
    )
    if not table:
        # Last resort: find table whose header rows contain both "Year" and "State"
        for t in soup.find_all("table"):
            all_trs = t.find_all("tr")
            # Gather text from all header rows (first few rows)
            header_text = " ".join(
                tr.get_text(" ", strip=True)
                for tr in all_trs[:5]
            )
            if "Year" in header_text and "State" in header_text:
                table = t
                break

    if not table:
        raise ValueError("No data table found in WONDER results HTML")

    rows = table.find_all("tr")
    if not rows:
        raise ValueError("Data table has no rows")

    # Find the header row that contains "Year" and "State"
    header_idx = 0
    for i, tr in enumerate(rows):
        cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
        if "Year" in cells and "State" in cells:
            header_idx = i
            break
    header_row = rows[header_idx]
    headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]

    records = []
    for tr in rows[header_idx + 1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if not cells:
            continue
        row = dict(zip(headers, cells))

        year_str = row.get("Year", "").strip()
        state_str = row.get("State", "").strip()
        if not year_str or not year_str.isdigit():
            continue
        if not state_str or state_str in ("United States", "Total", ""):
            continue

        deaths_str = row.get("Deaths", "").strip()
        pop_str = row.get("Population", "").strip()

        SUPPRESSED = ("Suppressed", "Not Applicable", "Missing", "")
        deaths = None if deaths_str in SUPPRESSED else int(deaths_str.replace(",", ""))
        population = None if pop_str in SUPPRESSED else (
            int(pop_str.replace(",", "")) if pop_str.replace(",", "").isdigit() else None
        )

        records.append({
            "year": int(year_str),
            "state": state_str,
            "deaths": deaths,
            "population": population,
        })

    return records


# ── Main query flow ────────────────────────────────────────────────────────────


def query_dataset(page, dataset: dict) -> list[dict]:
    """
    Navigate to a WONDER dataset page, fill the form, submit, and return records.
    """
    ds_id = dataset["id"]
    print(f"\n  → [{ds_id}] {dataset['label']}", flush=True)
    print(f"    URL: {dataset['url']}", flush=True)

    page.goto(dataset["url"], wait_until="domcontentloaded", timeout=60000)
    accept_agreement(page)

    # Group By 1: Year
    set_group_by(page, 1, dataset["year_group"])

    # Group By 2: State
    set_group_by(page, 2, dataset["state_group"])

    # UCD filter: Pregnancy, childbirth and the puerperium (O00-O99)
    set_ucd_filter(page, dataset["ucd_filter_name"], dataset["ucd_values"])

    # Show suppressed values (cells with 1–9 deaths get "Suppressed" label)
    show_suppressed(page, ds_id)

    print("    Submitting form …", flush=True)

    # Submit with "Send"
    page.click("input[name='action-Send']", timeout=10000)
    page.wait_for_load_state("domcontentloaded", timeout=180000)
    page.wait_for_timeout(3000)

    # Check for WONDER error in response
    title = page.title()
    if "error" in title.lower() or "processing error" in title.lower():
        snippet = page.locator("body").text_content()[:500]
        raise RuntimeError(f"WONDER returned an error: {snippet}")

    print("    Results received. Downloading export …", flush=True)

    # The export panel is collapsed by default. Expand it, pick TSV, then download.
    try:
        # Expand the export panel (button with text "Export")
        expand_btn = page.locator("button:has-text('Export'), input[value='Export Results']").first
        try:
            expand_btn.click(timeout=5000)
            page.wait_for_timeout(500)
        except Exception:
            pass

        # Set format to TSV if the selector exists
        fmt_sel = page.locator("select[name='O_export-format']")
        if fmt_sel.count() > 0:
            page.select_option("select[name='O_export-format']", value="tsv", timeout=3000)

        download_btn = page.locator("input[name='action-Export']")
        download_btn.wait_for(state="visible", timeout=10000)
        with page.expect_download(timeout=60000) as dl_info:
            download_btn.click()
        download = dl_info.value
        tsv = Path(download.path()).read_text("utf-8")
        records = parse_tsv_export(tsv)
        print(f"    TSV export: {len(tsv.splitlines())} lines → {len(records)} records", flush=True)
        return records
    except Exception as export_err:
        # Fallback: parse the HTML results table directly
        print(f"    Export download failed ({export_err}); parsing HTML table …", flush=True)
        html = page.content()
        records = parse_html_results(html)
        print(f"    HTML parse: {len(records)} records", flush=True)
        return records


# ── Merge and output ───────────────────────────────────────────────────────────


def merge(d76: list[dict], d158: list[dict]) -> list[dict]:
    """
    Prefer D158 for 2018+; use D76 for 1999–2017.
    In the 2018–2020 overlap, death counts are identical when not broken out by
    race — D158 is preferred as the more current final methodology.
    """
    combined: dict[tuple, dict] = {}

    for rec in d76:
        if rec["year"] < D158_PREFERRED_FROM:
            combined[(rec["year"], rec["state"])] = rec

    for rec in d158:
        combined[(rec["year"], rec["state"])] = rec

    return sorted(combined.values(), key=lambda r: (r["year"], r["state"]))


def write_csv(records: list[dict]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    years = sorted({r["year"] for r in records})
    states = sorted({r["state"] for r in records})

    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "state", "deaths", "population"])
        for rec in records:
            writer.writerow([
                rec["year"],
                rec["state"],
                "" if rec["deaths"] is None else rec["deaths"],
                "" if rec["population"] is None else rec["population"],
            ])

    print(
        f"  ✓ {OUTPUT_CSV.name}  "
        f"({len(records)} rows | {len(years)} years × {len(states)} states)"
    )


def print_preview(records: list[dict]) -> None:
    latest = max(r["year"] for r in records if r["deaths"] is not None)
    top = sorted(
        [r for r in records if r["year"] == latest and r["deaths"] is not None],
        key=lambda r: r["deaths"],
        reverse=True,
    )[:10]
    print(f"\n── Top 10 states by maternal deaths ({latest}) ─────────────────")
    for r in top:
        print(f"  {r['state']:<30} {r['deaths']:>4} deaths")

    suppressed = sum(1 for r in records if r["deaths"] is None)
    if suppressed:
        print(f"\n  Note: {suppressed} state×year cells were suppressed by WONDER (n < 10)")


# ── Entry point ────────────────────────────────────────────────────────────────


def main() -> None:
    print("CDC WONDER state-level maternal mortality scraper\n")
    print("  Datasets: D76 (1999–2020) + D158 (2018–2024)")
    print("  ICD-10 filter: O00–O99 (Pregnancy, childbirth and the puerperium)")
    print(f"  Output: {OUTPUT_CSV}\n")

    all_records: dict[str, list[dict]] = {"D76": [], "D158": []}

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=True,
                args=["--ignore-certificate-errors", "--no-sandbox", "--disable-dev-shm-usage"],
            )
        except Exception as e:
            print(
                f"\nERROR: Could not launch Chromium browser.\n"
                f"  {e}\n\n"
                f"Run this once to install the browser binary:\n"
                f"  uv run playwright install chromium\n",
                file=sys.stderr,
            )
            sys.exit(1)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()

        for i, dataset in enumerate(DATASETS):
            if i > 0:
                print(
                    f"\n  Rate-limit pause ({RATE_LIMIT_SLEEP}s) …",
                    flush=True,
                )
                time.sleep(RATE_LIMIT_SLEEP)

            try:
                records = query_dataset(page, dataset)
                years = sorted({r["year"] for r in records})
                states = {r["state"] for r in records}
                if years:
                    print(
                        f"    years {years[0]}–{years[-1]} | {len(states)} states | "
                        f"{len(records)} total rows",
                        flush=True,
                    )
                all_records[dataset["id"]] = records
            except Exception as e:
                print(f"\n    ERROR [{dataset['id']}]: {e}", file=sys.stderr)
                print("    Continuing with remaining datasets …", file=sys.stderr)

        browser.close()

    d76 = all_records["D76"]
    d158 = all_records["D158"]

    if not d76 and not d158:
        print("\nNo data returned from either dataset.", file=sys.stderr)
        sys.exit(1)

    print(f"\nMerging: D76 for 1999–{D158_PREFERRED_FROM - 1}, D158 for {D158_PREFERRED_FROM}+")
    merged = merge(d76, d158)
    print(f"Total merged rows: {len(merged)}")

    print("\nWriting CSV …")
    write_csv(merged)

    print_preview(merged)
    print("\nDone.")


if __name__ == "__main__":
    main()
