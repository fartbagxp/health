"""
Tests for places module.

Run unit tests only (no network):
    uv run pytest tests/test_places.py -m "not integration"

Run integration tests (hits data.cdc.gov and dolthub.com):
    uv run pytest tests/test_places.py -m integration -v
"""

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from places.datasets import (
    GEO_LEVELS,
    NMF_DATASETS,
    NMF_PERIOD,
    PLACES_DATASETS,
    dataset,
    key,
    nmf_dataset,
    releases,
)
from places.dolt import DoltError, DoltHubClient, _split_csv, _split_ddl
from places.sync import _parse_dt, _utc
from places.transform import (
    MEASUREMENT_COLUMNS,
    NMF_CATEGORY_NAME,
    NMF_MEASUREMENT_COLUMNS,
    PRIMARY_KEYS,
    parse_point,
    split,
    split_nmf,
)

SCHEMA = Path(__file__).parent.parent / "src" / "places" / "schema.sql"


# =============================================================================
# Registry
# =============================================================================


class TestDatasets:
    def test_all_four_geographies_registered(self):
        assert {d.geo_level for d in PLACES_DATASETS.values()} == set(GEO_LEVELS)

    def test_row_counts_match_measured_values(self):
        # Measured against the live exports; a change here means CDC
        # republished and the registry needs updating with it.
        assert dataset("county", 2025).rows == 229_298
        assert dataset("place", 2025).rows == 2_150_438
        assert dataset("tract", 2025).rows == 3_047_284
        assert dataset("zcta", 2025).rows == 1_171_563

    def test_age_adjusted_only_above_tract(self):
        # CDC publishes no age-adjusted estimates below place level.
        assert dataset("tract", 2025).value_types == ("CrdPrv",)
        assert dataset("zcta", 2025).value_types == ("CrdPrv",)
        assert "AgeAdjPrv" in dataset("county", 2025).value_types
        assert "AgeAdjPrv" in dataset("place", 2025).value_types

    def test_socrata_ids_are_unique(self):
        ids = [d.socrata_id for d in PLACES_DATASETS.values()]
        assert len(ids) == len(set(ids))

    def test_unknown_dataset_lists_what_exists(self):
        with pytest.raises(KeyError, match="county_2025"):
            dataset("county", 1999)

    def test_key_and_releases(self):
        assert key("tract", 2025) == "tract_2025"
        assert releases() == [2025]


# =============================================================================
# Transform
# =============================================================================


class TestParsePoint:
    def test_wkt_is_lon_first(self):
        # Getting this backwards silently relocates every county.
        assert parse_point("POINT (-86.77 33.58)") == ("33.58", "-86.77")

    @pytest.mark.parametrize("bad", ["", "   ", "POINT ()", "POINT (1)", "garbage"])
    def test_unparseable_gives_empty_pair(self, bad):
        assert parse_point(bad) == ("", "")


