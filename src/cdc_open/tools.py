"""
CDC Open Data — Anthropic API tool_use definitions and executor.

Usage with Claude API:
    from cdc_open.tools import TOOLS, execute_tool

    # Pass TOOLS to claude as tools= parameter
    # When Claude returns tool_use blocks, call execute_tool(name, input)
    result = execute_tool("get_leading_causes_of_death", {"state": "New York", "year": 2015})
"""

from typing import Any

from cdc_open import sdk

# ─── Tool definitions (Anthropic API tool_use format) ─────────────────────────

TOOLS: list[dict] = [
    {
        "name": "get_leading_causes_of_death",
        "description": (
            "Get leading causes of death in the U.S. by state and year (1999–2017). "
            "Causes include heart disease, cancer, stroke, kidney disease, Alzheimer's, etc. "
            "Returns rows with: year, cause_name, state, deaths, age_adjusted_death_rate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "Full state name: 'New York', 'California', 'Texas'. Omit for all states.",
                },
                "year": {
                    "type": "integer",
                    "description": "Year (1999–2017). Omit for all years.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records to return (default 200, max 1000).",
                },
            },
        },
    },
    {
        "name": "get_life_expectancy",
        "description": (
            "Get U.S. life expectancy at birth by race and sex (1900–2018). "
            "Returns rows with: year, race, sex, average_life_expectancy, age_adjusted_death_rate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {"type": "integer", "description": "Year (1900–2018)."},
                "race": {
                    "type": "string",
                    "enum": ["All Races", "Black", "White"],
                    "description": "Race filter.",
                },
                "sex": {
                    "type": "string",
                    "enum": ["Both Sexes", "Male", "Female"],
                    "description": "Sex filter.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 200).",
                },
            },
        },
    },
    {
        "name": "get_mortality_rates",
        "description": (
            "Get provisional age-adjusted death rates by cause, quarterly, 2020–present. "
            "Causes: 'All causes', 'Heart disease', 'Cancer', 'COVID-19', 'Drug overdose', "
            "'Suicide', 'Diabetes', 'Alzheimer disease'. "
            "Returns national and per-state rates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "quarter": {
                    "type": "string",
                    "description": "Quarter: '2024 Q4', '2025 Q1'. Omit for all.",
                },
                "cause": {
                    "type": "string",
                    "description": "'All causes', 'Heart disease', 'Cancer', 'COVID-19', 'Drug overdose', 'Suicide', 'Diabetes', 'Alzheimer disease'",
                },
                "rate_type": {
                    "type": "string",
                    "enum": ["Age-adjusted", "Crude"],
                    "description": "Rate type (default: Age-adjusted).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 200).",
                },
            },
        },
    },
    {
        "name": "get_places_county_health",
        "description": (
            "Get county-level health indicators from CDC PLACES (BRFSS-based estimates). "
            "Measures: OBESITY, DIABETES, CSMOKING (smoking), BINGE (binge drinking), BPHIGH (high BP), "
            "DEPRESSION, SLEEP (short sleep), CHD (heart disease), COPD, CANCER, STROKE, ARTHRITIS, "
            "CASTHMA (asthma), MHLTH (mental distress), PHLTH (physical distress), LPA (physical inactivity), "
            "ACCESS2 (no health insurance), DENTAL, FOODINSECU (food insecurity), LONELINESS, HOUSINSECU. "
            "Returns crude prevalence (%) by county."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "Two-letter state code: 'NY', 'CA', 'TX'. Omit for all states.",
                },
                "measure": {
                    "type": "string",
                    "description": "Measure ID: 'OBESITY', 'DIABETES', 'CSMOKING', 'DEPRESSION', 'BINGE', 'SLEEP', 'BPHIGH', 'LPA', 'ACCESS2', 'FOODINSECU', 'LONELINESS'",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 200).",
                },
            },
        },
    },
    {
        "name": "get_places_city_health",
        "description": (
            "Get city-level health indicators from CDC PLACES for all U.S. cities with population > 50,000. "
            "Each row contains all measures for a city (obesity_crudeprev, diabetes_crudeprev, etc.)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "Two-letter state code: 'NY', 'CA'.",
                },
                "city": {
                    "type": "string",
                    "description": "City name (partial match): 'Los Angeles', 'Chicago'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 200).",
                },
            },
        },
    },
    {
        "name": "get_covid_data",
        "description": (
            "Get COVID-19 weekly case and death counts by state (data through early 2023). "
            "Returns: state, date_updated, new_cases, new_deaths, tot_cases, tot_death."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "Two-letter state abbreviation: 'NY', 'CA', 'TX'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 200).",
                },
            },
        },
    },
    {
        "name": "get_weekly_deaths",
        "description": (
            "Get weekly provisional death counts by state — COVID-19, pneumonia, influenza, and total deaths. "
            "MOST CURRENT CDC MORTALITY DATA — updated weekly, covers 2020–present. "
            "Includes percent_of_expected_deaths to detect excess mortality."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "Full state name: 'New York', 'California'. Omit for all states.",
                },
                "year": {
                    "type": "integer",
                    "description": "Year (2020–present). Omit for all.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 200).",
                },
            },
        },
    },
    {
        "name": "get_disability_data",
        "description": (
            "Get disability prevalence by state and type from BRFSS survey. "
            "Types: 'Any Disability', 'Mobility Disability', 'Cognitive Disability', "
            "'Hearing Disability', 'Vision Disability', 'Self-care Disability', "
            "'Independent Living Disability', 'No Disability'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "Two-letter state code: 'NY', 'CA'. Omit for all.",
                },
                "disability_type": {
                    "type": "string",
                    "description": "'Any Disability', 'Mobility Disability', 'Cognitive Disability', 'Hearing Disability', 'Vision Disability', 'Self-care Disability', 'Independent Living Disability'",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 200).",
                },
            },
        },
    },
    {
        "name": "get_drug_overdose_data",
        "description": (
            "Get drug poisoning/overdose mortality by state (1999–2016). "
            "Includes death rates by state, sex, race, and age group. "
            "Critical for opioid crisis analysis."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "Full state name: 'West Virginia', 'Ohio', 'New Hampshire'. Omit for all.",
                },
                "year": {"type": "integer", "description": "Year (1999–2016)."},
                "sex": {
                    "type": "string",
                    "enum": ["Both Sexes", "Male", "Female"],
                    "description": "Sex filter.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 200).",
                },
            },
        },
    },
    {
        "name": "get_nutrition_obesity_data",
        "description": (
            "Get adult obesity, physical inactivity, and fruit/vegetable consumption by state (BRFSS). "
            "Topics: 'Obesity', 'Physical Activity', 'Fruits and Vegetables'. "
            "Data by state, race, age, income, and education."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "Two-letter state code: 'NY', 'CA'. Omit for all.",
                },
                "topic": {
                    "type": "string",
                    "description": "'Obesity', 'Physical Activity', 'Fruits and Vegetables'",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 200).",
                },
            },
        },
    },
    {
        "name": "get_historical_death_rates",
        "description": (
            "Get age-adjusted death rates for major causes since 1900. "
            "Causes: 'Heart Disease', 'Cancer', 'Stroke', 'Unintentional injuries', 'CLRD'. "
            "Great for long-term trend analysis — 120+ years of data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cause": {
                    "type": "string",
                    "enum": [
                        "Heart Disease",
                        "Cancer",
                        "Stroke",
                        "Unintentional injuries",
                        "CLRD",
                    ],
                    "description": "Cause of death. Omit for all causes.",
                },
                "start_year": {
                    "type": "integer",
                    "description": "Start year (earliest: 1900).",
                },
                "end_year": {
                    "type": "integer",
                    "description": "End year (latest: ~2017).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 200).",
                },
            },
        },
    },
    {
        "name": "get_birth_indicators",
        "description": (
            "Get quarterly provisional birth indicators: fertility rates, teen birth rates, "
            "preterm birth rates, cesarean delivery rates, low birthweight — by race/ethnicity. "
            "Topics: 'General Fertility', 'Teen Birth', 'Preterm', 'Cesarean', 'Low Birthweight'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "'General Fertility', 'Teen Birth', 'Preterm', 'Cesarean', 'Low Birthweight', 'NICU', 'Medicaid'",
                },
                "race_ethnicity": {
                    "type": "string",
                    "description": "'All races and origins', 'Hispanic', 'Non-Hispanic Black', 'Non-Hispanic White', 'Non-Hispanic Asian'",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 200).",
                },
            },
        },
    },
    {
        "name": "query_dataset",
        "description": (
            "Custom SODA query against any CDC dataset using raw Socrata syntax. "
            "Use when the specialized functions above don't cover your need. "
            "Dataset IDs: bi63-dtpu (leading causes of death 1999–2017), w9j2-ggv5 (life expectancy), "
            "489q-934x (mortality rates 2020+), swc5-untb (PLACES county), dxpw-cm5u (PLACES city), "
            "pwn4-m3yp (COVID), r8kw-7aab (weekly deaths), s2qv-b27b (disability), "
            "xbxb-epbu (drug overdose 1999–2016), hn4x-zwk7 (nutrition/obesity), "
            "6rkc-nb2q (historical death rates since 1900), 76vv-a7x8 (birth indicators), "
            "hk9y-quqm (COVID conditions), muzy-jte6 (weekly deaths by cause)."
        ),
        "input_schema": {
            "type": "object",
            "required": ["dataset_id"],
            "properties": {
                "dataset_id": {
                    "type": "string",
                    "description": "Socrata dataset ID, e.g. 'bi63-dtpu'",
                },
                "where": {
                    "type": "string",
                    "description": "SODA $where clause: \"year = '2015' AND state = 'New York'\"",
                },
                "select": {
                    "type": "string",
                    "description": "SODA $select clause: 'year, state, deaths'",
                },
                "group": {
                    "type": "string",
                    "description": "SODA $group clause: 'year, state'",
                },
                "order": {
                    "type": "string",
                    "description": "SODA $order clause: 'year DESC'",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max rows (default 1000, max 1000 per call).",
                },
            },
        },
    },
]

