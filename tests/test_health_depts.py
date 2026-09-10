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

from health_depts import fsis, main, naccho, progress
from health_depts.client import ScrapeError
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
# write guard — stops a blocked scrape from wiping the committed directory
# ---------------------------------------------------------------------------
class TestWriteGuard:
    def _rows(self):
        return (
            fsis.parse_state_departments(FSIS_HTML),
            naccho.parse_local_departments(NACCHO_HTML, state="AL"),
        )

    def test_page_without_table_raises(self):
        # a Cloudflare challenge is a 200 carrying no directory table; parsing
        # it must fail loudly rather than report an empty directory
        with pytest.raises(ScrapeError):
            naccho.parse_local_departments("<html><body>Just a moment…</body></html>")

    def test_first_run_writes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(main, "PROCESSED_DIR", tmp_path)
        states, locals_ = self._rows()
        summary = main._write_processed(states, locals_)
        assert summary["generated_locals"] == 4
        assert (tmp_path / "local_departments.csv").exists()

    def test_refuses_to_empty_a_populated_directory(self, tmp_path, monkeypatch):
        monkeypatch.setattr(main, "PROCESSED_DIR", tmp_path)
        states, locals_ = self._rows()
        main._write_processed(states, locals_)
        before = (tmp_path / "local_departments.csv").read_text()

        with pytest.raises(main.DataRegression, match="local departments"):
            main._write_processed(states, [])

        # the previously committed data is still intact
        assert (tmp_path / "local_departments.csv").read_text() == before

    def test_guard_also_covers_state_departments(self, tmp_path, monkeypatch):
        monkeypatch.setattr(main, "PROCESSED_DIR", tmp_path)
        states, locals_ = self._rows()
        main._write_processed(states, locals_)
        with pytest.raises(main.DataRegression, match="state departments"):
            main._write_processed([], locals_)

    def test_unchanged_count_is_allowed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(main, "PROCESSED_DIR", tmp_path)
        states, locals_ = self._rows()
        main._write_processed(states, locals_)
        summary = main._write_processed(states, locals_)
        assert summary["generated_locals"] == 4

    def test_force_overrides_the_guard(self, tmp_path, monkeypatch):
        monkeypatch.setattr(main, "PROCESSED_DIR", tmp_path)
        states, locals_ = self._rows()
        main._write_processed(states, locals_)
        summary = main._write_processed(states, [], force=True)
        assert summary["generated_locals"] == 0


# ---------------------------------------------------------------------------
# progress narration
# ---------------------------------------------------------------------------
class TestProgress:
    @pytest.fixture(autouse=True)
    def _restore(self):
        yield
        progress.set_enabled(True)

    @pytest.mark.parametrize(
        "seconds,expected",
        [
            (0.0, "0.0s"),
            (4.24, "4.2s"),
            (59.9, "59.9s"),
            (60, "1m 00s"),
            (332, "5m 32s"),
        ],
    )
    def test_duration_formatting(self, seconds, expected):
        assert progress.duration(seconds) == expected

    def test_log_goes_to_stderr_not_stdout(self, capsys):
        progress.set_enabled(True)
        progress.log("scraping AL")
        captured = capsys.readouterr()
        assert captured.out == ""  # stdout stays clean for -f csv piping
        assert "scraping AL" in captured.err

    def test_quiet_suppresses_output(self, capsys):
        progress.set_enabled(False)
        progress.log("scraping AL")
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == ""


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
