"""
Tests for the NIS (National Immunization Survey) parser and SDK.

Run unit tests only (no network):
    uv run pytest tests/test_nis.py -m "not integration"

Run integration tests (hits CDC FTP — large files, slow):
    uv run pytest tests/test_nis.py -m integration -v
"""

import sys
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nis.datasets import (
    CHILD_COLS,
    CHILD_GEO_COLS,
    CHILD_VAX_COLS,
    FIPS_TO_STATE,
    STATE_TO_FIPS,
    SURVEY_COLS,
    SURVEY_YEARS,
    TEEN_COLS,
    TEEN_VAX_COLS,
    CHILD_YEARS,
    TEEN_YEARS,
)
from nis.parser import _extract, parse_sas_columns, stream_dat
from nis.sdk import (
    _geo_key,
    get_national_rates,
    get_vaccination_rates,
    list_years,
    stream_records,
)


# =============================================================================
# SAS parser
# =============================================================================


_POINTER_SAS = """
DATA nis;
  INFILE 'NISPUF22.dat' lrecl=1000;
  INPUT
    @1   SEQNUMC   7.
    @8   YEAR      4.
    @12  RETEILI   2.
    @14  P_UTDDTP4 1.
    @15  P_UTDMMX  1.
    @16  SHOT_HES  1.
    @17  PROVWT_D  8.
    ;
RUN;
"""

_RANGE_SAS = """
DATA nis;
  INFILE 'NISTEENPUF22.dat';
  INPUT
    SEQNUMT 1-7
    YEAR    8-11
    STATE   12-13
    P_UTDTDAP 14-14
    SHOT_HES  15-15
    PROVWT_C  16-23
    ;
RUN;
"""

_COMMENT_SAS = """
DATA nis;
  /* This is a block comment */
  INFILE 'NISPUF22.dat' lrecl=1000;
  INPUT
    /* sequence number */ @1  SEQNUMC 7.
    @8   YEAR    4.   /* survey year */
    @12  STATE   2.
    * This line comment should be ignored ;
    @14  P_UTDMMX 1.
    ;
RUN;
"""


class TestParseSASColumns:
    def test_pointer_notation_parses_all_columns(self):
        cols = parse_sas_columns(_POINTER_SAS)
        assert set(cols.keys()) == {
            "SEQNUMC", "YEAR", "RETEILI", "P_UTDDTP4", "P_UTDMMX", "SHOT_HES", "PROVWT_D"
        }

    def test_pointer_notation_positions_are_zero_indexed(self):
        cols = parse_sas_columns(_POINTER_SAS)
        # @1 width 7 → (0, 7)
        assert cols["SEQNUMC"] == (0, 7)
        # @8 width 4 → (7, 11)
        assert cols["YEAR"] == (7, 11)
        # @17 width 8 → (16, 24)
        assert cols["PROVWT_D"] == (16, 24)

    def test_pointer_notation_single_char_columns(self):
        cols = parse_sas_columns(_POINTER_SAS)
        assert cols["P_UTDDTP4"] == (13, 14)
        assert cols["P_UTDMMX"] == (14, 15)
        assert cols["SHOT_HES"] == (15, 16)

    def test_range_notation_parses_all_columns(self):
        cols = parse_sas_columns(_RANGE_SAS)
        assert set(cols.keys()) == {
            "SEQNUMT", "YEAR", "STATE", "P_UTDTDAP", "SHOT_HES", "PROVWT_C"
        }

    def test_range_notation_positions_are_zero_indexed(self):
        cols = parse_sas_columns(_RANGE_SAS)
        # SEQNUMT 1-7 → (0, 7)
        assert cols["SEQNUMT"] == (0, 7)
        # YEAR 8-11 → (7, 11)
        assert cols["YEAR"] == (7, 11)
        # STATE 12-13 → (11, 13)
        assert cols["STATE"] == (11, 13)

    def test_variable_names_uppercased(self):
        sas = "DATA x; INFILE 'f.dat'; INPUT @1 seqnum 7. @8 year 4.; RUN;"
        cols = parse_sas_columns(sas)
        assert "SEQNUM" in cols
        assert "YEAR" in cols

    def test_block_comments_stripped(self):
        cols = parse_sas_columns(_COMMENT_SAS)
        assert "STATE" in cols
        assert "P_UTDMMX" in cols

    def test_line_comments_stripped(self):
        cols = parse_sas_columns(_COMMENT_SAS)
        # Line comment "* This line comment... ;" should not produce a column
        assert "THIS" not in cols
        assert "LINE" not in cols

    def test_no_input_block_returns_empty(self):
        sas = "DATA x; INFILE 'f.dat'; RUN;"  # no INPUT statement
        assert parse_sas_columns(sas) == {}

    def test_empty_string_returns_empty(self):
        assert parse_sas_columns("") == {}

    def test_pointer_preferred_over_range_when_both_present(self):
        # Pointer notation (@) should win because we try it first
        sas = "DATA x; INFILE 'f.dat'; INPUT @1 A 3. @4 B 2.; RUN;"
        cols = parse_sas_columns(sas)
        assert cols["A"] == (0, 3)
        assert cols["B"] == (3, 5)

    def test_slicing_gives_correct_field_values(self):
        cols = parse_sas_columns(_POINTER_SAS)
        # Build a fake fixed-width record matching the layout:
        # SEQNUMC(0-7) YEAR(7-11) RETEILI(11-13) P_UTDDTP4(13) P_UTDMMX(14)
        # SHOT_HES(15) PROVWT_D(16-24)
        line = "1234567202206111" + "1234.567"
        assert line[0:7] == "1234567"
        assert line[7:11] == "2022"
        assert line[11:13] == "06"
        assert line[13:14] == "1"
        assert line[14:15] == "1"
        assert line[15:16] == "1"
        assert line[16:24] == "1234.567"


