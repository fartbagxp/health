"""
CDC Open Data SDK — high-level query functions for data.cdc.gov datasets.

Each function wraps a specific dataset with sensible defaults and filtering.
For advanced queries, use query_dataset() directly.

Example:
    from cdc_open.sdk import get_leading_causes_of_death
    rows = get_leading_causes_of_death(state="New York", year=2015)
"""

import os
from typing import Any

from cdc_open.client import SodaClient
from cdc_open.datasets import DATASETS

_client: SodaClient | None = None


def _get_client() -> SodaClient:
    global _client
    if _client is None:
        _client = SodaClient(app_token=os.environ.get("CDC_DATA_APP_TOKEN"))
    return _client


def query_dataset(
    dataset_id: str,
    where: str | None = None,
    select: str | None = None,
    group: str | None = None,
    order: str | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """Generic SODA query against any CDC dataset by its Socrata ID."""
    return _get_client().get(
        dataset_id, where=where, select=select, group=group, order=order, limit=limit
    )


def get_leading_causes_of_death(
    state: str | None = None,
    year: int | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Leading causes of death by state/year (1999–2017)."""
    clauses = []
    if state:
        clauses.append(f"state = '{state}'")
    if year:
        clauses.append(f"year = '{year}'")
    return query_dataset(
        DATASETS["leading_death"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="deaths DESC",
        limit=limit,
    )


def get_life_expectancy(
    year: int | None = None,
    race: str | None = None,
    sex: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Life expectancy at birth by race and sex (1900–2018).
    race: 'All Races', 'Black', 'White'
    sex: 'Both Sexes', 'Male', 'Female'
    """
    clauses = []
    if year:
        clauses.append(f"year = '{year}'")
    if race:
        clauses.append(f"race = '{race}'")
    if sex:
        clauses.append(f"sex = '{sex}'")
    return query_dataset(
        DATASETS["life_expectancy"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="year DESC",
        limit=limit,
    )


def get_mortality_rates(
    quarter: str | None = None,
    cause: str | None = None,
    rate_type: str = "Age-adjusted",
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Provisional quarterly age-adjusted mortality rates by cause (2020–present).
    cause: 'All causes', 'Heart disease', 'Cancer', 'COVID-19', 'Drug overdose', 'Suicide'
    quarter: '2024 Q4', '2025 Q1'
    """
    clauses = [
        f"rate_type = '{rate_type}'",
        "time_period = '12 months ending with quarter'",
    ]
    if quarter:
        clauses.append(f"year_and_quarter = '{quarter}'")
    if cause:
        clauses.append(f"cause_of_death = '{cause}'")
    return query_dataset(
        DATASETS["mortality_rates"].id,
        where=" AND ".join(clauses),
        order="year_and_quarter DESC",
        limit=limit,
    )


def get_places_county_health(
    state: str | None = None,
    measure: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """County-level PLACES health indicators (BRFSS-based).
    state: two-letter code e.g. 'NY', 'CA'
    measure: 'OBESITY', 'DIABETES', 'CSMOKING', 'DEPRESSION', 'BINGE', 'SLEEP',
             'BPHIGH', 'LPA', 'ACCESS2', 'FOODINSECU', 'LONELINESS', 'HOUSINSECU'
    """
    clauses = []
    if state:
        clauses.append(f"stateabbr = '{state.upper()}'")
    if measure:
        clauses.append(f"measureid = '{measure.upper()}'")
    return query_dataset(
        DATASETS["places_county"].id,
        where=" AND ".join(clauses) if clauses else None,
        select="stateabbr, statedesc, locationname, measureid, short_question_text, data_value, data_value_type, totalpopulation, category",
        order="data_value DESC",
        limit=limit,
    )


def get_places_city_health(
    state: str | None = None,
    city: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """City-level PLACES health indicators for all U.S. cities with population > 50,000."""
    clauses = []
    if state:
        clauses.append(f"stateabbr = '{state.upper()}'")
    if city:
        clauses.append(f"upper(placename) LIKE '%{city.upper()}%'")
    return query_dataset(
        DATASETS["places_city"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="stateabbr, placename",
        limit=limit,
    )


def get_covid_data(
    state: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """COVID-19 weekly cases and deaths by state (data through early 2023).
    state: two-letter abbreviation e.g. 'NY', 'CA'
    """
    clauses = []
    if state:
        clauses.append(f"state = '{state.upper()}'")
    return query_dataset(
        DATASETS["covid_cases"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="date_updated DESC",
        limit=limit,
    )


def get_weekly_deaths(
    state: str | None = None,
    year: int | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Weekly provisional death counts: COVID-19, pneumonia, influenza, total deaths (2020–present).
    Most current CDC mortality data — updated weekly.
    state: full state name e.g. 'New York', 'California'
    """
    clauses = ["`group` = 'By Week'"]
    if state:
        clauses.append(f"state = '{state}'")
    if year:
        clauses.append(f"year = '{year}'")
    return query_dataset(
        DATASETS["weekly_deaths"].id,
        where=" AND ".join(clauses),
        order="end_date DESC",
        limit=limit,
    )


def get_disability_data(
    state: str | None = None,
    disability_type: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Disability prevalence by state and type from BRFSS.
    disability_type: 'Any Disability', 'Mobility Disability', 'Cognitive Disability',
                     'Hearing Disability', 'Vision Disability', 'Self-care Disability'
    state: two-letter code e.g. 'NY'
    """
    clauses = [
        "stratificationcategoryid1 = 'CAT1'"
    ]  # Overall, not by age/race subgroup
    if state:
        clauses.append(f"locationabbr = '{state.upper()}'")
    if disability_type:
        clauses.append(f"response = '{disability_type}'")
    return query_dataset(
        DATASETS["disability"].id,
        where=" AND ".join(clauses),
        select="locationabbr, locationdesc, response, data_value, data_value_type, year, number, weightednumber",
        order="year DESC, locationabbr",
        limit=limit,
    )


def get_drug_overdose_data(
    state: str | None = None,
    year: int | None = None,
    sex: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Drug poisoning/overdose mortality by state (1999–2016).
    sex: 'Both Sexes', 'Male', 'Female'
    """
    clauses = []
    if state:
        clauses.append(f"state = '{state}'")
    if year:
        clauses.append(f"year = '{year}'")
    if sex:
        clauses.append(f"sex = '{sex}'")
    return query_dataset(
        DATASETS["drug_overdose_state"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="year DESC",
        limit=limit,
    )


def get_nutrition_obesity_data(
    state: str | None = None,
    topic: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Adult obesity, physical inactivity, and fruit/vegetable consumption by state (BRFSS).
    topic: 'Obesity', 'Physical Activity', 'Fruits and Vegetables'
    state: two-letter code e.g. 'NY'
    """
    clauses = ["data_value IS NOT NULL"]
    if state:
        clauses.append(f"locationabbr = '{state.upper()}'")
    if topic:
        clauses.append(f"class LIKE '%{topic}%'")
    return query_dataset(
        DATASETS["nutrition_obesity"].id,
        where=" AND ".join(clauses),
        select="yearstart, yearend, locationabbr, locationdesc, class, topic, question, data_value, data_value_unit, stratificationcategory1, stratification1",
        order="yearend DESC",
        limit=limit,
    )


def get_historical_death_rates(
    cause: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Age-adjusted death rates for major causes since 1900.
    cause: 'Heart Disease', 'Cancer', 'Stroke', 'Unintentional injuries', 'CLRD'
    """
    clauses = []
    if cause:
        clauses.append(f"leading_causes = '{cause}'")
    if start_year:
        clauses.append(f"year >= '{start_year}'")
    if end_year:
        clauses.append(f"year <= '{end_year}'")
    return query_dataset(
        DATASETS["death_rates_historical"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="year DESC",
        limit=limit,
    )


def get_birth_indicators(
    topic: str | None = None,
    race_ethnicity: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Quarterly birth indicators: fertility rates, teen births, preterm, cesarean by race/ethnicity.
    topic: 'General Fertility', 'Teen Birth', 'Preterm', 'Cesarean', 'Low Birthweight'
    race_ethnicity: 'All races and origins', 'Hispanic', 'Non-Hispanic Black', 'Non-Hispanic White'
    """
    clauses = []
    if topic:
        clauses.append(f"topic_subgroup LIKE '%{topic}%'")
    if race_ethnicity:
        clauses.append(f"race_ethnicity = '{race_ethnicity}'")
    return query_dataset(
        DATASETS["birth_indicators"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="year_and_quarter DESC",
        limit=limit,
    )


def clear_cache() -> None:
    _get_client().clear_cache()
