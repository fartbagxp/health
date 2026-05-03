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


_WASTEWATER_DATASETS = {
    "sars_cov2": "wastewater_covid",
    "flu_a": "wastewater_flu",
    "measles": "wastewater_measles",
}

_WASTEWATER_SELECT = (
    "state_territory, sample_collect_date, counties_served, county_fips, "
    "population_served, pcr_target, pcr_target_detect, pcr_target_avg_conc, "
    "pcr_target_units, pcr_target_flowpop_lin, date_updated"
)


def get_wastewater_data(
    pathogen: str = "sars_cov2",
    state: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    detected_only: bool = False,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """NWSS wastewater surveillance: RNA concentrations by pathogen (updated weekly).
    pathogen: 'sars_cov2' (2020+), 'flu_a' (2022+), 'measles' (2024+)
    state: two-letter code e.g. 'NY', 'CA'
    start_date / end_date: 'YYYY-MM-DD'
    detected_only: only return samples where pcr_target_detect='yes'
    Key metric: pcr_target_flowpop_lin (flow-population-normalized, comparable across sites)
    """
    dataset_key = _WASTEWATER_DATASETS.get(pathogen)
    if dataset_key is None:
        raise ValueError(
            f"Unknown pathogen {pathogen!r}. Use: {list(_WASTEWATER_DATASETS)}"
        )
    clauses = []
    if state:
        clauses.append(f"state_territory = '{state.lower()}'")
    if start_date:
        clauses.append(f"sample_collect_date >= '{start_date}'")
    if end_date:
        clauses.append(f"sample_collect_date <= '{end_date}'")
    if detected_only:
        clauses.append("pcr_target_detect = 'yes'")
    return query_dataset(
        DATASETS[dataset_key].id,
        where=" AND ".join(clauses) if clauses else None,
        select=_WASTEWATER_SELECT,
        order="sample_collect_date DESC",
        limit=limit,
    )


def get_resp_net_hospitalizations(
    network: str | None = None,
    season: str | None = None,
    age_group: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """RESP-NET weekly hospitalization rates for RSV, COVID-19, and Influenza (2017–present).
    network: 'FluSurv-NET', 'COVID-NET', 'RSV-NET'
    season: '2024-25'
    age_group: 'Overall', '0-4 years', '5-17 years', '18-49 years', '65+ years'
    """
    clauses = []
    if network:
        clauses.append(f"surveillance_network = '{network}'")
    if season:
        clauses.append(f"season = '{season}'")
    if age_group:
        clauses.append(f"age_group = '{age_group}'")
    return query_dataset(
        DATASETS["resp_net"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="week_ending_date DESC",
        limit=limit,
    )


def get_rsv_hospitalizations(
    season: str | None = None,
    age_category: str | None = None,
    state: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """RSV-NET weekly RSV hospitalization rates by state/age/sex/race (2018–present).
    season: '2024-25'
    age_category: 'Overall', '0-5 months', '6-11 months', '1-4 years', '65-74 years', '75+ years'
    state: surveillance site name e.g. 'California', 'New York'
    """
    clauses = []
    if season:
        clauses.append(f"season = '{season}'")
    if age_category:
        clauses.append(f"age_category = '{age_category}'")
    if state:
        clauses.append(f"state = '{state}'")
    return query_dataset(
        DATASETS["rsv_net"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="week_ending_date DESC",
        limit=limit,
    )


def get_covid_net_hospitalizations(
    season: str | None = None,
    age_category: str | None = None,
    state: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """COVID-NET weekly COVID-19 hospitalization rates by state/age/sex/race (2020–present).
    season: '2024-25'
    age_category: 'Overall', '0-4 years', '18-49 years', '65-74 years', '75+ years'
    state: surveillance site name e.g. 'California', 'New York'
    """
    clauses = []
    if season:
        clauses.append(f"season = '{season}'")
    if age_category:
        clauses.append(f"agecat_label = '{age_category}'")
    if state:
        clauses.append(f"state = '{state}'")
    return query_dataset(
        DATASETS["covid_net"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="week_ending_date DESC",
        limit=limit,
    )


def get_resp_deaths_pct(
    pathogen: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Provisional weekly % of total US deaths from COVID-19, Influenza, and RSV (2020–present).
    pathogen: 'COVID-19', 'Influenza', 'RSV'
    start_date / end_date: 'YYYY-MM-DD'
    """
    clauses = []
    if pathogen:
        clauses.append(f"pathogen = '{pathogen}'")
    if start_date:
        clauses.append(f"week_end >= '{start_date}'")
    if end_date:
        clauses.append(f"week_end <= '{end_date}'")
    return query_dataset(
        DATASETS["resp_deaths_pct"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="week_end DESC",
        limit=limit,
    )


def get_resp_deaths_pct_demo(
    pathogen: str | None = None,
    demographic_type: str | None = None,
    state: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Provisional weekly % deaths for COVID-19/Flu/RSV by demographics and state (2020–present).
    pathogen: 'COVID-19', 'Flu', 'RSV', 'Combined'
    demographic_type: 'Age', 'Sex', 'Race/Ethnicity'
    state: full state name or 'United States'
    start_date / end_date: 'YYYY-MM-DD'
    """
    clauses = []
    if pathogen:
        clauses.append(f"pathogen = '{pathogen}'")
    if demographic_type:
        clauses.append(f"demographic_type = '{demographic_type}'")
    if state:
        clauses.append(f"state = '{state}'")
    if start_date:
        clauses.append(f"weekending_date >= '{start_date}'")
    if end_date:
        clauses.append(f"weekending_date <= '{end_date}'")
    return query_dataset(
        DATASETS["resp_deaths_pct_demo"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="weekending_date DESC",
        limit=limit,
    )


def get_rsv_positivity(
    level: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Weekly RSV NAAT test positivity from NREVSS labs (2020–present).
    level: 'National', 'HHS Region 1' through 'HHS Region 10'
    start_date / end_date: 'YYYY-MM-DD'
    Key metric: pcr_percent_positive (3-week centered moving average)
    """
    clauses = []
    if level:
        clauses.append(f"level = '{level}'")
    if start_date:
        clauses.append(f"mmwrweek_end >= '{start_date}'")
    if end_date:
        clauses.append(f"mmwrweek_end <= '{end_date}'")
    return query_dataset(
        DATASETS["rsv_positivity"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="mmwrweek_end DESC",
        limit=limit,
    )


def get_nursing_home_resp(
    jurisdiction: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Weekly COVID-19/Flu/RSV cases, hospitalizations, and vaccination rates for nursing home residents (2024–present).
    jurisdiction: full state name e.g. 'California', or 'National'
    start_date / end_date: 'YYYY-MM-DD'
    """
    clauses = []
    if jurisdiction:
        clauses.append(f"jurisdiction = '{jurisdiction}'")
    if start_date:
        clauses.append(f"survweekend >= '{start_date}'")
    if end_date:
        clauses.append(f"survweekend <= '{end_date}'")
    return query_dataset(
        DATASETS["nursing_home_resp"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="survweekend DESC",
        limit=limit,
    )


def get_resp_vaccination(
    vaccine: str | None = None,
    geographic_level: str | None = None,
    geographic_name: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Weekly flu, COVID-19, and RSV vaccination coverage from National Immunization Survey (2023–present).
    vaccine: 'Influenza', 'COVID-19', 'RSV'
    geographic_level: 'National', 'State', 'Region'
    geographic_name: 'California', 'HHS Region 1', etc.
    """
    clauses = []
    if vaccine:
        clauses.append(f"vaccine = '{vaccine}'")
    if geographic_level:
        clauses.append(f"geographic_level = '{geographic_level}'")
    if geographic_name:
        clauses.append(f"geographic_name = '{geographic_name}'")
    return query_dataset(
        DATASETS["resp_vaccination"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="week_ending DESC",
        limit=limit,
    )


def get_flu_vaccine_doses(
    season: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Weekly cumulative flu vaccine doses distributed nationally by season (2009–present).
    season: '2024-2025', '2023-2024'
    """
    clauses = []
    if season:
        clauses.append(f"influenza_season = '{season}'")
    return query_dataset(
        DATASETS["flu_vaccine_doses"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="end_date DESC",
        limit=limit,
    )


def get_drug_overdose_counts(
    state: str | None = None,
    year: int | None = None,
    indicator: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Monthly provisional drug overdose death counts by state and drug type (2015–present).
    state: two-letter code e.g. 'OH', 'WV'
    year: e.g. 2023
    indicator: 'Drug Overdose Deaths', 'All Opioids', 'Natural & Semi-Synthetic Opioids',
               'Methadone', 'Synthetic Opioids', 'Heroin', 'Cocaine', 'Psychostimulants'
    """
    clauses = []
    if state:
        clauses.append(f"state = '{state.upper()}'")
    if year:
        clauses.append(f"year = {year}")
    if indicator:
        clauses.append(f"indicator LIKE '%{indicator}%'")
    return query_dataset(
        DATASETS["drug_overdose_vsrr"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="year DESC, month DESC",
        limit=limit,
    )


def get_drug_overdose_county(
    state: str | None = None,
    year: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Quarterly provisional county-level drug overdose death counts (2020–present).
    state: two-letter code e.g. 'OH', 'WV'
    year: '2023'
    """
    clauses = []
    if state:
        clauses.append(f"st_abbrev = '{state.upper()}'")
    if year:
        clauses.append(f"year = '{year}'")
    return query_dataset(
        DATASETS["drug_overdose_county"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="monthendingdate DESC",
        limit=limit,
    )


def get_nndss_weekly(
    state: str | None = None,
    year: str | None = None,
    week: int | None = None,
    disease: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """NNDSS provisional weekly cases for ~100 nationally notifiable diseases (2014–present).
    disease: partial match on disease label e.g. 'Measles', 'Pertussis', 'Hepatitis A',
             'Lyme Disease', 'Tuberculosis', 'Salmonellosis', 'Gonorrhea'
    state: full state name or two-letter code
    year: '2024'
    week: MMWR week number 1–53
    Columns: m1 = current week cases, m2 = previous 52-week median, m1_flag/m2_flag = suppression notes
    """
    clauses = []
    if state:
        clauses.append(f"states = '{state}'")
    if year:
        clauses.append(f"year = '{year}'")
    if week:
        clauses.append(f"week = {week}")
    if disease:
        clauses.append(f"upper(label) LIKE '%{disease.upper()}%'")
    return query_dataset(
        DATASETS["nndss_weekly"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="year DESC, week DESC",
        limit=limit,
    )


def clear_cache() -> None:
    _get_client().clear_cache()
