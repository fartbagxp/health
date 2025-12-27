"""
CDC WONDER API Client

This module provides a client for interacting with the CDC WONDER API.
CDC WONDER (Wide-ranging ONline Data for Epidemiologic Research) provides
access to birth, death, cancer, and other public health statistics.

API Documentation: https://wonder.cdc.gov/wonder/help/wonder-api.html

Key Concepts:
- Dataset IDs: Each dataset has a unique ID (e.g., D176 for Provisional Mortality)
- Request Parameters: Complex XML-based parameter system with several categories:
  - B: Group By controls (B_1, B_2, etc.)
  - M: Measure controls (M_1, M_2, etc.)
  - F: Filter values (F_D176.V1, F_D176.V9, etc.)
  - I: Display labels
  - V: Variable values
  - O: Output options
  - VM: Values for adjusted rates
- Response Format: XML with data tables containing rows and cells
"""

import requests
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path


@dataclass
class QueryParameter:
    """Represents a single query parameter"""
    name: str
    values: List[str]

    def to_xml(self) -> str:
        """Convert parameter to XML format"""
        lines = [f"    <parameter>", f"        <name>{self.name}</name>"]
        for value in self.values:
            lines.append(f"        <value>{value}</value>")
        lines.append("    </parameter>")
        return "\n".join(lines)


@dataclass
class ResponseCell:
    """Represents a cell in the response data table"""
    label: Optional[str] = None  # l attribute
    value: Optional[str] = None  # v attribute
    column: Optional[str] = None  # c attribute
    data_total: Optional[str] = None  # dt attribute
    attribute: Optional[str] = None  # a attribute
    sub_label: Optional[str] = None  # nested <l> element value

    def get_numeric_value(self) -> Optional[float]:
        """Try to parse the value as a number, handling commas"""
        val = self.value or self.data_total
        if val is None:
            return None
        try:
            # Remove commas and convert to float
            return float(val.replace(',', ''))
        except (ValueError, AttributeError):
            return None


