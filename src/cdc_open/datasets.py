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
    soql_where: str | None = None


@dataclass(frozen=True)
class WcmsDataset:
    """A CDC WCMS visualization JSON endpoint that backs a chart on a CDC page."""

    url: str
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
    "wastewater_covid": Dataset(
        id="j9g8-acpt",
        name="NWSS Wastewater: SARS-CoV-2",
        description="SARS-CoV-2 RNA concentrations from US wastewater sampling sites via NWSS, updated weekly",
        years="2020–present",
        key_columns=[
            "state_territory",
            "sample_collect_date",
            "counties_served",
            "population_served",
            "pcr_target_detect",
            "pcr_target_avg_conc",
            "pcr_target_flowpop_lin",
            "date_updated",
        ],
    ),
    "wastewater_flu": Dataset(
        id="ymmh-divb",
        name="NWSS Wastewater: Influenza A",
        description="Influenza A RNA concentrations from US wastewater sampling sites via NWSS, updated weekly",
        years="2022–present",
        key_columns=[
            "state_territory",
            "sample_collect_date",
            "counties_served",
            "population_served",
            "pcr_target_detect",
            "pcr_target_avg_conc",
            "pcr_target_flowpop_lin",
            "date_updated",
        ],
    ),
    "wastewater_measles": Dataset(
        id="akvg-8vrb",
        name="NWSS Wastewater: Measles",
        description="Measles RNA concentrations from US wastewater sampling sites via NWSS, updated weekly",
        years="2024–present",
        key_columns=[
            "state_territory",
            "sample_collect_date",
            "counties_served",
            "population_served",
            "pcr_target_detect",
            "pcr_target_avg_conc",
            "pcr_target_flowpop_lin",
            "date_updated",
        ],
    ),
    # ── Wastewater: scored activity levels & avian flu ───────────────────────
    "wastewater_activity": Dataset(
        id="atcp-73re",
        name="CDC Wastewater Viral Activity Level (SARS-CoV-2, Flu A, RSV)",
        description="Weekly wastewater viral activity level (WVAL) scores and categories (Very Low/Low/Moderate/High/Very High) per sampling site for SARS-CoV-2, Influenza A, and RSV",
        years="2023–present",
        key_columns=[
            "state_territory",
            "site",
            "pathogen_target",
            "site_wval",
            "site_wval_category",
            "week_end",
            "population_served",
        ],
    ),
    "wastewater_rsv": Dataset(
        id="45cq-cw4i",
        name="NWSS Wastewater: RSV",
        description="RSV RNA concentrations from US wastewater sampling sites via NWSS, updated weekly",
        years="2023–present",
        key_columns=[
            "state_territory",
            "sample_collect_date",
            "counties_served",
            "population_served",
            "pcr_target_detect",
            "pcr_target_avg_conc",
            "pcr_target_flowpop_lin",
            "date_updated",
        ],
    ),
    "wastewater_h5": Dataset(
        id="mtpu-urpp",
        name="CDC Wastewater Data for Avian Influenza A (H5)",
        description="Raw wastewater sample measurements for Avian Influenza A (H5) at US sampling sites — concentration, flow-normalized values, and detection flags",
        years="2024–present",
        key_columns=[
            "state_territory",
            "site",
            "sample_collect_date",
            "pcr_target",
            "pcr_target_detect",
            "pcr_target_avg_conc",
            "pcr_target_flowpop_lin",
            "counties_served",
            "population_served",
        ],
    ),
    # ── Respiratory surveillance (weekly) ────────────────────────────────────
    "resp_net": Dataset(
        id="kvib-3txy",
        name="RESP-NET: RSV, COVID-19 & Flu Hospitalizations",
        description="Weekly lab-confirmed hospitalization rates for RSV, COVID-19, and Influenza from RESP-NET population-based surveillance, by age/sex/race",
        years="2017–present",
        key_columns=[
            "surveillance_network",
            "season",
            "week_ending_date",
            "age_group",
            "sex",
            "race_ethnicity",
            "site",
            "weekly_rate",
            "cumulative_rate",
            "rate_type",
        ],
    ),
    "rsv_net": Dataset(
        id="29hc-w46k",
        name="RSV-NET: RSV Hospitalizations",
        description="Weekly lab-confirmed RSV hospitalization rates in children and adults from RSV-NET surveillance, by state/age/sex/race",
        years="2018–present",
        key_columns=[
            "state",
            "season",
            "week_ending_date",
            "age_category",
            "sex",
            "race",
            "rate",
            "cumulative_rate",
            "type",
        ],
    ),
    "covid_net": Dataset(
        id="6jg4-xsqq",
        name="COVID-NET: COVID-19 Hospitalizations",
        description="Weekly lab-confirmed COVID-19 hospitalization rates from COVID-NET surveillance, by state/age/sex/race",
        years="2020–present",
        key_columns=[
            "state",
            "season",
            "week_ending_date",
            "agecat_label",
            "sex_label",
            "race_label",
            "rate_type",
            "weekly_rate",
            "cumulative_rate",
        ],
    ),
    "resp_deaths_pct": Dataset(
        id="4bc2-bbpq",
        name="Provisional % Deaths: COVID-19, Flu & RSV",
        description="Provisional weekly percentage of total US deaths attributed to COVID-19, Influenza, and RSV",
        years="2020–present",
        key_columns=["week_end", "pathogen", "percent_deaths"],
    ),
    "resp_deaths_pct_demo": Dataset(
        id="53g5-jf7x",
        name="Provisional % Deaths: COVID-19, Flu & RSV by Demographics",
        description="Provisional weekly percentage of deaths for COVID-19, Influenza, and RSV stratified by age, sex, race/ethnicity, and state",
        years="2020–present",
        key_columns=[
            "weekending_date",
            "state",
            "demographic_type",
            "demographic_values",
            "pathogen",
            "deaths",
            "total_deaths",
            "percent_deaths",
        ],
    ),
    "rsv_positivity": Dataset(
        id="3cxc-4k8q",
        name="RSV Test Positivity (NREVSS)",
        description="Weekly RSV NAAT test positivity rates and detection counts by national and HHS region, from NREVSS participating labs",
        years="2020–present",
        key_columns=[
            "mmwrweek_end",
            "level",
            "pcr_percent_positive",
            "pcr_detections",
            "pcr_tests",
            "posted",
        ],
    ),
    "nursing_home_resp": Dataset(
        id="tscn-ryh9",
        name="Nursing Home Respiratory Pathogens & Vaccination (NHSN)",
        description="Weekly COVID-19, Influenza, and RSV case counts, hospitalizations, and vaccination rates for nursing home residents by state, from NHSN",
        years="2024–present",
        key_columns=[
            "jurisdiction",
            "survweekend",
            "numres",
            "numresc19postest",
            "numresflupostest",
            "numresrsvpostest",
            "pct_totresuptodate",
            "pct_numresfluvacc",
            "pct_numresrsvvacc",
        ],
    ),
    # ── Vaccination (weekly) ─────────────────────────────────────────────────
    "resp_vaccination": Dataset(
        id="5c6r-xi2t",
        name="Weekly Respiratory Virus Vaccination Coverage",
        description="Weekly flu, COVID-19, and RSV vaccination coverage for children and adults from National Immunization Survey, by state/demographics",
        years="2023–present",
        key_columns=[
            "vaccine",
            "influenza_season",
            "geographic_level",
            "geographic_name",
            "demographic_level",
            "demographic_name",
            "indicator_label",
            "week_ending",
            "nd_weekly_estimate",
        ],
    ),
    "flu_vaccine_doses": Dataset(
        id="k87d-gv3u",
        name="Weekly Cumulative Flu Vaccine Doses Distributed",
        description="Weekly cumulative influenza vaccine doses distributed nationally by flu season",
        years="2009–present",
        key_columns=[
            "influenza_season",
            "end_date",
            "week",
            "cumulative_flu_doses",
            "current_through",
        ],
    ),
    # ── Drug overdose (monthly/quarterly) ───────────────────────────────────
    "drug_overdose_vsrr": Dataset(
        id="xkb8-kh2a",
        name="VSRR Provisional Drug Overdose Deaths",
        description="Monthly provisional drug overdose death counts by state and drug type from NVSS, with 12-month rolling totals (2015–present)",
        years="2015–present",
        key_columns=[
            "state_name",
            "state",
            "year",
            "month",
            "period",
            "indicator",
            "data_value",
            "predicted_value",
            "percent_complete",
        ],
    ),
    "drug_overdose_county": Dataset(
        id="gb4e-yj24",
        name="VSRR Provisional County-Level Drug Overdose Deaths",
        description="Quarterly provisional drug overdose death counts at county level from NVSS, with 12-month rolling periods",
        years="2020–present",
        key_columns=[
            "state_name",
            "countyname",
            "fips",
            "year",
            "month",
            "provisional_drug_overdose",
            "monthendingdate",
            "percentage_of_records_pending",
        ],
    ),
    # ── Surveillance: ED visits & lab positivity ────────────────────────────
    "nssp_ed_visits": Dataset(
        id="rdmq-nq56",
        name="NSSP Emergency Department Visit Trajectories",
        description="Weekly % of ED visits for COVID-19, influenza, and RSV by state and county from NSSP sentinel emergency departments, with trend direction (increasing/stable/decreasing)",
        years="2022–present",
        key_columns=[
            "week_end",
            "geography",
            "county",
            "percent_visits_covid",
            "percent_visits_influenza",
            "percent_visits_rsv",
            "percent_visits_combined",
            "ed_trends_covid",
            "ed_trends_influenza",
            "ed_trends_rsv",
            "hsa",
            "fips",
        ],
    ),
    "nrevss_rsv_historic": Dataset(
        id="52kb-ccu2",
        name="NREVSS RSV Laboratory Data (Historical)",
        description="Weekly RSV antigen and PCR test counts and positivity from NREVSS participating labs by HHS region (historical; for 2020–present use rsv_positivity instead)",
        years="2010–2020",
        key_columns=[
            "diagnostic_test_type",
            "week_ending_date",
            "hhs_region",
            "rsv_detections",
            "rsv_tests",
        ],
    ),
    # ── Vaccination coverage (VaxView / NIS) ────────────────────────────────
    "flu_coverage_all_ages": Dataset(
        id="vh55-3he6",
        name="Influenza Vaccination Coverage, All Ages 6+ Months (NIS-Flu)",
        description="Monthly cumulative influenza vaccination coverage by state, age group, race/ethnicity, and poverty level from NIS-Flu (2009–present)",
        years="2009–present",
        key_columns=[
            "vaccine",
            "geography_type",
            "geography",
            "fips",
            "year_season",
            "month",
            "dimension_type",
            "dimension",
            "coverage_estimate",
            "_95_ci",
        ],
    ),
    "resp_coverage_adults": Dataset(
        id="ee83-ukst",
        name="NIS-FRVM: Fall Respiratory Virus Vaccination Coverage, Adults",
        description="Monthly COVID-19, influenza, and RSV vaccination coverage among adults and older adults from the National Immunization Survey Fall Respiratory Virus Module (NIS-FRVM), by state and demographics (2024–present)",
        years="2024–present",
        key_columns=[
            "geographic_level",
            "geographic_label",
            "dsss_group_variable_name",
            "dsss_group_variable_category",
            "dsss_indicator_label",
            "dsss_year",
            "dsss_timeperiodlabel",
            "dsss_value",
            "dsss_confidenceinterval",
            "new_vax_group",
        ],
    ),
    "covid_coverage_adults": Dataset(
        id="si7g-c2bs",
        name="NIS-ACM: Adult COVID-19 Vaccination Coverage and Attitudes",
        description="Monthly COVID-19 vaccination coverage and vaccine confidence among adults by state and demographic group from the National Immunization Survey Adult COVID Module (NIS-ACM)",
        years="2021–present",
        key_columns=[
            "geography_type",
            "geography",
            "group_name",
            "group_category",
            "indicator_name",
            "indicator_category",
            "time_period",
            "year",
            "estimate",
            "_95_ci",
            "new_vax_group",
        ],
    ),
    "rsv_coverage_adults_60plus": Dataset(
        id="qve4-fp9c",
        name="RSV Vaccination Coverage, Adults 60+, by Jurisdiction (Weekly)",
        description="Weekly cumulative RSV vaccination coverage among adults 60 years and older by state and nationally, from NIS-ACM (2023–present)",
        years="2023–present",
        key_columns=[
            "vaccine",
            "geographic_level",
            "geographic_name",
            "week_ending",
            "estimate",
            "ci_half_width_95pct",
            "suppression_flag",
        ],
    ),
    "adult_vaccination_coverage": Dataset(
        id="aetd-68ew",
        name="Vaccination Coverage among Adults 18+ Years (BRFSS)",
        description="Annual vaccination coverage for flu, pneumococcal, shingles, Tdap, HPV, and hepatitis among adults 18+ by state, age, race/ethnicity, and insurance status from BRFSS (2008–present)",
        years="2008–present",
        key_columns=[
            "vaccine",
            "dose",
            "geography_type",
            "geography",
            "fips",
            "year_season",
            "dimension_type",
            "dimension",
            "coverage_estimate",
            "_95_ci",
        ],
    ),
    "pregnant_vaccination_coverage": Dataset(
        id="h7pm-wmjc",
        name="Vaccination Coverage among Pregnant Women",
        description="Annual flu and Tdap vaccination coverage among pregnant women by state, race/ethnicity, and insurance status (2012–present)",
        years="2012–present",
        key_columns=[
            "vaccine",
            "geography_type",
            "geography",
            "year_season",
            "dimension_type",
            "dimension",
            "coverage_estimate",
            "_95_ci",
        ],
    ),
    "nursing_home_vaccination_coverage": Dataset(
        id="8w4j-reb4",
        name="Vaccination Coverage among Nursing Home Residents",
        description="Annual influenza and pneumococcal vaccination coverage among nursing home residents by state, age group, and HHS region from the Long-Term Care Minimum Data Set (2005–2021)",
        years="2005–2021",
        key_columns=[
            "vaccine",
            "geography_type",
            "geography",
            "year_season",
            "dimension_type",
            "dimension",
            "coverage_estimate",
            "population_sample_size",
        ],
    ),
    "hcp_vaccination_coverage": Dataset(
        id="xerk-pcm8",
        name="Vaccination Coverage among Health Care Personnel",
        description="Annual influenza vaccination coverage among health care personnel by state, personnel type, and setting from the National Healthcare Safety Network (2013–2021)",
        years="2013–2021",
        key_columns=[
            "vaccine",
            "geography_type",
            "geography",
            "year_season",
            "dimension",
            "coverage_estimate",
            "_95_ci",
            "population_sample_size",
        ],
    ),
    # ── Child vaccination ────────────────────────────────────────────────────
    "children_vaccination": Dataset(
        id="fhky-rtsk",
        name="Vaccination Coverage: Young Children (0–35 months)",
        description="National Immunization Survey (NIS-Child) vaccination coverage for DTaP, MMR, polio, Hib, PCV, rotavirus, Hep A/B, varicella, and influenza — by state, race/ethnicity, insurance status, and birth cohort",
        years="2011–2022",
        key_columns=[
            "vaccine",
            "dose",
            "geography_type",
            "geography",
            "birth_year_birth_cohort",
            "dimension_type",
            "dimension",
            "estimate",
            "sample_size",
        ],
    ),
    # ── Flu / respiratory lab & activity surveillance ────────────────────────
    "ari_activity_state": Dataset(
        id="f3zz-zga5",
        name="Acute Respiratory Illness (ARI) Activity Level by State",
        description="Weekly state-level ARI activity indicator labels (Minimal/Low/Moderate/High/Very High) derived from NSSP emergency department data — the modern equivalent of the FluView ILI activity map",
        years="2024–present",
        key_columns=[
            "week_end",
            "geography",
            "label",
        ],
    ),
    "resp_ed_conditions": Dataset(
        id="v58w-vynu",
        name="Respiratory Conditions Treated in the Emergency Department",
        description="Weekly % of ED visits for specific respiratory conditions (influenza, RSV, COVID-19, pneumonia, bronchiolitis, etc.) by age group, from NSSP — equivalent to ILI surveillance",
        years="2023–present",
        key_columns=[
            "week_end",
            "condition",
            "percent_visits",
            "age_group",
        ],
    ),
    "resp_lens": Dataset(
        id="ch5i-63ve",
        name="RESP-LENS: Respiratory Virus Lab Positivity (ED Network)",
        description="Weekly % positivity for 9 respiratory viruses (influenza A/B, RSV, SARS-CoV-2, etc.) among ED patients by HHS region and age group — the closest Socrata equivalent to NREVSS flu lab data (2021–2024)",
        years="2021–2024",
        key_columns=[
            "season",
            "week",
            "virus",
            "region",
            "age_gp",
            "number_pos",
            "number_tested",
            "percent_pos",
        ],
    ),
    "epidemic_trends_rt": Dataset(
        id="5dqz-y4ea",
        name="CDC Epidemic Trends and Rt",
        description="Weekly estimated effective reproduction number (Rt), trend category, and probability of epidemic growth for COVID-19 and influenza by state",
        years="2020–present",
        key_columns=[
            "as_of",
            "disease",
            "state",
            "date",
            "median",
            "lower",
            "upper",
            "p_growing",
            "category",
        ],
    ),
    "nvsn_pathogen_positivity": Dataset(
        id="kipu-qxy8",
        name="NVSN Viral Pathogen Positivity in Children (ARI)",
        description="Weekly % positivity for 9 viral pathogens (influenza A/B, RSV, SARS-CoV-2, rhinovirus, etc.) among children enrolled in the New Vaccine Surveillance Network with acute respiratory illness, by age group (2017–present)",
        years="2017–present",
        key_columns=[
            "mmwr_week_end",
            "mmwr_week",
            "pathogen",
            "pct_positive",
            "age_group",
        ],
    ),
    "cumulative_rsv_hosp": Dataset(
        id="hmye-mqgq",
        name="Preliminary Estimates of Cumulative RSV Hospitalizations by Week",
        description="Weekly preliminary estimates of cumulative US RSV hospitalizations since start of each respiratory season, with 95% uncertainty intervals",
        years="2024–present",
        key_columns=[
            "season",
            "date",
            "burden",
            "low",
            "high",
        ],
    ),
    "cumulative_covid_hosp": Dataset(
        id="xnjn-rdmd",
        name="Preliminary Estimates of Cumulative COVID-19 Hospitalizations by Week",
        description="Weekly preliminary estimates of cumulative US COVID-19 hospitalizations since start of each respiratory season, with 95% uncertainty intervals",
        years="2024–present",
        key_columns=[
            "season",
            "date",
            "burden",
            "low",
            "high",
        ],
    ),
    # ── COVID / flu / RSV hospitalization (NHSN / archived) ─────────────────
    "covid_hosp_archived": Dataset(
        id="7dk4-g6vg",
        name="Weekly COVID-19 Hospitalization Metrics by Jurisdiction (Archived)",
        description="Archived weekly COVID-19 hospital admissions, inpatient bed utilization, and staff ICU bed occupancy by state and national (USA) — data through May 2024 when mandatory reporting ended",
        years="2020–2024",
        key_columns=[
            "week_ending_date",
            "state",
            "total_adm_all_covid_confirmed",
            "avg_adm_all_covid_confirmed",
            "avg_percent_inpatient_beds",
            "avg_percent_staff_icu_beds",
        ],
    ),
    "nhsn_hrd": Dataset(
        id="ua7e-t2fy",
        name="Weekly Hospital Respiratory Data (NHSN)",
        description="Weekly hospital-reported COVID-19, influenza, and RSV new admissions, current inpatient/ICU patients, and bed occupancy by state/territory and nationally (jurisdiction='USA'), from NHSN (2020–present)",
        years="2020–present",
        key_columns=[
            "weekendingdate",
            "jurisdiction",
            "totalconfc19newadm",
            "totalconfflunewadm",
            "totalconfrsvnewadm",
            "totalconfc19hosppats",
            "totalconffluhosppats",
            "totalconfrsvhosppats",
            "totalconfc19icupats",
            "totalconffluicupats",
            "totalconfrsvicupats",
        ],
    ),
    # ── Notifiable diseases (weekly) ─────────────────────────────────────────
    "nndss_weekly": Dataset(
        id="x9gk-5huc",
        name="NNDSS Weekly Notifiable Diseases",
        description="Provisional weekly case counts for ~100 nationally notifiable diseases (measles, pertussis, hepatitis, TB, Lyme, etc.) by state",
        years="2014–present",
        key_columns=[
            "states",
            "year",
            "week",
            "label",
            "m1",
            "m1_flag",
            "m2",
            "m2_flag",
        ],
    ),
    "nndss_measles": Dataset(
        id="x9gk-5huc",
        name="NNDSS Weekly Measles Cases",
        description="Weekly provisional measles case counts (imported and indigenous) by state/territory, with cumulative annual totals, from NNDSS",
        years="2014–present",
        key_columns=[
            "states",
            "year",
            "week",
            "label",
            "m1",
            "m1_flag",
            "m2",
            "m2_flag",
            "m3",
            "m3_flag",
            "m4",
            "m4_flag",
        ],
        soql_where="label like 'Measles%'",
    ),
    # ── Sexually Transmitted Infections (NNDSS weekly tables) ────────────────
    "nndss_sti_chlamydia": Dataset(
        id="hwyy-s2tt",
        name="NNDSS Table 1G: Chlamydia & Carbapenemase-Producing Organisms",
        description="Weekly provisional case counts for chlamydia trachomatis, chancroid, and carbapenemase-producing organisms by state/territory from NNDSS",
        years="2014–present",
        key_columns=[
            "reporting_area",
            "mmwr_year",
            "mmwr_week",
            "chlamydia_trachomatis",
            "chlamydia_trachomatis_2",
            "chlamydia_trachomatis_4",
            "chlamydia_trachomatis_6",
            "chancroid_current_week",
            "chancroid_cum_2021",
        ],
    ),
    "nndss_sti_gonorrhea": Dataset(
        id="vx8v-gfyf",
        name="NNDSS Table 1M: Gonorrhea",
        description="Weekly provisional gonorrhea case counts by state/territory from NNDSS (current week, 52-week max, cumulative)",
        years="2014–present",
        key_columns=[
            "reporting_area",
            "mmwr_year",
            "mmwr_week",
            "gonorrhea_current_week",
            "gonorrhea_previous_52_weeks_max",
        ],
    ),
    "nndss_sti_syphilis": Dataset(
        id="6ie8-bpiy",
        name="NNDSS Table 1HH: Syphilis",
        description="Weekly provisional syphilis case counts (primary & secondary, congenital) by state/territory from NNDSS",
        years="2014–present",
        key_columns=[
            "reporting_area",
            "mmwr_year",
            "mmwr_week",
            "syphilis_primary_and_secondary",
            "syphilis_primary_and_secondary_2",
            "syphilis_primary_and_secondary_4",
            "syphilis_congenital_current_1",
            "syphilis_congenital_cum_2021_1",
        ],
    ),
    # ── Chronic Disease Indicators ───────────────────────────────────────────
    "chronic_disease_indicators": Dataset(
        id="hksd-2xuw",
        name="U.S. Chronic Disease Indicators (CDI)",
        description=(
            "State-level indicators across 19 chronic disease topics: alcohol, arthritis, asthma, cancer, "
            "cardiovascular disease, COPD, diabetes, mental health, tobacco, and more. "
            "Includes prevalence, mortality, and risk factor measures by state and demographics."
        ),
        years="2001–present",
        key_columns=[
            "yearstart",
            "yearend",
            "locationabbr",
            "locationdesc",
            "topic",
            "question",
            "datavalue",
            "datavalueunit",
            "datavaluetype",
            "stratificationcategory1",
            "stratification1",
            "datasource",
            "questionid",
            "topicid",
        ],
    ),
    # ── Cancer Deaths ────────────────────────────────────────────────────────
    "monthly_deaths_by_cause": Dataset(
        id="9dzk-mvmi",
        name="Monthly Provisional Counts of Deaths by Select Causes",
        description=(
            "Monthly provisional US death counts for 20+ causes: cancer (malignant neoplasms), "
            "heart disease, diabetes, Alzheimer's, influenza/pneumonia, CLRD, stroke, "
            "drug overdose, suicide, COVID-19, and more. National and state-level."
        ),
        years="2020–present",
        key_columns=[
            "jurisdiction_of_occurrence",
            "year",
            "month",
            "start_date",
            "end_date",
            "all_cause",
            "malignant_neoplasms",
            "diseases_of_heart",
            "cerebrovascular_diseases",
            "diabetes_mellitus",
            "alzheimer_disease",
            "chronic_lower_respiratory",
            "drug_overdose",
            "intentional_self_harm_suicide",
            "assault_homicide",
            "covid_19_underlying_cause",
        ],
    ),
    # ── Healthcare-Associated Infections (HAI) / Antimicrobial Resistance ───
    "hai_mrsa": Dataset(
        id="ssz5-s49e",
        name="HAICViz: Invasive Staphylococcus aureus (MRSA/MSSA)",
        description=(
            "Annual case rates for invasive Staphylococcus aureus (MRSA and MSSA) "
            "from the CDC Emerging Infections Program (EIP) network. "
            "Breakdowns by age, sex, race, dialysis status, and exposure type."
        ),
        years="2005–2021",
        key_columns=[
            "yearname",
            "topic",
            "viewby",
            "series",
            "value",
        ],
    ),
    "hai_amr": Dataset(
        id="v4tm-h8pe",
        name="HAICViz: Antimicrobial Resistance (CRAB, CRE, ESBL)",
        description=(
            "Annual case rates for carbapenem-resistant Acinetobacter baumannii (CRAB), "
            "carbapenem-resistant Enterobacterales (CRE), and ESBL-producing organisms "
            "from the CDC MuGSI/EIP network. Breakdowns by age, organism, and exposure."
        ),
        years="2012–present",
        key_columns=[
            "yearname",
            "organism",
            "topic",
            "viewby",
            "series",
            "value",
        ],
    ),
    "hai_cdiff": Dataset(
        id="abgz-qs4g",
        name="HAICViz: Clostridioides difficile (C. diff)",
        description=(
            "Annual case rates for Clostridioides difficile infection (CDI) "
            "from the CDC Emerging Infections Program (EIP) network. "
            "Breakdowns by age, community vs. healthcare onset, and case severity."
        ),
        years="2011–present",
        key_columns=[
            "yearname",
            "topic",
            "viewby",
            "grouping",
            "series",
            "value",
        ],
    ),
    "hai_candidemia": Dataset(
        id="34p9-h4us",
        name="HAICViz: Candidemia (Invasive Candida)",
        description=(
            "Annual drug resistance rates and case metrics for Candida bloodstream infections "
            "from CDC surveillance. Species-level breakdown and antifungal resistance trends."
        ),
        years="2009–present",
        key_columns=[
            "yearname",
            "topic",
            "viewby",
            "series",
            "value",
        ],
    ),
}