# ─── Tool executor ─────────────────────────────────────────────────────────────

_DISPATCH: dict[str, Any] = {
    "get_leading_causes_of_death": sdk.get_leading_causes_of_death,
    "get_life_expectancy": sdk.get_life_expectancy,
    "get_mortality_rates": sdk.get_mortality_rates,
    "get_places_county_health": sdk.get_places_county_health,
    "get_places_city_health": sdk.get_places_city_health,
    "get_covid_data": sdk.get_covid_data,
    "get_weekly_deaths": sdk.get_weekly_deaths,
    "get_disability_data": sdk.get_disability_data,
    "get_drug_overdose_data": sdk.get_drug_overdose_data,
    "get_nutrition_obesity_data": sdk.get_nutrition_obesity_data,
    "get_historical_death_rates": sdk.get_historical_death_rates,
    "get_birth_indicators": sdk.get_birth_indicators,
    "query_dataset": sdk.query_dataset,
}


def execute_tool(name: str, input: dict) -> list[dict[str, Any]]:
    """
    Execute a CDC tool by name with the given input dict.

    Args:
        name: Tool name matching one of the TOOLS definitions
        input: Dict of keyword arguments for the tool

    Returns:
        List of row dicts from the CDC dataset

    Raises:
        ValueError: If tool name is unknown
    """
    fn = _DISPATCH.get(name)
    if fn is None:
        raise ValueError(f"Unknown tool: {name!r}. Available: {list(_DISPATCH)}")
    return fn(**input)