# =============================================================================
# _extract helper
# =============================================================================


class TestExtract:
    def test_extracts_fields_correctly(self):
        cols = {"A": (0, 3), "B": (3, 6), "C": (6, 9)}
        row = _extract("abcdefghi", cols)
        assert row == {"A": "abc", "B": "def", "C": "ghi"}

    def test_strips_whitespace(self):
        cols = {"A": (0, 5)}
        row = _extract(" hi  ", cols)
        assert row["A"] == "hi"

    def test_returns_empty_string_when_line_too_short(self):
        cols = {"A": (0, 3), "LONG": (100, 110)}
        row = _extract("abc", cols)
        assert row["A"] == "abc"
        assert row["LONG"] == ""

    def test_empty_line_returns_empty_values(self):
        cols = {"A": (0, 3)}
        row = _extract("", cols)
        assert row["A"] == ""


# =============================================================================
# stream_dat  (mocked HTTP)
# =============================================================================


def _fake_response(lines: list[str]) -> MagicMock:
    """Build a mock requests.Response that streams the given lines."""
    content = b"\n".join(line.encode("latin-1") for line in lines) + b"\n"
    mock = MagicMock()
    mock.raise_for_status = MagicMock()

    # iter_content returns one chunk per call
    def _iter_content(chunk_size=65536):
        yield content

    mock.iter_content.side_effect = _iter_content
    return mock


_SIMPLE_COLS = {"NAME": (0, 7), "YEAR": (7, 11), "STATE": (11, 13), "UTD": (13, 14)}
# Each line: NAME(7) + YEAR(4) + STATE(2) + UTD(1) = 14 chars, no gaps
_LINES = [
    "1234567" + "2022" + "06" + "1",   # NAME=1234567, YEAR=2022, STATE=06, UTD=1
    "7654321" + "2021" + "48" + "0",   # NAME=7654321, YEAR=2021, STATE=48, UTD=0
    "9999999" + "2020" + "48" + "1",   # NAME=9999999, YEAR=2020, STATE=48, UTD=1
    "",                                 # blank line — should be skipped
]


