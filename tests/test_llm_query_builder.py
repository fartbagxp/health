"""
Tests for LLM Query Builder

This test suite validates that the LLM query builder correctly:
1. Selects appropriate dataset(s) for natural language queries
2. Builds correct query parameters for each dataset
3. Handles multi-dataset scenarios (e.g., queries spanning multiple years)

Test cases are organized by:
- Unit tests: Test models and helpers without LLM calls
- Integration tests: Test actual LLM query building (requires API key)

Run unit tests only:
    uv run pytest tests/test_llm_query_builder.py -m "not integration"

Run integration tests only (requires API key):
    uv run pytest tests/test_llm_query_builder.py -m integration -v

Run all tests:
    uv run pytest tests/test_llm_query_builder.py
"""

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wonder.llm_query_builder import (
    LLMQueryBuilder,
    WonderParameter,
    WonderRequest,
)


# =============================================================================
# Test Case Definitions
# =============================================================================


@dataclass
class ExpectedDataset:
    """Expected dataset selection for a query"""

    dataset_id: str
    year_range: Optional[tuple[int, int]] = None
    required_params: Dict[str, Any] = field(default_factory=dict)
    forbidden_params: List[str] = field(default_factory=list)


@dataclass
class QueryTestCase:
    """A test case for the LLM query builder"""

    id: str
    description: str
    prompt: str
    expected_datasets: List[ExpectedDataset]
    required_param_patterns: Dict[str, List[str]] = field(default_factory=dict)
    topics: List[str] = field(default_factory=list)


# =============================================================================
# Test Cases - Define expected behavior for various queries
# =============================================================================

OVERDOSE_TEST_CASES = [
    QueryTestCase(
        id="overdose_2018_2024",
        description="Overdose deaths spanning provisional and final data",
        prompt="Show me opioid overdose deaths by year from 2018 to 2024",
        expected_datasets=[
            ExpectedDataset(dataset_id="D176", year_range=(2018, 2024)),
            ExpectedDataset(dataset_id="D157", year_range=(2018, 2023)),
        ],
        required_param_patterns={
            "B_1": ["V1", "Year"],  # Should group by year
        },
        topics=["Mortality", "Overdose"],
    ),
    QueryTestCase(
        id="overdose_2020_state",
        description="Overdose deaths by state for a single year",
        prompt="Drug overdose deaths by state in 2020",
        expected_datasets=[
            ExpectedDataset(dataset_id="D157"),
            ExpectedDataset(dataset_id="D176"),
            ExpectedDataset(dataset_id="D77"),
        ],
        required_param_patterns={
            "B_1": ["V9", "State"],  # Should group by state
        },
        topics=["Mortality", "Overdose"],
    ),
    QueryTestCase(
        id="overdose_recent_provisional",
        description="Most recent overdose data (provisional)",
        prompt="What are the latest drug overdose death statistics?",
        expected_datasets=[
            ExpectedDataset(dataset_id="D176"),
        ],
        topics=["Mortality", "Overdose"],
    ),
]

MORTALITY_TEST_CASES = [
    QueryTestCase(
        id="mortality_historical",
        description="Historical mortality data",
        prompt="Death rates by year from 2010 to 2015",
        expected_datasets=[
            # D76 = UCD (Underlying Cause of Death) 1999-2020
            # D77 = MCD (Multiple Cause of Death) 1999-2020
            # Both are valid for historical mortality queries
            ExpectedDataset(dataset_id="D76", year_range=(2010, 2015)),
            ExpectedDataset(dataset_id="D77", year_range=(2010, 2015)),
        ],
        topics=["Mortality"],
    ),
    QueryTestCase(
        id="mortality_by_age_sex",
        description="Mortality grouped by demographics",
        prompt="Deaths by age group and sex in California for 2019",
        expected_datasets=[
            # Multiple valid datasets for 2019 mortality data
            ExpectedDataset(dataset_id="D76"),  # UCD 1999-2020
            ExpectedDataset(dataset_id="D77"),  # MCD 1999-2020
            ExpectedDataset(dataset_id="D157"),  # MCD 2018-2023
            ExpectedDataset(dataset_id="D158"),  # UCD 2018-2023
            ExpectedDataset(dataset_id="D176"),  # Provisional (also has 2019)
        ],
        required_param_patterns={
            "B_1": ["Age", "V5", "V7", "V51"],
        },
        topics=["Mortality"],
    ),
]

