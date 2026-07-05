"""
Tests for the SEER module.

Run unit tests only (no network):
    uv run pytest tests/test_seer.py -m "not integration"

Run integration tests (hits seer.cancer.gov):
    uv run pytest tests/test_seer.py -m integration -v
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# =============================================================================
# Catalog (bundled snapshot, no network)
# =============================================================================


class TestCatalog:
    def test_cancer_sites_loaded(self):
        from seer.catalog import cancer_sites

        sites = cancer_sites()
        assert len(sites) > 50
        assert sites["1"] == "All Cancer Sites Combined"
        assert sites["55"] == "Breast"

    def test_find_site_case_insensitive(self):
        from seer.catalog import find_site

        results = dict(find_site("BREAST"))
        assert "55" in results
        assert results["55"] == "Breast"

    def test_find_site_no_match(self):
        from seer.catalog import find_site

        assert find_site("not-a-real-cancer-site") == []

    def test_variable_formats_has_expected_fields(self):
        from seer.catalog import variable_formats

        vf = variable_formats()
        for field in ["sex", "race", "age_range", "site", "data_type", "rate_type"]:
            assert field in vf


# =============================================================================
# SDK response parsing (mocked client)
# =============================================================================


_FAKE_RESP = {
    "info": {
        "y-axis": "rate",
        "x-axis": "year",
        "key-order": ["sex", "race", "age_range", "site"],
        "data-fields": [
            "year",
            "rate",
            "rate_lower_ci",
            "rate_upper_ci",
            "modeled_rate",
            "count",
        ],
    },
    "data": {
        "3_1_1_55": {
            "data_series": [
                [2020, "19.4", "19.2", "19.6", "19.5", 42273],
                [2021, "19.2", "19.0", "19.4", "19.1", 42310],
            ]
        }
    },
}


class TestSdkParsing:
    def test_get_trend_parses_dims_and_labels(self):
        from seer import sdk

        with patch.object(sdk, "_get_client") as get_client:
            get_client.return_value.get_chart_data.return_value = _FAKE_RESP
            rows = sdk.get_trend(site=55, sex="female")

        assert len(rows) == 2
        assert rows[0]["sex"] == "3"
        assert rows[0]["sex_label"] == "Female"
        assert rows[0]["site_label"] == "Breast"
        assert rows[0]["year"] == 2020
        assert rows[0]["rate"] == "19.4"
        assert rows[1]["year"] == 2021

    def test_get_trend_builds_expected_params(self):
        from seer import sdk

        with patch.object(sdk, "_get_client") as get_client:
            get_client.return_value.get_chart_data.return_value = _FAKE_RESP
            sdk.get_trend(site=55, sex="female", compare_by="race")

        params = get_client.return_value.get_chart_data.call_args[0][0]
        assert params["site"] == 55
        assert params["data_type"] == "2"  # mortality default
        assert params["sex"] == "3"
        assert params["compareBy"] == "race"
        assert params["chk_race_1"] == "1"

    def test_get_trend_rejects_unknown_sex(self):
        from seer import sdk

        with pytest.raises(ValueError):
            sdk.get_trend(site=55, sex="unknown")

    def test_get_trend_rejects_unknown_compare_by(self):
        from seer import sdk

        with pytest.raises(ValueError):
            sdk.get_trend(site=55, compare_by="not-a-field")


# =============================================================================
# Integration tests (hit seer.cancer.gov)
# =============================================================================


@pytest.mark.integration
class TestSeerIntegration:
    def test_get_mortality_trend(self):
        from seer.sdk import get_mortality_trend

        rows = get_mortality_trend(site=55, sex="female")
        assert len(rows) > 10
        assert all(r["sex_label"] == "Female" for r in rows)

    def test_search_cancer_sites(self):
        from seer.sdk import search_cancer_sites

        results = search_cancer_sites("lung")
        assert any(r["name"] == "Lung and Bronchus" for r in results)


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires API key)"
    )