class TestStreamDat:
    def test_yields_one_dict_per_non_empty_line(self):
        with patch("nis.parser.requests.get", return_value=_fake_response(_LINES)):
            rows = list(stream_dat("http://fake.url/data.dat", _SIMPLE_COLS))
        assert len(rows) == 3  # blank line skipped

    def test_extracts_correct_field_values(self):
        with patch("nis.parser.requests.get", return_value=_fake_response(_LINES)):
            rows = list(stream_dat("http://fake.url/data.dat", _SIMPLE_COLS))
        assert rows[0]["NAME"] == "1234567"
        assert rows[0]["YEAR"] == "2022"
        assert rows[0]["STATE"] == "06"
        assert rows[0]["UTD"] == "1"

    def test_second_row_parsed_correctly(self):
        with patch("nis.parser.requests.get", return_value=_fake_response(_LINES)):
            rows = list(stream_dat("http://fake.url/data.dat", _SIMPLE_COLS))
        assert rows[1]["NAME"] == "7654321"
        assert rows[1]["UTD"] == "0"

    def test_select_filters_columns(self):
        with patch("nis.parser.requests.get", return_value=_fake_response(_LINES)):
            rows = list(
                stream_dat("http://fake.url/data.dat", _SIMPLE_COLS, select={"UTD", "STATE"})
            )
        assert set(rows[0].keys()) == {"UTD", "STATE"}
        assert "NAME" not in rows[0]

    def test_select_none_returns_all_columns(self):
        with patch("nis.parser.requests.get", return_value=_fake_response(_LINES)):
            rows = list(stream_dat("http://fake.url/data.dat", _SIMPLE_COLS, select=None))
        assert set(rows[0].keys()) == set(_SIMPLE_COLS.keys())

    def test_empty_response_yields_nothing(self):
        with patch("nis.parser.requests.get", return_value=_fake_response([])):
            rows = list(stream_dat("http://fake.url/data.dat", _SIMPLE_COLS))
        assert rows == []

    def test_raises_on_http_error(self):
        mock = MagicMock()
        mock.raise_for_status.side_effect = Exception("404 Not Found")
        with patch("nis.parser.requests.get", return_value=mock):
            with pytest.raises(Exception, match="404"):
                list(stream_dat("http://fake.url/data.dat", _SIMPLE_COLS))

    def test_handles_chunk_boundary(self):
        # Split a two-line record across two chunks to verify the leftover-buffer logic.
        line1 = b"1234567202206 1"
        line2 = b"7654321202148 0"
        content = line1 + b"\n" + line2 + b"\n"
        # Split in the middle of line2
        split = len(line1) + 1 + 4
        chunk1, chunk2 = content[:split], content[split:]

        mock = MagicMock()
        mock.raise_for_status = MagicMock()

        def _iter_content(chunk_size=65536):
            yield chunk1
            yield chunk2

        mock.iter_content.side_effect = _iter_content
        with patch("nis.parser.requests.get", return_value=mock):
            rows = list(stream_dat("http://fake.url/data.dat", _SIMPLE_COLS))
        assert len(rows) == 2
        assert rows[0]["YEAR"] == "2022"
        assert rows[1]["YEAR"] == "2021"

    def test_uses_correct_url(self):
        with patch("nis.parser.requests.get", return_value=_fake_response([])) as mock_get:
            list(stream_dat("http://example.com/NISPUF22.DAT", _SIMPLE_COLS))
        mock_get.assert_called_once()
        assert mock_get.call_args[0][0] == "http://example.com/NISPUF22.DAT"

    def test_streams_with_stream_true(self):
        with patch("nis.parser.requests.get", return_value=_fake_response([])) as mock_get:
            list(stream_dat("http://fake.url/data.dat", _SIMPLE_COLS))
        kwargs = mock_get.call_args[1]
        assert kwargs.get("stream") is True


# =============================================================================
# Dataset registry
# =============================================================================


