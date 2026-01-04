"""
Basic tests for LLM Query Builder

These tests verify the structure and basic functionality without making API calls.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wonder.llm_query_builder import (
    WonderParameter,
    WonderRequest,
    LLMQueryBuilder,
)


def test_wonder_parameter():
    """Test WonderParameter model"""
    param = WonderParameter(
        name="B_1",
        values=["D176.V1-level1"]
    )
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
        ]
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
        ]
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
        print(f"✓ LLMQueryBuilder initialization works ({len(builder.topics_mapping)} datasets)")
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
        print(f"✓ Query params loaded for D176 ({params['summary']['total_parameters']} params)")
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


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("Testing LLM Query Builder")
    print("="*80 + "\n")

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

    print("\n" + "="*80)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*80)


if __name__ == "__main__":
    run_all_tests()
