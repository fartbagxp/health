"""
Split CDC exports into normalized fact and dimension CSVs, streaming.

Two families live here, matching the two products behind CDC's PLACES portal:
split() handles the six BRFSS-derived PLACES categories, and split_nmf()
handles the seventh page, the ACS-derived Non-Medical Factors. They share the
`measure` and `category` dimensions and nothing else; see split_nmf's docstring
for the source differences.

The published long format repeats eleven of its twenty-four columns on every
row. Verified against the full downloaded files:

  * TotalPopulation / TotalPop18plus are constant per (LocationID, Year) --
    zero violations across all 229,298 county rows. They describe a place, not
    a measurement, and belong in location_population.
  * Geolocation is a WKT POINT constant per LocationID -- a location attribute.
  * Category / Measure / Short_Question_Text / Data_Value_Unit / DataSource are
    functions of MeasureId (40 distinct values).
  * StateDesc / CountyName / LocationName are functions of LocationID.

Hoisting those into dimensions takes the fact table from ~239 bytes/row to
roughly 45, and makes the database join-able rather than a pile of denormalized
CSV.

Everything here is single-pass and streaming. The census-tract export is 694MB;
the fact rows are written out as they arrive and only the dimensions (at most
~83.5k locations) are held in memory.
"""

import csv
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

# Output column orders -- these must match the Dolt table definitions, since
# the import API maps by column name but a stable order keeps diffs readable.
MEASUREMENT_COLUMNS = [
    "release_year",
    "geo_level",
    "location_id",
    "measure_id",
    "data_value_type",
    "year",
    "data_value",
    "low_confidence_limit",
    "high_confidence_limit",
    "footnote_symbol",
]
LOCATION_COLUMNS = [
    "geo_level",
    "location_id",
    "state_abbr",
    "state_desc",
    "county_name",
    "county_fips",
    "location_name",
    "lat",
    "lon",
]
LOCATION_POPULATION_COLUMNS = [
    "geo_level",
    "location_id",
    "year",
    "total_population",
    "total_pop_18plus",
]
MEASURE_COLUMNS = [
    "measure_id",
    "category_id",
    "measure_name",
    "short_question_text",
    "data_value_unit",
    "data_source",
]
CATEGORY_COLUMNS = ["category_id", "category_name"]

# Non-Medical Factors (ACS). `measure` and `category` are shared with PLACES
# above -- the nine ACS measure IDs do not collide with PLACES' forty -- so
# only the fact and location tables need their own column orders.
NMF_MEASUREMENT_COLUMNS = [
    "period",
    "geo_level",
    "location_id",
    "measure_id",
    "data_value",
    "moe",
]
NMF_LOCATION_COLUMNS = [
    "geo_level",
    "location_id",
    "state_abbr",
    "state_desc",
    "county_name",
    "county_fips",
    "location_name",
    "lat",
    "lon",
]
NMF_LOCATION_POPULATION_COLUMNS = [
    "period",
    "geo_level",
    "location_id",
    "total_population",
]

# The source sets both Category and CategoryID to the bare string 'SDOH'.
# Stored under the name CDC's own dataset titles and portal page use, so the
# shared category table reads consistently alongside the other six.
NMF_CATEGORY_NAME = "Non-Medical Factors"

# Primary keys, passed to the DoltHub import API so re-importing a release
# upserts rather than duplicating.
PRIMARY_KEYS = {
    "measurement": [
        "release_year",
        "geo_level",
        "location_id",
        "measure_id",
        "data_value_type",
        "year",
    ],
    "location": ["geo_level", "location_id"],
    "location_population": ["geo_level", "location_id", "year"],
    "measure": ["measure_id"],
    "category": ["category_id"],
    # Written by places.sync rather than by split(), but keyed here so every
    # table's primary key lives in one place.
    "release_meta": ["release_year", "geo_level"],
    # Non-Medical Factors (ACS). Keyed by ACS period rather than release year,
    # and with no data_value_type: that column is always 'Percentage' here.
    "nmf_measurement": ["period", "geo_level", "location_id", "measure_id"],
    "nmf_location": ["geo_level", "location_id"],
    "nmf_location_population": ["period", "geo_level", "location_id"],
    "nmf_release_meta": ["period", "geo_level"],
}


@dataclass
class TransformResult:
    """Where each table was written, and how many rows it holds."""

    paths: dict[str, Path]
    counts: dict[str, int]


