"""
LLM-Powered CDC WONDER Query Builder

This module uses an LLM with tool calling to convert natural language queries
into structured WONDER API requests. It leverages the topics_mapping.json and
query_params files to intelligently select datasets and build valid queries.

The builder uses base templates per dataset so the LLM only needs to output
meaningful overrides rather than a complete ~120-parameter request. Code merges
those overrides onto the template and enforces constraint rules (e.g. AAR
disabled when grouping by age).

Datasets with base templates:
  D176  Provisional Mortality (2018–present)
  D157  Final Mortality, Single Race (2018–2023)
  D158  Underlying Cause of Death, Single Race (2018–2023)
  D141  Multiple Cause of Death with US–Mexico Border Regions (1999–2020)
  D77   Multiple Cause of Death (1999–2020)
  D76   Underlying Cause of Death (1999–2020)
  D74   Compressed Mortality (1968–1978)
  D16   Compressed Mortality (1979–1998)
  D140  Compressed Mortality (1999–2016)
  D69   Linked Birth / Infant Death Records (2007–2023)
  D159  Linked Birth / Infant Death Records, Expanded (2017–2023)
  D31   Linked Birth / Infant Death Records (2003–2006)
  D18   Linked Birth / Infant Death Records (1999–2002)
  D23   Linked Birth / Infant Death Records (1995–1998)
  D104  Number of Heat Wave Days (1981–2010)
  D80   NLDAS Daily Sunlight (1979–2011)
  D61   MODIS Land Surface Temperature (2003–2008)
  D60   NLDAS Daily Air Temperatures and Heat Index (1979–2011)
  D73   Fine Particulate Matter PM2.5 (2003–2011)
  D81   NLDAS Daily Precipitation (1979–2011)
  D66   Natality (2007–2024)
  D149  Natality, Expanded (2016–2024)
  D192  Provisional Natality (2023–present)
  D27   Natality (2003–2006)
  D10   Natality (1995–2002)
  D8    VAERS — Vaccine Adverse Event Reporting System (1990–present)
"""

import anthropic
import json
import os
import xml.etree.ElementTree as ET

from dotenv import load_dotenv
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union

# Load environment variables from .env file
load_dotenv()

# Datasets that have base templates
TEMPLATE_DATASETS = {
    "D176",  # Provisional Mortality (2018–present)
    "D157",  # Final Mortality, Single Race (2018–2023)
    "D158",  # Underlying Cause of Death, Single Race (2018–2023)
    "D141",  # MCD with US–Mexico Border Regions (1999–2020)
    "D77",  # Multiple Cause of Death (1999–2020)
    "D76",  # Underlying Cause of Death (1999–2020)
    "D74",  # Compressed Mortality (1968–1978)
    "D16",  # Compressed Mortality (1979–1998)
    "D140",  # Compressed Mortality (1999–2016)
    "D69",  # Linked Birth / Infant Death (2007–2023)
    "D159",  # Linked Birth / Infant Death, Expanded (2017–2023)
    "D31",  # Linked Birth / Infant Death (2003–2006)
    "D18",  # Linked Birth / Infant Death (1999–2002)
    "D23",  # Linked Birth / Infant Death (1995–1998)
    "D104",  # Heat Wave Days (1981–2010)
    "D80",  # NLDAS Daily Sunlight (1979–2011)
    "D61",  # MODIS Land Surface Temperature (2003–2008)
    "D60",  # NLDAS Daily Air Temperatures and Heat Index (1979–2011)
    "D73",  # Fine Particulate Matter PM2.5 (2003–2011)
    "D81",  # NLDAS Daily Precipitation (1979–2011)
    "D66",  # Natality (2007–2024)
    "D149",  # Natality, Expanded (2016–2024)
    "D192",  # Provisional Natality (2023–present)
    "D27",  # Natality (2003–2006)
    "D10",  # Natality (1995–2002)
    "D8",  # VAERS
}

# Age-related variables across mortality datasets — AAR is
# incompatible with grouping by age dimension
AGE_VARIABLES = {
    "D176.V5",
    "D176.V51",
    "D176.V52",
    "D176.V6",
    "D157.V5",
    "D157.V51",
    "D157.V52",
    "D157.V6",
    "D158.V5",
    "D158.V51",
    "D158.V52",
    "D158.V6",
    "D141.V5",
    "D141.V51",
    "D141.V52",
    "D141.V6",
    "D77.V5",
    "D77.V51",
    "D77.V52",
    "D77.V6",
    "D76.V5",
    "D76.V51",
    "D76.V52",
    "D76.V6",
    "D74.V5",
    "D74.V6",
    "D16.V5",
    "D16.V6",
    "D140.V5",
    "D140.V6",
}


