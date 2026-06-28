"""
Tests for CDC WONDER fetched data and query parsers.

Run unit tests only (no network):
    uv run pytest tests/test_wonder.py -m "not integration"

Run integration tests (hits wonder.cdc.gov, slow — respects 16s rate limit):
    uv run pytest tests/test_wonder.py -m integration -v
"""

import csv
import sys
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DATA_DIR = Path(__file__).parent.parent / "data" / "raw" / "wonder"

FENTANYL_CSV = DATA_DIR / "fentanyl-deaths-by-month.csv"
DRUG_YEAR_CSV = DATA_DIR / "drug-deaths-by-year.csv"
DRUG_MONTH_CSV = DATA_DIR / "drug-deaths-by-month.csv"

EXPECTED_DRUG_CODES = {"T40.1", "T40.2", "T40.3", "T40.4", "T40.5", "T40.7", "T43.6"}

# ── helpers ──────────────────────────────────────────────────────────────────

def _load_csv(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


# ── fentanyl-deaths-by-month.csv ─────────────────────────────────────────────

class TestFentanylDeathsByMonth:
    """Shape, completeness, and spot-check tests for fentanyl-deaths-by-month.csv."""

    @pytest.fixture(scope="class")
    @classmethod
    def rows(cls):
        return _load_csv(FENTANYL_CSV)

    def test_file_exists(self):
        assert FENTANYL_CSV.exists(), f"Missing {FENTANYL_CSV}"

    def test_columns(self, rows):
        assert rows[0].keys() == {"year", "month", "deaths", "provisional"}

    def test_row_count(self, rows):
        # 26 years (1999–2024) × 12 months = 312
        assert len(rows) == 312

    def test_year_range(self, rows):
        years = {int(r["year"]) for r in rows}
        assert min(years) == 1999
        assert max(years) == 2024

    def test_month_range(self, rows):
        months = {int(r["month"]) for r in rows}
        assert months == set(range(1, 13))

    def test_no_duplicate_year_month(self, rows):
        keys = [(r["year"], r["month"]) for r in rows]
        assert len(keys) == len(set(keys))

    def test_deaths_are_integers(self, rows):
        for r in rows:
            if r["deaths"]:
                assert r["deaths"].isdigit(), f"Non-integer deaths: {r}"

    def test_deaths_are_positive(self, rows):
        for r in rows:
            if r["deaths"]:
                assert int(r["deaths"]) > 0

    def test_provisional_flag_format(self, rows):
        for r in rows:
            assert r["provisional"] in ("true", "false")

    def test_d77_rows_not_provisional(self, rows):
        """All years ≤ 2020 come from D77 (final)."""
        for r in rows:
            if int(r["year"]) <= 2020:
                assert r["provisional"] == "false", f"Unexpected provisional in {r}"

    def test_d176_rows_provisional(self, rows):
        """All years > 2020 come from D176 (provisional)."""
        for r in rows:
            if int(r["year"]) > 2020:
                assert r["provisional"] == "true", f"Expected provisional in {r}"

    # ── known-value pins (CDC WONDER D77 final data) ──────────────────────────

    def test_fentanyl_annual_total_1999(self, rows):
        """1999 fentanyl annual total = 772 (verified against dawaldron/fentanyl-deaths)."""
        total = sum(int(r["deaths"]) for r in rows if r["year"] == "1999" and r["deaths"])
        assert total == 772

    def test_fentanyl_monthly_jan_1999(self, rows):
        """January 1999 fentanyl deaths = 62."""
        jan = next(r for r in rows if r["year"] == "1999" and r["month"] == "1")
        assert int(jan["deaths"]) == 62

    def test_fentanyl_monthly_feb_1999(self, rows):
        assert int(next(r for r in rows if r["year"] == "1999" and r["month"] == "2")["deaths"]) == 72

    def test_fentanyl_annual_total_2020(self, rows):
        """2020 fentanyl annual total = 57,390."""
        total = sum(int(r["deaths"]) for r in rows if r["year"] == "2020" and r["deaths"])
        assert total == 57390

    def test_fentanyl_trend_growing(self, rows):
        """Annual totals increase from 1999 to 2020 (net, not necessarily monotone)."""
        by_year = {}
        for r in rows:
            if r["deaths"]:
                by_year.setdefault(int(r["year"]), 0)
                by_year[int(r["year"])] += int(r["deaths"])
        assert by_year[2020] > by_year[1999] * 10, "Expect >10× growth 1999→2020"


# ── drug-deaths-by-year.csv ───────────────────────────────────────────────────

class TestDrugDeathsByYear:
    """Shape, completeness, and spot-check tests for drug-deaths-by-year.csv."""

    @pytest.fixture(scope="class")
    @classmethod
    def rows(cls):
        return _load_csv(DRUG_YEAR_CSV)

    def test_file_exists(self):
        assert DRUG_YEAR_CSV.exists(), f"Missing {DRUG_YEAR_CSV}"

    def test_columns(self, rows):
        assert rows[0].keys() == {"year", "drug_code", "drug_name", "deaths", "provisional"}

    def test_row_count(self, rows):
        # 26 years × 7 drugs = 182
        assert len(rows) == 182

    def test_year_range(self, rows):
        years = {int(r["year"]) for r in rows}
        assert min(years) == 1999
        assert max(years) == 2024

    def test_all_drug_codes_present(self, rows):
        codes = {r["drug_code"] for r in rows}
        assert codes == EXPECTED_DRUG_CODES

    def test_all_drugs_in_every_year(self, rows):
        by_year: dict[int, set] = {}
        for r in rows:
            by_year.setdefault(int(r["year"]), set()).add(r["drug_code"])
        for yr, codes in by_year.items():
            assert codes == EXPECTED_DRUG_CODES, f"Missing drugs in year {yr}: {EXPECTED_DRUG_CODES - codes}"

    def test_no_duplicate_year_drug(self, rows):
        keys = [(r["year"], r["drug_code"]) for r in rows]
        assert len(keys) == len(set(keys))

    def test_deaths_are_integers_when_present(self, rows):
        for r in rows:
            if r["deaths"]:
                assert r["deaths"].isdigit(), f"Non-integer deaths: {r}"

    def test_provisional_flag_format(self, rows):
        for r in rows:
            assert r["provisional"] in ("true", "false")

    def test_d77_rows_not_provisional(self, rows):
        for r in rows:
            if int(r["year"]) <= 2020:
                assert r["provisional"] == "false"

    # ── known-value pins ──────────────────────────────────────────────────────

    def test_heroin_1999(self, rows):
        r = next(r for r in rows if r["year"] == "1999" and r["drug_code"] == "T40.1")
        assert int(r["deaths"]) == 2103

    def test_cocaine_1999(self, rows):
        r = next(r for r in rows if r["year"] == "1999" and r["drug_code"] == "T40.5")
        assert int(r["deaths"]) == 4494

    def test_fentanyl_1999(self, rows):
        r = next(r for r in rows if r["year"] == "1999" and r["drug_code"] == "T40.4")
        assert int(r["deaths"]) == 772

    def test_fentanyl_2020(self, rows):
        r = next(r for r in rows if r["year"] == "2020" and r["drug_code"] == "T40.4")
        assert int(r["deaths"]) == 57390

    def test_meth_2020(self, rows):
        r = next(r for r in rows if r["year"] == "2020" and r["drug_code"] == "T43.6")
        assert int(r["deaths"]) == 26575

    def test_cannabis_1999_annual_total(self, rows):
        """Cannabis 1999 annual total = 49 (not suppressed at annual level, even though
        each individual month is suppressed — WONDER still reports the annual aggregate)."""
        r = next(r for r in rows if r["year"] == "1999" and r["drug_code"] == "T40.7")
        assert int(r["deaths"]) == 49


# ── drug-deaths-by-month.csv ──────────────────────────────────────────────────

class TestDrugDeathsByMonth:
    """Shape, completeness, and spot-check tests for drug-deaths-by-month.csv."""

    @pytest.fixture(scope="class")
    @classmethod
    def rows(cls):
        return _load_csv(DRUG_MONTH_CSV)

    def test_file_exists(self):
        assert DRUG_MONTH_CSV.exists(), f"Missing {DRUG_MONTH_CSV}"

    def test_columns(self, rows):
        assert rows[0].keys() == {"year", "month", "drug_code", "drug_name", "deaths", "provisional"}

    def test_row_count(self, rows):
        # 26 years × 12 months × 7 drugs = 2184
        assert len(rows) == 2184

    def test_year_range(self, rows):
        years = {int(r["year"]) for r in rows}
        assert min(years) == 1999
        assert max(years) == 2024

    def test_month_range(self, rows):
        months = {int(r["month"]) for r in rows}
        assert months == set(range(1, 13))

    def test_all_drug_codes_present(self, rows):
        codes = {r["drug_code"] for r in rows}
        assert codes == EXPECTED_DRUG_CODES

    def test_no_duplicate_keys(self, rows):
        keys = [(r["year"], r["month"], r["drug_code"]) for r in rows]
        assert len(keys) == len(set(keys))

    def test_provisional_flag_format(self, rows):
        for r in rows:
            assert r["provisional"] in ("true", "false")

    def test_d77_rows_not_provisional(self, rows):
        for r in rows:
            if int(r["year"]) <= 2020:
                assert r["provisional"] == "false"

    def test_d176_rows_provisional(self, rows):
        for r in rows:
            if int(r["year"]) > 2020:
                assert r["provisional"] == "true"

    # ── known-value pins ──────────────────────────────────────────────────────

    def test_heroin_jan_1999(self, rows):
        r = next(r for r in rows if r["year"] == "1999" and r["month"] == "1" and r["drug_code"] == "T40.1")
        assert int(r["deaths"]) == 186

    def test_cocaine_jan_1999(self, rows):
        r = next(r for r in rows if r["year"] == "1999" and r["month"] == "1" and r["drug_code"] == "T40.5")
        assert int(r["deaths"]) == 315

    def test_meth_jan_1999(self, rows):
        r = next(r for r in rows if r["year"] == "1999" and r["month"] == "1" and r["drug_code"] == "T43.6")
        assert int(r["deaths"]) == 47

    def test_cannabis_jan_1999_suppressed(self, rows):
        r = next(r for r in rows if r["year"] == "1999" and r["month"] == "1" and r["drug_code"] == "T40.7")
        assert r["deaths"] == ""

    # ── cross-dataset consistency ──────────────────────────────────────────────

    def test_fentanyl_monthly_sums_match_fentanyl_csv(self, rows):
        """Monthly fentanyl deaths (T40.4) should sum to the same annual totals as fentanyl-deaths-by-month.csv."""
        fentanyl_rows = _load_csv(FENTANYL_CSV)
        fentanyl_by_year = {}
        for r in fentanyl_rows:
            if r["deaths"] and int(r["year"]) <= 2020:
                fentanyl_by_year.setdefault(int(r["year"]), 0)
                fentanyl_by_year[int(r["year"])] += int(r["deaths"])

        drug_fentanyl_by_year = {}
        for r in rows:
            if r["drug_code"] == "T40.4" and r["deaths"] and int(r["year"]) <= 2020:
                drug_fentanyl_by_year.setdefault(int(r["year"]), 0)
                drug_fentanyl_by_year[int(r["year"])] += int(r["deaths"])

        for yr in fentanyl_by_year:
            assert fentanyl_by_year[yr] == drug_fentanyl_by_year.get(yr), (
                f"Fentanyl sum mismatch in {yr}: "
                f"fentanyl csv={fentanyl_by_year[yr]}, drug csv={drug_fentanyl_by_year.get(yr)}"
            )

    def test_monthly_sums_match_annual_totals(self, rows):
        """Monthly sums per drug match annual totals for high-volume drugs (D77 years only).

        WONDER suppresses monthly cells with < 10 deaths but still reports the annual aggregate,
        so monthly sums will be lower than annual totals whenever individual months are suppressed.
        Cannabis (T40.7) has persistent per-month suppression throughout the dataset and is
        excluded from this cross-check; its suppression behavior is covered by separate tests.
        All other queried drugs have counts well above 10 per month by 1999, so their monthly
        sums should exactly equal the annual totals.
        """
        SKIP_CODES = {"T40.7"}  # cannabis: chronic per-month suppression

        annual_rows = _load_csv(DRUG_YEAR_CSV)
        annual = {
            (int(r["year"]), r["drug_code"]): int(r["deaths"])
            for r in annual_rows
            if r["deaths"] and int(r["year"]) <= 2020 and r["drug_code"] not in SKIP_CODES
        }

        monthly_sums: dict[tuple, int] = {}
        for r in rows:
            if r["deaths"] and int(r["year"]) <= 2020 and r["drug_code"] not in SKIP_CODES:
                key = (int(r["year"]), r["drug_code"])
                monthly_sums[key] = monthly_sums.get(key, 0) + int(r["deaths"])

        mismatches = []
        for key, annual_total in annual.items():
            monthly_total = monthly_sums.get(key, 0)
            if annual_total != monthly_total:
                mismatches.append(f"{key}: annual={annual_total}, monthly sum={monthly_total}")

        assert not mismatches, "Monthly→annual sum mismatches:\n" + "\n".join(mismatches)


# ── parser unit tests (no network) ────────────────────────────────────────────

def _make_cell(label=None, value=None, is_total=False):
    cell = MagicMock()
    cell.label = label
    cell.value = value
    cell.get_numeric_value.return_value = (
        None if value in (None, "Suppressed")
        else float(value.replace(",", ""))
    )
    return cell


def _make_row(cells, is_total=False):
    row = MagicMock()
    row.cells = cells
    row.is_total = is_total
    return row


class TestFentanylParser:
    """Unit tests for the hierarchical 2-level parser in fetch_fentanyl_deaths."""

    def _import(self):
        from wonder.queries.fetch_fentanyl_deaths import parse_rows
        return parse_rows

    def test_hierarchical_year_carry_forward(self):
        parse_rows = self._import()
        client = MagicMock()

        xml_rows = [
            _make_row([_make_cell("1999"), _make_cell("Jan"), _make_cell(value="62")]),
            _make_row([_make_cell("Feb"), _make_cell(value="72")]),
            _make_row([_make_cell("2000"), _make_cell("Jan"), _make_cell(value="59")]),
        ]
        client.parse_response_table.return_value = xml_rows

        records = parse_rows(client, "<xml/>", provisional=False)
        assert len(records) == 3
        assert records[0] == {"year": 1999, "month": 1, "deaths": 62.0, "provisional": False}
        assert records[1] == {"year": 1999, "month": 2, "deaths": 72.0, "provisional": False}
        assert records[2] == {"year": 2000, "month": 1, "deaths": 59.0, "provisional": False}

    def test_totals_rows_are_skipped(self):
        parse_rows = self._import()
        client = MagicMock()

        xml_rows = [
            _make_row([_make_cell("1999"), _make_cell("Jan"), _make_cell(value="62")]),
            _make_row([], is_total=True),
        ]
        client.parse_response_table.return_value = xml_rows

        records = parse_rows(client, "<xml/>", provisional=False)
        assert len(records) == 1

    def test_suppressed_cells_produce_none(self):
        parse_rows = self._import()
        client = MagicMock()

        suppressed_cell = _make_cell(value="Suppressed")
        suppressed_cell.get_numeric_value.return_value = None

        xml_rows = [
            _make_row([_make_cell("1999"), _make_cell("Jan"), suppressed_cell]),
        ]
        client.parse_response_table.return_value = xml_rows

        records = parse_rows(client, "<xml/>", provisional=False)
        assert records[0]["deaths"] is None


class TestDrugDeathsByYearParser:
    """Unit tests for the hierarchical parser in fetch_drug_deaths."""

    def _import(self):
        from wonder.queries.fetch_drug_deaths import parse_rows
        return parse_rows

    def test_year_and_drug_first_row(self):
        parse_rows = self._import()
        client = MagicMock()

        xml_rows = [
            _make_row([_make_cell("1999"), _make_cell("Heroin"), _make_cell(value="2103")]),
            _make_row([_make_cell("Cocaine"), _make_cell(value="4494")]),
        ]
        client.parse_response_table.return_value = xml_rows

        records = parse_rows(client, "<xml/>", provisional=False)
        assert len(records) == 2
        assert records[0]["drug_code"] == "T40.1"
        assert records[0]["deaths"] == 2103.0
        assert records[1]["drug_code"] == "T40.5"
        assert records[1]["deaths"] == 4494.0
        assert records[0]["year"] == 1999
        assert records[1]["year"] == 1999

    def test_unknown_drug_label_is_skipped(self):
        parse_rows = self._import()
        client = MagicMock()

        xml_rows = [
            _make_row([_make_cell("1999"), _make_cell("Unknown substance"), _make_cell(value="10")]),
        ]
        client.parse_response_table.return_value = xml_rows

        records = parse_rows(client, "<xml/>", provisional=False)
        assert records == []


class TestDrugDeathsByMonthParser:
    """Unit tests for the flat 3-level parser in fetch_drug_deaths_monthly."""

    def _import(self):
        from wonder.queries.fetch_drug_deaths_monthly import parse_rows
        return parse_rows

    def test_flat_row_parsing(self):
        parse_rows = self._import()
        client = MagicMock()

        xml_rows = [
            _make_row([
                _make_cell("1999"),
                _make_cell("Jan., 1999"),
                _make_cell("Heroin"),
                _make_cell(value="186"),
            ]),
            _make_row([
                _make_cell("1999"),
                _make_cell("Jan., 1999"),
                _make_cell("Cocaine"),
                _make_cell(value="315"),
            ]),
        ]
        client.parse_response_table.return_value = xml_rows

        records = parse_rows(client, "<xml/>", provisional=False)
        assert len(records) == 2
        assert records[0] == {
            "year": 1999, "month": 1, "drug_code": "T40.1",
            "drug_name": "Heroin", "deaths": 186.0, "provisional": False,
        }
        assert records[1]["drug_code"] == "T40.5"
        assert records[1]["deaths"] == 315.0

    def test_suppressed_cell_becomes_none(self):
        parse_rows = self._import()
        client = MagicMock()

        suppressed = _make_cell(value="Suppressed")
        suppressed.get_numeric_value.return_value = None

        xml_rows = [
            _make_row([_make_cell("1999"), _make_cell("Jan., 1999"), _make_cell("Cannabis (derivatives)"), suppressed]),
        ]
        client.parse_response_table.return_value = xml_rows

        records = parse_rows(client, "<xml/>", provisional=False)
        assert records[0]["drug_code"] == "T40.7"
        assert records[0]["deaths"] is None

    def test_non_year_first_cell_is_skipped(self):
        parse_rows = self._import()
        client = MagicMock()

        xml_rows = [
            _make_row([_make_cell("Total"), _make_cell(""), _make_cell("Heroin"), _make_cell(value="100")]),
        ]
        client.parse_response_table.return_value = xml_rows

        records = parse_rows(client, "<xml/>", provisional=False)
        assert records == []

    def test_month_label_variations(self):
        """'Jan., 1999', 'January', 'Jan' all parse to month=1."""
        from wonder.queries.fetch_drug_deaths_monthly import _parse_month
        assert _parse_month("Jan., 1999") == 1
        assert _parse_month("January") == 1
        assert _parse_month("Jan") == 1
        assert _parse_month("Dec., 2024") == 12
        assert _parse_month("") is None


# ── integration tests (hits wonder.cdc.gov) ───────────────────────────────────

@pytest.mark.integration
class TestFentanylFetchIntegration:
    """Live fetch test — validates the full pipeline against CDC WONDER."""

    def test_fetch_produces_expected_rows(self, tmp_path):
        import subprocess
        result = subprocess.run(
            ["uv", "run", "python", "src/wonder/queries/fetch_fentanyl_deaths.py"],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        assert result.returncode == 0, result.stderr
        assert "312 rows" in result.stdout or "fentanyl-deaths-by-month.csv" in result.stdout


@pytest.mark.integration
class TestDrugDeathsFetchIntegration:
    def test_drug_deaths_by_year_produces_expected_rows(self):
        import subprocess
        result = subprocess.run(
            ["uv", "run", "python", "src/wonder/queries/fetch_drug_deaths.py"],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        assert result.returncode == 0, result.stderr

    def test_drug_deaths_by_month_produces_expected_rows(self):
        import subprocess
        result = subprocess.run(
            ["uv", "run", "python", "src/wonder/queries/fetch_drug_deaths_monthly.py"],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        assert result.returncode == 0, result.stderr
        assert "2184 rows" in result.stdout