class TestDatasetRegistry:
    def test_child_years_span_2011_to_2022(self):
        assert min(CHILD_YEARS) == 2011
        assert max(CHILD_YEARS) == 2022

    def test_teen_years_span_2011_to_2022(self):
        assert min(TEEN_YEARS) == 2011
        assert max(TEEN_YEARS) == 2022

    def test_all_child_years_have_dat_and_sas_urls(self):
        for year, entry in CHILD_YEARS.items():
            assert entry.dat_url.endswith(".DAT"), f"child {year}: dat_url wrong suffix"
            assert ".sas" in entry.sas_url.lower(), f"child {year}: sas_url missing .sas"

    def test_all_teen_years_have_dat_and_sas_urls(self):
        for year, entry in TEEN_YEARS.items():
            assert entry.dat_url.endswith(".DAT"), f"teen {year}: dat_url wrong suffix"
            assert ".sas" in entry.sas_url.lower(), f"teen {year}: sas_url missing .sas"

    def test_child_url_pattern_contains_year(self):
        entry = CHILD_YEARS[2022]
        assert "22" in entry.dat_url
        assert "22" in entry.sas_url

    def test_teen_url_pattern_contains_year(self):
        entry = TEEN_YEARS[2019]
        assert "19" in entry.dat_url
        assert "19" in entry.sas_url

    def test_child_and_teen_urls_are_different(self):
        for year in range(2011, 2023):
            child_dat = CHILD_YEARS[year].dat_url
            teen_dat = TEEN_YEARS[year].dat_url
            assert child_dat != teen_dat, f"year {year}: child and teen share same dat_url"

    def test_all_years_on_cdc_ftp(self):
        ftp = "https://ftp.cdc.gov/pub/health_statistics/nchs/datasets/nis"
        for entry in list(CHILD_YEARS.values()) + list(TEEN_YEARS.values()):
            assert entry.dat_url.startswith(ftp)
            assert entry.sas_url.startswith(ftp)

    def test_year_field_matches_dict_key(self):
        for year, entry in CHILD_YEARS.items():
            assert entry.year == year
        for year, entry in TEEN_YEARS.items():
            assert entry.year == year


class TestColumnDefinitions:
    def test_child_vax_cols_all_start_with_p_utd(self):
        for col in CHILD_VAX_COLS:
            assert col.startswith("P_UTD"), f"unexpected non-UTD col: {col}"

    def test_teen_vax_cols_all_start_with_p_utd(self):
        for col in TEEN_VAX_COLS:
            assert col.startswith("P_UTD"), f"unexpected non-UTD col: {col}"

    def test_child_cols_is_superset_of_vax_and_geo(self):
        assert CHILD_VAX_COLS <= CHILD_COLS
        assert CHILD_GEO_COLS <= CHILD_COLS

    def test_survey_cols_map_contains_both_surveys(self):
        assert "child" in SURVEY_COLS
        assert "teen" in SURVEY_COLS

    def test_child_has_weight_col(self):
        assert "PROVWT_D" in CHILD_COLS

    def test_teen_has_weight_col(self):
        assert "PROVWT_C" in TEEN_COLS

    def test_both_surveys_have_hesitancy_col(self):
        assert "SHOT_HES" in CHILD_COLS
        assert "SHOT_HES" in TEEN_COLS

    def test_known_child_vaccines_present(self):
        expected = {"P_UTDMMX", "P_UTDDTP4", "P_UTDPOL3", "P_UTDHEP_B", "P_UTDVAR"}
        assert expected <= CHILD_VAX_COLS

    def test_known_teen_vaccines_present(self):
        expected = {"P_UTDTDAP", "P_UTDMCV4", "P_UTDHPV13"}
        assert expected <= TEEN_VAX_COLS


class TestFIPSLookup:
    def test_fips_to_state_has_50_states_plus_dc(self):
        # 50 states + DC + PR + USVI = at least 53
        assert len(FIPS_TO_STATE) >= 53

    def test_california_fips(self):
        assert FIPS_TO_STATE["06"] == "California"

    def test_new_york_fips(self):
        assert FIPS_TO_STATE["36"] == "New York"

    def test_dc_fips(self):
        assert FIPS_TO_STATE["11"] == "District of Columbia"

    def test_state_to_fips_roundtrip(self):
        for fips, name in FIPS_TO_STATE.items():
            assert STATE_TO_FIPS[name.upper()] == fips

    def test_state_to_fips_all_uppercase_keys(self):
        for key in STATE_TO_FIPS:
            assert key == key.upper(), f"state key not uppercase: {key}"


# =============================================================================
# SDK (mocked HTTP)
# =============================================================================


