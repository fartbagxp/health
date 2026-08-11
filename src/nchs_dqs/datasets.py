"""
NCHS Data Query System (DQS) dataset registry.

DQS is CDC/NCHS's unified query layer over the "Health, United States" report
family (NHANES, NHIS, NHAMCS, NVSS, NPALS, NHCS). Every topic is published as a
Socrata dataset on data.cdc.gov with a shared tidy schema:

    topic · subtopic · classification · group · subgroup
          · estimate_type · time_period · estimate · estimate_lci · estimate_uci

`classification = 'Total'` is the all-persons row; other classifications are
demographic / geographic / socioeconomic cuts.

This catalogs the 28 current (non-archived, non-footnote) DQS data tables — the
same set pulse-code's `pulse source dqs` explores. `charted=True` marks the
slices health archives into data/raw/dqs and health-charts renders; the rest are
the backlog of charts we could add next (each is already a working Socrata
endpoint, queryable today).
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Dataset:
    id: str  # Socrata 4x4 ID, e.g. "rdjz-vn2n"
    name: str
    description: str
    years: str  # observed time_period coverage
    survey: str  # source survey/system feeding the estimates
    topic: str  # topic bucket (mirrors pulse's DQS topic taxonomy)
    dimensions: list[str] = field(default_factory=list)  # available `classification` cuts
    # True once a slice of this dataset is archived to data/raw/dqs and read by
    # health-charts. Collected-but-uncharted datasets are the backlog.
    charted: bool = False
    # Output CSV under data/raw/dqs written by nchs_dqs.fetch_dqs (charted only).
    csv: str | None = None


# Ordered by topic relevance (mortality/natality first), matching pulse.
DATASETS: dict[str, Dataset] = {
    # ── Mortality / cause-of-death (NVSS, mirrors CDC WONDER) ──────────────────
    "heart-disease-deaths": Dataset(
        id="7aq9-prdf",
        name="Death rates for heart disease, by sex, race, Hispanic origin, and age",
        description="Age-adjusted and crude heart-disease death rates.",
        years="2018–2024", survey="NVSS", topic="Mortality",
        dimensions=["Total", "Demographic Characteristic", "Multiple Characteristics"],
    ),
    "cancer-deaths": Dataset(
        id="h3hw-hzvg",
        name="Death rates for malignant neoplasms, by sex, race, Hispanic origin, and age",
        description="Age-adjusted and crude cancer (malignant neoplasm) death rates.",
        years="2018–2024", survey="NVSS", topic="Cancer",
        dimensions=["Total", "Demographic Characteristic", "Multiple Characteristics"],
    ),
    "suicide-deaths": Dataset(
        id="w26f-tf3h",
        name="Death rates for suicide, by sex, race, Hispanic origin, and age",
        description="Age-adjusted and crude suicide death rates.",
        years="2018–2024", survey="NVSS", topic="Injury & Overdose",
        dimensions=["Total", "Demographic Characteristic", "Multiple Characteristics"],
    ),
    "drug-overdose-deaths": Dataset(
        id="rdjz-vn2n",
        name="Drug overdose death rates, by drug type, sex, age, race, and Hispanic origin",
        description="Age-adjusted and crude drug-overdose death rates, broken out by opioid type.",
        years="2018–2024", survey="NVSS", topic="Injury & Overdose",
        dimensions=["Total", "Demographic Characteristic", "Multiple Characteristics"],
        charted=True, csv="drug_overdose_by_type.csv",
    ),
    # ── Birth / infant / fetal (NVSS) ─────────────────────────────────────────
    "infant-mortality": Dataset(
        id="j7ym-uwqy",
        name="Infant, neonatal, and postneonatal mortality rates, by detailed race and Hispanic origin of mother",
        description="Infant/neonatal/postneonatal mortality rates.",
        years="2017–2024", survey="NVSS", topic="Infant Mortality",
        dimensions=["Total", "Demographic Characteristic"],
    ),
    "fetal-perinatal-mortality": Dataset(
        id="wd75-kcmv",
        name="Fetal, late fetal, and perinatal mortality rates, by detailed race and Hispanic origin of mother",
        description="Fetal, late fetal, and perinatal mortality rates.",
        years="1995–2021", survey="NVSS", topic="Fetal Deaths",
        dimensions=["Total", "Demographic Characteristic"],
    ),
    "birth-fertility-rates": Dataset(
        id="daba-4vfq",
        name="Birth and fertility rates, by age group, race, and Hispanic origin of mother",
        description="Birth and fertility rates.",
        years="2016–2024", survey="NVSS", topic="Natality",
        dimensions=["Total", "Demographic Characteristic", "Multiple Characteristics"],
    ),
    "low-birthweight": Dataset(
        id="ga7k-kycn",
        name="Low birthweight live births, by state",
        description="Percent of live births that are low birthweight (<2,500g), by state.",
        years="2014–2023", survey="NVSS", topic="Natality",
        dimensions=["Total", "Geographic Characteristic"],
        charted=True, csv="low_birthweight_by_state.csv",
    ),
    # ── Chronic disease & risk factors (NHANES) ───────────────────────────────
    "cholesterol-adults": Dataset(
        id="6tn6-vc33",
        name="Cholesterol in adults age 20 and older, by selected characteristics",
        description="Mean serum cholesterol and high-cholesterol prevalence in adults 20+.",
        years="1988–2020", survey="NHANES", topic="Chronic Disease & Risk Factors",
        dimensions=["Total", "Demographic Characteristic", "Socioeconomic Characteristic", "Multiple Characteristics"],
    ),
    "hypertension-adults": Dataset(
        id="va5e-efw9",
        name="Hypertension in adults age 20 and older, by selected characteristics",
        description="Hypertension prevalence in adults 20+.",
        years="1988–2020", survey="NHANES", topic="Chronic Disease & Risk Factors",
        dimensions=["Total", "Demographic Characteristic", "Socioeconomic Characteristic", "Multiple Characteristics"],
    ),
    "chronic-conditions": Dataset(
        id="6rvp-rahv",
        name="Select chronic conditions prevalence estimates",
        description="Prevalence of select chronic conditions.",
        years="1999–2023", survey="NHANES", topic="Chronic Disease & Risk Factors",
        dimensions=["Total", "Demographic Characteristic", "Multiple Characteristics"],
    ),
    # ── Nutrition, oral health, infectious prevalence (NHANES) ─────────────────
    "dietary-intake": Dataset(
        id="8ekv-ep3s",
        name="Select mean dietary intake estimates",
        description="Mean dietary intake estimates from 24-hour recall.",
        years="1999–2023", survey="NHANES", topic="Nutrition & Diet",
        dimensions=["Total", "Demographic Characteristic", "Multiple Characteristics"],
    ),
    "oral-health": Dataset(
        id="36ue-xht5",
        name="Select oral health prevalence estimates",
        description="Dental caries, untreated decay, and other oral-health prevalence.",
        years="1999–2018", survey="NHANES", topic="Oral Health",
        dimensions=["Total", "Demographic Characteristic", "Multiple Characteristics"],
    ),
    "infectious-prevalence": Dataset(
        id="v7tk-n6v3",
        name="Select infectious diseases prevalence estimates",
        description="Serologic prevalence of select infectious diseases.",
        years="1999–2018", survey="NHANES", topic="Infectious Disease Prevalence",
        dimensions=["Total", "Demographic Characteristic", "Multiple Characteristics"],
    ),
    # ── Self-reported health & disability (NHIS) ──────────────────────────────
    "nhis-adult": Dataset(
        id="gj3i-hsbz",
        name="NHIS adult summary health statistics",
        description="Adult self-reported health status, conditions, access, and behaviors.",
        years="2019–2024", survey="NHIS", topic="Self-Reported Health",
        dimensions=["Total", "Demographic Characteristic", "Geographic Characteristic", "Socioeconomic Characteristic"],
    ),
    "nhis-child": Dataset(
        id="7ctq-myvs",
        name="NHIS child summary health statistics",
        description="Child self-reported health status, conditions, and access.",
        years="2019–2024", survey="NHIS", topic="Self-Reported Health",
        dimensions=["Total", "Demographic Characteristic", "Geographic Characteristic", "Socioeconomic Characteristic"],
    ),
    "functioning-difficulties": Dataset(
        id="btv3-srcc",
        name="Functioning difficulties in adults age 18 and older, by selected characteristics",
        description="Vision, hearing, mobility, and cognition difficulties in adults 18+.",
        years="2019–2024", survey="NHIS", topic="Disability & Functioning",
        dimensions=["Total", "Demographic Characteristic", "Geographic Characteristic", "Socioeconomic Characteristic"],
    ),
    # ── Substance & medication use (NHANES / MTF) ─────────────────────────────
    "prescription-drug-use": Dataset(
        id="kusj-ex57",
        name="Prescription medication use in the past 30 days, by sex, race and Hispanic origin, and age group",
        description="Prescription-medication use prevalence.",
        years="1988–2023", survey="NHANES", topic="Substance & Medication Use",
        dimensions=["Total", "Demographic Characteristic", "Multiple Characteristics"],
    ),
    "substance-use": Dataset(
        id="mtgp-t7vw",
        name="Use of selected substances in the past 30 days among 8th, 10th, and 12th graders, by sex and race",
        description="Substance use among 8th/10th/12th graders (Monitoring the Future).",
        years="1980–2024", survey="MTF", topic="Substance & Medication Use",
        dimensions=["Total", "Socioeconomic Characteristic", "Multiple Characteristics"],
    ),
    # ── Health-care system: capacity & utilization (NHAMCS / NHCS) ─────────────
    "hospital-beds": Dataset(
        id="8miz-siyd",
        name="Community hospital beds, by state",
        description="Community hospital beds per capita, by state.",
        years="1980–2023", survey="NHCS", topic="Health Care System",
        dimensions=["Total", "Geographic Characteristic"],
    ),
    "ed-visits": Dataset(
        id="e4ec-z5aa",
        name="Estimate of emergency department visits in the United States",
        description="Emergency department visit estimates.",
        years="2016–2022", survey="NHAMCS", topic="Health Care System",
        dimensions=["Total", "Demographic Characteristic", "Geographic Characteristic", "Socioeconomic Characteristic"],
    ),
    "hospital-utilization": Dataset(
        id="4q35-rqzk",
        name="Hospital admission, average length of stay, outpatient visits, and outpatient surgery, by ownership and size",
        description="Hospital admission, length of stay, and outpatient measures.",
        years="1975–2023", survey="NHCS", topic="Health Care System",
        dimensions=["Total", "Other Characteristic"],
    ),
    # ── Health-care workforce ─────────────────────────────────────────────────
    "dentists": Dataset(
        id="yib5-h3pw",
        name="Dentists, by state",
        description="Dentists per capita, by state.",
        years="2001–2024", survey="NCHS", topic="Health Care Workforce",
        dimensions=["Total", "Geographic Characteristic"],
    ),
    "healthcare-employment": Dataset(
        id="7siw-u4fz",
        name="Health care employment and wages, by selected occupations",
        description="Health-care employment counts and wages by occupation.",
        years="2000–2024", survey="BLS/NCHS", topic="Health Care Workforce",
        dimensions=["Other Characteristic"],
    ),
    # ── Health expenditure (CMS NHEA) ─────────────────────────────────────────
    "national-health-spending": Dataset(
        id="s57w-7gbe",
        name="National health spending",
        description="U.S. national health expenditure — total, per capita, and share of GDP.",
        years="1960–2024", survey="CMS/NHEA", topic="Health Expenditure",
        dimensions=["Total", "Other Characteristic"],
        charted=True, csv="national_health_spending.csv",
    ),
    "personal-healthcare-spending": Dataset(
        id="gu48-2cs8",
        name="Personal healthcare spending",
        description="Personal health-care spending series.",
        years="1960–2024", survey="CMS/NHEA", topic="Health Expenditure",
        dimensions=["Total", "Other Characteristic"],
    ),
    # ── Long-term care (NPALS) ────────────────────────────────────────────────
    "ltc-providers": Dataset(
        id="sz5x-j2c3",
        name="National post-acute and long-term care providers",
        description="Post-acute and long-term-care provider counts.",
        years="2020–2022", survey="NPALS", topic="Long-Term Care",
        dimensions=["Total", "Geographic Characteristic", "Other Characteristic"],
    ),
    "ltc-users": Dataset(
        id="6pdm-py4x",
        name="National post-acute and long-term care users",
        description="Post-acute and long-term-care user counts and characteristics.",
        years="2020–2022", survey="NPALS", topic="Long-Term Care",
        dimensions=["Total", "Demographic Characteristic", "Socioeconomic Characteristic", "Other Characteristic"],
    ),
}

_BY_ID: dict[str, Dataset] = {d.id: d for d in DATASETS.values()}


def dataset(key_or_id: str) -> Dataset | None:
    """Look up by registry key (e.g. 'low-birthweight') or Socrata ID ('ga7k-kycn')."""
    return DATASETS.get(key_or_id) or _BY_ID.get(key_or_id)


def charted_datasets() -> dict[str, Dataset]:
    """The datasets health archives and health-charts renders."""
    return {k: d for k, d in DATASETS.items() if d.charted}