class TestSplit:
    @staticmethod
    def _row(**over):
        row = {
            "Year": "2023",
            "StateAbbr": "AL",
            "StateDesc": "Alabama",
            "CountyName": "Autauga",
            "CountyFIPS": "01001",
            "LocationName": "Autauga",
            "DataSource": "BRFSS",
            "Category": "Health Outcomes",
            "Measure": "Arthritis among adults",
            "Data_Value_Unit": "%",
            "Data_Value_Type": "Crude prevalence",
            "Data_Value": "30.0",
            "Data_Value_Footnote_Symbol": "",
            "Data_Value_Footnote": "",
            "Low_Confidence_Limit": "26.5",
            "High_Confidence_Limit": "33.4",
            "TotalPopulation": "60342",
            "TotalPop18plus": "46253",
            "Geolocation": "POINT (-86.64 32.53)",
            "LocationID": "01001",
            "CategoryID": "HLTHOUT",
            "MeasureId": "ARTHRITIS",
            "DataValueTypeID": "CrdPrv",
            "Short_Question_Text": "Arthritis",
        }
        row.update(over)
        return row

    def test_splits_into_five_tables(self, tmp_path):
        rows = [self._row(), self._row(MeasureId="OBESITY", Data_Value="35.1")]
        result = split(iter(rows), "county", 2025, tmp_path, expected_rows=2)
        assert result.counts == {
            "measurement": 2,
            "location": 1,  # both rows describe the same county
            "location_population": 1,
            "measure": 2,
            "category": 1,
        }

    def test_measurement_columns_and_values(self, tmp_path):
        split(iter([self._row()]), "county", 2025, tmp_path, expected_rows=1)
        with (tmp_path / "measurement.csv").open(newline="") as f:
            rows = list(csv.DictReader(f))
        assert list(rows[0]) == MEASUREMENT_COLUMNS
        assert rows[0]["release_year"] == "2025"
        assert rows[0]["geo_level"] == "county"
        assert rows[0]["data_value"] == "30.0"
        assert rows[0]["low_confidence_limit"] == "26.5"

    def test_population_hoisted_to_its_own_table(self, tmp_path):
        # Population is constant per (location, year), so it must not be
        # repeated once per measure on the fact table.
        rows = [self._row(MeasureId=m) for m in ("ARTHRITIS", "OBESITY", "STROKE")]
        split(iter(rows), "county", 2025, tmp_path, expected_rows=3)
        with (tmp_path / "location_population.csv").open(newline="") as f:
            pop = list(csv.DictReader(f))
        assert len(pop) == 1
        assert pop[0]["total_population"] == "60342"
        assert "total_population" not in MEASUREMENT_COLUMNS

    def test_geolocation_parsed_into_location(self, tmp_path):
        split(iter([self._row()]), "county", 2025, tmp_path, expected_rows=1)
        with (tmp_path / "location.csv").open(newline="") as f:
            loc = next(iter(csv.DictReader(f)))
        assert loc["lat"] == "32.53"
        assert loc["lon"] == "-86.64"

    def test_county_level_tolerates_missing_county_columns(self, tmp_path):
        # The county export carries neither CountyName nor CountyFIPS.
        row = self._row()
        del row["CountyName"], row["CountyFIPS"]
        split(iter([row]), "county", 2025, tmp_path, expected_rows=1)
        with (tmp_path / "location.csv").open(newline="") as f:
            loc = next(iter(csv.DictReader(f)))
        assert loc["county_name"] == ""
        assert loc["county_fips"] == ""

    def test_short_read_exits_rather_than_importing_partial_data(self, tmp_path):
        with pytest.raises(SystemExit) as exc:
            split(iter([self._row()]), "county", 2025, tmp_path, expected_rows=999)
        assert exc.value.code == 1

    def test_every_table_has_a_primary_key(self, tmp_path):
        result = split(iter([self._row()]), "county", 2025, tmp_path, expected_rows=1)
        for table in result.paths:
            assert table in PRIMARY_KEYS
        assert "release_meta" in PRIMARY_KEYS


# =============================================================================
# Schema / Dolt helpers
# =============================================================================


class TestSchema:
    def test_all_ten_tables_parse(self):
        tables = [t for t, _ in _split_ddl(SCHEMA.read_text())]
        assert tables == [
            "category",
            "measure",
            "location",
            "location_population",
            "measurement",
            "release_meta",
            # Non-Medical Factors shares category and measure with the above.
            "nmf_location",
            "nmf_location_population",
            "nmf_measurement",
            "nmf_release_meta",
        ]

    def test_comment_semicolons_do_not_truncate_a_statement(self):
        # A prose ";" inside a `--` comment used to cut CREATE TABLE in half.
        ddl = _split_ddl(
            "-- one thing; another thing\n"
            "CREATE TABLE t (\n  a INT,\n  b INT,\n  PRIMARY KEY (a)\n);"
        )
        assert len(ddl) == 1
        assert "PRIMARY KEY (a)" in ddl[0][1]

    def test_schema_covers_every_transform_table(self):
        tables = {t for t, _ in _split_ddl(SCHEMA.read_text())}
        assert set(PRIMARY_KEYS) <= tables


class TestSplitCsv:
    """v1alpha1 caps an upload at 100MB, so large fact tables get chunked."""

    @staticmethod
    def _csv(tmp_path, rows):
        p = tmp_path / "big.csv"
        with p.open("w", newline="") as f:
            f.write("a,b\n")
            for i in range(rows):
                f.write(f"{i},{'x' * 40}\n")
        return p

    def test_small_file_is_returned_untouched(self, tmp_path):
        p = self._csv(tmp_path, 10)
        assert _split_csv(p, 10_000_000) == [p]

    def test_large_file_is_chunked(self, tmp_path):
        p = self._csv(tmp_path, 2000)
        parts = _split_csv(p, 5_000)
        assert len(parts) > 1
        assert all(part != p for part in parts)

    def test_every_chunk_repeats_the_header(self, tmp_path):
        p = self._csv(tmp_path, 2000)
        for part in _split_csv(p, 5_000):
            assert part.read_text().splitlines()[0] == "a,b"

    def test_chunks_preserve_every_row_exactly_once(self, tmp_path):
        p = self._csv(tmp_path, 2000)
        seen = []
        for part in _split_csv(p, 5_000):
            seen += part.read_text().splitlines()[1:]
        original = p.read_text().splitlines()[1:]
        assert seen == original