# Pre-parsed respondent dicts used by SDK-level tests.
# Patching stream_dat to return these avoids the shared-requests-module problem
# (nis.sdk.requests and nis.parser.requests are the same singleton; the second
# patch always wins, so both calls would get the wrong mock).
_SAMPLE_ROWS = [
    # RETEILI 06 = California (3 records)
    {"RETEILI": "06", "STATE": "", "P_UTDDTP4": "1", "P_UTDMMX": "1", "SHOT_HES": "0", "PROVWT_D": "1234.567"},
    {"RETEILI": "06", "STATE": "", "P_UTDDTP4": "1", "P_UTDMMX": "0", "SHOT_HES": "1", "PROVWT_D": "2345.678"},
    {"RETEILI": "06", "STATE": "", "P_UTDDTP4": "0", "P_UTDMMX": "1", "SHOT_HES": "0", "PROVWT_D": "3456.789"},
    # RETEILI 36 = New York (2 records)
    {"RETEILI": "36", "STATE": "", "P_UTDDTP4": "1", "P_UTDMMX": "1", "SHOT_HES": "0", "PROVWT_D": "4567.890"},
    {"RETEILI": "36", "STATE": "", "P_UTDDTP4": "0", "P_UTDMMX": "0", "SHOT_HES": "1", "PROVWT_D": "5678.901"},
]

# Fake column map returned by the patched _fetch_columns
_FAKE_COLS: dict[str, tuple[int, int]] = {
    "RETEILI": (11, 13), "STATE": (0, 0),
    "P_UTDDTP4": (13, 14), "P_UTDMMX": (14, 15),
    "SHOT_HES": (15, 16), "PROVWT_D": (16, 24),
}


class TestListYears:
    def test_child_returns_sorted_list(self):
        years = list_years("child")
        assert years == sorted(years)
        assert years[0] == 2011
        assert years[-1] == 2022

    def test_teen_returns_sorted_list(self):
        years = list_years("teen")
        assert years == sorted(years)

    def test_unknown_survey_raises(self):
        with pytest.raises(ValueError, match="child.*teen"):
            list_years("adult")


class TestGeoKey:
    def test_returns_zero_padded_fips(self):
        assert _geo_key({"STATE": "6"}, "teen") == "06"
        assert _geo_key({"RETEILI": "6"}, "child") == "06"

    def test_two_digit_fips_returned_as_is(self):
        assert _geo_key({"STATE": "36"}, "teen") == "36"

    def test_prefers_state_over_reteili(self):
        rec = {"STATE": "06", "RETEILI": "48"}
        assert _geo_key(rec, "teen") == "06"

    def test_falls_back_to_reteili_when_no_state(self):
        rec = {"RETEILI": "48"}
        assert _geo_key(rec, "child") == "48"

    def test_empty_record_returns_empty(self):
        assert _geo_key({}, "child") == ""
        assert _geo_key({}, "teen") == ""

    def test_non_numeric_returns_empty(self):
        assert _geo_key({"STATE": "XX"}, "teen") == ""


def _sdk_patches(rows=None):
    """Return a pair of patches that bypass all HTTP for SDK-level tests.

    Patches nis.sdk._fetch_columns (returns _FAKE_COLS) and
    nis.sdk.stream_dat (yields pre-built dicts from *rows*).
    This avoids the shared-requests-module problem where both
    nis.sdk.requests and nis.parser.requests are the same singleton.
    """
    rows = rows if rows is not None else _SAMPLE_ROWS
    return (
        patch("nis.sdk._fetch_columns", return_value=_FAKE_COLS),
        patch("nis.sdk.stream_dat", return_value=iter(rows)),
    )


