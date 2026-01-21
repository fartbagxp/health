"""
Pytest configuration and shared fixtures for WONDER tests.
"""

import json
import re
from pathlib import Path

import pytest


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
    from wonder.llm_query_builder import LLMQueryBuilder

    return LLMQueryBuilder()


@pytest.fixture
def dataset_registry(data_dir):
    """
    Build a registry of datasets with their year ranges.
    Parses the page_title from query_params files to extract year coverage.
    """
    registry = {}
    for params_file in data_dir.glob("query_params_D*.json"):
        with open(params_file) as f:
            params = json.load(f)

        dataset_id = params_file.stem.replace("query_params_", "")
        title = params.get("page_title", "")

        # Try to extract year range from title like "1999-2020" or "2018–2023"
        year_match = re.search(r"(\d{4})[-–](\d{4})", title)
        if year_match:
            registry[dataset_id] = {
                "start_year": int(year_match.group(1)),
                "end_year": int(year_match.group(2)),
                "title": title,
                "is_provisional": "provisional" in title.lower(),
            }
        elif "provisional" in title.lower():
            # Provisional datasets have open-ended year ranges
            year_match = re.search(r"(\d{4})", title)
            if year_match:
                registry[dataset_id] = {
                    "start_year": int(year_match.group(1)),
                    "end_year": 9999,  # Open-ended
                    "title": title,
                    "is_provisional": True,
                }

    return registry


def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires API key)"
    )
