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
    # ── Respiratory surveillance ──────────────────────────────────────────────
    {
        "name": "get_resp_net_hospitalizations",
        "description": (
            "Get weekly lab-confirmed hospitalization rates for RSV, COVID-19, and Influenza from RESP-NET (2017–present). "
            "Population-based surveillance across US sites. Rates per 100,000 population by age, sex, race/ethnicity. "
            "network: 'FluSurv-NET', 'COVID-NET', 'RSV-NET'. Omit to get all three in one call."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "network": {
                    "type": "string",
                    "enum": ["FluSurv-NET", "COVID-NET", "RSV-NET"],
                    "description": "Surveillance network. Omit for all three.",
                },
                "season": {
                    "type": "string",
                    "description": "Flu season: '2024-25', '2023-24'. Omit for all seasons.",
                },
                "age_group": {
                    "type": "string",
                    "description": "'Overall', '0-4 years', '5-17 years', '18-49 years', '50-64 years', '65+ years'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 500).",
                },
            },
        },
    },
    {
        "name": "get_rsv_hospitalizations",
        "description": (
            "Get weekly RSV hospitalization rates from RSV-NET surveillance (2018–present). "
            "Population-based, covers children and adults. By state/age/sex/race."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "season": {"type": "string", "description": "'2024-25', '2023-24'."},
                "age_category": {
                    "type": "string",
                    "description": "'Overall', '0-5 months', '6-11 months', '1-4 years', '5-17 years', '18-49 years', '65-74 years', '75+ years'.",
                },
                "state": {
                    "type": "string",
                    "description": "Surveillance site state name e.g. 'California'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 500).",
                },
            },
        },
    },
    {
        "name": "get_covid_net_hospitalizations",
        "description": (
            "Get weekly COVID-19 hospitalization rates from COVID-NET surveillance (2020–present). "
            "Population-based, covers all ages. By state/age/sex/race."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "season": {"type": "string", "description": "'2024-25', '2023-24'."},
                "age_category": {
                    "type": "string",
                    "description": "'Overall', '0-4 years', '5-17 years', '18-49 years', '50-64 years', '65-74 years', '75+ years'.",
                },
                "state": {
                    "type": "string",
                    "description": "Surveillance site state name e.g. 'New York'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 500).",
                },
            },
        },
    },
    {
        "name": "get_resp_deaths_pct",
        "description": (
            "Get provisional weekly percentage of total US deaths from COVID-19, Influenza, and RSV (2020–present). "
            "Simple national-level time series — good for tracking respiratory burden over time."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pathogen": {
                    "type": "string",
                    "enum": ["COVID-19", "Influenza", "RSV"],
                    "description": "Pathogen to filter. Omit for all three.",
                },
                "start_date": {"type": "string", "description": "'YYYY-MM-DD'."},
                "end_date": {"type": "string", "description": "'YYYY-MM-DD'."},
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 500).",
                },
            },
        },
    },
    {
        "name": "get_resp_deaths_pct_demo",
        "description": (
            "Get provisional weekly % deaths for COVID-19/Flu/RSV stratified by age, sex, race/ethnicity, and state (2020–present). "
            "Use this to compare demographic disparities in respiratory mortality."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pathogen": {
                    "type": "string",
                    "enum": ["COVID-19", "Flu", "RSV", "Combined"],
                    "description": "Pathogen. Omit for all.",
                },
                "demographic_type": {
                    "type": "string",
                    "enum": ["Age", "Sex", "Race/Ethnicity"],
                    "description": "Stratification variable.",
                },
                "state": {
                    "type": "string",
                    "description": "Full state name or 'United States'. Omit for all.",
                },
                "start_date": {"type": "string", "description": "'YYYY-MM-DD'."},
                "end_date": {"type": "string", "description": "'YYYY-MM-DD'."},
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 500).",
                },
            },
        },
    },
    {
        "name": "get_rsv_positivity",
        "description": (
            "Get weekly RSV NAAT test positivity rates from NREVSS participating labs (2020–present). "
            "Key metric: pcr_percent_positive (3-week centered moving average). "
            "Covers national level and 10 HHS regions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "description": "'National', 'HHS Region 1' through 'HHS Region 10'. Omit for all.",
                },
                "start_date": {"type": "string", "description": "'YYYY-MM-DD'."},
                "end_date": {"type": "string", "description": "'YYYY-MM-DD'."},
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 500).",
                },
            },
        },
    },
    {
        "name": "get_nursing_home_resp",
        "description": (
            "Get weekly COVID-19, Influenza, and RSV case counts, hospitalizations, and vaccination rates "
            "for nursing home residents by state from NHSN (September 2024–present). "
            "Useful for tracking vulnerable-population outcomes and vaccine effectiveness."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "jurisdiction": {
                    "type": "string",
                    "description": "Full state name e.g. 'California', or 'National'. Omit for all.",
                },
                "start_date": {"type": "string", "description": "'YYYY-MM-DD'."},
                "end_date": {"type": "string", "description": "'YYYY-MM-DD'."},
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 500).",
                },
            },
        },
    },
    # ── Vaccination ───────────────────────────────────────────────────────────
    {
        "name": "get_resp_vaccination",
        "description": (
            "Get weekly flu, COVID-19, and RSV vaccination coverage from National Immunization Survey (2023–present). "
            "By state, HHS region, age group, sex, race/ethnicity. "
            "Use to track uptake trends and compare demographics."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "vaccine": {
                    "type": "string",
                    "enum": ["Influenza", "COVID-19", "RSV"],
                    "description": "Vaccine type. Omit for all.",
                },
                "geographic_level": {
                    "type": "string",
                    "enum": ["National", "State", "Region"],
                    "description": "Geographic aggregation.",
                },
                "geographic_name": {
                    "type": "string",
                    "description": "State name 'California', region 'HHS Region 1', or 'United States'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 500).",
                },
            },
        },
    },
    {
        "name": "get_flu_vaccine_doses",
        "description": (
            "Get weekly cumulative influenza vaccine doses distributed nationally by flu season (2009–present). "
            "Tracks vaccine supply rollout week by week."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "season": {
                    "type": "string",
                    "description": "Flu season: '2024-2025', '2023-2024'. Omit for all seasons.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 200).",
                },
            },
        },
    },
    # ── Drug overdose ─────────────────────────────────────────────────────────
    {
        "name": "get_drug_overdose_counts",
        "description": (
            "Get monthly provisional drug overdose death counts by state and drug type (2015–present). "
            "MOST CURRENT overdose data — updated monthly via VSRR. "
            "Indicators: 'Drug Overdose Deaths', 'All Opioids', 'Natural & Semi-Synthetic Opioids', "
            "'Methadone', 'Synthetic Opioids' (fentanyl), 'Heroin', 'Cocaine', 'Psychostimulants' (meth). "
            "Includes 12-month rolling totals and predicted values for reporting lag."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "Two-letter state code: 'OH', 'WV', 'KY'. Omit for all states.",
                },
                "year": {
                    "type": "integer",
                    "description": "Year e.g. 2023. Omit for all.",
                },
                "indicator": {
                    "type": "string",
                    "description": "'Drug Overdose Deaths', 'All Opioids', 'Synthetic Opioids', 'Heroin', 'Cocaine', 'Psychostimulants'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 500).",
                },
            },
        },
    },
    {
        "name": "get_drug_overdose_county",
        "description": (
            "Get quarterly provisional county-level drug overdose death counts (2020–present). "
            "12-month rolling totals by county FIPS. "
            "Use for geographic hotspot analysis."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "Two-letter state code: 'OH', 'WV'. Omit for all states.",
                },
                "year": {
                    "type": "string",
                    "description": "Year e.g. '2023'. Omit for all.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 500).",
                },
            },
        },
    },
    # ── Notifiable diseases ───────────────────────────────────────────────────
    {
        "name": "get_nndss_weekly",
        "description": (
            "Get NNDSS provisional weekly case counts for ~100 nationally notifiable diseases (2014–present). "
            "Diseases include: Measles, Mumps, Pertussis (whooping cough), Hepatitis A/B/C, "
            "Lyme Disease, Tuberculosis, Salmonellosis, Gonorrhea, Syphilis, Dengue, West Nile, Mpox. "
            "m1 = cases for current week; m2 = cases for same week prior year. "
            "m1_flag/m2_flag: 'U'=unavailable, 'N'=not reportable, '-'=no cases."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "disease": {
                    "type": "string",
                    "description": "Disease label (partial match): 'Measles', 'Pertussis', 'Hepatitis A', 'Lyme Disease', 'Tuberculosis', 'Salmonellosis', 'Gonorrhea', 'Mpox'.",
                },
                "state": {
                    "type": "string",
                    "description": "Full state name: 'New York', 'California'. Omit for all.",
                },
                "year": {
                    "type": "string",
                    "description": "Year: '2024'. Omit for all.",
                },
                "week": {"type": "integer", "description": "MMWR week 1–53."},
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 500).",
                },
            },
        },
    },
    {
        "name": "get_wastewater_data",
        "description": (
            "Get NWSS wastewater surveillance data: RNA concentrations from US sampling sites, updated weekly. "
            "Tracks SARS-CoV-2 (COVID-19), Influenza A, and Measles viral signal in sewage as early-warning. "
            "Pathogens: 'sars_cov2' (2020–present), 'flu_a' (2022–present), 'measles' (2024–present). "
            "Key metric: pcr_target_flowpop_lin — flow-population-normalized concentration, comparable across sites. "
            "pcr_target_detect: 'yes' or 'no' — whether pathogen was detected at that site."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pathogen": {
                    "type": "string",
                    "enum": ["sars_cov2", "flu_a", "measles"],
                    "description": "'sars_cov2' (COVID-19, 2020+), 'flu_a' (Influenza A, 2022+), 'measles' (2024+).",
                },
                "state": {
                    "type": "string",
                    "description": "Two-letter state code: 'NY', 'CA', 'TX'. Omit for all states.",
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date inclusive: 'YYYY-MM-DD'.",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date inclusive: 'YYYY-MM-DD'.",
                },
                "detected_only": {
                    "type": "boolean",
                    "description": "If true, only return samples where pathogen was detected (pcr_target_detect='yes').",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 500).",
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
            "hk9y-quqm (COVID conditions), muzy-jte6 (weekly deaths by cause), "
            "j9g8-acpt (wastewater SARS-CoV-2), ymmh-divb (wastewater Influenza A), "
            "akvg-8vrb (wastewater Measles)."
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
    "get_wastewater_data": sdk.get_wastewater_data,
    "get_resp_net_hospitalizations": sdk.get_resp_net_hospitalizations,
    "get_rsv_hospitalizations": sdk.get_rsv_hospitalizations,
    "get_covid_net_hospitalizations": sdk.get_covid_net_hospitalizations,
    "get_resp_deaths_pct": sdk.get_resp_deaths_pct,
    "get_resp_deaths_pct_demo": sdk.get_resp_deaths_pct_demo,
    "get_rsv_positivity": sdk.get_rsv_positivity,
    "get_nursing_home_resp": sdk.get_nursing_home_resp,
    "get_resp_vaccination": sdk.get_resp_vaccination,
    "get_flu_vaccine_doses": sdk.get_flu_vaccine_doses,
    "get_drug_overdose_counts": sdk.get_drug_overdose_counts,
    "get_drug_overdose_county": sdk.get_drug_overdose_county,
    "get_nndss_weekly": sdk.get_nndss_weekly,
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
