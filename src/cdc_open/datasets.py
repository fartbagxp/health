"""
CDC Open Data dataset registry.

Each entry describes a data.cdc.gov Socrata dataset including its ID,
human-readable name, date coverage, and key queryable columns.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Dataset:
    id: str
    name: str
    description: str
    years: str
    key_columns: list[str] = field(default_factory=list)


DATASETS: dict[str, Dataset] = {
    "leading_death": Dataset(
        id="bi63-dtpu",
        name="Leading Causes of Death",
        description="U.S. leading causes of death by state and year",
        years="1999–2017",
        key_columns=[
            "year",
            "cause_name",
            "state",
            "deaths",
            "age_adjusted_death_rate",
        ],
    ),
    "life_expectancy": Dataset(
        id="w9j2-ggv5",
        name="Life Expectancy",
        description="Life expectancy at birth by race (All Races, Black, White) and sex",
        years="1900–2018",
        key_columns=[
            "year",
            "race",
            "sex",
            "average_life_expectancy",
            "age_adjusted_death_rate",
        ],
    ),
    "mortality_rates": Dataset(
        id="489q-934x",
        name="Provisional Mortality Rates",
        description="Quarterly age-adjusted death rates by cause, sex, and state",
        years="2020–present",
        key_columns=[
            "year_and_quarter",
            "cause_of_death",
            "rate_type",
            "time_period",
            "rate_overall",
        ],
    ),
    "places_county": Dataset(
        id="swc5-untb",
        name="PLACES: County Health",
        description="County-level health indicators: obesity, diabetes, smoking, depression, sleep, etc. (BRFSS-based)",
        years="Current",
        key_columns=[
            "stateabbr",
            "statedesc",
            "locationname",
            "measureid",
            "short_question_text",
            "data_value",
            "totalpopulation",
        ],
    ),
    "places_city": Dataset(
        id="dxpw-cm5u",
        name="PLACES: City Health",
        description="City-level health indicators: obesity, diabetes, smoking, depression, and 30+ more (BRFSS-based)",
        years="Current",
        key_columns=[
            "stateabbr",
            "placename",
            "obesity_crudeprev",
            "diabetes_crudeprev",
            "csmoking_crudeprev",
            "depression_crudeprev",
        ],
    ),
    "covid_cases": Dataset(
        id="pwn4-m3yp",
        name="COVID-19 Cases & Deaths",
        description="COVID-19 weekly cases and deaths by state",
        years="2020–2023",
        key_columns=[
            "state",
            "date_updated",
            "new_cases",
            "new_deaths",
            "tot_cases",
            "tot_death",
        ],
    ),
    "covid_conditions": Dataset(
        id="hk9y-quqm",
        name="COVID-19 Contributing Conditions",
        description="COVID-19 deaths by contributing condition, age group, and state",
        years="2020–2023",
        key_columns=[
            "state",
            "condition_group",
            "condition",
            "age_group",
            "covid_19_deaths",
        ],
    ),
    "weekly_deaths": Dataset(
        id="r8kw-7aab",
        name="Weekly Death Surveillance",
        description="Provisional weekly death counts by state: COVID-19, pneumonia, influenza, total deaths (updated weekly)",
        years="2020–present",
        key_columns=[
            "state",
            "end_date",
            "year",
            "week",
            "covid_19_deaths",
            "pneumonia_deaths",
            "influenza_deaths",
            "total_deaths",
            "percent_of_expected_deaths",
        ],
    ),
    "disability": Dataset(
        id="s2qv-b27b",
        name="Disability Prevalence",
        description="Disability status and types by state: mobility, cognitive, hearing, vision, self-care (BRFSS)",
        years="Current",
        key_columns=[
            "locationabbr",
            "locationdesc",
            "response",
            "data_value",
            "data_value_type",
            "year",
        ],
    ),
    "weekly_deaths_by_cause": Dataset(
        id="muzy-jte6",
        name="Weekly Deaths by Cause",
        description="Weekly deaths by state and cause: heart disease, cancer, diabetes, stroke, COVID, respiratory",
        years="2020–2023",
        key_columns=[
            "jurisdiction_of_occurrence",
            "mmwr_year",
            "mmwr_week",
            "all_cause",
            "heart_disease",
            "malignant_neoplasms",
            "covid_19_u071_underlying_cause_of_death",
        ],
    ),
    "drug_overdose_state": Dataset(
        id="xbxb-epbu",
        name="Drug Poisoning Mortality by State",
        description="Drug poisoning/overdose death rates by state, sex, race, and age",
        years="1999–2016",
        key_columns=[
            "year",
            "state",
            "sex",
            "race",
            "age",
            "death_rate",
            "lower_confidence_limit",
            "upper_confidence_limit",
        ],
    ),
    "nutrition_obesity": Dataset(
        id="hn4x-zwk7",
        name="Nutrition, Physical Activity & Obesity",
        description="Adult obesity, physical inactivity, and fruit/vegetable consumption by state from BRFSS",
        years="Current",
        key_columns=[
            "yearstart",
            "yearend",
            "locationabbr",
            "locationdesc",
            "class",
            "topic",
            "question",
            "data_value",
            "data_value_unit",
            "stratification1",
        ],
    ),
    "death_rates_historical": Dataset(
        id="6rkc-nb2q",
        name="Historical Death Rates by Cause",
        description="Age-adjusted death rates for major causes (heart disease, cancer, stroke, etc.) since 1900",
        years="1900–2017",
        key_columns=["year", "leading_causes", "deaths", "age_adjusted_death_rate"],
    ),
    "birth_indicators": Dataset(
        id="76vv-a7x8",
        name="Quarterly Birth Indicators",
        description="Provisional quarterly birth rates, teen births, preterm births, cesarean rates by race/ethnicity",
        years="Current",
        key_columns=[
            "year_and_quarter",
            "topic_subgroup",
            "race_ethnicity",
            "indicator",
            "period",
            "value",
        ],
    ),
}
