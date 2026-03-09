"""
Tests for cdc_open module.

Run unit tests only (no network):
    uv run pytest tests/test_cdc_open.py -m "not integration"

Run integration tests (hits data.cdc.gov):
    uv run pytest tests/test_cdc_open.py -m integration -v
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cdc_open.client import SodaClient
from cdc_open.datasets import DATASETS, Dataset
from cdc_open.tools import TOOLS, execute_tool


# =============================================================================
# Dataset registry
# =============================================================================


class TestDatasets:
    def test_all_datasets_have_required_fields(self):
        for key, ds in DATASETS.items():
            assert isinstance(ds, Dataset), key
            assert ds.id, f"{key} missing id"
            assert ds.name, f"{key} missing name"
            assert ds.description, f"{key} missing description"
            assert ds.years, f"{key} missing years"

    def test_dataset_ids_are_unique(self):
        ids = [ds.id for ds in DATASETS.values()]
        assert len(ids) == len(set(ids)), "Duplicate dataset IDs found"

    def test_known_datasets_present(self):
        expected = [
            "leading_death",
            "life_expectancy",
            "places_county",
            "weekly_deaths",
            "drug_overdose_state",
        ]
        for key in expected:
            assert key in DATASETS, f"Missing dataset: {key}"

    def test_dataset_count(self):
        assert len(DATASETS) == 14


# =============================================================================
# SodaClient
# =============================================================================


class TestSodaClient:
    def _mock_response(self, data: list[dict]):
        resp = MagicMock()
        resp.json.return_value = data
        resp.raise_for_status = MagicMock()
        return resp

    def test_builds_correct_url(self):
        client = SodaClient()
        with patch.object(
            client.session, "get", return_value=self._mock_response([])
        ) as mock_get:
            client.get("bi63-dtpu")
            url = mock_get.call_args[0][0]
            assert url == "https://data.cdc.gov/resource/bi63-dtpu.json"

    def test_passes_limit(self):
        client = SodaClient()
        with patch.object(
            client.session, "get", return_value=self._mock_response([])
        ) as mock_get:
            client.get("bi63-dtpu", limit=42)
            params = mock_get.call_args[1]["params"]
            assert params["$limit"] == 42

    def test_passes_where_clause(self):
        client = SodaClient()
        with patch.object(
            client.session, "get", return_value=self._mock_response([])
        ) as mock_get:
            client.get("bi63-dtpu", where="year = '2015'")
            params = mock_get.call_args[1]["params"]
            assert params["$where"] == "year = '2015'"

    def test_omits_none_params(self):
        client = SodaClient()
        with patch.object(
            client.session, "get", return_value=self._mock_response([])
        ) as mock_get:
            client.get("bi63-dtpu")
            params = mock_get.call_args[1]["params"]
            assert "$where" not in params
            assert "$select" not in params
            assert "$group" not in params
            assert "$order" not in params

    def test_passes_all_soda_params(self):
        client = SodaClient()
        with patch.object(
            client.session, "get", return_value=self._mock_response([])
        ) as mock_get:
            client.get(
                "bi63-dtpu",
                where="year='2015'",
                select="year, state",
                group="year",
                order="year DESC",
                limit=50,
            )
            params = mock_get.call_args[1]["params"]
            assert params["$where"] == "year='2015'"
            assert params["$select"] == "year, state"
            assert params["$group"] == "year"
            assert params["$order"] == "year DESC"
            assert params["$limit"] == 50

    def test_returns_parsed_json(self):
        client = SodaClient()
        fake_data = [{"year": "2015", "state": "Ohio", "deaths": "100"}]
        with patch.object(
            client.session, "get", return_value=self._mock_response(fake_data)
        ):
            result = client.get("bi63-dtpu")
            assert result == fake_data

    def test_caches_identical_requests(self):
        client = SodaClient()
        fake_data = [{"year": "2015"}]
        with patch.object(
            client.session, "get", return_value=self._mock_response(fake_data)
        ) as mock_get:
            client.get("bi63-dtpu", where="year='2015'")
            client.get("bi63-dtpu", where="year='2015'")
            assert mock_get.call_count == 1

    def test_does_not_cache_different_requests(self):
        client = SodaClient()
        with patch.object(
            client.session, "get", return_value=self._mock_response([])
        ) as mock_get:
            client.get("bi63-dtpu", where="year='2015'")
            client.get("bi63-dtpu", where="year='2016'")
            assert mock_get.call_count == 2

    def test_clear_cache_forces_refetch(self):
        client = SodaClient()
        with patch.object(
            client.session, "get", return_value=self._mock_response([])
        ) as mock_get:
            client.get("bi63-dtpu")
            client.clear_cache()
            client.get("bi63-dtpu")
            assert mock_get.call_count == 2

    def test_sets_app_token_header(self):
        client = SodaClient(app_token="test-token-123")
        assert client.session.headers.get("X-App-Token") == "test-token-123"

    def test_no_app_token_header_when_omitted(self):
        client = SodaClient()
        assert "X-App-Token" not in client.session.headers


# =============================================================================
# Tools
# =============================================================================


class TestTools:
    def test_tools_is_list(self):
        assert isinstance(TOOLS, list)
        assert len(TOOLS) > 0

    def test_each_tool_has_required_keys(self):
        for tool in TOOLS:
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert "description" in tool, f"Tool {tool['name']} missing 'description'"
            assert "input_schema" in tool, f"Tool {tool['name']} missing 'input_schema'"

    def test_input_schemas_are_objects(self):
        for tool in TOOLS:
            schema = tool["input_schema"]
            assert schema["type"] == "object", f"{tool['name']} schema type != object"
            assert "properties" in schema, f"{tool['name']} schema missing properties"

    def test_query_dataset_tool_has_required_field(self):
        tool = next(t for t in TOOLS if t["name"] == "query_dataset")
        required = tool["input_schema"].get("required", [])
        assert "dataset_id" in required

    def test_tool_names_are_unique(self):
        names = [t["name"] for t in TOOLS]
        assert len(names) == len(set(names))

    def test_execute_tool_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            execute_tool("nonexistent_tool", {})

    def test_execute_tool_dispatches_correctly(self):
        # _DISPATCH holds direct function references captured at import time,
        # so patch the dict entry rather than the sdk module attribute.
        fake_rows = [{"year": "2015", "state": "Ohio"}]
        mock_fn = MagicMock(return_value=fake_rows)
        with patch(
            "cdc_open.tools._DISPATCH", {"get_leading_causes_of_death": mock_fn}
        ):
            result = execute_tool(
                "get_leading_causes_of_death", {"state": "Ohio", "year": 2015}
            )
            mock_fn.assert_called_once_with(state="Ohio", year=2015)
            assert result == fake_rows

    def test_execute_query_dataset_tool(self):
        fake_rows = [{"year": "2015"}]
        mock_fn = MagicMock(return_value=fake_rows)
        with patch("cdc_open.tools._DISPATCH", {"query_dataset": mock_fn}):
            result = execute_tool(
                "query_dataset", {"dataset_id": "bi63-dtpu", "limit": 10}
            )
            mock_fn.assert_called_once_with(dataset_id="bi63-dtpu", limit=10)
            assert result == fake_rows

    def test_all_tools_are_dispatchable(self):
        """Every tool in TOOLS must have a corresponding executor entry."""
        for tool in TOOLS:
            with patch("cdc_open.sdk.query_dataset", return_value=[]):
                try:
                    execute_tool(tool["name"], {"dataset_id": "bi63-dtpu"})
                except TypeError:
                    pass  # Wrong args is fine — just checking it doesn't raise ValueError


# =============================================================================
# CLI
# =============================================================================

SRC = Path(__file__).parent.parent / "src"


class TestCLI:
    def _run(self, *args, **kwargs):
        return subprocess.run(
            [sys.executable, "-m", "cdc_open", *args],
            capture_output=True,
            text=True,
            cwd=SRC,
            **kwargs,
        )

    def test_help(self):
        result = self._run("--help")
        assert result.returncode == 0
        assert "data.cdc.gov" in result.stdout

    def test_list_table(self):
        result = self._run("list")
        assert result.returncode == 0
        assert "leading_death" in result.stdout
        assert "bi63-dtpu" in result.stdout

    def test_list_json(self):
        result = self._run("list", "-f", "json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) == 14
        keys = {row["key"] for row in data}
        assert "leading_death" in keys
        assert "weekly_deaths" in keys

    def test_query_help(self):
        result = self._run("query", "--help")
        assert result.returncode == 0
        assert "dataset_id" in result.stdout

    def test_analyze_help(self):
        result = self._run("analyze", "--help")
        assert result.returncode == 0
        assert "question" in result.stdout

    def test_analyze_requires_api_key(self):
        # Pass the full env but explicitly unset the key.
        # load_dotenv() won't override an already-set (empty) env var.
        import os

        env = {**os.environ, "ANTHROPIC_API_KEY": ""}
        result = self._run("analyze", "test question", env=env)
        assert result.returncode != 0
        assert "ANTHROPIC_API_KEY" in result.stderr

    def test_query_bad_dataset_returns_error(self):
        result = self._run("query", "nonexistent-id-xyz")
        assert result.returncode != 0


# =============================================================================
# Integration tests (hit real data.cdc.gov)
# =============================================================================


@pytest.mark.integration
class TestSDKIntegration:
    """Live API calls — requires network access to data.cdc.gov."""

    def test_get_leading_causes_of_death(self):
        from cdc_open.sdk import get_leading_causes_of_death

        rows = get_leading_causes_of_death(state="New York", year=2015, limit=5)
        assert len(rows) > 0
        assert "state" in rows[0]
        assert rows[0]["state"] == "New York"

    def test_get_life_expectancy(self):
        from cdc_open.sdk import get_life_expectancy

        rows = get_life_expectancy(year=2000, race="All Races", sex="Both Sexes")
        assert len(rows) > 0
        assert "average_life_expectancy" in rows[0]

    def test_get_places_county_health(self):
        from cdc_open.sdk import get_places_county_health

        rows = get_places_county_health(state="OH", measure="OBESITY", limit=10)
        assert len(rows) > 0
        assert "locationname" in rows[0]
        assert "data_value" in rows[0]

    def test_get_weekly_deaths(self):
        from cdc_open.sdk import get_weekly_deaths

        rows = get_weekly_deaths(state="California", limit=5)
        assert len(rows) > 0
        assert "total_deaths" in rows[0]

    def test_get_historical_death_rates(self):
        from cdc_open.sdk import get_historical_death_rates

        rows = get_historical_death_rates(
            cause="Heart Disease", start_year=2000, end_year=2010
        )
        assert len(rows) > 0
        assert "year" in rows[0]

    def test_query_dataset_raw(self):
        from cdc_open.sdk import query_dataset

        rows = query_dataset("bi63-dtpu", where="year='2010' AND state='Ohio'", limit=5)
        assert isinstance(rows, list)
        assert len(rows) > 0

    def test_cli_query_json(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "cdc_open",
                "query",
                "bi63-dtpu",
                "--where",
                "year='2010' AND state='Ohio'",
                "--limit",
                "3",
            ],
            capture_output=True,
            text=True,
            cwd=SRC,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) == 3

    def test_cli_query_csv(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "cdc_open",
                "query",
                "bi63-dtpu",
                "--where",
                "year='2010' AND state='Ohio'",
                "--limit",
                "3",
                "-f",
                "csv",
            ],
            capture_output=True,
            text=True,
            cwd=SRC,
        )
        assert result.returncode == 0
        lines = result.stdout.strip().splitlines()
        assert len(lines) >= 2  # header + at least one row
        assert "state" in lines[0] or "year" in lines[0]
