"""
Curated registry of CDC EPHT measures to archive as small state-level series.

EPHT exposes ~867 measures across 27 environmental-health content areas. The
full county-level firehose is far too large for a git repo, so this registry
picks a handful of **state-level, annual** measures — 50 states + DC over ~20
years is only ~1,000 rows each, well under the 5MB archive cap.

Measure IDs are stable and come from the ``/measuresearch`` endpoint
(``epht measures --search <term>``). ``charted`` marks whether health-charts
renders the series yet.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Measure:
    key: str
    measure_id: int
    name: str
    content_area: str
    description: str
    years: str
    unit: str
    charted: bool = False


MEASURES: dict[str, Measure] = {
    "pm25_annual_avg": Measure(
        key="pm25_annual_avg",
        measure_id=87,
        name="PM2.5: Highest Annual Average Concentration (Monitor Data)",
        content_area="Air Quality",
        description="Highest annual average ambient PM2.5 concentration from air-quality monitors, by state and year.",
        years="2001–present",
        unit="µg/m³",
    ),
    "pm25_days_over_standard": Measure(
        key="pm25_days_over_standard",
        measure_id=85,
        name="PM2.5: Percent of Days over Air Quality Standard (Monitor Only)",
        content_area="Air Quality",
        description="Percent of days per year with ambient PM2.5 above the national air-quality standard, by state.",
        years="2001–present",
        unit="% of days",
    ),
    "asthma_hosp_rate": Measure(
        key="asthma_hosp_rate",
        measure_id=103,
        name="Age-adjusted Rate of Hospitalizations for Asthma per 10,000",
        content_area="Asthma",
        description="Age-adjusted asthma hospitalization rate per 10,000 population, by state and year.",
        years="2000–present",
        unit="per 10,000",
    ),
    "asthma_ed_rate": Measure(
        key="asthma_ed_rate",
        measure_id=436,
        name="Crude Rate of Emergency Department Visits for Asthma per 10,000",
        content_area="Asthma",
        description="Emergency department visit rate for asthma per 10,000 population, by state and year.",
        years="2005–present",
        unit="per 10,000",
    ),
    "heat_related_deaths": Measure(
        key="heat_related_deaths",
        measure_id=370,
        name="Annual Number of Heat-related Deaths",
        content_area="Heat & Heat-related Illness",
        description="Annual count of deaths with heat as an underlying or contributing cause, by state.",
        years="2000–present",
        unit="deaths",
    ),
    "extreme_heat_days": Measure(
        key="extreme_heat_days",
        measure_id=423,
        name="Annual Number of Extreme Heat Days (May–September)",
        content_area="Heat & Heat-related Illness",
        description="Count of extreme heat days during the warm season, by state and year.",
        years="1979–present",
        unit="days",
    ),
    "child_blood_lead_5": Measure(
        key="child_blood_lead_5",
        measure_id=1156,
        name="Percent of Children Tested With Confirmed Blood Lead ≥5 µg/dL",
        content_area="Childhood Lead Poisoning",
        description="Percent of tested children under 6 with confirmed blood lead level at or above 5 µg/dL, by state.",
        years="2012–present",
        unit="% of tested",
    ),
    "total_fertility_rate": Measure(
        key="total_fertility_rate",
        measure_id=45,
        name="Total Fertility Rate per 1,000 Women",
        content_area="Reproductive & Birth Outcomes",
        description="Total fertility rate per 1,000 women, by state and year.",
        years="2000–present",
        unit="per 1,000 women",
    ),
}