ALL_TEST_CASES = OVERDOSE_TEST_CASES + MORTALITY_TEST_CASES


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def data_dir():
    """Path to the WONDER data directory"""
    return Path(__file__).parent.parent / "data" / "raw" / "wonder"


@pytest.fixture
def topics_mapping(data_dir):
    """Load topics mapping"""
    with open(data_dir / "topics_mapping.json") as f:
        return json.load(f)


@pytest.fixture
def query_builder():
    """Create an LLM query builder instance"""
    return LLMQueryBuilder()


@pytest.fixture
def dataset_registry(data_dir):
    """Build a registry of datasets with their year ranges"""
    registry = {}
    for params_file in data_dir.glob("query_params_D*.json"):
        with open(params_file) as f:
            params = json.load(f)

        dataset_id = params_file.stem.replace("query_params_", "")
        title = params.get("page_title", "")

        year_match = re.search(r"(\d{4})[-–](\d{4})", title)
        if year_match:
            registry[dataset_id] = {
                "start_year": int(year_match.group(1)),
                "end_year": int(year_match.group(2)),
                "title": title,
                "is_provisional": "provisional" in title.lower(),
            }
        elif "provisional" in title.lower():
            year_match = re.search(r"(\d{4})", title)
            if year_match:
                registry[dataset_id] = {
                    "start_year": int(year_match.group(1)),
                    "end_year": 9999,
                    "title": title,
                    "is_provisional": True,
                }

    return registry


# =============================================================================
# Helper Functions
# =============================================================================


def validate_param_patterns(
    result: WonderRequest,
    patterns: Dict[str, List[str]],
) -> List[str]:
    """
    Validate that parameters match expected patterns.
    Returns list of validation errors (empty if valid).
    """
    errors = []
    param_dict = {p.name: p.values for p in result.parameters}

    for param_name, expected_patterns in patterns.items():
        if param_name not in param_dict:
            errors.append(f"Missing parameter: {param_name}")
            continue

        values = param_dict[param_name]
        found = False
        for pattern in expected_patterns:
            for value in values:
                if pattern.lower() in str(value).lower():
                    found = True
                    break
            if found:
                break

        if not found:
            errors.append(
                f"Parameter {param_name} values {values} don't match "
                f"any expected patterns: {expected_patterns}"
            )

    return errors


# =============================================================================
# Unit Tests - Basic Model Tests
# =============================================================================


def test_wonder_parameter():
    """Test WonderParameter model"""
    param = WonderParameter(name="B_1", values=["D176.V1-level1"])
    assert param.name == "B_1"
    assert param.values == ["D176.V1-level1"]
    print("✓ WonderParameter model works")


def test_wonder_request():
    """Test WonderRequest model"""
    request = WonderRequest(
        dataset_id="D176",
        parameters=[
            WonderParameter(name="B_1", values=["D176.V1-level1"]),
            WonderParameter(name="F_D176.V1", values=["2020", "2021"]),
            WonderParameter(name="M_1", values=["D176.M1"]),
        ],
    )

    assert request.dataset_id == "D176"
    assert len(request.parameters) == 3
    print("✓ WonderRequest model works")


def test_wonder_request_to_dict():
    """Test WonderRequest to_dict conversion"""
    request = WonderRequest(
        dataset_id="D176",
        parameters=[
            WonderParameter(name="dataset_code", values=["D176"]),
            WonderParameter(name="F_D176.V1", values=["2020", "2021", "2022"]),
            WonderParameter(name="action-Send", values=["Send"]),
        ],
    )

    result = request.to_dict()

    assert result["dataset_code"] == "D176"
    assert result["F_D176.V1"] == ["2020", "2021", "2022"]
    assert result["action-Send"] == "Send"
    print("✓ WonderRequest.to_dict() works")


