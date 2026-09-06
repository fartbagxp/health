"""
Scrape the FSIS directory of State Departments of Public Health and Agriculture.

Source: https://www.fsis.usda.gov/food-safety/foodborne-illness-and-disease/
        resources-public-health-partners/state-departments-public

The page is a single static HTML table, one row per state (50 states + DC),
with three columns: the state's home portal, its public-health department
(name + link), and its agriculture department (name + link).
"""

from bs4 import BeautifulSoup

from health_depts.client import fetch

FSIS_URL = (
    "https://www.fsis.usda.gov/food-safety/foodborne-illness-and-disease/"
    "resources-public-health-partners/state-departments-public"
)

FIELDS = [
    "state",
    "state_url",
    "public_health_dept",
    "public_health_url",
    "agriculture_dept",
    "agriculture_url",
]


def _cell(cell) -> tuple[str, str]:
    """Return (text, first href) for a table cell."""
    text = cell.get_text(" ", strip=True)
    link = cell.find("a")
    href = link.get("href", "").strip() if link else ""
    return text, href


def parse_state_departments(html: str) -> list[dict]:
    """Parse the FSIS state-departments table from raw HTML."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if table is None:
        return []

    rows: list[dict] = []
    for tr in table.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) != 3:
            continue  # skips the title/header rows (which use <th> or a colspan)
        state, state_url = _cell(cells[0])
        ph_name, ph_url = _cell(cells[1])
        ag_name, ag_url = _cell(cells[2])
        if not state:
            continue
        rows.append(
            {
                "state": state,
                "state_url": state_url,
                "public_health_dept": ph_name,
                "public_health_url": ph_url,
                "agriculture_dept": ag_name,
                "agriculture_url": ag_url,
            }
        )
    return rows


def scrape_state_departments() -> list[dict]:
    """Fetch and parse the FSIS state-departments directory."""
    return parse_state_departments(fetch(FSIS_URL))
