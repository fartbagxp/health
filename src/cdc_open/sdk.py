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
    "rsv": "wastewater_rsv",
}

_WASTEWATER_SELECT = (
    "state_territory, sample_collect_date, counties_served, county_fips, "
    "population_served, pcr_target, pcr_target_detect, pcr_target_avg_conc, "
    "pcr_target_units, pcr_target_flowpop_lin, date_updated"
)


def get_wastewater_activity(
    pathogen: str | None = None,
    state: str | None = None,
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """CDC wastewater viral activity level (scored/categorized) for SARS-CoV-2, Flu A, and RSV (2023–present).
    pathogen: 'SARS-CoV-2', 'Influenza A virus', 'Respiratory syncytial virus'
    state: full state/territory name e.g. 'California'
    category: 'Very Low', 'Low', 'Moderate', 'High', 'Very High'
    start_date / end_date: 'YYYY-MM-DD'
    Key metric: site_wval (score), site_wval_category (level label)
    """
    clauses = []
    if pathogen:
        clauses.append(f"pathogen_target = '{pathogen}'")
    if state:
        clauses.append(f"state_territory = '{state}'")
    if category:
        clauses.append(f"site_wval_category = '{category}'")
    if start_date:
        clauses.append(f"week_end >= '{start_date}'")
    if end_date:
        clauses.append(f"week_end <= '{end_date}'")
    return query_dataset(
        DATASETS["wastewater_activity"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="week_end DESC",
        limit=limit,
    )


def get_wastewater_h5(
    state: str | None = None,
    detected_only: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Avian Influenza A (H5) wastewater sample data from US sampling sites (2024–present).
    state: two-letter state abbreviation e.g. 'ca', 'tx' (lowercase in this dataset)
    detected_only: only return samples where pcr_target_detect='yes'
    start_date / end_date: 'YYYY-MM-DD'
    Key metric: pcr_target_flowpop_lin (flow-population-normalized concentration)
    """
    clauses = []
    if state:
        clauses.append(f"state_territory = '{state.lower()}'")
    if detected_only:
        clauses.append("pcr_target_detect = 'yes'")
    if start_date:
        clauses.append(f"sample_collect_date >= '{start_date}'")
    if end_date:
        clauses.append(f"sample_collect_date <= '{end_date}'")
    return query_dataset(
        DATASETS["wastewater_h5"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="sample_collect_date DESC",
        limit=limit,
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
    pathogen: 'sars_cov2' (2020+), 'flu_a' (2022+), 'measles' (2024+), 'rsv' (2023+)
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
    jurisdiction: two-letter state code e.g. 'CA', 'TX', or 'USA' for national, 'Region 1'-'Region 10' for HHS regions
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


def get_flu_coverage_all_ages(
    geography: str | None = None,
    geography_type: str | None = None,
    season: str | None = None,
    dimension_type: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Monthly cumulative influenza vaccination coverage for all ages 6+ months by state (NIS-Flu, 2009–present).
    geography: county/state name e.g. 'California' — for national use geography_type='HHS Regions/National'
    geography_type: 'States/Local Areas', 'HHS Regions/National'
    season: '2024-25', '2023-24'
    dimension_type: 'Age', 'Race/Ethnicity', 'Poverty', 'Overall'
    Key metric: coverage_estimate (%)
    """
    clauses = []
    if geography:
        clauses.append(f"geography = '{geography}'")
    if geography_type:
        clauses.append(f"geography_type = '{geography_type}'")
    if season:
        clauses.append(f"year_season = '{season}'")
    if dimension_type:
        clauses.append(f"dimension_type = '{dimension_type}'")
    return query_dataset(
        DATASETS["flu_coverage_all_ages"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="year_season DESC, month DESC",
        limit=limit,
    )


def get_resp_coverage_adults(
    geography: str | None = None,
    vaccine: str | None = None,
    year: int | None = None,
    dimension: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Monthly COVID-19, flu, and RSV vaccination coverage among adults from NIS-FRVM (2024–present).
    geography: state name e.g. 'California', or 'National'
    vaccine: 'COVID-19', 'Influenza', 'RSV'  (filters on new_vax_group)
    year: 2024, 2025
    dimension: demographic group e.g. 'Black, Non-Hispanic', 'Age 65+'
    Key metric: dsss_value (% vaccinated), dsss_confidenceinterval
    """
    clauses = []
    if geography:
        clauses.append(f"geographic_label = '{geography}'")
    if vaccine:
        clauses.append(f"new_vax_group = '{vaccine}'")
    if year:
        clauses.append(f"dsss_year = '{year}'")
    if dimension:
        clauses.append(
            f"upper(dsss_group_variable_category) LIKE '%{dimension.upper()}%'"
        )
    return query_dataset(
        DATASETS["resp_coverage_adults"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="dsss_year DESC",
        limit=limit,
    )


def get_covid_coverage_adults(
    geography: str | None = None,
    year: int | None = None,
    indicator: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Monthly COVID-19 vaccination coverage and vaccine confidence among adults from NIS-ACM.
    geography: state name e.g. 'California', or 'National'
    year: 2021–present
    indicator: partial match on indicator_name e.g. 'Up to date', 'Received a 2024'
    Key metric: estimate (%), _95_ci
    """
    clauses = []
    if geography:
        clauses.append(f"geography = '{geography}'")
    if year:
        clauses.append(f"year = '{year}'")
    if indicator:
        clauses.append(f"upper(indicator_name) LIKE '%{indicator.upper()}%'")
    return query_dataset(
        DATASETS["covid_coverage_adults"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="year DESC",
        limit=limit,
    )


def get_rsv_coverage_adults_60plus(
    geography: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Weekly cumulative RSV vaccination coverage among adults 60+ by state (2023–present).
    geography: state name e.g. 'California', or 'National'
    start_date / end_date: 'YYYY-MM-DD'
    Key metric: estimate (% vaccinated), ci_half_width_95pct
    """
    clauses = []
    if geography:
        clauses.append(f"geographic_name = '{geography}'")
    if start_date:
        clauses.append(f"week_ending >= '{start_date}'")
    if end_date:
        clauses.append(f"week_ending <= '{end_date}'")
    return query_dataset(
        DATASETS["rsv_coverage_adults_60plus"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="week_ending DESC",
        limit=limit,
    )


def get_adult_vaccination_coverage(
    vaccine: str | None = None,
    geography: str | None = None,
    year: str | None = None,
    dimension_type: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Annual vaccination coverage for adults 18+ from BRFSS by state/demographics (2008–present).
    vaccine: 'Pneumococcal', 'Zoster (Shingles)', 'Tetanus'
            (for flu use get_flu_coverage_all_ages; for COVID/RSV use get_resp_coverage_adults)
    geography: state name e.g. 'California'
    year: '2022', '2021' (through 2022 for most vaccines)
    dimension_type: 'Age', 'Race/Ethnicity', 'Insurance', 'Poverty', 'Overall'
    Key metric: coverage_estimate (%), _95_ci
    """
    clauses = []
    if vaccine:
        clauses.append(f"upper(vaccine) LIKE '%{vaccine.upper()}%'")
    if geography:
        clauses.append(f"geography = '{geography}'")
    if year:
        clauses.append(f"year_season = '{year}'")
    if dimension_type:
        clauses.append(f"upper(dimension_type) LIKE '%{dimension_type.upper()}%'")
    return query_dataset(
        DATASETS["adult_vaccination_coverage"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="year_season DESC",
        limit=limit,
    )


def get_pregnant_vaccination_coverage(
    vaccine: str | None = None,
    geography: str | None = None,
    season: str | None = None,
    dimension_type: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Annual flu and Tdap vaccination coverage among pregnant women by state (2012–present).
    vaccine: 'Influenza', 'Tdap'
    geography: state name e.g. 'California', or 'United States'
    season: '2022', '2021'
    dimension_type: 'Race and Ethnicity', 'Age', 'Insurance', 'Overall'
    Key metric: coverage_estimate (%), _95_ci
    """
    clauses = []
    if vaccine:
        clauses.append(f"vaccine = '{vaccine}'")
    if geography:
        clauses.append(f"geography = '{geography}'")
    if season:
        clauses.append(f"year_season = '{season}'")
    if dimension_type:
        clauses.append(f"dimension_type = '{dimension_type}'")
    return query_dataset(
        DATASETS["pregnant_vaccination_coverage"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="year_season DESC",
        limit=limit,
    )


def get_nursing_home_vaccination_coverage(
    vaccine: str | None = None,
    geography: str | None = None,
    season: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Annual flu and pneumococcal vaccination coverage among nursing home residents by state (2005–2021).
    vaccine: 'Seasonal Influenza', 'Pneumococcal'
    geography: state name, HHS region e.g. 'Region 1', or 'National'
    season: '2020-21', '2019-20'
    Key metric: coverage_estimate (%)
    """
    clauses = []
    if vaccine:
        clauses.append(f"vaccine = '{vaccine}'")
    if geography:
        clauses.append(f"geography = '{geography}'")
    if season:
        clauses.append(f"year_season = '{season}'")
    return query_dataset(
        DATASETS["nursing_home_vaccination_coverage"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="year_season DESC",
        limit=limit,
    )


def get_hcp_vaccination_coverage(
    geography: str | None = None,
    season: str | None = None,
    personnel_type: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Annual influenza vaccination coverage among health care personnel by state (2013–2021).
    geography: state name e.g. 'California', or 'National'
    season: '2020-21', '2019-20'
    personnel_type: partial match e.g. 'Nurse', 'Physician', 'Volunteer'
    Key metric: coverage_estimate (%), _95_ci
    """
    clauses = []
    if geography:
        clauses.append(f"geography = '{geography}'")
    if season:
        clauses.append(f"year_season = '{season}'")
    if personnel_type:
        clauses.append(f"upper(dimension) LIKE '%{personnel_type.upper()}%'")
    return query_dataset(
        DATASETS["hcp_vaccination_coverage"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="year_season DESC",
        limit=limit,
    )


def get_nssp_ed_visits(
    geography: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Weekly % of ED visits for COVID-19, influenza, and RSV by state/county from NSSP (2022–present).
    geography: state name e.g. 'California', or 'United States' for national
    start_date / end_date: 'YYYY-MM-DD'
    Key metrics: percent_visits_covid, percent_visits_influenza, percent_visits_rsv
    Trend fields: ed_trends_covid, ed_trends_influenza, ed_trends_rsv ('Increasing', 'Decreasing', 'Stable')
    """
    clauses = []
    if geography:
        clauses.append(f"geography = '{geography}'")
    if start_date:
        clauses.append(f"week_end >= '{start_date}'")
    if end_date:
        clauses.append(f"week_end <= '{end_date}'")
    return query_dataset(
        DATASETS["nssp_ed_visits"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="week_end DESC",
        limit=limit,
    )


def get_nrevss_rsv_historic(
    hhs_region: int | None = None,
    test_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Historical weekly RSV test counts and positivity from NREVSS labs by HHS region (2010–2020).
    For 2020–present RSV data, use get_rsv_positivity() instead.
    hhs_region: 1–10
    test_type: 'Antigen Detection' or 'PCR'
    start_date / end_date: 'YYYY-MM-DD'
    """
    clauses = []
    if hhs_region is not None:
        clauses.append(f"hhs_region = {hhs_region}")
    if test_type:
        clauses.append(f"diagnostic_test_type = '{test_type}'")
    if start_date:
        clauses.append(f"week_ending_date >= '{start_date}'")
    if end_date:
        clauses.append(f"week_ending_date <= '{end_date}'")
    return query_dataset(
        DATASETS["nrevss_rsv_historic"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="week_ending_date DESC",
        limit=limit,
    )


def get_children_vaccination(
    vaccine: str | None = None,
    geography: str | None = None,
    geography_type: str | None = None,
    birth_cohort: str | None = None,
    dimension_type: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Vaccination coverage for children 0–35 months from NIS-Child survey (2011–2022).
    vaccine: 'DTaP', 'MMR', 'Polio', 'Hib', 'PCV', 'Rotavirus', 'Hep A', 'Hep B', 'Varicella', 'Influenza'
    geography: state name or 'United States'
    geography_type: 'National', 'HHS Region', 'States', 'Local Area'
    birth_cohort: '2020', '2019-2020', etc.
    dimension_type: 'Overall', 'Race/Hispanic Origin', 'Insurance Coverage', 'Poverty Level', 'Urbanicity'
    """
    clauses = []
    if vaccine:
        clauses.append(f"upper(vaccine) LIKE '%{vaccine.upper()}%'")
    if geography:
        clauses.append(f"geography = '{geography}'")
    if geography_type:
        clauses.append(f"geography_type = '{geography_type}'")
    if birth_cohort:
        clauses.append(f"birth_year_birth_cohort = '{birth_cohort}'")
    if dimension_type:
        clauses.append(f"dimension_type = '{dimension_type}'")
    return query_dataset(
        DATASETS["children_vaccination"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="birth_year_birth_cohort DESC",
        limit=limit,
    )


def get_ari_activity_state(
    state: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Weekly ARI activity level by state (2024–present) — FluView ILI activity map equivalent.
    state: full state name e.g. 'California', or 'United States' for national
    label: 'Minimal', 'Low', 'Moderate', 'High', 'Very High'
    start_date / end_date: 'YYYY-MM-DD'
    """
    clauses = []
    if state:
        clauses.append(f"geography = '{state}'")
    if start_date:
        clauses.append(f"week_end >= '{start_date}'")
    if end_date:
        clauses.append(f"week_end <= '{end_date}'")
    return query_dataset(
        DATASETS["ari_activity_state"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="week_end DESC",
        limit=limit,
    )


def get_resp_ed_conditions(
    condition: str | None = None,
    age_group: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Weekly % of ED visits for respiratory conditions by age group from NSSP (2023–present).
    condition: 'Influenza', 'COVID-19', 'RSV', 'Pneumonia', 'Bronchiolitis',
               'Acute upper respiratory infection', 'Bronchitis', 'Sore throat (including strep throat)'
    age_group: 'Infants 0-1', 'Children 2-4', 'Children 5-17', 'Adults 18-64', 'Adults 65+', 'All ages'
    start_date / end_date: 'YYYY-MM-DD'
    """
    clauses = []
    if condition:
        clauses.append(f"upper(condition) LIKE '%{condition.upper()}%'")
    if age_group:
        clauses.append(f"age_group = '{age_group}'")
    if start_date:
        clauses.append(f"week_end >= '{start_date}'")
    if end_date:
        clauses.append(f"week_end <= '{end_date}'")
    return query_dataset(
        DATASETS["resp_ed_conditions"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="week_end DESC",
        limit=limit,
    )


def get_resp_lens(
    virus: str | None = None,
    region: str | None = None,
    season: str | None = None,
    age_group: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """RESP-LENS weekly % positivity for 9 respiratory viruses from ED labs, by HHS region/age (2021–2024).
    virus: 'Influenza A', 'Influenza B', 'RSV', 'SARS-CoV-2', 'Rhinovirus/Enterovirus',
           'Adenovirus', 'Human Metapneumovirus', 'Parainfluenza'
    region: 'Region 1' through 'Region 10', or 'National'
    season: '2021-22', '2022-23', '2023-24'
    age_group: '0-4 years', '5-17 years', '18-49 years', '50-64 years', '65+ years', 'All ages'
    """
    clauses = []
    if virus:
        clauses.append(f"upper(virus) LIKE '%{virus.upper()}%'")
    if region:
        clauses.append(f"region = '{region}'")
    if season:
        clauses.append(f"season = '{season}'")
    if age_group:
        clauses.append(f"age_gp = '{age_group}'")
    return query_dataset(
        DATASETS["resp_lens"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="week DESC",
        limit=limit,
    )


def get_epidemic_trends_rt(
    disease: str | None = None,
    state: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Weekly estimated Rt and epidemic trend category for COVID-19 and influenza by state (2020–present).
    disease: 'COVID-19', 'Influenza'
    state: full state name e.g. 'California', or 'United States'
    start_date / end_date: 'YYYY-MM-DD' (filters on `date` field)
    Key metrics: median/lower/upper (Rt estimate + CI), p_growing (probability of growth),
                 category ('Growing', 'Likely Growing', 'Stable', 'Likely Declining', 'Declining')
    """
    clauses = []
    if disease:
        clauses.append(f"disease = '{disease}'")
    if state:
        clauses.append(f"state = '{state}'")
    if start_date:
        clauses.append(f"date >= '{start_date}'")
    if end_date:
        clauses.append(f"date <= '{end_date}'")
    return query_dataset(
        DATASETS["epidemic_trends_rt"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="date DESC",
        limit=limit,
    )


def get_nvsn_pathogen_positivity(
    pathogen: str | None = None,
    age_group: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Weekly % positivity for 9 viral pathogens in children with ARI from NVSN (2017–present).
    pathogen: 'Influenza A', 'Influenza B', 'RSV', 'SARS-CoV-2', 'Rhinovirus/Enterovirus',
              'Adenovirus', 'Human Metapneumovirus', 'Parainfluenza'
    age_group: '--- 0-2 months', '--- 2-6 months', '--- 6-24 months', '--- 2-4 years', '--- 5-17 years'
    start_date / end_date: 'YYYY-MM-DD'
    """
    clauses = []
    if pathogen:
        clauses.append(f"upper(pathogen) LIKE '%{pathogen.upper()}%'")
    if age_group:
        clauses.append(f"age_group = '{age_group}'")
    if start_date:
        clauses.append(f"mmwr_week_end >= '{start_date}'")
    if end_date:
        clauses.append(f"mmwr_week_end <= '{end_date}'")
    return query_dataset(
        DATASETS["nvsn_pathogen_positivity"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="mmwr_week_end DESC",
        limit=limit,
    )


def get_cumulative_rsv_hosp(
    season: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Preliminary weekly estimates of cumulative US RSV hospitalizations (2024–present).
    season: '2024-2025'
    Key columns: date, burden (always 'Hospitalizations'), low/high (95% CI)
    """
    clauses = []
    if season:
        clauses.append(f"season = '{season}'")
    return query_dataset(
        DATASETS["cumulative_rsv_hosp"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="date DESC",
        limit=limit,
    )


def get_cumulative_covid_hosp(
    season: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Preliminary weekly estimates of cumulative US COVID-19 hospitalizations (2024–present).
    season: '2024-2025'
    Key columns: date, burden (always 'Hospitalizations'), low/high (95% CI)
    """
    clauses = []
    if season:
        clauses.append(f"season = '{season}'")
    return query_dataset(
        DATASETS["cumulative_covid_hosp"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="date DESC",
        limit=limit,
    )


def get_covid_hosp_archived(
    state: str | None = "USA",
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Archived weekly COVID-19 hospital admissions and bed utilization (2020–May 2024).
    state: two-letter code e.g. 'CA', 'TX', or 'USA' for national aggregate
    start_date / end_date: 'YYYY-MM-DD'
    Key metrics: total_adm_all_covid_confirmed (weekly admissions), avg_percent_inpatient_beds
    """
    clauses = []
    if state:
        clauses.append(f"state = '{state.upper()}'")
    if start_date:
        clauses.append(f"week_ending_date >= '{start_date}'")
    if end_date:
        clauses.append(f"week_ending_date <= '{end_date}'")
    return query_dataset(
        DATASETS["covid_hosp_archived"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="week_ending_date ASC",
        limit=limit,
    )


def get_nhsn_hrd(
    jurisdiction: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Weekly hospital COVID-19, flu, and RSV admissions and inpatient counts from NHSN (2020–present).
    jurisdiction: two-letter state code e.g. 'CA', 'TX', or 'USA' for national
    start_date / end_date: 'YYYY-MM-DD'
    Key metrics: totalconfc19newadm, totalconfflunewadm, totalconfrsvnewadm (weekly new admissions)
                 totalconfc19hosppats, totalconffluhosppats, totalconfrsvhosppats (current inpatients)
    """
    clauses = []
    if jurisdiction:
        clauses.append(f"jurisdiction = '{jurisdiction.upper()}'")
    if start_date:
        clauses.append(f"weekendingdate >= '{start_date}'")
    if end_date:
        clauses.append(f"weekendingdate <= '{end_date}'")
    return query_dataset(
        DATASETS["nhsn_hrd"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="weekendingdate DESC",
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


def get_sti_chlamydia(
    state: str | None = None,
    year: int | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Weekly provisional chlamydia case counts by state from NNDSS (2014–present).
    state: uppercase state name e.g. 'CALIFORNIA', 'NEW YORK' (reporting_area column is all-caps)
    year: MMWR year e.g. 2024
    Key columns: chlamydia_trachomatis_4 (cum year), chlamydia_trachomatis_2 (prev 52-week max)
    """
    clauses = []
    if state:
        clauses.append(f"reporting_area = '{state.upper()}'")
    if year:
        clauses.append(f"mmwr_year = '{year}'")
    return query_dataset(
        DATASETS["nndss_sti_chlamydia"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="mmwr_year DESC, mmwr_week DESC",
        limit=limit,
    )


def get_sti_gonorrhea(
    state: str | None = None,
    year: int | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Weekly provisional gonorrhea case counts by state from NNDSS (2014–present).
    state: uppercase state name e.g. 'CALIFORNIA', 'NEW YORK' (reporting_area column is all-caps)
    year: MMWR year e.g. 2024
    Key columns: gonorrhea_current_week, gonorrhea_previous_52_weeks_max
    """
    clauses = []
    if state:
        clauses.append(f"reporting_area = '{state.upper()}'")
    if year:
        clauses.append(f"mmwr_year = '{year}'")
    return query_dataset(
        DATASETS["nndss_sti_gonorrhea"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="mmwr_year DESC, mmwr_week DESC",
        limit=limit,
    )


def get_sti_syphilis(
    state: str | None = None,
    year: int | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Weekly provisional syphilis case counts by state from NNDSS (2014–present).
    state: uppercase state name e.g. 'CALIFORNIA', 'NEW YORK' (reporting_area column is all-caps)
    year: MMWR year e.g. 2024
    Key columns: syphilis_primary_and_secondary (current week + variants), syphilis_congenital_current_1
    """
    clauses = []
    if state:
        clauses.append(f"reporting_area = '{state.upper()}'")
    if year:
        clauses.append(f"mmwr_year = '{year}'")
    return query_dataset(
        DATASETS["nndss_sti_syphilis"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="mmwr_year DESC, mmwr_week DESC",
        limit=limit,
    )


def get_chronic_disease_indicators(
    topic: str | None = None,
    state: str | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    question_id: str | None = None,
    stratification: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """U.S. Chronic Disease Indicators: state-level measures across 19 disease topics (2001–present).
    topic: 'Alcohol', 'Arthritis', 'Asthma', 'Cancer', 'Cardiovascular Disease',
           'Chronic Kidney Disease', 'COPD', 'Diabetes', 'Mental Health', 'Tobacco',
           'Nutrition, Physical Activity, and Weight Status', 'Maternal Health', 'Sleep'
    state: two-letter code e.g. 'CA', 'NY'
    year_start / year_end: filter by yearstart / yearend
    question_id: specific CDI question code e.g. 'AST01', 'DIA01'
    stratification: demographic group e.g. 'Overall', 'Male', 'Female', 'Hispanic'
    Key columns: datavalue (estimate), datavalueunit (%, per 100k, etc.), question, datasource
    """
    clauses = []
    if topic:
        clauses.append(f"upper(topic) LIKE '%{topic.upper()}%'")
    if state:
        clauses.append(f"locationabbr = '{state.upper()}'")
    if year_start:
        clauses.append(f"yearstart >= '{year_start}'")
    if year_end:
        clauses.append(f"yearend <= '{year_end}'")
    if question_id:
        clauses.append(f"questionid = '{question_id.upper()}'")
    if stratification:
        clauses.append(f"upper(stratification1) LIKE '%{stratification.upper()}%'")
    return query_dataset(
        DATASETS["chronic_disease_indicators"].id,
        where=" AND ".join(clauses) if clauses else None,
        select=(
            "yearstart, yearend, locationabbr, locationdesc, topic, question, "
            "datavalue, datavalueunit, datavaluetype, stratificationcategory1, "
            "stratification1, datasource, questionid, topicid"
        ),
        order="yearend DESC",
        limit=limit,
    )


def get_monthly_deaths_by_cause(
    jurisdiction: str | None = None,
    year: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Monthly provisional US death counts for 20+ causes including cancer, heart disease, drug overdose (2020–present).
    jurisdiction: 'United States' for national, or full state name e.g. 'California'
    year: 2020–present
    start_date / end_date: 'YYYY-MM-DD'
    Key columns: malignant_neoplasms (cancer), diseases_of_heart, drug_overdose,
                 intentional_self_harm_suicide, alzheimer_disease, covid_19_underlying_cause
    """
    clauses = []
    if jurisdiction:
        clauses.append(f"jurisdiction_of_occurrence = '{jurisdiction}'")
    if year:
        clauses.append(f"year = '{year}'")
    if start_date:
        clauses.append(f"start_date >= '{start_date}'")
    if end_date:
        clauses.append(f"end_date <= '{end_date}'")
    return query_dataset(
        DATASETS["monthly_deaths_by_cause"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="year DESC, month DESC",
        limit=limit,
    )


def get_hai_mrsa(
    topic: str | None = None,
    viewby: str | None = None,
    year: int | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Annual invasive Staphylococcus aureus (MRSA/MSSA) case rates from CDC EIP (2005–present).
    topic: 'Case rates', 'Incidence trends', 'Proportion MRSA'
    viewby: 'Age', 'Sex', 'Race', 'Dialysis', 'Exposure'
    year: e.g. 2022
    Key column: value (rate or proportion)
    """
    clauses = []
    if topic:
        clauses.append(f"upper(topic) LIKE '%{topic.upper()}%'")
    if viewby:
        clauses.append(f"upper(viewby) LIKE '%{viewby.upper()}%'")
    if year:
        clauses.append(f"yearname = '{year}'")
    return query_dataset(
        DATASETS["hai_mrsa"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="yearname DESC",
        limit=limit,
    )


def get_hai_amr(
    organism: str | None = None,
    topic: str | None = None,
    viewby: str | None = None,
    year: int | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Annual antimicrobial resistance case rates for CRAB, CRE, ESBL from CDC MuGSI (2012–present).
    organism: 'CRAB' (carbapenem-resistant Acinetobacter), 'CRE' (carbapenem-resistant Enterobacterales),
              'ESBL' (extended-spectrum beta-lactamase producers)
    topic: 'Case Rates', 'Proportion resistant'
    viewby: 'Age', 'Exposure'
    year: e.g. 2022
    Key column: value (rate per 100,000)
    """
    clauses = []
    if organism:
        clauses.append(f"upper(organism) LIKE '%{organism.upper()}%'")
    if topic:
        clauses.append(f"upper(topic) LIKE '%{topic.upper()}%'")
    if viewby:
        clauses.append(f"upper(viewby) LIKE '%{viewby.upper()}%'")
    if year:
        clauses.append(f"yearname = '{year}'")
    return query_dataset(
        DATASETS["hai_amr"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="yearname DESC",
        limit=limit,
    )


def get_hai_cdiff(
    viewby: str | None = None,
    grouping: str | None = None,
    year: int | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Annual Clostridioides difficile (C. diff) infection case rates from CDC EIP (2011–present).
    viewby: 'Age', 'Sex', 'Race'
    grouping: 'All cases', 'Community-associated', 'Healthcare-associated', 'Recurrent'
    year: e.g. 2022
    Key column: value (cases per 100,000)
    """
    clauses = []
    if viewby:
        clauses.append(f"upper(viewby) LIKE '%{viewby.upper()}%'")
    if grouping:
        clauses.append(f"upper(grouping) LIKE '%{grouping.upper()}%'")
    if year:
        clauses.append(f"yearname = '{year}'")
    return query_dataset(
        DATASETS["hai_cdiff"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="yearname DESC",
        limit=limit,
    )


def get_hai_candidemia(
    viewby: str | None = None,
    topic: str | None = None,
    year: int | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Annual Candida bloodstream infection drug resistance rates from CDC surveillance (2009–present).
    viewby: Candida species e.g. 'Candida albicans', 'Candida glabrata', 'Candida auris'
    topic: 'Drug resistance', 'Incidence'
    year: e.g. 2022
    Key column: value (resistance proportion or rate)
    """
    clauses = []
    if viewby:
        clauses.append(f"upper(viewby) LIKE '%{viewby.upper()}%'")
    if topic:
        clauses.append(f"upper(topic) LIKE '%{topic.upper()}%'")
    if year:
        clauses.append(f"yearname = '{year}'")
    return query_dataset(
        DATASETS["hai_candidemia"].id,
        where=" AND ".join(clauses) if clauses else None,
        order="yearname DESC",
        limit=limit,
    )


def clear_cache() -> None:
    _get_client().clear_cache()