@dataclass
class ResponseRow:
    """Represents a row in the response data table"""
    cells: List[ResponseCell]
    is_total: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert row to dictionary format"""
        return {
            'cells': [
                {
                    'label': c.label,
                    'value': c.value,
                    'data_total': c.data_total,
                    'sub_label': c.sub_label,
                    'numeric_value': c.get_numeric_value()
                }
                for c in self.cells
            ],
            'is_total': self.is_total
        }


class WonderClient:
    """
    Client for interacting with CDC WONDER API

    Example usage:
        client = WonderClient()

        # Load and execute a query from file
        response = client.execute_query_file("src/wonder/queries/my-query.xml")
        table = client.parse_response_table(response)

        # Or build a custom query
        params = QueryBuilder(dataset_id="D176") \
            .group_by("D176.V1-level1") \
            .measures(["D176.M1", "D176.M2"]) \
            .filter("F_D176.V1", ["2020", "2021"]) \
            .build()
        response = client.query(params)
    """

    BASE_URL = "https://wonder.cdc.gov/controller/datarequest"

    def __init__(self, timeout: int = 60):
        """
        Initialize the WONDER client

        Args:
            timeout: Request timeout in seconds (default: 60)
        """
        self.timeout = timeout
        self.session = requests.Session()

    def _build_request_data(self, request_xml: str) -> Dict[str, str]:
        """
        Build request data dict from XML

        Args:
            request_xml: XML string containing request parameters

        Returns:
            Dictionary with request_xml and accept_datause_restrictions
        """
        return {
            "request_xml": request_xml,
            "accept_datause_restrictions": "true",
        }

    def query(
        self,
        dataset_id: str,
        parameters: Dict[str, Union[str, List[str]]],
    ) -> str:
        """
        Execute a query against CDC WONDER API

        Args:
            dataset_id: Dataset ID (e.g., "D176")
            parameters: Dictionary of parameter name to value(s)

        Returns:
            XML response string

        Raises:
            RuntimeError: If request fails or returns non-200 status
        """
        # Build XML from parameters
        request_xml = self._build_request_xml(parameters)

        # Build request data
        data = self._build_request_data(request_xml)

        # Make request
        url = f"{self.BASE_URL}/{dataset_id}"
        response = self.session.post(url, data=data, timeout=self.timeout)

        if response.status_code != 200:
            raise RuntimeError(
                f"CDC WONDER request failed with status {response.status_code}: {response.text[:500]}"
            )

        return response.text

    def query_from_xml(self, dataset_id: str, request_xml: str) -> str:
        """
        Execute a query using raw XML request

        Args:
            dataset_id: Dataset ID (e.g., "D176")
            request_xml: Complete XML request string

        Returns:
            XML response string

        Raises:
            RuntimeError: If request fails
        """
        data = self._build_request_data(request_xml)
        url = f"{self.BASE_URL}/{dataset_id}"
        response = self.session.post(url, data=data, timeout=self.timeout)

        if response.status_code != 200:
            raise RuntimeError(
                f"CDC WONDER request failed with status {response.status_code}"
            )

        return response.text

    def execute_query_file(self, file_path: str) -> str:
        """
        Load and execute a query from an XML file

        Args:
            file_path: Path to XML query file

        Returns:
            XML response string

        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If request fails
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Query file not found: {file_path}")

        with open(path, 'r', encoding='utf-8') as f:
            request_xml = f.read()

        # Extract dataset_id from XML
        dataset_id = self._extract_dataset_id(request_xml)
        if not dataset_id:
            raise ValueError("Could not extract dataset_id from query XML")

        return self.query_from_xml(dataset_id, request_xml)

    def _extract_dataset_id(self, xml_string: str) -> Optional[str]:
        """Extract dataset_id from request XML"""
        try:
            root = ET.fromstring(xml_string)
            dataset_code = root.find(".//parameter[name='dataset_code']/value")
            if dataset_code is not None and dataset_code.text:
                return dataset_code.text
        except ET.ParseError:
            pass
        return None

    def _build_request_xml(self, parameters: Dict[str, Union[str, List[str]]]) -> str:
        """
        Build XML request from parameters dictionary

        Args:
            parameters: Dictionary mapping parameter names to value(s)

        Returns:
            Complete XML request string
        """
        lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<request-parameters>']

        for name, value in parameters.items():
            lines.append('    <parameter>')
            lines.append(f'        <name>{name}</name>')

            if isinstance(value, list):
                for v in value:
                    lines.append(f'        <value>{v}</value>')
            else:
                lines.append(f'        <value>{value}</value>')

            lines.append('    </parameter>')

        lines.append('</request-parameters>')
        return '\n'.join(lines)

    def parse_response_table(self, response_xml: str) -> List[ResponseRow]:
        """
        Parse the data table from response XML

        Args:
            response_xml: XML response string

        Returns:
            List of ResponseRow objects

        Raises:
            ValueError: If response cannot be parsed
        """
        try:
            root = ET.fromstring(response_xml)
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse response XML: {e}")

        data_table = root.find('.//data-table')
        if data_table is None:
            raise ValueError("No data-table found in response")

        rows = []
        for row_elem in data_table.findall('r'):
            cells = []
            is_total = False

            for cell_elem in row_elem.findall('c'):
                # Extract all cell attributes
                label = cell_elem.get('l')
                value = cell_elem.get('v')
                column = cell_elem.get('c')
                data_total = cell_elem.get('dt')
                attribute = cell_elem.get('a')

                # Check for nested <l> element
                sub_label_elem = cell_elem.find('l')
                sub_label = sub_label_elem.get('v') if sub_label_elem is not None else None

                # If we see data_total, this is a totals row
                if data_total is not None:
                    is_total = True

                cell = ResponseCell(
                    label=label,
                    value=value,
                    column=column,
                    data_total=data_total,
                    attribute=attribute,
                    sub_label=sub_label
                )
                cells.append(cell)

            rows.append(ResponseRow(cells=cells, is_total=is_total))

        return rows

    def parse_response_to_dicts(self, response_xml: str) -> List[Dict[str, Any]]:
        """
        Parse response table to list of dictionaries (simpler format)

        Args:
            response_xml: XML response string

        Returns:
            List of dictionaries, one per row
        """
        rows = self.parse_response_table(response_xml)
        return [row.to_dict() for row in rows]

    def parse_response_to_arrays(self, response_xml: str) -> List[List[Any]]:
        """
        Parse response table to 2D array (compatible with Handler.xml_to_table)

        Args:
            response_xml: XML response string

        Returns:
            2D list of values
        """
        rows = self.parse_response_table(response_xml)
        result = []

        for row in rows:
            row_data = []
            for cell in row.cells:
                # Prefer label for first column, then value, then data_total
                if cell.label:
                    row_data.append(cell.label)
                elif cell.value:
                    # Try to convert to number
                    numeric = cell.get_numeric_value()
                    row_data.append(numeric if numeric is not None else cell.value)
                elif cell.data_total:
                    numeric = cell.get_numeric_value()
                    row_data.append(numeric if numeric is not None else cell.data_total)
                else:
                    row_data.append(None)

            result.append(row_data)

        return result

    def get_dataset_metadata(self, response_xml: str) -> Dict[str, Any]:
        """
        Extract dataset metadata from response

        Args:
            response_xml: XML response string

        Returns:
            Dictionary with metadata fields
        """
        try:
            root = ET.fromstring(response_xml)
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse response XML: {e}")

        dataset = root.find('.//dataset')
        if dataset is None:
            return {}

        metadata = {
            'code': dataset.get('code'),
            'label': dataset.get('label'),
            'family': dataset.get('family'),
            'vintage': dataset.get('vintage'),
            'suppress_counts': dataset.get('suppress-counts') == 'true',
            'suppress_zeros': dataset.get('suppress-zeros') == 'true',
        }

        return {k: v for k, v in metadata.items() if v is not None}


