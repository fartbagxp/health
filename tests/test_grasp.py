"""
Tests for the GRASP module.

Run unit tests only (no network):
    uv run pytest tests/test_grasp.py -m "not integration"

Run integration tests (hits gis.cdc.gov and api.delphi.cmu.edu):
    uv run pytest tests/test_grasp.py -m integration -v
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

SRC = Path(__file__).parent.parent / "src"


# =============================================================================
# Dataset registry
# =============================================================================


class TestDatasets:
    def test_all_datasets_have_required_fields(self):
        from grasp.datasets import DATASETS, GraspDataset

        for key, ds in DATASETS.items():
            assert isinstance(ds, GraspDataset), key
            assert ds.url, f"{key} missing url"
            assert ds.name, f"{key} missing name"
            assert ds.description, f"{key} missing description"
            assert ds.years, f"{key} missing years"

    def test_known_datasets_present(self):
        from grasp.datasets import DATASETS

        assert "hantavirus" in DATASETS
        assert "fluview_ili" in DATASETS
        assert "fluview_clinical" in DATASETS
        assert "flusurv_net" in DATASETS

    def test_flusurv_net_metadata(self):
        from grasp.datasets import DATASETS

        ds = DATASETS["flusurv_net"]
        assert "delphi.cmu.edu" in ds.url
        assert "flusurv" in ds.url
        assert "2009-10" in ds.years
        assert "rate_overall" in ds.key_columns

    def test_flusurv_locations_completeness(self):
        from grasp.datasets import FLUSURV_LOCATIONS

        assert "network_all" in FLUSURV_LOCATIONS
        assert "network_eip" in FLUSURV_LOCATIONS
        assert "network_ihsp" in FLUSURV_LOCATIONS
        # 12 participating states
        state_codes = [k for k in FLUSURV_LOCATIONS if not k.startswith("network_")]
        assert len(state_codes) == 12

    def test_flusurv_locations_all_have_names(self):
        from grasp.datasets import FLUSURV_LOCATIONS

        for code, name in FLUSURV_LOCATIONS.items():
            assert name, f"Location {code} has empty name"


    def test_fluview_ili_metadata(self):
        from grasp.datasets import DATASETS

        ds = DATASETS["fluview_ili"]
        assert "delphi.cmu.edu" in ds.url
        assert "fluview" in ds.url
        assert "1997-98" in ds.years
        assert "wili" in ds.key_columns

    def test_fluview_clinical_metadata(self):
        from grasp.datasets import DATASETS

        ds = DATASETS["fluview_clinical"]
        assert "delphi.cmu.edu" in ds.url
        assert "fluview_clinical" in ds.url
        assert "2016-17" in ds.years
        assert "percent_positive" in ds.key_columns


# =============================================================================
# Client — flusurv_fetch / fluview_fetch / fluview_clinical_fetch
# =============================================================================


def _mock_delphi_response(rows: list[dict], result: int = 1) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {"result": result, "epidata": rows, "message": "success"}
    resp.raise_for_status = MagicMock()
    return resp


class TestFlusurvClient:
    def setup_method(self):
        # Clear module-level cache between tests
        import grasp.client as _client
        _client._CACHE.clear()
        _client._SESSION = None

    def test_calls_correct_endpoint(self):
        from grasp.client import flusurv_fetch

        with patch("requests.Session.get", return_value=_mock_delphi_response([])) as mock_get:
            flusurv_fetch(["network_all"], "202001")
            url = mock_get.call_args[0][0]
            assert "delphi.cmu.edu" in url
            assert "flusurv" in url

    def test_passes_locations_param(self):
        from grasp.client import flusurv_fetch

        with patch("requests.Session.get", return_value=_mock_delphi_response([])) as mock_get:
            flusurv_fetch(["CA", "OH"], "202001")
            params = mock_get.call_args[1]["params"]
            assert "CA" in params["locations"]
            assert "OH" in params["locations"]

    def test_passes_epiweeks_param(self):
        from grasp.client import flusurv_fetch

        with patch("requests.Session.get", return_value=_mock_delphi_response([])) as mock_get:
            flusurv_fetch(["network_all"], "202001-202026")
            params = mock_get.call_args[1]["params"]
            assert params["epiweeks"] == "202001-202026"

    def test_returns_epidata_array(self):
        from grasp.client import flusurv_fetch

        rows = [{"location": "network_all", "epiweek": 202001, "rate_overall": 5.3}]
        with patch("requests.Session.get", return_value=_mock_delphi_response(rows)):
            result = flusurv_fetch(["network_all"], "202001")
            assert result == rows

    def test_raises_on_api_error(self):
        from grasp.client import flusurv_fetch

        with patch(
            "requests.Session.get",
            return_value=_mock_delphi_response([], result=-2),
        ):
            # Override message to something meaningful
            mock_resp = _mock_delphi_response([], result=-2)
            mock_resp.json.return_value["message"] = "no results found"
            with patch("requests.Session.get", return_value=mock_resp):
                with pytest.raises(ValueError, match="Delphi flusurv API error"):
                    flusurv_fetch(["network_all"], "999999")

    def test_caches_identical_requests(self):
        from grasp.client import flusurv_fetch

        rows = [{"location": "network_all", "epiweek": 202001, "rate_overall": 5.3}]
        with patch("requests.Session.get", return_value=_mock_delphi_response(rows)) as mock_get:
            flusurv_fetch(["network_all"], "202001")
            flusurv_fetch(["network_all"], "202001")
            assert mock_get.call_count == 1

    def test_cache_miss_on_different_locations(self):
        from grasp.client import flusurv_fetch

        with patch("requests.Session.get", return_value=_mock_delphi_response([])) as mock_get:
            flusurv_fetch(["network_all"], "202001")
            flusurv_fetch(["CA"], "202001")
            assert mock_get.call_count == 2

    def test_cache_miss_on_different_epiweeks(self):
        from grasp.client import flusurv_fetch

        with patch("requests.Session.get", return_value=_mock_delphi_response([])) as mock_get:
            flusurv_fetch(["network_all"], "202001")
            flusurv_fetch(["network_all"], "202002")
            assert mock_get.call_count == 2

    def test_clear_cache_forces_refetch(self):
        from grasp.client import clear_cache, flusurv_fetch

        with patch("requests.Session.get", return_value=_mock_delphi_response([])) as mock_get:
            flusurv_fetch(["network_all"], "202001")
            clear_cache()
            flusurv_fetch(["network_all"], "202001")
            assert mock_get.call_count == 2


class TestFluviewClient:
    def setup_method(self):
        import grasp.client as _client
        _client._CACHE.clear()
        _client._SESSION = None

    def test_fluview_calls_correct_endpoint(self):
        from grasp.client import fluview_fetch

        with patch("requests.Session.get", return_value=_mock_delphi_response([])) as mock_get:
            fluview_fetch(["nat"], "202001")
            url = mock_get.call_args[0][0]
            assert "fluview" in url
            assert "delphi.cmu.edu" in url

    def test_fluview_does_not_call_fluview_clinical(self):
        from grasp.client import fluview_fetch

        with patch("requests.Session.get", return_value=_mock_delphi_response([])) as mock_get:
            fluview_fetch(["nat"], "202001")
            url = mock_get.call_args[0][0]
            # Must not hit the clinical endpoint
            assert "fluview_clinical" not in url

    def test_fluview_passes_regions_param(self):
        from grasp.client import fluview_fetch

        with patch("requests.Session.get", return_value=_mock_delphi_response([])) as mock_get:
            fluview_fetch(["nat", "ca"], "202001")
            params = mock_get.call_args[1]["params"]
            assert "nat" in params["regions"]
            assert "ca" in params["regions"]

    def test_fluview_clinical_calls_correct_endpoint(self):
        from grasp.client import fluview_clinical_fetch

        with patch("requests.Session.get", return_value=_mock_delphi_response([])) as mock_get:
            fluview_clinical_fetch(["nat"], "202001")
            url = mock_get.call_args[0][0]
            assert "fluview_clinical" in url

    def test_fluview_caches_requests(self):
        from grasp.client import fluview_fetch

        with patch("requests.Session.get", return_value=_mock_delphi_response([])) as mock_get:
            fluview_fetch(["nat"], "202001")
            fluview_fetch(["nat"], "202001")
            assert mock_get.call_count == 1

    def test_fluview_clinical_caches_requests(self):
        from grasp.client import fluview_clinical_fetch

        with patch("requests.Session.get", return_value=_mock_delphi_response([])) as mock_get:
            fluview_clinical_fetch(["nat"], "202001")
            fluview_clinical_fetch(["nat"], "202001")
            assert mock_get.call_count == 1

    def test_fluview_separate_cache_from_flusurv(self):
        from grasp.client import fluview_fetch, flusurv_fetch

        with patch("requests.Session.get", return_value=_mock_delphi_response([])) as mock_get:
            fluview_fetch(["nat"], "202001")
            flusurv_fetch(["network_all"], "202001")
            # Different endpoints → different cache keys → 2 calls
            assert mock_get.call_count == 2


# =============================================================================
# SDK — FluView functions
# =============================================================================

_ILI_SAMPLE = [
    {"region": "nat", "epiweek": 202001, "wili": 5.9, "ili": 6.2, "num_ili": 88731, "num_patients": 1426691, "num_providers": 2970},
    {"region": "nat", "epiweek": 202002, "wili": 4.1, "ili": 4.3, "num_ili": 75000, "num_patients": 1400000, "num_providers": 2900},
    {"region": "ca",  "epiweek": 202001, "wili": 4.9, "ili": 4.9, "num_ili": 5000,  "num_patients": 100000,  "num_providers": 200},
]

_CLINICAL_SAMPLE = [
    {"region": "nat", "epiweek": 202001, "total_specimens": 65177, "total_a": 5645, "total_b": 9664, "percent_positive": 23.5, "percent_a": 8.7, "percent_b": 14.8},
    {"region": "nat", "epiweek": 202002, "total_specimens": 60717, "total_a": 6109, "total_b": 7928, "percent_positive": 23.1, "percent_a": 10.1, "percent_b": 13.1},
]


class TestFluviewSDK:
    def setup_method(self):
        import grasp.client as _client
        _client._CACHE.clear()

    def test_get_fluview_ili_defaults_to_nat(self):
        from grasp.sdk import get_fluview_ili

        with patch("grasp.sdk.fluview_fetch", return_value=_ILI_SAMPLE) as mock_fetch:
            get_fluview_ili()
            assert mock_fetch.call_args[0][0] == ["nat"]

    def test_get_fluview_ili_accepts_string_region(self):
        from grasp.sdk import get_fluview_ili

        with patch("grasp.sdk.fluview_fetch", return_value=_ILI_SAMPLE) as mock_fetch:
            get_fluview_ili(regions="ca")
            assert mock_fetch.call_args[0][0] == ["ca"]

    def test_get_fluview_ili_accepts_list_regions(self):
        from grasp.sdk import get_fluview_ili

        with patch("grasp.sdk.fluview_fetch", return_value=_ILI_SAMPLE) as mock_fetch:
            get_fluview_ili(regions=["nat", "ca"])
            assert mock_fetch.call_args[0][0] == ["nat", "ca"]

    def test_get_fluview_ili_sorted_by_region_epiweek(self):
        from grasp.sdk import get_fluview_ili

        with patch("grasp.sdk.fluview_fetch", return_value=_ILI_SAMPLE):
            rows = get_fluview_ili(regions=["nat", "ca"])
            epiweeks_nat = [r["epiweek"] for r in rows if r["region"] == "nat"]
            assert epiweeks_nat == sorted(epiweeks_nat)

    def test_get_fluview_ili_passes_epiweeks(self):
        from grasp.sdk import get_fluview_ili

        with patch("grasp.sdk.fluview_fetch", return_value=_ILI_SAMPLE) as mock_fetch:
            get_fluview_ili(epiweeks="202001-202010")
            assert mock_fetch.call_args[0][1] == "202001-202010"

    def test_get_fluview_clinical_defaults_to_nat(self):
        from grasp.sdk import get_fluview_clinical

        with patch("grasp.sdk.fluview_clinical_fetch", return_value=_CLINICAL_SAMPLE) as mock_fetch:
            get_fluview_clinical()
            assert mock_fetch.call_args[0][0] == ["nat"]

    def test_get_fluview_clinical_returns_sorted_records(self):
        from grasp.sdk import get_fluview_clinical

        with patch("grasp.sdk.fluview_clinical_fetch", return_value=_CLINICAL_SAMPLE):
            rows = get_fluview_clinical()
            epiweeks = [r["epiweek"] for r in rows]
            assert epiweeks == sorted(epiweeks)

    def test_summarize_fluview_ili_by_region_fields(self):
        from grasp.sdk import summarize_fluview_ili_by_region

        with patch("grasp.sdk.fluview_fetch", return_value=_ILI_SAMPLE):
            rows = summarize_fluview_ili_by_region()
            for row in rows:
                assert "region" in row
                assert "peak_wili" in row
                assert "avg_wili" in row
                assert "weeks" in row

    def test_summarize_fluview_ili_by_region_sorted_by_peak_desc(self):
        from grasp.sdk import summarize_fluview_ili_by_region

        with patch("grasp.sdk.fluview_fetch", return_value=_ILI_SAMPLE):
            rows = summarize_fluview_ili_by_region()
            peaks = [r["peak_wili"] for r in rows]
            assert peaks == sorted(peaks, reverse=True)

    def test_summarize_fluview_ili_correct_peak(self):
        from grasp.sdk import summarize_fluview_ili_by_region

        with patch("grasp.sdk.fluview_fetch", return_value=_ILI_SAMPLE):
            rows = summarize_fluview_ili_by_region()
            by_region = {r["region"]: r for r in rows}
            assert by_region["nat"]["peak_wili"] == 5.9
            assert by_region["ca"]["peak_wili"] == 4.9


# =============================================================================
# SDK — FluSurv-NET functions
# =============================================================================

_SAMPLE_RECORDS = [
    {"location": "network_all", "season": "2019-20", "epiweek": 201940, "rate_overall": 0.1},
    {"location": "network_all", "season": "2019-20", "epiweek": 201952, "rate_overall": 4.5},
    {"location": "network_all", "season": "2019-20", "epiweek": 202001, "rate_overall": 5.3},
    {"location": "network_all", "season": "2018-19", "epiweek": 201840, "rate_overall": 0.2},
    {"location": "network_all", "season": "2018-19", "epiweek": 201852, "rate_overall": 3.1},
    {"location": "CA",          "season": "2019-20", "epiweek": 201940, "rate_overall": 0.3},
    {"location": "CA",          "season": "2019-20", "epiweek": 202001, "rate_overall": 4.9},
]


class TestFlusurvSDK:
    def setup_method(self):
        import grasp.client as _client
        _client._CACHE.clear()

    def _patch_fetch(self, records=_SAMPLE_RECORDS):
        return patch("grasp.sdk.flusurv_fetch", return_value=records)

    def test_get_flusurv_net_defaults_to_network_all(self):
        from grasp.sdk import get_flusurv_net

        with patch("grasp.sdk.flusurv_fetch", return_value=_SAMPLE_RECORDS) as mock_fetch:
            get_flusurv_net()
            locations_arg = mock_fetch.call_args[0][0]
            assert locations_arg == ["network_all"]

    def test_get_flusurv_net_accepts_string_location(self):
        from grasp.sdk import get_flusurv_net

        with patch("grasp.sdk.flusurv_fetch", return_value=_SAMPLE_RECORDS) as mock_fetch:
            get_flusurv_net(locations="CA")
            assert mock_fetch.call_args[0][0] == ["CA"]

    def test_get_flusurv_net_accepts_list_locations(self):
        from grasp.sdk import get_flusurv_net

        with patch("grasp.sdk.flusurv_fetch", return_value=_SAMPLE_RECORDS) as mock_fetch:
            get_flusurv_net(locations=["CA", "OH"])
            assert mock_fetch.call_args[0][0] == ["CA", "OH"]

    def test_get_flusurv_net_filters_by_season(self):
        from grasp.sdk import get_flusurv_net

        with self._patch_fetch():
            rows = get_flusurv_net(locations="network_all", season="2019-20")
            seasons = {r["season"] for r in rows}
            assert seasons == {"2019-20"}

    def test_get_flusurv_net_returns_sorted_by_location_epiweek(self):
        from grasp.sdk import get_flusurv_net

        with self._patch_fetch():
            rows = get_flusurv_net()
            epiweeks = [r["epiweek"] for r in rows if r["location"] == "network_all"]
            assert epiweeks == sorted(epiweeks)

    def test_summarize_flusurv_by_season_fields(self):
        from grasp.sdk import summarize_flusurv_by_season

        with patch("grasp.sdk.flusurv_fetch", return_value=_SAMPLE_RECORDS):
            rows = summarize_flusurv_by_season(location="network_all")
            assert len(rows) == 2
            for row in rows:
                assert "season" in row
                assert "peak_rate" in row
                assert "avg_rate" in row
                assert "weeks" in row

    def test_summarize_flusurv_by_season_correct_peak(self):
        from grasp.sdk import summarize_flusurv_by_season

        with patch("grasp.sdk.flusurv_fetch", return_value=_SAMPLE_RECORDS):
            rows = summarize_flusurv_by_season(location="network_all")
            by_season = {r["season"]: r for r in rows}
            assert by_season["2019-20"]["peak_rate"] == 5.3
            assert by_season["2018-19"]["peak_rate"] == 3.1

    def test_summarize_flusurv_by_season_sorted_chronologically(self):
        from grasp.sdk import summarize_flusurv_by_season

        with patch("grasp.sdk.flusurv_fetch", return_value=_SAMPLE_RECORDS):
            rows = summarize_flusurv_by_season(location="network_all")
            seasons = [r["season"] for r in rows]
            assert seasons == sorted(seasons)

    def test_summarize_flusurv_by_season_week_count(self):
        from grasp.sdk import summarize_flusurv_by_season

        # Real API scopes results to the requested location; mirror that here
        network_records = [r for r in _SAMPLE_RECORDS if r["location"] == "network_all"]
        with patch("grasp.sdk.flusurv_fetch", return_value=network_records):
            rows = summarize_flusurv_by_season(location="network_all")
            by_season = {r["season"]: r for r in rows}
            assert by_season["2019-20"]["weeks"] == 3
            assert by_season["2018-19"]["weeks"] == 2

    def test_summarize_flusurv_by_location_sorted_by_peak_desc(self):
        from grasp.sdk import summarize_flusurv_by_location

        with patch("grasp.sdk.flusurv_fetch", return_value=_SAMPLE_RECORDS):
            rows = summarize_flusurv_by_location(season="2019-20")
            peak_rates = [r["peak_rate"] for r in rows]
            assert peak_rates == sorted(peak_rates, reverse=True)

    def test_summarize_flusurv_by_location_includes_name(self):
        from grasp.sdk import summarize_flusurv_by_location

        with patch("grasp.sdk.flusurv_fetch", return_value=_SAMPLE_RECORDS):
            rows = summarize_flusurv_by_location(season="2019-20")
            for row in rows:
                assert "name" in row
                assert row["name"]  # non-empty

    def test_summarize_flusurv_by_location_filters_season(self):
        from grasp.sdk import summarize_flusurv_by_location

        with patch("grasp.sdk.flusurv_fetch", return_value=_SAMPLE_RECORDS):
            # With season filter, only records for that season contribute
            rows_2019 = summarize_flusurv_by_location(season="2019-20")
            rows_2018 = summarize_flusurv_by_location(season="2018-19")
            # network_all 2019-20 peak is 5.3, 2018-19 peak is 3.1
            peak_2019 = next(r for r in rows_2019 if r["location"] == "network_all")["peak_rate"]
            peak_2018 = next(r for r in rows_2018 if r["location"] == "network_all")["peak_rate"]
            assert peak_2019 == 5.3
            assert peak_2018 == 3.1


# =============================================================================
# CLI
# =============================================================================


class TestGraspCLI:
    def _run(self, *args, **kwargs):
        return subprocess.run(
            [sys.executable, "-m", "grasp", *args],
            capture_output=True,
            text=True,
            cwd=SRC,
            **kwargs,
        )

    def test_help(self):
        result = self._run("--help")
        assert result.returncode == 0
        assert "grasp" in result.stdout.lower()

    def test_list(self):
        result = self._run("list")
        assert result.returncode == 0
        assert "hantavirus" in result.stdout
        assert "flusurv_net" in result.stdout

    def test_flusurv_help(self):
        result = self._run("flusurv", "--help")
        assert result.returncode == 0
        assert "flusurv" in result.stdout.lower()

    def test_flusurv_by_season_help(self):
        result = self._run("flusurv", "by-season", "--help")
        assert result.returncode == 0
        assert "network_all" in result.stdout

    def test_flusurv_by_location_help(self):
        result = self._run("flusurv", "by-location", "--help")
        assert result.returncode == 0

    def test_flusurv_data_help(self):
        result = self._run("flusurv", "data", "--help")
        assert result.returncode == 0
        assert "--location" in result.stdout
        assert "--season" in result.stdout

    def test_hantavirus_help(self):
        result = self._run("hantavirus", "--help")
        assert result.returncode == 0

    def test_fluview_help(self):
        result = self._run("fluview", "--help")
        assert result.returncode == 0

    def test_fluview_ili_help(self):
        result = self._run("fluview", "ili", "--help")
        assert result.returncode == 0

    def test_fluview_ili_data_help(self):
        result = self._run("fluview", "ili", "data", "--help")
        assert result.returncode == 0
        assert "--region" in result.stdout
        assert "--epiweeks" in result.stdout

    def test_fluview_ili_by_region_help(self):
        result = self._run("fluview", "ili", "by-region", "--help")
        assert result.returncode == 0

    def test_fluview_clinical_help(self):
        result = self._run("fluview", "clinical", "--help")
        assert result.returncode == 0

    def test_fluview_clinical_data_help(self):
        result = self._run("fluview", "clinical", "data", "--help")
        assert result.returncode == 0
        assert "--region" in result.stdout

    def test_unknown_command_fails(self):
        result = self._run("nonexistent")
        assert result.returncode != 0


# =============================================================================
# Integration tests (hit real APIs)
# =============================================================================


@pytest.mark.integration
class TestFlusurvIntegration:
    """Live API calls — requires network access to api.delphi.cmu.edu."""

    def setup_method(self):
        import grasp.client as _client
        _client._CACHE.clear()

    def test_fetch_network_all_returns_data(self):
        from grasp.sdk import get_flusurv_net

        rows = get_flusurv_net(locations="network_all", season="2019-20")
        assert len(rows) > 0

    def test_response_has_required_fields(self):
        from grasp.sdk import get_flusurv_net

        rows = get_flusurv_net(locations="network_all", season="2019-20")
        required = {"location", "season", "epiweek", "rate_overall", "rate_flu_a", "rate_flu_b"}
        assert required.issubset(rows[0].keys()), f"Missing fields: {required - rows[0].keys()}"

    def test_response_has_age_rate_fields(self):
        from grasp.sdk import get_flusurv_net

        rows = get_flusurv_net(locations="network_all", season="2019-20")
        for i in range(5):
            assert f"rate_age_{i}" in rows[0], f"Missing rate_age_{i}"

    def test_all_known_locations_return_data(self):
        from grasp.datasets import FLUSURV_LOCATIONS
        from grasp.sdk import get_flusurv_net

        rows = get_flusurv_net(
            locations=list(FLUSURV_LOCATIONS.keys()),
            season="2019-20",
        )
        returned_locs = {r["location"] for r in rows}
        assert returned_locs == set(FLUSURV_LOCATIONS.keys()), (
            f"Missing locations: {set(FLUSURV_LOCATIONS.keys()) - returned_locs}"
        )

    def test_summarize_by_season_covers_expected_range(self):
        from grasp.sdk import summarize_flusurv_by_season

        rows = summarize_flusurv_by_season(location="network_all")
        seasons = {r["season"] for r in rows}
        # Spot-check known seasons
        assert "2009-10" in seasons
        assert "2017-18" in seasons  # notably severe season
        assert "2019-20" in seasons

    def test_summarize_by_season_peak_rates_are_positive(self):
        from grasp.sdk import summarize_flusurv_by_season

        rows = summarize_flusurv_by_season(location="network_all")
        for row in rows:
            assert row["peak_rate"] > 0, f"Non-positive peak in {row['season']}"
            assert row["avg_rate"] > 0, f"Non-positive avg in {row['season']}"
            assert row["weeks"] >= 20, f"Too few weeks in {row['season']}"

    def test_summarize_by_location_covers_all_locations(self):
        from grasp.datasets import FLUSURV_LOCATIONS
        from grasp.sdk import summarize_flusurv_by_location

        rows = summarize_flusurv_by_location(season="2019-20")
        returned_locs = {r["location"] for r in rows}
        assert returned_locs == set(FLUSURV_LOCATIONS.keys()), (
            f"Missing locations: {set(FLUSURV_LOCATIONS.keys()) - returned_locs}"
        )

    def test_cli_by_season_produces_valid_output(self):
        result = subprocess.run(
            [sys.executable, "-m", "grasp", "flusurv", "by-season",
             "--location", "network_all", "-f", "json"],
            capture_output=True,
            text=True,
            cwd=SRC,
        )
        assert result.returncode == 0, result.stderr
        rows = json.loads(result.stdout)
        assert isinstance(rows, list)
        assert len(rows) >= 10  # at least 10 flu seasons
        assert rows[0]["season"] < rows[-1]["season"]  # sorted chronologically

    def test_cli_by_location_produces_valid_output(self):
        result = subprocess.run(
            [sys.executable, "-m", "grasp", "flusurv", "by-location",
             "--season", "2019-20", "-f", "json"],
            capture_output=True,
            text=True,
            cwd=SRC,
        )
        assert result.returncode == 0, result.stderr
        rows = json.loads(result.stdout)
        assert len(rows) == 15  # all 15 locations
        # sorted by peak_rate descending
        assert rows[0]["peak_rate"] >= rows[-1]["peak_rate"]

    def test_cli_data_csv_output(self):
        result = subprocess.run(
            [sys.executable, "-m", "grasp", "flusurv", "data",
             "--location", "network_all", "--season", "2019-20", "-f", "csv"],
            capture_output=True,
            text=True,
            cwd=SRC,
        )
        assert result.returncode == 0, result.stderr
        lines = result.stdout.strip().splitlines()
        assert len(lines) >= 2  # header + data
        assert "epiweek" in lines[0]
        assert "rate_overall" in lines[0]


@pytest.mark.integration
class TestFluviewIntegration:
    """Live API calls — requires network access to api.delphi.cmu.edu."""

    def setup_method(self):
        import grasp.client as _client
        _client._CACHE.clear()

    def test_fluview_ili_national_returns_data(self):
        from grasp.sdk import get_fluview_ili

        rows = get_fluview_ili(regions="nat", epiweeks="202001-202010")
        assert len(rows) > 0

    def test_fluview_ili_has_required_fields(self):
        from grasp.sdk import get_fluview_ili

        rows = get_fluview_ili(regions="nat", epiweeks="202001")
        assert len(rows) == 1
        required = {"region", "epiweek", "wili", "ili", "num_ili", "num_patients", "num_providers"}
        assert required.issubset(rows[0].keys()), f"Missing: {required - rows[0].keys()}"

    def test_fluview_ili_state_level(self):
        from grasp.sdk import get_fluview_ili

        rows = get_fluview_ili(regions=["ca", "tx", "ny"], epiweeks="202001")
        regions = {r["region"] for r in rows}
        assert regions == {"ca", "tx", "ny"}

    def test_fluview_ili_covers_historical_range(self):
        from grasp.sdk import get_fluview_ili

        rows = get_fluview_ili(regions="nat", epiweeks="199740-200040")
        # Should have data back to 1997
        epiweeks = {r["epiweek"] for r in rows}
        assert any(ew < 200000 for ew in epiweeks), "Expected pre-2000 epiweeks"

    def test_fluview_clinical_returns_data(self):
        from grasp.sdk import get_fluview_clinical

        rows = get_fluview_clinical(regions="nat", epiweeks="202001-202010")
        assert len(rows) > 0

    def test_fluview_clinical_has_required_fields(self):
        from grasp.sdk import get_fluview_clinical

        rows = get_fluview_clinical(regions="nat", epiweeks="202001")
        required = {"region", "epiweek", "total_specimens", "total_a", "total_b",
                    "percent_positive", "percent_a", "percent_b"}
        assert required.issubset(rows[0].keys()), f"Missing: {required - rows[0].keys()}"

    def test_fluview_clinical_multi_region(self):
        from grasp.sdk import get_fluview_clinical

        rows = get_fluview_clinical(regions=["nat", "hhs1", "ca"], epiweeks="202001")
        regions = {r["region"] for r in rows}
        assert regions == {"nat", "hhs1", "ca"}

    def test_summarize_fluview_ili_by_region(self):
        from grasp.sdk import summarize_fluview_ili_by_region

        rows = summarize_fluview_ili_by_region(epiweeks="202001-202020")
        regions = {r["region"] for r in rows}
        # Should include national, all HHS, all census
        assert "nat" in regions
        assert all(f"hhs{i}" in regions for i in range(1, 11))
        assert all(f"cen{i}" in regions for i in range(1, 10))

    def test_cli_fluview_ili_json(self):
        result = subprocess.run(
            [sys.executable, "-m", "grasp", "fluview", "ili", "data",
             "--region", "nat", "--epiweeks", "202001-202005", "-f", "json"],
            capture_output=True, text=True, cwd=SRC,
        )
        assert result.returncode == 0, result.stderr
        rows = json.loads(result.stdout)
        assert len(rows) == 5
        assert rows[0]["region"] == "nat"
        assert "wili" in rows[0]

    def test_cli_fluview_ili_by_region(self):
        result = subprocess.run(
            [sys.executable, "-m", "grasp", "fluview", "ili", "by-region",
             "--epiweeks", "202001-202026", "-f", "json"],
            capture_output=True, text=True, cwd=SRC,
        )
        assert result.returncode == 0, result.stderr
        rows = json.loads(result.stdout)
        assert len(rows) == 20  # nat + 10 HHS + 9 census
        assert rows[0]["peak_wili"] >= rows[-1]["peak_wili"]  # sorted desc

    def test_cli_fluview_clinical_csv(self):
        result = subprocess.run(
            [sys.executable, "-m", "grasp", "fluview", "clinical", "data",
             "--region", "nat", "--epiweeks", "202001-202005", "-f", "csv"],
            capture_output=True, text=True, cwd=SRC,
        )
        assert result.returncode == 0, result.stderr
        lines = result.stdout.strip().splitlines()
        assert len(lines) == 6  # header + 5 rows
        assert "percent_positive" in lines[0]