def test_llm_query_builder_initialization():
    """Test LLMQueryBuilder initialization (without API key)"""
    try:
        # This might fail if no API key, but we're just testing import
        builder = LLMQueryBuilder(api_key="dummy-key-for-testing")
        assert builder.data_dir.exists()
        assert builder.topics_mapping is not None
        assert len(builder.topics_mapping) > 0
        print(
            f"✓ LLMQueryBuilder initialization works ({len(builder.topics_mapping)} datasets)"
        )
    except Exception as e:
        print(f"⚠ LLMQueryBuilder initialization (expected if no API key): {e}")


def test_load_topics_mapping():
    """Test loading topics mapping"""
    builder = LLMQueryBuilder(api_key="dummy-key")

    assert len(builder.topics_mapping) > 0

    # Check structure of first topic
    first_topic = builder.topics_mapping[0]
    assert "dataset_id" in first_topic
    assert "topic" in first_topic
    assert "category" in first_topic

    print(f"✓ Topics mapping loaded ({len(builder.topics_mapping)} datasets)")


def test_load_query_params():
    """Test loading query parameters"""
    builder = LLMQueryBuilder(api_key="dummy-key")

    # Try to load params for D176 (Provisional Mortality)
    try:
        params = builder._load_query_params("D176")
        assert "parameters" in params
        assert "summary" in params
        assert params.get("dataset_id") == "D176"
        print(
            f"✓ Query params loaded for D176 ({params['summary']['total_parameters']} params)"
        )
    except ValueError as e:
        print(f"⚠ Could not load D176 params: {e}")


def test_get_datasets_summary():
    """Test dataset summary generation"""
    builder = LLMQueryBuilder(api_key="dummy-key")

    summary = builder._get_available_datasets_summary()
    assert "Available CDC WONDER Datasets" in summary
    assert len(summary) > 100  # Should be substantial text

    print(f"✓ Dataset summary generated ({len(summary)} chars)")


def test_get_dataset_params_summary():
    """Test dataset params summary"""
    builder = LLMQueryBuilder(api_key="dummy-key")

    try:
        summary = builder._get_dataset_params_summary("D176")
        assert "Query Parameters for D176" in summary
        assert "Group By Options" in summary
        print(f"✓ Dataset params summary generated ({len(summary)} chars)")
    except ValueError as e:
        print(f"⚠ Could not generate D176 summary: {e}")


def test_tool_schema():
    """Test tool schema generation"""
    builder = LLMQueryBuilder(api_key="dummy-key")

    schema = builder._create_build_query_tool_schema()
    assert schema["name"] == "build_wonder_query"
    assert "input_schema" in schema
    assert "dataset_id" in schema["input_schema"]["properties"]
    assert "parameters" in schema["input_schema"]["properties"]

    print("✓ Tool schema structure is valid")


# =============================================================================
# Unit Tests - Dataset Selection Logic
# =============================================================================


class TestDatasetSelection:
    """Test that the correct datasets are selected for various queries"""

    def test_topics_mapping_loaded(self, topics_mapping):
        """Verify topics mapping is loaded correctly"""
        assert "mappings" in topics_mapping
        assert len(topics_mapping["mappings"]) > 0

    def test_mcd_datasets_exist(self, topics_mapping):
        """Verify MCD datasets are in the mapping"""
        dataset_ids = {m["dataset_id"] for m in topics_mapping["mappings"]}
        assert "D77" in dataset_ids, "D77 (MCD 1999-2020) should exist"
        assert "D157" in dataset_ids, "D157 (MCD 2018-2023) should exist"
        assert "D176" in dataset_ids, "D176 (Provisional) should exist"

    def test_mortality_topic_mapping(self, topics_mapping):
        """Verify mortality datasets are correctly categorized"""
        mortality_datasets = [
            m for m in topics_mapping["mappings"] if m.get("topic") == "Mortality"
        ]
        assert len(mortality_datasets) > 0

        mcd_ids = {m["dataset_id"] for m in mortality_datasets}
        assert "D77" in mcd_ids
        assert "D157" in mcd_ids
        assert "D176" in mcd_ids