class QueryBuilder:
    """
    Helper class to build query parameters

    Example:
        params = QueryBuilder(dataset_id="D176") \
            .group_by("D176.V1-level1", slot=1) \
            .measures(["D176.M1", "D176.M2", "D176.M3"]) \
            .filter("F_D176.V1", ["2020", "2021", "2022"]) \
            .filter("F_D176.V9", "*All*") \
            .option("O_rate_per", "100000") \
            .option("O_show_totals", "true") \
            .build()
    """

    def __init__(self, dataset_id: str):
        """Initialize builder with dataset ID"""
        self.dataset_id = dataset_id
        self.params: Dict[str, Union[str, List[str]]] = {
            "dataset_code": dataset_id,
            "action-Send": "Send",
            "stage": "request",
        }

        # Initialize empty group-by slots
        for i in range(1, 6):
            self.params[f"B_{i}"] = "*None*"

    def group_by(self, variable: str, slot: int = 1) -> "QueryBuilder":
        """
        Set a group-by variable

        Args:
            variable: Variable code (e.g., "D176.V1-level1" for Year)
            slot: Group-by slot number (1-5)

        Returns:
            Self for chaining
        """
        if not 1 <= slot <= 5:
            raise ValueError("Group-by slot must be 1-5")
        self.params[f"B_{slot}"] = variable
        return self

    def measures(self, measures: List[str]) -> "QueryBuilder":
        """
        Set measures to include

        Args:
            measures: List of measure codes (e.g., ["D176.M1", "D176.M2"])

        Returns:
            Self for chaining
        """
        for i, measure in enumerate(measures, start=1):
            self.params[f"M_{i}"] = measure
        return self

    def filter(
        self,
        parameter: str,
        values: Union[str, List[str]]
    ) -> "QueryBuilder":
        """
        Add a filter parameter

        Args:
            parameter: Parameter name (e.g., "F_D176.V1" for Year filter)
            values: Single value or list of values

        Returns:
            Self for chaining
        """
        self.params[parameter] = values
        return self

    def option(self, option: str, value: str) -> "QueryBuilder":
        """
        Set an output option

        Args:
            option: Option name (e.g., "O_rate_per")
            value: Option value

        Returns:
            Self for chaining
        """
        self.params[option] = value
        return self

    def build(self) -> Dict[str, Union[str, List[str]]]:
        """
        Build and return the parameters dictionary

        Returns:
            Parameters dictionary ready for use with WonderClient.query()
        """
        return self.params.copy()


# Backwards compatibility with old Client class
class Client:
    """Legacy client interface (backwards compatible)"""

    def __init__(self):
        self._client = WonderClient()

    def post_cdc_wonder(self, data):
        """Legacy method for posting to CDC WONDER"""
        # Extract dataset_id from request_xml
        request_xml = data.get("request_xml", "")
        dataset_id = self._client._extract_dataset_id(request_xml)

        if not dataset_id:
            # Try D176 as default
            dataset_id = "D176"

        url = f"https://wonder.cdc.gov/controller/datarequest/{dataset_id}"
        r = requests.post(url, data=data)
        if r.status_code != 200:
            raise RuntimeError("CDC WONDER request failed")
        return r.text