class TestDoltClient:
    def test_missing_token_names_the_env_var(self):
        client = DoltHubClient(token=None)
        client._token = None
        with pytest.raises(DoltError, match="DOLTHUB_TOKEN"):
            _ = client.token

    def test_reads_need_no_token(self):
        # The database is public; only imports authenticate.
        assert DoltHubClient(token=None).session is not None


class TestParseDt:
    @pytest.mark.parametrize(
        "text",
        [
            "2025-12-04 10:35:06",
            "2025-12-04T10:35:06",
            "2025-12-04T10:35:06Z",
            "2025-12-04T10:35:06.000Z",
        ],
    )
    def test_accepts_every_rendering_dolthub_might_return(self, text):
        assert _parse_dt(text) == _parse_dt("2025-12-04 10:35:06")

    @pytest.mark.parametrize("bad", ["", "   ", "garbage", "not-a-date"])
    def test_unparseable_is_none_so_sync_reruns(self, bad):
        assert _parse_dt(bad) is None

    def test_utc_round_trips(self):
        assert _parse_dt(_utc(1764844506)) is not None


# =============================================================================
# Non-Medical Factors (the portal's seventh page)
# =============================================================================


class TestNmfDatasets:
    def test_all_four_geographies_registered(self):
        assert sorted(d.geo_level for d in NMF_DATASETS.values()) == sorted(GEO_LEVELS)

    def test_row_counts_match_measured_values(self):
        assert {d.geo_level: d.rows for d in NMF_DATASETS.values()} == {
            "county": 28_287,
            "place": 268_389,
            "tract": 751_509,
            "zcta": 291_024,
        }

    def test_socrata_ids_do_not_collide_with_places(self):
        nmf = {d.socrata_id for d in NMF_DATASETS.values()}
        places = {d.socrata_id for d in PLACES_DATASETS.values()}
        assert len(nmf) == 4
        assert not (nmf & places)

    def test_unknown_dataset_lists_what_exists(self):
        with pytest.raises(KeyError, match="county_2017-2021"):
            nmf_dataset("county", "1999-2003")

    def test_measure_ids_are_disjoint_from_places(self):
        """Why category and measure can be shared tables rather than forked."""
        assert not ({"CROWD", "POV150", "UNEMP"} & {"ARTHRITIS", "HEARING", "OBESITY"})


