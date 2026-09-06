"""
Tests for the health_depts module (FSIS + NACCHO directory scrapers).

Unit tests parse saved HTML fixtures offline — no network:
    uv run pytest tests/test_health_depts.py -m "not integration"

Integration tests hit the live directories:
    uv run pytest tests/test_health_depts.py -m integration -v
"""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from health_depts import fsis, naccho
from health_depts.main import build_summary
from health_depts.naccho import _derive_county

FIXTURES = Path(__file__).parent / "fixtures"
FSIS_HTML = (FIXTURES / "fsis_state_departments.html").read_text()
NACCHO_HTML = (FIXTURES / "naccho_al.html").read_text()


# ---------------------------------------------------------------------------
# FSIS parser
# ---------------------------------------------------------------------------
class TestFsis:
    def test_parses_all_states(self):
        rows = fsis.parse_state_departments(FSIS_HTML)
        # 50 states + DC + a couple of territories the table carries
        assert len(rows) >= 51
        assert all(set(fsis.FIELDS) <= set(r) for r in rows)

    def test_first_row_is_alabama(self):
        rows = fsis.parse_state_departments(FSIS_HTML)
        al = next(r for r in rows if r["state"] == "Alabama")
        assert al["public_health_dept"] == "Department of Public Health"
        assert al["public_health_url"].startswith("http")
        assert "Agriculture" in al["agriculture_dept"]

    def test_empty_html(self):
        assert fsis.parse_state_departments("<html></html>") == []


# ---------------------------------------------------------------------------
# NACCHO parser
# ---------------------------------------------------------------------------
class TestNaccho:
    def test_parses_rows_with_state_param(self):
        rows = naccho.parse_local_departments(NACCHO_HTML, state="AL")
        assert len(rows) == 4
        assert all(r["state"] == "AL" for r in rows)
        assert all(set(naccho.FIELDS) <= set(r) for r in rows)

    def test_field_extraction(self):
        rows = naccho.parse_local_departments(NACCHO_HTML, state="AL")
        autauga = rows[0]
        assert autauga["name"] == "Autauga County Health Department"
        assert autauga["county"] == "Autauga"
        assert autauga["city"] == "Prattville"
        assert autauga["zip"] == "36067"
        assert autauga["phone"].startswith("(334)")
        assert autauga["website"].startswith("http")
        assert autauga["has_email"] is True

    def test_state_derived_from_address_when_no_param(self):
        # without an authoritative state code, the parser reads it from the address
        rows = naccho.parse_local_departments(NACCHO_HTML)
        assert rows
        assert all(r["state"] == "AL" for r in rows)

    def test_non_state_rows_dropped(self):
        html = (
            "<table><tr><td>Name</td><td>Address</td><td>Details</td></tr>"
            "<tr><td>Guam DPHSS</td><td>123 Main ST Hagatna, GU 96910</td>"
            "<td></td></tr></table>"
        )
        # GU is not one of the 50 states + DC → dropped when derived from address
        assert naccho.parse_local_departments(html) == []

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("Autauga County Health Department", "Autauga"),
            ("Baldwin County Health Department", "Baldwin"),
            ("Chicago Department of Public Health", "Chicago"),
            ("Southwest District Health", "Southwest"),
        ],
    )
    def test_derive_county(self, name, expected):
        assert _derive_county(name) == expected

    def test_state_names_are_51(self):
        assert len(naccho.STATE_NAMES) == 51  # 50 states + DC
        assert "DC" in naccho.STATE_NAMES


# ---------------------------------------------------------------------------
# summary (the blob the Svelte graph bakes in)
# ---------------------------------------------------------------------------
class TestSummary:
    def _data(self):
        states = fsis.parse_state_departments(FSIS_HTML)
        locals_ = naccho.parse_local_departments(NACCHO_HTML, state="AL")
        return states, locals_

    def test_build_summary_shape(self):
        states, locals_ = self._data()
        summary = build_summary(states, locals_)
        assert summary["generated_locals"] == 4
        assert set(summary["states"]) == set(naccho.STATE_NAMES)
        al = summary["states"]["AL"]
        assert al["name"] == "Alabama"
        assert al["dept"] == "Department of Public Health"
        assert al["county_count"] == 4
        assert "Autauga" in al["counties"]


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------
class TestCli:
    def test_help(self):
        r = subprocess.run(
            [sys.executable, "-m", "health_depts", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin"},
            check=False,
        )
        assert r.returncode == 0
        assert "state" in r.stdout and "local" in r.stdout and "all" in r.stdout


# ---------------------------------------------------------------------------
# Integration (network)
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestLive:
    def test_fsis_live(self):
        rows = fsis.scrape_state_departments()
        assert len(rows) >= 51

    def test_naccho_live_single_state(self):
        html = naccho.fetch(f"{naccho.NACCHO_URL}&lhd-state=DC")
        rows = naccho.parse_local_departments(html, state="DC")
        assert len(rows) >= 1