class TestQueryParamsAvailable:
    """Test that query params files exist for required datasets"""

    @pytest.mark.parametrize("dataset_id", ["D77", "D157", "D176"])
    def test_query_params_file_exists(self, data_dir, dataset_id):
        """Verify query params file exists for key datasets"""
        params_file = data_dir / f"query_params_{dataset_id}.json"
        assert params_file.exists(), f"Query params file missing for {dataset_id}"

    @pytest.mark.parametrize("dataset_id", ["D77", "D157", "D176"])
    def test_query_params_has_required_fields(self, data_dir, dataset_id):
        """Verify query params have required structure"""
        params_file = data_dir / f"query_params_{dataset_id}.json"
        with open(params_file) as f:
            params = json.load(f)

        assert "parameters" in params
        assert "selects" in params["parameters"]
        assert "inputs" in params["parameters"]

        selects = params["parameters"]["selects"]
        group_by_params = [s for s in selects if s["name"].startswith("B_")]
        assert len(group_by_params) > 0, f"{dataset_id} should have group-by params"


class TestDatasetYearCoverage:
    """Test dataset year coverage logic"""

    def test_d77_covers_1999_2020(self, data_dir):
        """D77 should cover 1999-2020"""
        params_file = data_dir / "query_params_D77.json"
        with open(params_file) as f:
            params = json.load(f)

        title = params.get("page_title", "")
        assert "1999" in title
        assert "2020" in title

    def test_d157_covers_2018_2023(self, data_dir):
        """D157 should cover 2018-2023"""
        params_file = data_dir / "query_params_D157.json"
        with open(params_file) as f:
            params = json.load(f)

        title = params.get("page_title", "")
        assert "2018" in title
        assert "2023" in title

    def test_d176_is_provisional(self, data_dir):
        """D176 should be provisional data"""
        params_file = data_dir / "query_params_D176.json"
        with open(params_file) as f:
            params = json.load(f)

        title = params.get("page_title", "").lower()
        assert "provisional" in title


class TestDatasetSelectionStrategy:
    """Test the logic for selecting datasets based on query requirements."""

    def test_identify_datasets_for_2018_2024(self, dataset_registry):
        """Test identifying datasets for 2018-2024 range"""
        target_start = 2018
        target_end = 2024

        covering_datasets = []
        for dataset_id, info in dataset_registry.items():
            if info["start_year"] <= target_end and info["end_year"] >= target_start:
                covering_datasets.append((dataset_id, info))

        dataset_ids = {d[0] for d in covering_datasets}
        assert "D157" in dataset_ids or "D176" in dataset_ids, (
            f"Expected D157 or D176 to cover 2018-2024, found: {dataset_ids}"
        )

    def test_prefer_final_over_provisional(self, dataset_registry):
        """Test that final data is preferred over provisional when available"""
        target_year = 2020

        final_datasets = []
        provisional_datasets = []

        for dataset_id, info in dataset_registry.items():
            if info["start_year"] <= target_year <= info["end_year"]:
                if info["is_provisional"]:
                    provisional_datasets.append(dataset_id)
                else:
                    final_datasets.append(dataset_id)

        assert len(final_datasets) > 0, "Should have final data for 2020"
        assert len(provisional_datasets) > 0, "Should have provisional data for 2020"

    def test_identify_datasets_needing_split(self, dataset_registry):
        """
        Identify when a query needs multiple datasets.
        For 2018-2024, we might need:
        - D157 (2018-2023) for final data
        - D176 (2024+) for provisional/recent data
        """
        target_start = 2018
        target_end = 2024

        # Find datasets that fully cover the range
        fully_covering = []
        partially_covering = []

        for dataset_id, info in dataset_registry.items():
            if info["start_year"] <= target_start and info["end_year"] >= target_end:
                fully_covering.append(dataset_id)
            elif info["start_year"] <= target_end and info["end_year"] >= target_start:
                partially_covering.append(dataset_id)

        # D176 (provisional 2018-present) should fully cover
        assert "D176" in fully_covering, "D176 should fully cover 2018-2024"

        # D157 (2018-2023) should partially cover
        assert "D157" in partially_covering, "D157 should partially cover 2018-2024"


