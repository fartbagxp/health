"""
CDC PLACES dataset registry.

Two families, matching the seven pages of CDC's PLACES portal: PLACES proper
(40 BRFSS-modeled measures in six categories, below) and Non-Medical Factors
(9 ACS-derived measures, at the bottom of this file).

PLACES ("Local Data for Better Health") publishes model-based small-area
estimates of 40 health measures at four geographic levels. Each annual release
is a separate Socrata dataset on data.cdc.gov in "Open Data" long format:

    year · stateabbr · statedesc · countyname · countyfips · locationname
         · datasource · category · measure · data_value_unit · data_value_type
         · data_value · data_value_footnote_symbol · data_value_footnote
         · low_confidence_limit · high_confidence_limit · totalpopulation
         · totalpop18plus · geolocation · locationid · categoryid · measureid
         · datavaluetypeid · short_question_text

These are far too large for this repository -- the 2025 release alone is ~6.6M
rows / ~1.4GB across the four levels (~7.9M / ~1.7GB with Non-Medical Factors),
and the census-tract file is 694MB on its own, past GitHub's 100MB hard limit. They are mirrored into the public Dolt
database instead (see places.dolt); only small derived slices land in
data/processed/places/ for health-charts.

`rows` is the expected row count, checked after every download. Socrata has
silently truncated results for this project before (see the comment in
.github/workflows/update_cdc_open.yml), so a short read must fail loudly rather
than quietly import a partial release.
"""

from dataclasses import dataclass

# Geographic levels, in ascending resolution. Used as the `geo_level` ENUM in
# Dolt and as the --geo choices on the CLI.
GEO_LEVELS = ("county", "place", "tract", "zcta")


@dataclass(frozen=True)
class PlacesDataset:
    socrata_id: str  # Socrata 4x4 ID, e.g. "swc5-untb"
    geo_level: str  # one of GEO_LEVELS
    release: int  # PLACES release year, e.g. 2025
    rows: int  # expected row count -- truncation guard, see module docstring
    name: str
    # Value types present at this level. County and place carry both crude and
    # age-adjusted prevalence; tract and ZCTA are crude-only (CDC does not
    # publish age-adjusted estimates below place level).
    value_types: tuple[str, ...] = ("CrdPrv", "AgeAdjPrv")


PLACES_DATASETS: dict[str, PlacesDataset] = {
    # ── 2025 release ──────────────────────────────────────────────────────────
    "county_2025": PlacesDataset(
        socrata_id="swc5-untb",
        geo_level="county",
        release=2025,
        rows=229_298,
        name="PLACES: Local Data for Better Health, County Data, 2025 release",
    ),
    "place_2025": PlacesDataset(
        socrata_id="eav7-hnsx",
        geo_level="place",
        release=2025,
        rows=2_150_438,
        name="PLACES: Local Data for Better Health, Place Data, 2025 release",
    ),
    "tract_2025": PlacesDataset(
        socrata_id="cwsq-ngmh",
        geo_level="tract",
        release=2025,
        rows=3_047_284,
        name="PLACES: Local Data for Better Health, Census Tract Data, 2025 release",
        value_types=("CrdPrv",),
    ),
    "zcta_2025": PlacesDataset(
        socrata_id="qnzd-25i4",
        geo_level="zcta",
        release=2025,
        rows=1_171_563,
        name="PLACES: Local Data for Better Health, ZCTA Data, 2025 release",
        value_types=("CrdPrv",),
    ),
}


def key(geo_level: str, release: int) -> str:
    return f"{geo_level}_{release}"


def dataset(geo_level: str, release: int) -> PlacesDataset:
    """Look up one dataset, raising a useful error listing what is registered."""
    k = key(geo_level, release)
    if k not in PLACES_DATASETS:
        available = ", ".join(sorted(PLACES_DATASETS))
        raise KeyError(f"no PLACES dataset {k!r}; registered: {available}")
    return PLACES_DATASETS[k]


def releases() -> list[int]:
    return sorted({d.release for d in PLACES_DATASETS.values()})


# ── Non-Medical Factors (ACS) ─────────────────────────────────────────────────
#
# The PLACES data portal has seven pages; the six categories above cover six of
# them. The seventh, "Non-Medical Factors", is a separate CDC product --
# "Non-Medical Factor Measures", nine social-determinant measures derived from
# the 5-year American Community Survey rather than from BRFSS. It ships as four
# more Socrata datasets with a different row shape, so it gets its own tables.
#
# What differs from PLACES, all verified against the full county export:
#
#   * `year` is a five-year ACS period string ('2017-2021'), not an integer.
#   * There is a margin of error (`MOE`) instead of confidence limits, and no
#     footnote columns.
#   * `Data_Value_Type` is always 'Percentage', so it is not part of any key.
#   * Column availability differs by level in its own way: place carries no
#     CountyName/CountyFIPS (PLACES place does), and ZCTA carries no state
#     columns at all.
#   * The geography vintage differs. ACS 2017-2021 still uses Connecticut's
#     retired county FIPS (09001-09015); PLACES 2025 uses the new planning
#     regions (09110-09190). The two families therefore do not share a location
#     universe, and county names disagree besides ('Autauga County' here vs
#     'Autauga' in PLACES, on 3,131 of 3,133 shared counties). This is why
#     nmf_location exists rather than reusing `location`.
#
# The measure and category dimensions ARE shared: the nine measure IDs do not
# collide with PLACES' forty, so one `measure` table describes all seven pages.

NMF_PERIOD = "2017-2021"


@dataclass(frozen=True)
class NmfDataset:
    socrata_id: str
    geo_level: str  # one of GEO_LEVELS
    period: str  # ACS 5-year period, e.g. "2017-2021"
    rows: int  # expected row count -- truncation guard
    name: str


NMF_DATASETS: dict[str, NmfDataset] = {
    "county_2017-2021": NmfDataset(
        socrata_id="i6u4-y3g4",
        geo_level="county",
        period=NMF_PERIOD,
        rows=28_287,
        name="Non-Medical Factor Measures for County, ACS 2017-2021",
    ),
    "place_2017-2021": NmfDataset(
        socrata_id="edkk-ze78",
        geo_level="place",
        period=NMF_PERIOD,
        rows=268_389,
        name="Non-Medical Factor Measures for Place, ACS 2017-2021",
    ),
    "tract_2017-2021": NmfDataset(
        socrata_id="e539-uadk",
        geo_level="tract",
        period=NMF_PERIOD,
        rows=751_509,
        name="Non-Medical Factor Measures for Census Tract, ACS 2017-2021",
    ),
    "zcta_2017-2021": NmfDataset(
        socrata_id="bumh-rgsq",
        geo_level="zcta",
        period=NMF_PERIOD,
        rows=291_024,
        name="Non-Medical Factor Measures for ZCTA, ACS 2017-2021",
    ),
}


def nmf_dataset(geo_level: str, period: str = NMF_PERIOD) -> NmfDataset:
    """Look up one Non-Medical Factors dataset."""
    k = f"{geo_level}_{period}"
    if k not in NMF_DATASETS:
        available = ", ".join(sorted(NMF_DATASETS))
        raise KeyError(f"no Non-Medical Factors dataset {k!r}; registered: {available}")
    return NMF_DATASETS[k]


def nmf_periods() -> list[str]:
    return sorted({d.period for d in NMF_DATASETS.values()})