class WonderParameter(BaseModel):
    """Single query parameter with one or more values"""

    name: str = Field(..., description="Parameter name (e.g., B_1, F_D176.V1, M_1)")
    values: List[str] = Field(..., description="List of values for this parameter")


class WonderRequest(BaseModel):
    """
    Structured WONDER API request matching the XML schema.
    This represents the complete set of parameters sent to CDC WONDER.
    """

    dataset_id: str = Field(..., description="CDC WONDER dataset ID (e.g., D176)")
    parameters: List[WonderParameter] = Field(
        default_factory=list, description="List of all query parameters"
    )

    def to_dict(self) -> Dict[str, Union[str, List[str]]]:
        """Convert to dictionary format used by WonderClient"""
        result = {}
        for param in self.parameters:
            if len(param.values) == 1:
                result[param.name] = param.values[0]
            else:
                result[param.name] = param.values
        return result

    def to_xml(self) -> str:
        """Convert WonderRequest to CDC WONDER XML format"""
        lines = ['<?xml version="1.0" encoding="UTF-8"?><request-parameters>']
        for param in self.parameters:
            lines.append("\t<parameter>")
            lines.append(f"\t\t<name>{param.name}</name>")
            for value in param.values:
                if value:
                    lines.append(f"\t\t<value>{value}</value>")
                else:
                    lines.append("\t\t<value/>")
            lines.append("\t</parameter>")
        lines.append("</request-parameters>")
        return "\n".join(lines)


class QueryIntent(BaseModel):
    """User's query intent parsed by the LLM"""

    description: str = Field(
        ..., description="Natural language description of what data is requested"
    )
    health_topics: List[str] = Field(
        default_factory=list, description="Identified health topics"
    )
    time_period: Optional[str] = Field(None, description="Time period if specified")
    geography: Optional[str] = Field(None, description="Geographic scope if specified")
    grouping_dimensions: List[str] = Field(
        default_factory=list, description="How to group the results"
    )
    filters: Dict[str, List[str]] = Field(
        default_factory=dict, description="Specific filters to apply"
    )


def _parse_xml_to_parameters(xml_str: str) -> List[WonderParameter]:
    """Parse XML request string into a list of WonderParameter objects."""
    root = ET.fromstring(xml_str)
    params = []
    for param in root.findall("parameter"):
        name_el = param.find("name")
        if name_el is None or name_el.text is None:
            continue
        name = name_el.text
        values = [v.text if v.text is not None else "" for v in param.findall("value")]
        params.append(WonderParameter(name=name, values=values))
    return params