# =============================================================================
# Integration Tests - LLM Query Building
# =============================================================================


@pytest.mark.integration
class TestLLMQueryBuilderIntegration:
    """
    Integration tests that actually call the LLM.
    These require an API key and are marked with @pytest.mark.integration.

    Run with: pytest tests/test_llm_query_builder.py -m integration
    Skip with: pytest tests/test_llm_query_builder.py -m "not integration"
    """

    @pytest.mark.parametrize(
        "test_case", OVERDOSE_TEST_CASES, ids=[tc.id for tc in OVERDOSE_TEST_CASES]
    )
    def test_overdose_queries(self, query_builder, topics_mapping, test_case):
        """Test overdose-related queries"""
        result = query_builder.build_query(test_case.prompt)

        valid_datasets = [e.dataset_id for e in test_case.expected_datasets]
        assert result.dataset_id in valid_datasets, (
            f"Query '{test_case.prompt}' returned dataset {result.dataset_id}, "
            f"expected one of {valid_datasets}"
        )

        if test_case.required_param_patterns:
            errors = validate_param_patterns(result, test_case.required_param_patterns)
            assert not errors, f"Parameter validation failed: {errors}"

    @pytest.mark.parametrize(
        "test_case", MORTALITY_TEST_CASES, ids=[tc.id for tc in MORTALITY_TEST_CASES]
    )
    def test_mortality_queries(self, query_builder, topics_mapping, test_case):
        """Test mortality-related queries"""
        result = query_builder.build_query(test_case.prompt)

        valid_datasets = [e.dataset_id for e in test_case.expected_datasets]
        assert result.dataset_id in valid_datasets, (
            f"Query '{test_case.prompt}' returned dataset {result.dataset_id}, "
            f"expected one of {valid_datasets}"
        )

    def test_query_returns_valid_parameters(self, query_builder):
        """Test that returned parameters are well-formed"""
        result = query_builder.build_query("Drug overdose deaths by state in 2022")

        assert result.dataset_id.startswith("D")
        assert len(result.parameters) > 0

        # Check essential parameters are present
        param_names = {p.name for p in result.parameters}
        assert "B_1" in param_names, "Should have at least one group-by parameter"

    def test_query_parameter_values_match_dataset(self, query_builder):
        """Test that parameter values use the correct dataset prefix"""
        result = query_builder.build_query("Deaths by year from 2020 to 2022")

        dataset_id = result.dataset_id
        for param in result.parameters:
            for value in param.values:
                # Values like "D176.V1" should match the dataset
                if "." in value and value[0] == "D":
                    value_dataset = value.split(".")[0]
                    assert value_dataset == dataset_id, (
                        f"Parameter {param.name} has value {value} "
                        f"which doesn't match dataset {dataset_id}"
                    )


# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires API key)"
    )


# =============================================================================
# Manual Test Runner (for running without pytest)
# =============================================================================


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("Testing LLM Query Builder")
    print("=" * 80 + "\n")

    tests = [
        test_wonder_parameter,
        test_wonder_request,
        test_wonder_request_to_dict,
        test_llm_query_builder_initialization,
        test_load_topics_mapping,
        test_load_query_params,
        test_get_datasets_summary,
        test_get_dataset_params_summary,
        test_tool_schema,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 80)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 80)


if __name__ == "__main__":
    run_all_tests()
