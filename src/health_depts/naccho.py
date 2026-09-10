"""
Scrape the NACCHO Local Health Department (LHD) directory.

Source: https://www.naccho.org/membership/lhd-directory

The directory renders one server-side ``data-table__table`` with three columns:
``Name | Address | Details``. The ``?lhd-state=XX`` query filters by a valid
USPS state code, so we fetch each of the 50 states + DC in turn (~3,400 LHDs
total). Fetching per state gives each row an authoritative state code from the
query itself; ``zip``/``city`` are still parsed from the address string.
"""

import re
import time

from bs4 import BeautifulSoup

from health_depts.client import ScrapeError, fetch

NACCHO_URL = "https://www.naccho.org/membership/lhd-directory?searchType=standard"

# 50 states + DC. NACCHO has no local health departments outside these.
STATE_NAMES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}

FIELDS = [
    "name",
    "county",
    "city",
    "state",
    "zip",
    "phone",
    "website",
    "facebook",
    "twitter",
    "has_email",
    "address",
]

_ADDR_RE = re.compile(r",\s*([A-Z]{2})\s+(\d{5})(?:-\d{4})?\s*$")

# Generic organisation words. A department name's jurisdiction is what remains
# after the trailing run of these is stripped ("Autauga County Health
# Department" -> "Autauga", "Chicago Department of Public Health" -> "Chicago").
_ORG_WORDS = {
    "county",
    "city",
    "city-county",
    "public",
    "health",
    "department",
    "dept",
    "dept.",
    "district",
    "board",
    "of",
    "unit",
    "units",
    "center",
    "centers",
    "services",
    "service",
    "human",
    "and",
    "&",
    "combined",
    "regional",
    "region",
    "authority",
    "division",
    "office",
    "agency",
    "consolidated",
    "metropolitan",
    "metro",
    "commission",
}


def _derive_county(name: str) -> str:
    """Best-effort county/jurisdiction label from a department name."""
    tokens = name.split()
    end = len(tokens)
    while end > 1 and tokens[end - 1].strip(".,").lower() in _ORG_WORDS:
        end -= 1
    return " ".join(tokens[:end]) or name


def _parse_details(cell) -> dict:
    phone = website = facebook = twitter = ""
    has_email = False
    for a in cell.find_all("a"):
        href = a.get("href", "") or ""
        label = a.get_text(" ", strip=True)
        low = f"{href} {label}".lower()
        if href.startswith("tel:"):
            phone = label
        elif "email-protection" in href or "email" in label.lower():
            has_email = True
        elif "facebook" in low:
            facebook = href
        elif "twitter" in low or "x.com" in low:
            twitter = href
        elif "website" in low or href.startswith("http"):
            website = href
    return {
        "phone": phone,
        "website": website,
        "facebook": facebook,
        "twitter": twitter,
        "has_email": has_email,
    }


def parse_local_departments(html: str, state: str | None = None) -> list[dict]:
    """Parse one NACCHO LHD directory table from raw HTML.

    If ``state`` (a USPS code) is given it is authoritative; otherwise the state
    is derived from each address and rows outside the 50 states + DC are dropped.

    Raises ``ScrapeError`` if the page carries no table at all.
    """
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if table is None:
        # The directory is always rendered server-side, so a page without a
        # table is not the directory. NACCHO sits behind Cloudflare and a
        # challenge comes back as a 200 that parses to zero rows -- raise, so a
        # blocked scrape fails loudly instead of quietly emptying the output.
        raise ScrapeError(
            "NACCHO returned a page with no directory table "
            "(bot-protection challenge, or the markup changed)"
        )

    rows: list[dict] = []
    for tr in table.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) != 3:
            continue  # header row
        name = cells[0].get_text(" ", strip=True)
        address = cells[1].get_text(" ", strip=True)
        if not name:
            continue

        zip_code = city = ""
        m = _ADDR_RE.search(address)
        if m:
            addr_state, zip_code = m.group(1), m.group(2)
            before = address[: m.start()].strip()
            city = before.split()[-1] if before else ""
        else:
            addr_state = ""
        code = state or addr_state
        if code not in STATE_NAMES:
            continue

        details = _parse_details(cells[2])
        rows.append(
            {
                "name": name,
                "county": _derive_county(name),
                "city": city,
                "state": code,
                "zip": zip_code,
                "address": address,
                **details,
            }
        )
    return rows


def scrape_local_departments(*, delay: float = 0.5) -> list[dict]:
    """Fetch and parse every state's NACCHO LHD directory (50 states + DC)."""
    rows: list[dict] = []
    for code in STATE_NAMES:
        html = fetch(f"{NACCHO_URL}&lhd-state={code}")
        rows.extend(parse_local_departments(html, state=code))
        if delay:
            time.sleep(delay)
    return rows