class TestStreamRecords:
    def test_yields_dict_per_record(self):
        with _sdk_patches()[0], _sdk_patches()[1]:
            rows = list(stream_records("child", 2022))
        assert len(rows) == 5

    def test_records_have_expected_keys(self):
        p1, p2 = patch("nis.sdk._fetch_columns", return_value=_FAKE_COLS), \
                  patch("nis.sdk.stream_dat", return_value=iter(_SAMPLE_ROWS))
        with p1, p2:
            rows = list(stream_records("child", 2022))
        assert "RETEILI" in rows[0]
        assert "P_UTDMMX" in rows[0]

    def test_state_filter_by_fips(self):
        p1 = patch("nis.sdk._fetch_columns", return_value=_FAKE_COLS)
        p2 = patch("nis.sdk.stream_dat", return_value=iter(_SAMPLE_ROWS))
        with p1, p2:
            rows = list(stream_records("child", 2022, state="06"))
        assert len(rows) == 3  # only CA records

    def test_state_filter_by_full_name(self):
        p1 = patch("nis.sdk._fetch_columns", return_value=_FAKE_COLS)
        p2 = patch("nis.sdk.stream_dat", return_value=iter(_SAMPLE_ROWS))
        with p1, p2:
            rows = list(stream_records("child", 2022, state="New York"))
        assert len(rows) == 2  # only NY records

    def test_unknown_survey_raises(self):
        with pytest.raises(ValueError, match="Unknown survey"):
            list(stream_records("unknown", 2022))

    def test_unknown_year_raises(self):
        with pytest.raises(ValueError, match="not in registry"):
            list(stream_records("child", 1999))

    def test_unknown_state_raises(self):
        p1 = patch("nis.sdk._fetch_columns", return_value=_FAKE_COLS)
        p2 = patch("nis.sdk.stream_dat", return_value=iter(_SAMPLE_ROWS))
        with p1, p2:
            with pytest.raises(ValueError, match="Unknown state"):
                list(stream_records("child", 2022, state="Narnia"))

    def test_no_matching_columns_raises_runtime_error(self):
        with patch("nis.sdk._fetch_columns", return_value={}):
            with pytest.raises(RuntimeError, match="No matching columns"):
                list(stream_records("child", 2022))


class TestGetVaccinationRates:
    def _run(self, rows=None, vaccines=None):
        rows = rows if rows is not None else _SAMPLE_ROWS
        p1 = patch("nis.sdk._fetch_columns", return_value=_FAKE_COLS)
        p2 = patch("nis.sdk.stream_dat", return_value=iter(rows))
        with p1, p2:
            return get_vaccination_rates(
                "child", 2022,
                vaccines=vaccines or ["P_UTDDTP4", "P_UTDMMX"],
            )

    def test_returns_one_row_per_state(self):
        rows = self._run()
        fips_codes = {r["state_fips"] for r in rows}
        assert fips_codes == {"06", "36"}

    def test_row_has_required_keys(self):
        row = self._run()[0]
        assert "state_fips" in row
        assert "state_name" in row
        assert "year" in row
        assert "survey" in row
        assert "n_respondents" in row

    def test_pct_columns_present_for_each_vaccine(self):
        rows = self._run(vaccines=["P_UTDMMX"])
        assert "P_UTDMMX_pct" in rows[0]
        assert "P_UTDMMX_n" in rows[0]
        assert "P_UTDMMX_denominator" in rows[0]

    def test_california_mmr_utd_rate(self):
        # CA records: MMR = 1, 0, 1 → 2/3 = 66.7%
        rows = self._run(vaccines=["P_UTDMMX"])
        ca = next(r for r in rows if r["state_fips"] == "06")
        assert ca["P_UTDMMX_pct"] == pytest.approx(66.7, abs=0.1)
        assert ca["P_UTDMMX_n"] == 2
        assert ca["P_UTDMMX_denominator"] == 3

    def test_new_york_dtap_utd_rate(self):
        # NY records: P_UTDDTP4 = 1, 0 → 1/2 = 50%
        rows = self._run(vaccines=["P_UTDDTP4"])
        ny = next(r for r in rows if r["state_fips"] == "36")
        assert ny["P_UTDDTP4_pct"] == pytest.approx(50.0, abs=0.1)

    def test_hesitancy_rate_california(self):
        # CA records: SHOT_HES = 0, 1, 0 → 1/3 = 33.3%
        rows = self._run()
        ca = next(r for r in rows if r["state_fips"] == "06")
        assert ca["hesitancy_pct"] == pytest.approx(33.3, abs=0.1)
        assert ca["hesitancy_n"] == 1

    def test_state_name_resolved_from_fips(self):
        rows = self._run()
        names = {r["state_name"] for r in rows}
        assert "California" in names
        assert "New York" in names

    def test_n_respondents_correct(self):
        rows = self._run()
        total = sum(r["n_respondents"] for r in rows)
        assert total == 5

    def test_pct_is_none_when_no_valid_values(self):
        # Records where the UTD columns are blank → no valid 0/1 values
        blank_rows = [
            {"RETEILI": "06", "STATE": "", "P_UTDDTP4": "", "P_UTDMMX": "", "SHOT_HES": "0", "PROVWT_D": "1.0"},
        ]
        rows = self._run(rows=blank_rows, vaccines=["P_UTDDTP4", "P_UTDMMX"])
        ca = next(r for r in rows if r["state_fips"] == "06")
        assert ca["P_UTDDTP4_pct"] is None
        assert ca["P_UTDMMX_pct"] is None