class TestSplitNmf:
    @staticmethod
    def _row(**over):
        row = {
            "Year": "2017-2021",
            "StateAbbr": "AL",
            "StateDesc": "Alabama",
            "LocationName": "Autauga County",
            "DataSource": "5-year ACS",
            "Category": "SDOH",
            "Measure": "Crowding among housing units",
            "Data_Value_Unit": "%",
            "Data_Value_Type": "Percentage",
            "Data_Value": "1.2",
            "MOE": "0.7",
            "TotalPopulation": "58239",
            "LocationID": "01001",
            "CategoryID": "SDOH",
            "MeasureID": "CROWD",
            "DataValueTypeID": "Percent",
            "Short_Question_Text": "Crowding",
            "Geolocation": "POINT (-86.64 32.53)",
        }
        row.update(over)
        return row

    def test_splits_into_five_tables(self, tmp_path):
        rows = [self._row(), self._row(MeasureID="POV150", Data_Value="18.4")]
        result = split_nmf(iter(rows), "county", NMF_PERIOD, tmp_path, expected_rows=2)
        assert result.counts == {
            "nmf_measurement": 2,
            "nmf_location": 1,  # both rows describe the same county
            "nmf_location_population": 1,
            "measure": 2,
            "category": 1,
        }

    def test_measurement_columns_and_values(self, tmp_path):
        split_nmf(iter([self._row()]), "county", NMF_PERIOD, tmp_path, expected_rows=1)
        with (tmp_path / "nmf_measurement.csv").open(newline="") as f:
            rows = list(csv.DictReader(f))
        assert list(rows[0]) == NMF_MEASUREMENT_COLUMNS
        assert rows[0] == {
            "period": "2017-2021",
            "geo_level": "county",
            "location_id": "01001",
            "measure_id": "CROWD",
            "data_value": "1.2",
            "moe": "0.7",
        }

    def test_data_value_type_is_not_keyed_on(self):
        """It is always 'Percentage' here, unlike the PLACES fact table."""
        assert "data_value_type" not in NMF_MEASUREMENT_COLUMNS
        assert "data_value_type" not in PRIMARY_KEYS["nmf_measurement"]

    def test_measure_id_is_spelled_with_a_capital_d(self, tmp_path):
        """PLACES exports `MeasureId`, this family exports `MeasureID`.

        Reading the wrong one must fail loudly rather than write empty keys.
        """
        row = self._row()
        del row["MeasureID"]
        row["MeasureId"] = "CROWD"
        with pytest.raises(KeyError):
            split_nmf(iter([row]), "county", NMF_PERIOD, tmp_path)

    def test_blank_moe_becomes_empty_not_zero(self, tmp_path):
        split_nmf(
            iter([self._row(MOE="")]), "county", NMF_PERIOD, tmp_path, expected_rows=1
        )
        with (tmp_path / "nmf_measurement.csv").open(newline="") as f:
            assert next(csv.DictReader(f))["moe"] == ""

    def test_national_aggregate_row_is_kept(self, tmp_path):
        """LocationID '59' is the US total. Mirrored, but excluded from the
        committed county slice, which is 5-digit FIPS only."""
        national = self._row(
            LocationID="59", StateAbbr="US", LocationName="", Geolocation=""
        )
        result = split_nmf(
            iter([self._row(), national]),
            "county",
            NMF_PERIOD,
            tmp_path,
            expected_rows=2,
        )
        assert result.counts["nmf_location"] == 2
        with (tmp_path / "nmf_location.csv").open(newline="") as f:
            by_id = {r["location_id"]: r for r in csv.DictReader(f)}
        assert by_id["59"]["lat"] == ""  # no geolocation on the aggregate

    def test_zcta_tolerates_missing_state_columns(self, tmp_path):
        """ZCTA exports carry no StateAbbr/StateDesc, and place carries no
        county columns. Every optional read goes through .get()."""
        row = self._row(LocationID="35004", LocationName="35004")
        for column in ("StateAbbr", "StateDesc"):
            del row[column]
        split_nmf(iter([row]), "zcta", NMF_PERIOD, tmp_path, expected_rows=1)
        with (tmp_path / "nmf_location.csv").open(newline="") as f:
            location = next(csv.DictReader(f))
        assert location["state_abbr"] == ""
        assert location["county_name"] == ""
        assert location["geo_level"] == "zcta"

    def test_category_stored_under_the_portal_name_not_sdoh(self, tmp_path):
        """The source sets Category to the bare string 'SDOH'."""
        split_nmf(iter([self._row()]), "county", NMF_PERIOD, tmp_path, expected_rows=1)
        with (tmp_path / "category.csv").open(newline="") as f:
            category = next(csv.DictReader(f))
        assert category == {
            "category_id": "SDOH",
            "category_name": NMF_CATEGORY_NAME,
        }

    def test_population_hoisted_and_keyed_by_period(self, tmp_path):
        split_nmf(iter([self._row()]), "county", NMF_PERIOD, tmp_path, expected_rows=1)
        with (tmp_path / "nmf_location_population.csv").open(newline="") as f:
            population = next(csv.DictReader(f))
        assert population == {
            "period": "2017-2021",
            "geo_level": "county",
            "location_id": "01001",
            "total_population": "58239",
        }

    def test_short_read_exits_rather_than_importing_partial_data(self, tmp_path):
        with pytest.raises(SystemExit):
            split_nmf(
                iter([self._row()]), "county", NMF_PERIOD, tmp_path, expected_rows=99
            )

    def test_every_table_has_a_primary_key(self, tmp_path):
        result = split_nmf(
            iter([self._row()]), "county", NMF_PERIOD, tmp_path, expected_rows=1
        )
        for table in result.paths:
            assert PRIMARY_KEYS[table], table