def parse_point(wkt: str) -> tuple[str, str]:
    """'POINT (-86.77 33.58)' -> ('33.58', '-86.77') as (lat, lon).

    WKT orders coordinates x then y, i.e. longitude first. Getting this
    backwards silently puts every county in the Indian Ocean, so it is parsed
    explicitly rather than by splitting and hoping.
    """
    if not wkt:
        return "", ""
    inner = wkt.strip().removeprefix("POINT").strip()
    inner = inner.removeprefix("(").removesuffix(")").strip()
    parts = inner.split()
    if len(parts) != 2:
        return "", ""
    lon, lat = parts
    return lat, lon


def _num(value: str) -> str:
    """Pass numbers through, mapping blanks to empty so Dolt reads them NULL."""
    return value.strip() if value else ""


def split(
    rows: Iterator[dict[str, str]],
    geo_level: str,
    release: int,
    out_dir: Path,
    expected_rows: int | None = None,
) -> TransformResult:
    """Stream `rows` into normalized CSVs under `out_dir`.

    Raises SystemExit if the row count does not match `expected_rows` -- a
    short read means Socrata truncated the export, and a partial release must
    never reach Dolt.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "measurement": out_dir / "measurement.csv",
        "location": out_dir / "location.csv",
        "location_population": out_dir / "location_population.csv",
        "measure": out_dir / "measure.csv",
        "category": out_dir / "category.csv",
    }

    # Dimensions accumulate in memory; the largest is ~83.5k tract locations.
    locations: dict[str, dict[str, str]] = {}
    populations: dict[tuple[str, str], dict[str, str]] = {}
    measures: dict[str, dict[str, str]] = {}
    categories: dict[str, str] = {}

    n = 0
    with paths["measurement"].open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=MEASUREMENT_COLUMNS,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            n += 1
            location_id = row["LocationID"]
            year = row["Year"]
            measure_id = row["MeasureId"]

            writer.writerow(
                {
                    "release_year": release,
                    "geo_level": geo_level,
                    "location_id": location_id,
                    "measure_id": measure_id,
                    "data_value_type": row["DataValueTypeID"],
                    "year": year,
                    "data_value": _num(row["Data_Value"]),
                    "low_confidence_limit": _num(row["Low_Confidence_Limit"]),
                    "high_confidence_limit": _num(row["High_Confidence_Limit"]),
                    "footnote_symbol": row.get(
                        "Data_Value_Footnote_Symbol", ""
                    ).strip(),
                }
            )

            if location_id not in locations:
                lat, lon = parse_point(row.get("Geolocation", ""))
                locations[location_id] = {
                    "geo_level": geo_level,
                    "location_id": location_id,
                    "state_abbr": row.get("StateAbbr", ""),
                    "state_desc": row.get("StateDesc", ""),
                    # County-level exports carry neither column; place, tract
                    # and ZCTA all do.
                    "county_name": row.get("CountyName", ""),
                    "county_fips": row.get("CountyFIPS", ""),
                    "location_name": row.get("LocationName", ""),
                    "lat": lat,
                    "lon": lon,
                }

            pop_key = (location_id, year)
            if pop_key not in populations:
                populations[pop_key] = {
                    "geo_level": geo_level,
                    "location_id": location_id,
                    "year": year,
                    "total_population": _num(row.get("TotalPopulation", "")),
                    "total_pop_18plus": _num(row.get("TotalPop18plus", "")),
                }

            if measure_id not in measures:
                measures[measure_id] = {
                    "measure_id": measure_id,
                    "category_id": row["CategoryID"],
                    "measure_name": row.get("Measure", ""),
                    "short_question_text": row.get("Short_Question_Text", ""),
                    "data_value_unit": row.get("Data_Value_Unit", ""),
                    "data_source": row.get("DataSource", ""),
                }
            categories.setdefault(row["CategoryID"], row.get("Category", ""))

    if expected_rows is not None and n != expected_rows:
        print(
            f"FAILED: read {n} rows, expected {expected_rows}. "
            "The export was truncated; refusing to import a partial release.",
            file=sys.stderr,
        )
        sys.exit(1)

    _write(paths["location"], LOCATION_COLUMNS, locations.values())
    _write(
        paths["location_population"], LOCATION_POPULATION_COLUMNS, populations.values()
    )
    _write(paths["measure"], MEASURE_COLUMNS, measures.values())
    _write(
        paths["category"],
        CATEGORY_COLUMNS,
        [{"category_id": k, "category_name": v} for k, v in sorted(categories.items())],
    )

    counts = {
        "measurement": n,
        "location": len(locations),
        "location_population": len(populations),
        "measure": len(measures),
        "category": len(categories),
    }
    return TransformResult(paths=paths, counts=counts)


def _write(path: Path, columns: list[str], rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=columns, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def split_nmf(
    rows: Iterator[dict[str, str]],
    geo_level: str,
    period: str,
    out_dir: Path,
    expected_rows: int | None = None,
) -> TransformResult:
    """Stream a Non-Medical Factors export into normalized CSVs.

    Same shape as split(), against a different source layout. The differences
    that matter, all verified against the full county export:

      * The header spells it `MeasureID`; PLACES spells it `MeasureId`. Reading
        the wrong one raises KeyError rather than corrupting anything, but it
        is the first thing to check when adding a geography.
      * `MOE` replaces the confidence limits, and there are no footnote
        columns.
      * `Data_Value_Type` is always 'Percentage', so it is dropped rather than
        keyed on.
      * TotalPopulation is constant per location, with no year dimension --
        the whole file is one ACS period.
      * Column availability varies by level: place carries no CountyName or
        CountyFIPS, and ZCTA carries no state columns at all. Every optional
        read below therefore goes through .get().
      * County includes a national aggregate row (LocationID '59', StateAbbr
        'US', no geolocation). It is kept -- a national baseline is useful to
        chart against -- but places.derive filters it out of the committed
        county slice, which is 5-digit FIPS only.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "nmf_measurement": out_dir / "nmf_measurement.csv",
        "nmf_location": out_dir / "nmf_location.csv",
        "nmf_location_population": out_dir / "nmf_location_population.csv",
        "measure": out_dir / "measure.csv",
        "category": out_dir / "category.csv",
    }

    locations: dict[str, dict[str, str]] = {}
    populations: dict[str, dict[str, str]] = {}
    measures: dict[str, dict[str, str]] = {}

    n = 0
    with paths["nmf_measurement"].open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=NMF_MEASUREMENT_COLUMNS,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            n += 1
            location_id = row["LocationID"]
            measure_id = row["MeasureID"]

            writer.writerow(
                {
                    "period": period,
                    "geo_level": geo_level,
                    "location_id": location_id,
                    "measure_id": measure_id,
                    "data_value": _num(row["Data_Value"]),
                    "moe": _num(row.get("MOE", "")),
                }
            )

            if location_id not in locations:
                lat, lon = parse_point(row.get("Geolocation", ""))
                locations[location_id] = {
                    "geo_level": geo_level,
                    "location_id": location_id,
                    "state_abbr": row.get("StateAbbr", ""),
                    "state_desc": row.get("StateDesc", ""),
                    "county_name": row.get("CountyName", ""),
                    "county_fips": row.get("CountyFIPS", ""),
                    "location_name": row.get("LocationName", ""),
                    "lat": lat,
                    "lon": lon,
                }
                populations[location_id] = {
                    "period": period,
                    "geo_level": geo_level,
                    "location_id": location_id,
                    "total_population": _num(row.get("TotalPopulation", "")),
                }

            if measure_id not in measures:
                measures[measure_id] = {
                    "measure_id": measure_id,
                    "category_id": row["CategoryID"],
                    "measure_name": row.get("Measure", ""),
                    "short_question_text": row.get("Short_Question_Text", ""),
                    "data_value_unit": row.get("Data_Value_Unit", ""),
                    "data_source": row.get("DataSource", ""),
                }

    if expected_rows is not None and n != expected_rows:
        print(
            f"FAILED: read {n} rows, expected {expected_rows}. "
            "The export was truncated; refusing to import a partial period.",
            file=sys.stderr,
        )
        sys.exit(1)

    _write(paths["nmf_location"], NMF_LOCATION_COLUMNS, locations.values())
    _write(
        paths["nmf_location_population"],
        NMF_LOCATION_POPULATION_COLUMNS,
        populations.values(),
    )
    _write(paths["measure"], MEASURE_COLUMNS, [measures[k] for k in sorted(measures)])
    _write(
        paths["category"],
        CATEGORY_COLUMNS,
        [
            {"category_id": category_id, "category_name": NMF_CATEGORY_NAME}
            for category_id in sorted({m["category_id"] for m in measures.values()})
        ],
    )

    counts = {
        "nmf_measurement": n,
        "nmf_location": len(locations),
        "nmf_location_population": len(populations),
        "measure": len(measures),
        "category": 1,
    }
    return TransformResult(paths=paths, counts=counts)