# ── CDC WCMS visualization JSON endpoints ─────────────────────────────────────
# These back interactive charts on CDC disease pages; not on data.cdc.gov.
_WCMS_BASE = "https://www.cdc.gov/wcms/vizdata"

WCMS_DATASETS: dict[str, WcmsDataset] = {
    "measles_annual_history": WcmsDataset(
        url=f"{_WCMS_BASE}/measles/MeaslesCasesHistory.json",
        name="Measles Annual Cases History",
        description=(
            "Annual confirmed measles case counts for the United States, "
            "1962–present. Powers the annotated history-of-measles line chart "
            "on the CDC measles data page."
        ),
        years="1962–present",
        key_columns=["year", "cases"],
    ),
    "measles_annual_cases": WcmsDataset(
        url=f"{_WCMS_BASE}/measles/MeaslesCasesYear.json",
        name="Measles Annual Cases (Filterable)",
        description=(
            "Annual confirmed measles case counts for the United States, "
            "1985–present, with a 'filter' column for two chart views: "
            "'1985-Present*' and '2000-Present*'. Powers the yearly-cases "
            "bar chart on the CDC measles data page."
        ),
        years="1985–present",
        key_columns=["year", "cases", "filter"],
    ),
    "measles_weekly_cases": WcmsDataset(
        url=f"{_WCMS_BASE}/measles/MeaslesCasesWeekly.json",
        name="Measles Weekly Cases by Rash Onset Date",
        description=(
            "Weekly confirmed measles case counts by rash onset date, "
            "2022–present. Powers the weekly-cases line chart on the CDC "
            "measles data page."
        ),
        years="2022–present",
        key_columns=["week_start", "week_end", "cases"],
    ),
}