class LLMQueryBuilder:
    """
    Builds WONDER queries using an LLM with tool calling.

    The LLM outputs only meaningful overrides (grouping, time range, cause
    filter, mode selectors). Code merges those onto a pre-validated base
    template and enforces constraint rules.
    """

    def __init__(self, api_key: Optional[str] = None, data_dir: Optional[Path] = None):
        """
        Initialize the LLM query builder.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            data_dir: Path to data/raw/wonder directory
        """
        self.client = anthropic.Anthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY")
        )
        self.data_dir = (
            data_dir or Path(__file__).parent.parent.parent / "data" / "raw" / "wonder"
        )

        # Load topics mapping
        topics_path = self.data_dir / "topics_mapping.json"
        with open(topics_path) as f:
            data = json.load(f)
            self.topics_mapping = data.get("mappings", [])

        # Cache for query params
        self._query_params_cache: Dict[str, Dict] = {}

    def _load_template(self, dataset_id: str) -> Optional[str]:
        """Load the base template XML for a dataset."""
        path = Path(__file__).parent / "templates" / f"{dataset_id}-base.xml"
        if not path.exists():
            return None
        return path.read_text()

    def _merge_with_template(
        self, template_xml: str, overrides: List[WonderParameter]
    ) -> str:
        """Overlay LLM-generated overrides onto a base template."""
        root = ET.fromstring(template_xml)

        # Build ordered list of [name, values]
        params = []
        for param in root.findall("parameter"):
            name_el = param.find("name")
            if name_el is None or name_el.text is None:
                continue
            name = name_el.text
            values = [
                v.text if v.text is not None else "" for v in param.findall("value")
            ]
            params.append([name, values])

        # Index for fast lookup
        index = {name: i for i, (name, _) in enumerate(params)}

        # Apply overrides
        for override in overrides:
            if override.name in index:
                params[index[override.name]][1] = override.values
            else:
                params.append([override.name, override.values])

        # Reconstruct via WonderRequest
        dataset_id = next((v[0] for n, v in params if n == "dataset_code"), "D176")
        request = WonderRequest(
            dataset_id=dataset_id,
            parameters=[WonderParameter(name=n, values=v) for n, v in params],
        )
        return request.to_xml()

    def _apply_constraints(
        self, overrides: List[WonderParameter]
    ) -> List[WonderParameter]:
        """Enforce CDC WONDER rules that the LLM doesn't know about."""
        by_name = {p.name: p for p in overrides}

        # AAR is incompatible with age-dimension group-by
        group_by_values = {
            v for k, p in by_name.items() if k.startswith("B_") for v in p.values
        }
        if group_by_values & AGE_VARIABLES:
            by_name["O_aar_enable"] = WonderParameter(
                name="O_aar_enable", values=["false"]
            )
            by_name["O_aar"] = WonderParameter(name="O_aar", values=["aar_none"])
            by_name["O_aar_CI"] = WonderParameter(name="O_aar_CI", values=["false"])

        return list(by_name.values())

    def _load_query_params(self, dataset_id: str) -> Dict[str, Any]:
        """Load query parameters for a specific dataset"""
        if dataset_id in self._query_params_cache:
            return self._query_params_cache[dataset_id]

        params_path = self.data_dir / f"query_params_{dataset_id}.json"
        if not params_path.exists():
            raise ValueError(f"No query parameters found for dataset {dataset_id}")

        with open(params_path) as f:
            params = json.load(f)
            self._query_params_cache[dataset_id] = params
            return params

    def _get_available_datasets_summary(self) -> str:
        """Create a summary of available datasets for the LLM"""
        # Group by topic
        by_topic: Dict[str, List[Dict]] = {}
        for dataset in self.topics_mapping:
            topic = dataset.get("topic", "Unknown")
            if topic not in by_topic:
                by_topic[topic] = []
            by_topic[topic].append(dataset)

        lines = ["Available CDC WONDER Datasets:\n"]
        for topic, datasets in sorted(by_topic.items()):
            lines.append(f"\n## {topic}")
            for ds in datasets[:5]:  # Limit to first 5 per topic to save tokens
                lines.append(
                    f"- {ds['dataset_id']}: {ds.get('category', 'N/A')} "
                    f"({ds.get('years', 'N/A')})"
                )
            if len(datasets) > 5:
                lines.append(f"  ... and {len(datasets) - 5} more datasets")

        return "\n".join(lines)

    def _get_dataset_params_summary(self, dataset_id: str) -> str:
        """Create a summary of query parameters for a specific dataset"""
        params = self._load_query_params(dataset_id)

        lines = [f"Query Parameters for {dataset_id}:\n"]

        # Group parameters by type
        selects = params.get("parameters", {}).get("selects", [])
        inputs = params.get("parameters", {}).get("inputs", [])

        # Show Group By options (B_*) — show ALL options (no truncation)
        lines.append("\n### Group By Options (B_1 through B_5):")
        for select in selects:
            if select["name"].startswith("B_"):
                lines.append(f"\n{select['name']}: {select.get('label', 'N/A')}")
                for opt in select["options"]:  # show all options
                    lines.append(f"  - {opt['value']}: {opt['text']}")

        # Show Measures (M_*)
        lines.append("\n### Measures (M_*):")
        for inp in inputs:
            if inp["name"].startswith("M_") and inp["type"] == "input_checkbox":
                lines.append(f"  - {inp['name']}: {inp.get('label', 'N/A')}")

        # Show important filters (F_*)
        lines.append("\n### Key Filter Parameters:")
        filter_selects = [s for s in selects if s["name"].startswith("F_")]
        for select in filter_selects[:5]:  # Show first 5 filters
            lines.append(f"\n{select['name']}: {select.get('label', 'N/A')}")
            for opt in select["options"][:5]:
                lines.append(f"  - {opt['value']}: {opt['text']}")

        # Show output options (O_*)
        lines.append("\n### Output Options (O_*):")
        for select in selects:
            if select["name"].startswith("O_"):
                lines.append(f"  - {select['name']}: {select.get('label', 'N/A')}")

        return "\n".join(lines)

    def _create_build_query_tool_schema(self) -> Dict[str, Any]:
        """Create the tool schema for build_wonder_query"""
        return {
            "name": "build_wonder_query",
            "description": (
                "Output OVERRIDES for a CDC WONDER query. "
                "The base template already contains all boilerplate (I_*, V_*, "
                "finder-stage-*, L_*, VM_*, O_*_fmode). You only need to specify: "
                "B_1..B_5 group-by dimensions, F_* filters for time/cause/geography, "
                "O_ucd/O_age/O_race mode selectors that match your active filters, "
                "O_aar_enable if needed, and any non-default O_* options. "
                "Do NOT include boilerplate parameters — they will be filled from the template."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": (
                            "The CDC WONDER dataset ID. Options: "
                            "'D176' (Provisional Mortality 2018–present), "
                            "'D157' (Final MCD+UCD Single Race 2018–2023), "
                            "'D158' (Final UCD Single Race 2018–2023), "
                            "'D141' (MCD with Border Regions 1999–2020), "
                            "'D77' (Multiple Cause of Death 1999–2020), "
                            "'D76' (UCD 1999–2020), "
                            "'D140' (Compressed 1999–2016), "
                            "'D16' (Compressed 1979–1998), "
                            "'D74' (Compressed 1968–1978), "
                            "'D69' (Linked Birth/Infant Death 2007–2023), "
                            "'D159' (Linked Birth/Infant Death Expanded 2017–2023), "
                            "'D31' (Linked Birth/Infant Death 2003–2006), "
                            "'D18' (Linked Birth/Infant Death 1999–2002), "
                            "'D23' (Linked Birth/Infant Death 1995–1998), "
                            "'D104' (Heat Wave Days 1981–2010), "
                            "'D80' (NLDAS Sunlight 1979–2011), "
                            "'D61' (MODIS Land Surface Temperature 2003–2008), "
                            "'D60' (NLDAS Air Temperatures/Heat Index 1979–2011), "
                            "'D73' (PM2.5 Air Quality 2003–2011), "
                            "'D81' (NLDAS Precipitation 1979–2011), "
                            "'D66' (Natality 2007–2024), "
                            "'D149' (Natality Expanded 2016–2024), "
                            "'D192' (Provisional Natality 2023–present), "
                            "'D27' (Natality 2003–2006), "
                            "'D10' (Natality 1995–2002), "
                            "'D8' (VAERS vaccine adverse events)"
                        ),
                    },
                    "parameters": {
                        "type": "array",
                        "description": (
                            "List of override parameters. Include only: "
                            "B_1..B_5 (group-by), F_* (filters), "
                            "O_ucd/O_age/O_race (mode selectors matching active filters), "
                            "M_* (measures to include/exclude), "
                            "O_aar_enable/O_aar (AAR settings). "
                            "Omit all I_*, V_*, finder-stage-*, L_*, VM_*, O_*_fmode — those come from the template."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": (
                                        "Parameter name following WONDER conventions: "
                                        "B_* for grouping, M_* for measures, F_* for filters, "
                                        "O_* for output options and mode selectors"
                                    ),
                                },
                                "values": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": (
                                        "List of values for this parameter. "
                                        "Use '*All*' for all values, '*None*' for empty grouping slots."
                                    ),
                                },
                            },
                            "required": ["name", "values"],
                        },
                    },
                },
                "required": ["dataset_id", "parameters"],
            },
        }

    def build_query(self, intent_text: str, max_tokens: int = 4096) -> WonderRequest:
        """
        Convert natural language intent into a structured WONDER query.

        The LLM outputs only overrides; code merges them onto a validated
        base template and enforces constraint rules.

        Args:
            intent_text: Natural language description of the desired query
            max_tokens: Maximum tokens for LLM response

        Returns:
            WonderRequest object with dataset_id and parameters

        Example:
            >>> builder = LLMQueryBuilder()
            >>> request = builder.build_query(
            ...     "Show me opioid overdose deaths by year from 2018 to 2024"
            ... )
            >>> print(request.dataset_id)
            'D176'
        """
        system_prompt = f"""You are a CDC WONDER query builder assistant. Your job is to convert
natural language queries into structured WONDER API requests.

{self._get_available_datasets_summary()}

## Process
1. Analyze the user's intent to determine which dataset is most appropriate:

   Recent / final mortality (ICD-10):
   - D176: Provisional Mortality (2018–present)          — most recent data; use by default for recent queries
   - D157: Final Mortality, Single Race (2018–2023)      — like D176 but final (MCD + UCD)
   - D158: Underlying Cause of Death, Single Race (2018–2023) — like D157 but UCD only (no MCD filters)

   Historical mortality (ICD-10):
   - D141: MCD with US–Mexico Border Regions (1999–2020) — like D77 but adds border/metro region geography
   - D77:  Multiple Cause of Death (1999–2020)           — ICD-10, bridged-race; for trends since 1999
   - D76:  Underlying Cause of Death (1999–2020)         — like D77 but UCD only (no MCD filters)

   Compressed mortality (older ICD):
   - D140: Compressed Mortality (1999–2016)              — ICD-10, bridged-race, fewer variables
   - D16:  Compressed Mortality (1979–1998)              — ICD-9; for trends from 1979
   - D74:  Compressed Mortality (1968–1978)              — ICD-8; for pre-1979 data

   Infant / birth mortality:
   - D69:  Linked Birth / Infant Death (2007–2023)           — most recent; use by default for infant mortality
   - D159: Linked Birth / Infant Death, Expanded (2017–2023) — like D69 with more variables (race detail, extended demographics)
   - D31:  Linked Birth / Infant Death (2003–2006)
   - D18:  Linked Birth / Infant Death (1999–2002)
   - D23:  Linked Birth / Infant Death (1995–1998)
             These datasets link birth certificates to infant death records.
             Rate = deaths per 1,000 live births. No age-adjusted rates.

   Natality (live births):
   - D66:  Natality (2007–2024)                             — use by default for recent birth data
   - D149: Natality, Expanded (2016–2024)                   — like D66 with race detail and more measures
   - D192: Provisional Natality (2023–present)              — most recent; updates monthly
   - D27:  Natality (2003–2006)
   - D10:  Natality (1995–2002)
             Rate = births per 1,000 (or per 10,000/100,000/1,000,000) population. No AAR.
             Use for birth counts, birth rates, fertility rates, obstetric outcomes.

   Environmental / climate:
   - D104: Heat Wave Days, May–Sep (1981–2010)             — annual heat wave day counts per county
   - D60:  NLDAS Daily Air Temperatures & Heat Index (1979–2011) — min/mean/max temp + heat index
   - D80:  NLDAS Daily Sunlight KJ/m² (1979–2011)          — solar radiation
   - D81:  NLDAS Daily Precipitation mm (1979–2011)        — rainfall
   - D61:  MODIS Land Surface Temperature (2003–2008)      — satellite-derived surface temperature
   - D73:  Fine Particulate Matter PM2.5 µg/m³ (2003–2011) — air quality
             Environmental datasets report statistical summaries (mean, min, max, CI) not rates.
             No AAR. No O_ucd/O_mcd. Geography is by county/state, not residence.

   Vaccine safety:
   - D8:   VAERS — Vaccine Adverse Event Reporting System (1990–present)
             Use for questions about vaccine safety, adverse reactions, outcomes
             after vaccination. Counts reports (not rates).

   Selection tips:
   - If the user asks about births, birth rates, fertility, or obstetric outcomes, choose D66 (default) or D149 for race detail.
   - If the user asks about natality before 2007, choose D27 or D10 by year range.
   - If the user asks about infant mortality or neonatal/postneonatal deaths, choose D69 (default) or D159.
   - If the user asks about infant mortality before 2007, choose D31, D18, or D23 by year range.
   - If the user asks about years before 1999, choose D16 (ICD-9) or D74 (ICD-8).
   - If the user asks for 1999–2020 and mentions multiple causes of death, choose D77 or D141.
   - If the user needs ICD-10 underlying cause only for 1999–2020, choose D76.
   - If the user does not specify a dataset and the query is about recent mortality, default to D176.
2. Request the detailed parameters for the selected dataset.
3. Output OVERRIDES using the build_wonder_query tool.

## Important: MODE SELECTORS (mortality datasets D176/D157/D77 only)

O_ucd, O_mcd, O_age, O_race, O_location are MODE SELECTORS — they must match
the active filter or group-by dimension:

  - Filter by ICD chapter (F_*.V2)          → O_ucd = {{DS}}.V2
  - Filter by drug/alcohol cause (F_*.V25)  → O_ucd = {{DS}}.V25
  - Filter by MCD ICD codes (F_*.V13)       → O_mcd = {{DS}}.V13
  - Group by ten-year age (B_* = *.V5)      → O_age = {{DS}}.V5
  - Group by five-year age (B_* = *.V51)    → O_age = {{DS}}.V51
  - Group by infant age (B_* = *.V6)        → O_age = {{DS}}.V6

Setting the wrong mode selector causes the filter to be silently ignored.
Always set the mode selector to match whatever filter or group-by you are using.

## D8 VAERS — Key Variables

Group By (B_*) useful values:
  D8.V14-level1  Vaccine Type (broad category)
  D8.V14-level2  Vaccine (specific product, e.g., COVID19, FLU, MMR)
  D8.V13-level2  Symptom (MedDRA symptom hierarchy)
  D8.V2-level1   Year Received
  D8.V16-level1  Year Reported
  D8.V1          Age group
  D8.V5          Sex
  D8.V12         State / Territory
  D8.V11         Event Category (Death, Life Threatening, Hospitalized, etc.)
  D8.V10         Serious (Yes / No)

Filters (F_*):
  F_D8.V14   Vaccine product (codes: COVID19, FLU, MMR, VARZOS, etc.)
  F_D8.V13   Symptom alphabet (A–Z groups; use V_ textareas for specific symptoms)
  F_D8.V16   Year Reported
  F_D8.V2    Year Received
  F_D8.V3    Year Vaccinated

Variable filters (V_*):
  V_D8.V1    Age group filter
  V_D8.V5    Sex filter (F/M)
  V_D8.V11   Event category filter (DTH=Death, LT=Life Threatening, etc.)
  V_D8.V10   Serious filter (Y=Yes, N=No)
  V_D8.V12   State/Territory filter

D8 has NO age-adjusted rates (AAR) — it counts adverse event reports.
D8 measures: M_1=D8.M1 (count of events), M_2=D8.M2 (count of reports).

## Important: OVERRIDES ONLY

The base template already contains all boilerplate:
  V_*, finder-stage-*, O_*_fmode

You ONLY need to specify:
  - B_1..B_5: group-by dimensions (use *None* for unused slots)
  - F_* filters: time periods, vaccine type, geography
  - V_* filters: for demographic/outcome restrictions (age, sex, seriousness)
  - O_ucd / O_age / O_race: mode selectors (mortality datasets only)
  - O_aar_enable: set to false when grouping by age (mortality only)
  - M_*: only if you need non-default measures

Do NOT include finder-stage-*, or O_*_fmode — those come from the template.

When you need parameter details for a specific dataset, just ask and I'll provide them.
"""

        messages = [{"role": "user", "content": intent_text}]

        # Iterative conversation with the LLM
        while True:
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                system=system_prompt,
                tools=[self._create_build_query_tool_schema()],
                messages=messages,
            )

            # Add assistant response to conversation
            messages.append({"role": "assistant", "content": response.content})

            # Check if we got a tool use
            tool_use_block = None
            for block in response.content:
                if block.type == "tool_use" and block.name == "build_wonder_query":
                    tool_use_block = block
                    break

            if tool_use_block:
                input_data = tool_use_block.input
                raw_request = WonderRequest(**input_data)

                # Apply template merge if template exists for this dataset
                template = self._load_template(raw_request.dataset_id)
                if template:
                    constrained = self._apply_constraints(raw_request.parameters)
                    merged_xml = self._merge_with_template(template, constrained)
                    merged_params = _parse_xml_to_parameters(merged_xml)
                    return WonderRequest(
                        dataset_id=raw_request.dataset_id,
                        parameters=merged_params,
                    )

                # Fallback: no template for this dataset
                return raw_request

            # Check if LLM is asking for more information
            text_response = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text_response += block.text

            if response.stop_reason == "end_turn":
                # LLM might be asking for dataset parameters
                import re

                dataset_matches = re.findall(r"\b(D\d+)\b", text_response)
                if dataset_matches:
                    dataset_id = dataset_matches[0]
                    params_summary = self._get_dataset_params_summary(dataset_id)
                    messages.append({"role": "user", "content": params_summary})
                    continue
                else:
                    raise ValueError(
                        f"LLM did not build a query. Response: {text_response}"
                    )

            # If we get here, something unexpected happened
            raise ValueError(f"Unexpected response from LLM: {response}")