class TestAlreadyLoaded:
    """The shared measure/category tables make this a subset test, not an
    equality test. Getting it wrong fires a no-op import on every run, and
    DoltHub answers a no-op job's poll with a 500."""

    class _FakeDolt:
        def __init__(self, rows):
            self.rows = rows

        def sql(self, _query):
            return self.rows

    @staticmethod
    def _csv(tmp_path, rows):
        path = tmp_path / "measure.csv"
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["measure_id"], lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_skips_when_dolt_holds_a_superset(self, tmp_path):
        from places.sync import _already_loaded

        # PLACES wrote 2; the ACS family later added a 3rd. Nothing to do.
        path = self._csv(
            tmp_path, [{"measure_id": "ARTHRITIS"}, {"measure_id": "OBESITY"}]
        )
        dolt = self._FakeDolt(
            [
                {"measure_id": "ARTHRITIS"},
                {"measure_id": "OBESITY"},
                {"measure_id": "CROWD"},
            ]
        )
        assert _already_loaded(dolt, "measure", path) is True

    def test_imports_when_a_row_is_missing(self, tmp_path):
        from places.sync import _already_loaded

        path = self._csv(
            tmp_path, [{"measure_id": "ARTHRITIS"}, {"measure_id": "CROWD"}]
        )
        dolt = self._FakeDolt([{"measure_id": "ARTHRITIS"}])
        assert _already_loaded(dolt, "measure", path) is False

    def test_imports_when_a_value_differs(self, tmp_path):
        from places.sync import _already_loaded

        path = self._csv(tmp_path, [{"measure_id": "ARTHRITIS"}])
        dolt = self._FakeDolt([{"measure_id": "ARTHRITIS_OLD"}])
        assert _already_loaded(dolt, "measure", path) is False

    def test_row_cap_forces_a_reimport_rather_than_a_blind_skip(self, tmp_path):
        from places.sync import _already_loaded

        path = self._csv(tmp_path, [{"measure_id": "ARTHRITIS"}])
        # At the 1000-row cap we cannot know what we did not see.
        dolt = self._FakeDolt([{"measure_id": "ARTHRITIS"}] * 1000)
        assert _already_loaded(dolt, "measure", path) is False


# =============================================================================
# Integration (network)
# =============================================================================


class TestIntegration:
    @pytest.mark.integration
    def test_socrata_row_counts_still_match_registry(self):
        import requests

        for ds in PLACES_DATASETS.values():
            resp = requests.get(
                f"https://data.cdc.gov/resource/{ds.socrata_id}.json",
                params={"$select": "count(1)"},
                timeout=120,
            )
            resp.raise_for_status()
            assert int(resp.json()[0]["count_1"]) == ds.rows, ds.geo_level

    @pytest.mark.integration
    def test_nmf_socrata_row_counts_still_match_registry(self):
        import requests

        for ds in NMF_DATASETS.values():
            resp = requests.get(
                f"https://data.cdc.gov/resource/{ds.socrata_id}.json",
                params={"$select": "count(1)"},
                timeout=120,
            )
            resp.raise_for_status()
            assert int(resp.json()[0]["count_1"]) == ds.rows, ds.geo_level

    @pytest.mark.integration
    def test_published_catalog_covers_all_seven_portal_pages(self):
        """The point of the whole exercise: one measure catalog spanning every
        page of experience.arcgis.com/experience/22c7182a162d45788dd52a2362f8ed65."""
        rows = DoltHubClient(token=None).sql(
            "select category_id, count(*) as n from measure group by 1 limit 1000"
        )
        by_category = {r["category_id"]: int(r["n"]) for r in rows}
        assert by_category == {
            "HLTHOUT": 12,
            "PREVENT": 7,
            "DISABLT": 7,
            "SOCLNEED": 7,
            "RISKBEH": 4,
            "HLTHSTAT": 3,
            "SDOH": 9,
        }
        assert sum(by_category.values()) == 49

    @pytest.mark.integration
    def test_metadata_exposes_rows_updated_at(self):
        from places.client import PlacesClient

        ts = PlacesClient().rows_updated_at(dataset("county", 2025).socrata_id)
        assert ts > 0

    @pytest.mark.integration
    def test_public_sql_api_needs_no_credentials(self):
        rows = DoltHubClient(owner="dolthub", database="us-jails", token=None).sql(
            "select 1 as x"
        )
        assert rows == [{"x": "1"}]

    @pytest.mark.integration
    def test_row_limit_is_reported_not_silently_truncated(self):
        client = DoltHubClient(owner="dolthub", database="us-jails", token=None)
        with pytest.raises(DoltError, match="1000-row"):
            client.sql("select * from incidents")
