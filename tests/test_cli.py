"""
Tests for the CDC WONDER CLI Tool

Run unit tests only:
    uv run pytest tests/test_cli.py -m "not integration"

Run integration tests only (requires API key):
    uv run pytest tests/test_cli.py -m integration -v

Run all tests:
    uv run pytest tests/test_cli.py
"""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wonder.llm_query_builder import WonderParameter, WonderRequest


# =============================================================================
# WonderRequest.to_xml() Tests
# =============================================================================


class TestWonderRequestToXml:
    """Tests for WonderRequest.to_xml() method"""

    def test_to_xml_basic(self):
        """Test basic XML generation"""
        request = WonderRequest(
            dataset_id="D176",
            parameters=[
                WonderParameter(name="B_1", values=["D176.V1-level1"]),
            ],
        )

        xml = request.to_xml()

        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
        assert "<request-parameters>" in xml
        assert "</request-parameters>" in xml
        assert "<name>B_1</name>" in xml
        assert "<value>D176.V1-level1</value>" in xml

    def test_to_xml_multiple_values(self):
        """Test XML generation with multiple values for a parameter"""
        request = WonderRequest(
            dataset_id="D176",
            parameters=[
                WonderParameter(name="F_D176.V1", values=["2020", "2021", "2022"]),
            ],
        )

        xml = request.to_xml()

        assert "<value>2020</value>" in xml
        assert "<value>2021</value>" in xml
        assert "<value>2022</value>" in xml

    def test_to_xml_empty_value(self):
        """Test XML generation with empty value uses <value/>"""
        request = WonderRequest(
            dataset_id="D176",
            parameters=[
                WonderParameter(name="I_D176.V1", values=[""]),
            ],
        )

        xml = request.to_xml()

        assert "<value/>" in xml

    def test_to_xml_uses_tabs(self):
        """Test that XML uses tab indentation"""
        request = WonderRequest(
            dataset_id="D176",
            parameters=[
                WonderParameter(name="B_1", values=["test"]),
            ],
        )

        xml = request.to_xml()

        assert "\t<parameter>" in xml
        assert "\t\t<name>" in xml
        assert "\t\t<value>" in xml

    def test_to_xml_multiple_parameters(self):
        """Test XML generation with multiple parameters"""
        request = WonderRequest(
            dataset_id="D176",
            parameters=[
                WonderParameter(name="B_1", values=["D176.V1-level1"]),
                WonderParameter(name="B_2", values=["*None*"]),
                WonderParameter(name="M_1", values=["D176.M1"]),
                WonderParameter(name="dataset_code", values=["D176"]),
            ],
        )

        xml = request.to_xml()

        assert xml.count("<parameter>") == 4
        assert xml.count("</parameter>") == 4
        assert "<name>B_1</name>" in xml
        assert "<name>B_2</name>" in xml
        assert "<name>M_1</name>" in xml
        assert "<name>dataset_code</name>" in xml

    def test_to_xml_matches_reference_format(self):
        """Test that XML format matches the reference file format"""
        request = WonderRequest(
            dataset_id="D176",
            parameters=[
                WonderParameter(name="B_1", values=["D176.V1-level1"]),
                WonderParameter(name="I_D176.V1", values=[""]),
            ],
        )

        xml = request.to_xml()
        lines = xml.split("\n")

        # First line should have XML declaration and root element on same line
        assert lines[0] == '<?xml version="1.0" encoding="UTF-8"?><request-parameters>'
        # Last line should be closing tag
        assert lines[-1] == "</request-parameters>"


# =============================================================================
# CLI Argument Parsing Tests
# =============================================================================


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing"""

    def test_help_flag(self):
        """Test that --help works"""
        result = subprocess.run(
            [sys.executable, "-m", "wonder", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent / "src",
        )
        assert result.returncode == 0
        assert "CDC WONDER CLI Tool" in result.stdout

    def test_build_help(self):
        """Test build subcommand help"""
        result = subprocess.run(
            [sys.executable, "-m", "wonder", "build", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent / "src",
        )
        assert result.returncode == 0
        assert "natural language" in result.stdout.lower()

    def test_run_help(self):
        """Test run subcommand help"""
        result = subprocess.run(
            [sys.executable, "-m", "wonder", "run", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent / "src",
        )
        assert result.returncode == 0
        assert "query_file" in result.stdout.lower()

    def test_query_help(self):
        """Test query subcommand help"""
        result = subprocess.run(
            [sys.executable, "-m", "wonder", "query", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent / "src",
        )
        assert result.returncode == 0
        assert "save-xml" in result.stdout


# =============================================================================
# Command Error Handling Tests
# =============================================================================


class TestCommandErrors:
    """Tests for CLI error handling"""

    def test_run_missing_file(self):
        """Test run command with missing file"""
        result = subprocess.run(
            [sys.executable, "-m", "wonder", "run", "/nonexistent/file.xml"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent / "src",
        )
        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_missing_command(self):
        """Test that missing command shows error"""
        result = subprocess.run(
            [sys.executable, "-m", "wonder"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent / "src",
        )
        assert result.returncode != 0


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.integration
class TestCLIIntegration:
    """Integration tests that make actual API calls"""

    def test_build_command(self, tmp_path):
        """Test build command creates valid XML"""
        output_file = tmp_path / "test_query.xml"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "wonder",
                "build",
                "opioid deaths 2020",
                "-o",
                str(output_file),
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent / "src",
        )

        assert result.returncode == 0
        assert output_file.exists()

        xml_content = output_file.read_text()
        assert '<?xml version="1.0"' in xml_content
        assert "<request-parameters>" in xml_content
        assert "</request-parameters>" in xml_content

    def test_run_command(self):
        """Test run command with existing query file"""
        query_file = (
            Path(__file__).parent.parent
            / "src"
            / "wonder"
            / "queries"
            / "opioid-overdose-deaths-2018-2024-req.xml"
        )

        if not query_file.exists():
            pytest.skip(f"Query file not found: {query_file}")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "wonder",
                "run",
                str(query_file),
                "-f",
                "json",
                "-t",
                "120",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent / "src",
        )

        assert result.returncode == 0
        # Should output valid JSON
        import json

        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_query_command_with_save(self, tmp_path):
        """Test query command with --save-xml option"""
        output_file = tmp_path / "saved_query.xml"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "wonder",
                "query",
                "deaths by year 2022",
                "--save-xml",
                str(output_file),
                "-f",
                "json",
                "-t",
                "120",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent / "src",
        )

        assert result.returncode == 0
        assert output_file.exists()

        xml_content = output_file.read_text()
        assert "<request-parameters>" in xml_content


# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires API key)"
    )


# =============================================================================
# Manual Test Runner
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not integration"])
