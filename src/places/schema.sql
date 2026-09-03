-- CDC PLACES -- normalized schema for fartbagxp/cdc-places on DoltHub.
--
-- The published long format repeats eleven of its twenty-four columns on every
-- row. Hoisting those into dimensions takes the fact table from ~239 bytes/row
-- to roughly 45 and makes the database join-able. See places/transform.py for
-- the evidence behind each split.
--
-- `release_year` is part of every measurement key so that backfilling an older
-- PLACES release is a pure insert, and so re-importing a release upserts
-- rather than duplicating. (It is `release_year`, not `release`: RELEASE is a
-- reserved word in MySQL/Dolt and will not parse as a bare column name.)

CREATE TABLE category (
  category_id   VARCHAR(12)  NOT NULL,
  category_name VARCHAR(64)  NOT NULL,
  PRIMARY KEY (category_id)
);

CREATE TABLE measure (
  measure_id          VARCHAR(16)  NOT NULL,
  category_id         VARCHAR(12)  NOT NULL,
  measure_name        VARCHAR(128) NOT NULL,
  short_question_text VARCHAR(64)  NOT NULL,
  data_value_unit     VARCHAR(8),
  data_source         VARCHAR(16),
  PRIMARY KEY (measure_id),
  KEY idx_measure_category (category_id)
);

CREATE TABLE location (
  geo_level     ENUM('county','place','tract','zcta') NOT NULL,
  location_id   VARCHAR(12) NOT NULL,
  state_abbr    CHAR(2),
  state_desc    VARCHAR(32),
  -- County-level exports carry neither of these; the other three levels do.
  county_name   VARCHAR(64),
  county_fips   CHAR(5),
  location_name VARCHAR(96),
  -- Parsed from the source's WKT POINT, which orders longitude first.
  lat           DECIMAL(9,6),
  lon           DECIMAL(9,6),
  PRIMARY KEY (geo_level, location_id),
  KEY idx_location_state (state_abbr),
  KEY idx_location_county (county_fips)
);

-- TotalPopulation / TotalPop18plus are constant per (LocationID, Year) --
-- verified with zero violations across all 229,298 county rows -- so they
-- describe a place, not a measurement.
CREATE TABLE location_population (
  geo_level        ENUM('county','place','tract','zcta') NOT NULL,
  location_id      VARCHAR(12) NOT NULL,
  year             SMALLINT NOT NULL,
  total_population INT,
  total_pop_18plus INT,
  PRIMARY KEY (geo_level, location_id, year)
);

-- County and place carry both crude and age-adjusted prevalence; tract and
-- ZCTA are crude-only, as CDC publishes no age-adjusted estimates below place.
CREATE TABLE measurement (
  release_year          SMALLINT NOT NULL,
  geo_level             ENUM('county','place','tract','zcta') NOT NULL,
  location_id           VARCHAR(12) NOT NULL,
  measure_id            VARCHAR(16) NOT NULL,
  data_value_type       ENUM('CrdPrv','AgeAdjPrv') NOT NULL,
  year                  SMALLINT NOT NULL,
  data_value            DECIMAL(5,1),
  low_confidence_limit  DECIMAL(5,1),
  high_confidence_limit DECIMAL(5,1),
  footnote_symbol       VARCHAR(4),
  PRIMARY KEY (release_year, geo_level, location_id, measure_id, data_value_type, year),
  KEY idx_measurement_slice (release_year, geo_level, measure_id),
  KEY idx_measurement_measure (measure_id, year)
);

-- What has been ingested, so a scheduled run can skip a release CDC has not
-- republished. `rows_updated_at` mirrors Socrata's own change timestamp.
CREATE TABLE release_meta (
  release_year    SMALLINT NOT NULL,
  geo_level       ENUM('county','place','tract','zcta') NOT NULL,
  socrata_id      CHAR(9)  NOT NULL,
  rows_updated_at DATETIME NOT NULL,
  row_count       INT      NOT NULL,
  ingested_at     DATETIME NOT NULL,
  PRIMARY KEY (release_year, geo_level)
);

-- ── Non-Medical Factors (ACS) ───────────────────────────────────────────────
--
-- The seventh page of CDC's PLACES portal is a separate product: nine
-- social-determinant measures derived from the 5-year American Community
-- Survey. It cannot share `measurement` (margin of error instead of
-- confidence limits, a period string instead of a year) and it cannot share
-- `location` (ACS 2017-2021 still uses Connecticut's retired county FIPS,
-- while PLACES 2025 uses the new planning regions, and county names carry a
-- ' County' suffix here that PLACES omits).
--
-- It DOES share `category` and `measure`. The nine measure IDs do not collide
-- with PLACES' forty, so one measure catalog covers all seven portal pages,
-- distinguishable by data_source ('5-year ACS' vs 'BRFSS') or by
-- category_id = 'SDOH'. The source sets both Category and CategoryID to the
-- bare string 'SDOH'; it is stored as 'Non-Medical Factors', the name CDC's
-- own dataset titles and portal page use.

CREATE TABLE nmf_location (
  geo_level     ENUM('county','place','tract','zcta') NOT NULL,
  location_id   VARCHAR(12) NOT NULL,
  -- ZCTA-level exports carry no state columns; place carries no county ones.
  state_abbr    CHAR(2),
  state_desc    VARCHAR(32),
  county_name   VARCHAR(64),
  county_fips   CHAR(5),
  location_name VARCHAR(96),
  lat           DECIMAL(9,6),
  lon           DECIMAL(9,6),
  PRIMARY KEY (geo_level, location_id),
  KEY idx_nmf_location_state (state_abbr),
  KEY idx_nmf_location_county (county_fips)
);

-- TotalPopulation is constant per location -- zero violations across all
-- 28,287 county rows. Keyed by period because a later ACS vintage will restate
-- it.
CREATE TABLE nmf_location_population (
  period           VARCHAR(9) NOT NULL,
  geo_level        ENUM('county','place','tract','zcta') NOT NULL,
  location_id      VARCHAR(12) NOT NULL,
  total_population INT,
  PRIMARY KEY (period, geo_level, location_id)
);

-- Data_Value_Type is always 'Percentage' in this family, so unlike
-- `measurement` it is not part of the key.
CREATE TABLE nmf_measurement (
  period      VARCHAR(9) NOT NULL,
  geo_level   ENUM('county','place','tract','zcta') NOT NULL,
  location_id VARCHAR(12) NOT NULL,
  measure_id  VARCHAR(16) NOT NULL,
  data_value  DECIMAL(5,1),
  moe         DECIMAL(5,1),
  PRIMARY KEY (period, geo_level, location_id, measure_id),
  KEY idx_nmf_measurement_slice (period, geo_level, measure_id)
);

-- Separate from release_meta: PLACES versions by annual release year, this
-- family by ACS period, and the two would collide in one integer-keyed table.
CREATE TABLE nmf_release_meta (
  period          VARCHAR(9) NOT NULL,
  geo_level       ENUM('county','place','tract','zcta') NOT NULL,
  socrata_id      CHAR(9)  NOT NULL,
  rows_updated_at DATETIME NOT NULL,
  row_count       INT      NOT NULL,
  ingested_at     DATETIME NOT NULL,
  PRIMARY KEY (period, geo_level)
);