class TestGetNationalRates:
    def _run(self, rows=None, vaccines=None):
        rows = rows if rows is not None else _SAMPLE_ROWS
        p1 = patch("nis.sdk._fetch_columns", return_value=_FAKE_COLS)
        p2 = patch("nis.sdk.stream_dat", return_value=iter(rows))
        with p1, p2:
            return get_national_rates(
                "child", 2022,
                vaccines=vaccines or ["P_UTDDTP4", "P_UTDMMX"],
            )

    def test_returns_single_national_row(self):
        result = self._run()
        assert result["state_fips"] == "00"
        assert result["state_name"] == "National"

    def test_national_mmr_pct_across_all_states(self):
        # All 5 records: MMR = 1,0,1,1,0 → 3/5 = 60%
        result = self._run(vaccines=["P_UTDMMX"])
        assert result["P_UTDMMX_pct"] == pytest.approx(60.0, abs=0.1)
        assert result["P_UTDMMX_n"] == 3
        assert result["P_UTDMMX_denominator"] == 5

    def test_national_dtap_pct(self):
        # All 5 records: DTaP = 1,1,0,1,0 → 3/5 = 60%
        result = self._run(vaccines=["P_UTDDTP4"])
        assert result["P_UTDDTP4_pct"] == pytest.approx(60.0, abs=0.1)

    def test_national_n_respondents(self):
        result = self._run()
        assert result["n_respondents"] == 5

    def test_empty_result_returns_empty_dict(self):
        p1 = patch("nis.sdk._fetch_columns", return_value=_FAKE_COLS)
        p2 = patch("nis.sdk.stream_dat", return_value=iter([]))
        with p1, p2:
            result = get_national_rates("child", 2022, vaccines=["P_UTDMMX"])
        assert result == {}


# =============================================================================
# Integration tests (hit real CDC FTP — requires network, large files)
# =============================================================================


@pytest.mark.integration
class TestNISIntegration:
    """Live tests that fetch the real SAS codebook from the CDC FTP server.

    The DAT files are large (50–200 MB) so these tests only fetch the SAS
    codebook and verify a handful of well-known column positions.  Full
    end-to-end streaming is tested manually.
    """

    def test_child_2022_sas_codebook_fetchable(self):
        import requests

        entry = CHILD_YEARS[2022]
        resp = requests.get(entry.sas_url, timeout=30)
        assert resp.status_code == 200
        assert len(resp.text) > 1000

    def test_child_2022_sas_contains_known_columns(self):
        import requests

        entry = CHILD_YEARS[2022]
        resp = requests.get(entry.sas_url, timeout=30)
        cols = parse_sas_columns(resp.text)
        # These columns exist in every recent NIS-Child release
        assert "SEQNUMC" in cols, "SEQNUMC not in 2022 child codebook"
        assert "RETEILI" in cols, "RETEILI not in 2022 child codebook"

    def test_teen_2022_sas_codebook_fetchable(self):
        import requests

        entry = TEEN_YEARS[2022]
        resp = requests.get(entry.sas_url, timeout=30)
        assert resp.status_code == 200
        assert len(resp.text) > 1000

    def test_teen_2022_sas_contains_known_columns(self):
        import requests

        entry = TEEN_YEARS[2022]
        resp = requests.get(entry.sas_url, timeout=30)
        cols = parse_sas_columns(resp.text)
        assert "SEQNUMT" in cols or "SEQNUMS" in cols, \
            "Neither SEQNUMT nor SEQNUMS found in 2022 teen codebook"

    def test_list_years_child(self):
        years = list_years("child")
        assert 2022 in years
        assert 2011 in years

    def test_list_years_teen(self):
        years = list_years("teen")
        assert 2022 in years
