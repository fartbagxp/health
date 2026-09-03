# CDC PLACES

Small-area estimates of 49 health and social measures for every US county,
place, census tract and ZIP Code tabulation area.

CDC's [PLACES data portal](https://experience.arcgis.com/experience/22c7182a162d45788dd52a2362f8ed65)
has seven pages. This module mirrors all seven:

| Category                    | `categoryid` | Measures | Source     |
| --------------------------- | ------------ | -------- | ---------- |
| Health Outcomes             | `HLTHOUT`    | 12       | BRFSS      |
| Prevention                  | `PREVENT`    | 7        | BRFSS      |
| Disability                  | `DISABLT`    | 7        | BRFSS      |
| Health-Related Social Needs | `SOCLNEED`   | 7        | BRFSS      |
| Health Risk Behaviors       | `RISKBEH`    | 4        | BRFSS      |
| Health Status               | `HLTHSTAT`   | 3        | BRFSS      |
| Non-Medical Factors         | `SDOH`       | 9        | 5-year ACS |

Health Outcomes covers arthritis, current asthma, high blood pressure, cancer,
coronary heart disease, COPD, depression, diabetes, high cholesterol, obesity,
stroke and all teeth lost. Disability covers hearing, vision, cognitive,
mobility, self-care and independent-living disability, plus any disability.
`data/processed/places/measures.csv` is the full catalog.

The first six categories are one CDC product — PLACES proper, modeled from
BRFSS — and the seventh is a separate one, "Non-Medical Factor Measures",
derived from the American Community Survey. Eight Socrata datasets in all. The
two families share a measure catalog but keep separate fact tables; see
[Two families](#two-families) for why they cannot merge.

That portal is a viewer built on ArcGIS, not a data source — it has nothing to
scrape. The authoritative tables live on `data.cdc.gov`, and that is what this
module reads.

## Why PLACES lives in Dolt, not git

| Geography    | PLACES ID   | Rows      | Export  | Non-Medical ID | Rows    |
| ------------ | ----------- | --------- | ------- | -------------- | ------- |
| County       | `swc5-untb` | 229,298   | 53 MB   | `i6u4-y3g4`    | 28,287  |
| Place        | `eav7-hnsx` | 2,150,438 | ~460 MB | `edkk-ze78`    | 268,389 |
| Census tract | `cwsq-ngmh` | 3,047,284 | 694 MB  | `e539-uadk`    | 751,509 |
| ZCTA         | `qnzd-25i4` | 1,171,563 | 224 MB  | `bumh-rgsq`    | 291,024 |

Together that is ~7.9M rows and ~1.7 GB. The census-tract file alone is past
GitHub's 100 MB hard limit, and `data/` in this repo is already 291 MB with a
131 MB `.git`. Committing this would break the repository.

So PLACES is mirrored into the public Dolt database
[`fartbagxp/cdc-places`](https://www.dolthub.com/repositories/fartbagxp/cdc-places)
— free at any size, versioned and diffable the way this project already thinks
about data — and only small derived slices are committed here.

> **The mirror is ours, not CDC's.** DoltHub is a commercial service run by
> DoltHub Inc., unaffiliated with CDC. `fartbagxp/cdc-places` is a copy this
> project maintains; CDC neither publishes nor endorses it. For authoritative
> data, cite `data.cdc.gov` and the Socrata dataset IDs above.

## Two families

The portal's seven pages are two CDC products, and they do not merge cleanly.
The six BRFSS categories share `measurement`; Non-Medical Factors gets
`nmf_measurement`, `nmf_location` and `nmf_location_population`. What forced
the split, all measured against the full county exports:

- **Different geography vintage.** ACS 2017-2021 still uses Connecticut's
  retired county FIPS `09001`—`09015`; PLACES 2025 uses the new planning
  regions `09110`—`09190`. Same land, different units. **A county map built
  from one family's FIPS will have holes in Connecticut for the other.** This
  is the one difference that can produce a wrong chart rather than an ugly one.
- **Different county names.** `Autauga County` here, `Autauga` in PLACES, on
  3,131 of the 3,133 counties both families cover. Harmless when joining on
  FIPS, visible in labels.
- **Different uncertainty column.** A margin of error, not low/high confidence
  limits.
- **Different version key.** An ACS period string (`2017-2021`), not a release
  year — which is also why there are two ledger tables, `release_meta` and
  `nmf_release_meta`.
- **Different value semantics.** One `Data_Value_Type` (`Percentage`) rather
  than crude and age-adjusted, so it is not part of the fact table's key.
- **Different population denominators.** Jefferson County, AL is 662,895 in
  PLACES 2025 and 672,550 in ACS 2017-2021. Both are correct for their vintage,
  so do not use one family's `totalpopulation` to weight the other's values
  — `state_rollup.csv` and `nmf_state_rollup.csv` are each weighted by their
  own.

What they _do_ share is `category` and `measure`. The nine ACS measure IDs do
not collide with PLACES' forty, so one 49-row catalog spans all seven pages,
and `data_source` (`BRFSS` vs `5-year ACS`) or `category_id = 'SDOH'`
separates them:

```sql
SELECT category_id, count(*) FROM measure GROUP BY 1;  -- 7 categories, 49 measures
```

## What health-charts plots

Every page of the portal is chartable at county level from committed CSVs, with
no DoltHub call at all:

| Portal page                 | `categoryid` | County file                              |
| --------------------------- | ------------ | ---------------------------------------- |
| Health Outcomes             | `HLTHOUT`    | `county_crude.csv` / `county_ageadj.csv` |
| Prevention                  | `PREVENT`    | `county_crude.csv` / `county_ageadj.csv` |
| Health Risk Behaviors       | `RISKBEH`    | `county_crude.csv` / `county_ageadj.csv` |
| Health Status               | `HLTHSTAT`   | `county_crude.csv` / `county_ageadj.csv` |
| Disability                  | `DISABLT`    | `county_crude.csv` / `county_ageadj.csv` |
| Health-Related Social Needs | `SOCLNEED`   | `county_crude.csv` / `county_ageadj.csv` |
| Non-Medical Factors         | `SDOH`       | `nmf_county.csv`                         |

Filter by `measureid`; join `measures.csv` on `measureid` for labels, units and
the category a measure belongs to. `state_rollup.csv` and
`nmf_state_rollup.csv` give population-weighted state means for the same
measures, for a state-level view without re-aggregating in the browser.

Below county — place, census tract, ZCTA — is Dolt-only, and that is where
the query limits below start to matter.

## The two tiers

**Committed CSVs** (`data/processed/places/`) serve anything that needs the
whole country at once:

| File                   | Rows    | Size   | Family      |
| ---------------------- | ------- | ------ | ----------- |
| `county_crude.csv`     | 114,576 | 4.1 MB | PLACES      |
| `county_ageadj.csv`    | 114,576 | 4.1 MB | PLACES      |
| `state_rollup.csv`     | 3,814   | 122 KB | PLACES      |
| `nmf_county.csv`       | 28,278  | 1.3 MB | Non-Medical |
| `nmf_state_rollup.csv` | 459     | 10 KB  | Non-Medical |
| `measures.csv`         | 49      | 5 KB   | both        |

`nmf_county.csv` adds a `moe` column — the ACS family reports a margin of
error rather than confidence limits — but its first six columns match
`county_crude.csv` exactly, so a chart that ignores the seventh reads both the
same way. Both county files drop the national aggregate row, which stays
queryable in Dolt.

`county_crude.csv` uses the same six columns as the older
`data/processed/cdc_open/places_county.csv` and is a strict superset of it — all
40 measures rather than 8, plus the age-adjusted companion.

**Live SQL** covers drill-down. The DoltHub API sends CORS headers and needs no
key, so health-charts can query it straight from the browser:

```
https://www.dolthub.com/api/v1alpha1/fartbagxp/cdc-places/main?q=<urlencoded>
```

Two limits shape every query, both measured against the live database:

- **1000 rows per response**, reported as a `RowLimit` status rather than an
  error, so every query needs an explicit `LIMIT`.
- **A query deadline of roughly 55 seconds**, after which the API returns
  `context deadline exceeded`. This is the one that bites: it is entirely
  possible to write a correct query against 6.6M rows that simply never
  returns.

### Query shapes that work

The fact table's primary key is
`(release_year, geo_level, location_id, measure_id, data_value_type, year)`.
Anything that hits a prefix of it is a fast range scan:

```sql
-- One county's full profile. 40 rows, ~0.3s.
SELECT measure_id, data_value, low_confidence_limit, high_confidence_limit
FROM measurement
WHERE release_year=2025 AND geo_level='county' AND location_id='01073'
  AND data_value_type='CrdPrv';

-- One census tract. 40 rows, ~0.3s.
SELECT measure_id, data_value FROM measurement
WHERE release_year=2025 AND geo_level='tract' AND location_id='01073010900';

-- Every tract in a county, by PK prefix. 189 rows, ~0.1s.
SELECT location_id, location_name, lat, lon FROM location
WHERE geo_level='tract' AND location_id LIKE '01073%' LIMIT 1000;
```

`nmf_measurement` is keyed `(period, geo_level, location_id, measure_id)` and
behaves the same way:

```sql
-- One county's 9 non-medical factors. 0.4s.
SELECT measure_id, data_value, moe FROM nmf_measurement
WHERE period='2017-2021' AND geo_level='county' AND location_id='01073';

-- One census tract. 0.5s.
SELECT measure_id, data_value FROM nmf_measurement
WHERE period='2017-2021' AND geo_level='tract' AND location_id='01073010900';

-- Every county for one measure, via idx_nmf_measurement_slice. 1.0s.
SELECT location_id, data_value FROM nmf_measurement
WHERE period='2017-2021' AND geo_level='county' AND measure_id='POV150'
LIMIT 1000;
```

The dimension tables are small enough to fetch whole (~0.1s each), which is how
labels should be resolved:

```sql
SELECT * FROM measure;    -- 49 rows, all 7 categories
SELECT * FROM category;   -- 7 rows
```

### Two shapes to avoid

**Never join against `measurement`.** The obvious query — joining `measure` to
get a readable label — reliably exceeds the deadline even when the fact-table
side is a fast 40-row PK lookup:

```sql
-- TIMES OUT (54.5s measured), despite the WHERE matching a PK prefix.
SELECT m.short_question_text, f.data_value
FROM measurement f JOIN measure m USING (measure_id)
WHERE f.release_year=2025 AND f.geo_level='county' AND f.location_id='01073';
```

Fetch the 49-row `measure` table once and join client-side instead — or just
read the committed `measures.csv`, which is already there for exactly this.

This one is about size, not shape. The identical join against
`nmf_measurement` returns in **0.5s**, because that table holds 1.34M rows
rather than 6.6M. So the honest rule is: joining a fact table is fine until it
is a few million rows, and there is no warning when you cross the line — the
query simply stops returning. Resolving labels client-side works at every size,
which is why it is the standing advice for both tables.

**Do not combine `geo_level` with a secondary-index column.** Mixing the
primary key's leading column with an indexed non-key column produces a bad
plan, on a table of only 149k rows:

```sql
-- TIMES OUT (>54s)
SELECT location_id FROM location WHERE geo_level='tract' AND county_fips='01073';

-- 0.3s, same 189 rows
SELECT location_id FROM location WHERE county_fips='01073' LIMIT 1000;
```

Both indexes exist and are correct (`SHOW CREATE TABLE` confirms it); this is
the query planner, not the schema. It reproduces exactly on `nmf_location`
(54.3s vs 0.8s for the same 189 rows), so treat it as a property of the API's
planner rather than of either table.

## Schema

`measurement` is the fact table, keyed
`(release_year, geo_level, location_id, measure_id, data_value_type, year)`.
`location`, `location_population`, `measure` and `category` are dimensions.

Eleven of the source's twenty-four columns repeat identically on every row.
Verified against the full exports: population is constant per
`(location, year)` — zero violations across all 229,298 county rows — and
geolocation is constant per location. Hoisting them into dimensions takes the
fact table from ~239 bytes/row to about 45.

Two asymmetries the schema has to carry: county-level exports have no
`CountyName`/`CountyFIPS` column, and age-adjusted prevalence exists only at
county and place level — tract and ZCTA are crude-only.

`nmf_measurement` is the second fact table, keyed
`(period, geo_level, location_id, measure_id)`, with `nmf_location` and
`nmf_location_population` beside it and `nmf_release_meta` as its ledger. It
carries its own asymmetries: place has no county columns (PLACES place does),
and ZCTA has no state columns at all. Population is constant per location with
no year dimension — zero violations across all 28,287 county rows — since
the whole file is one ACS period.

## Usage

```bash
uv run python -m places list                  # the registry, both families
uv run python -m places status                # has CDC published newer data than the mirror has?
uv run python -m places sync --geo county     # mirror one PLACES geography
uv run python -m places sync --all --family nmf    # mirror Non-Medical Factors
uv run python -m places sync --all --family both   # all seven portal pages
uv run python -m places derive                # rebuild the committed CSVs
uv run python -m places query "select count(*) from measurement"
```

`--family` defaults to `places` — the six BRFSS categories. `derive` always
rebuilds both families' slices, since it reads the two county exports directly
from Socrata and they cost about ten seconds together.

`sync` needs `DOLTHUB_TOKEN`; reads need nothing.

## Scheduling

`update_places.yml` runs monthly (1st, 17:00 UTC) rather than weekly, because
both products are annual at best — the four 2025 PLACES datasets were last
updated in December 2025, and the Non-Medical Factors datasets have not moved
since November 2023. `sync` compares Socrata's `rowsUpdatedAt` against the
matching ledger table before downloading, so a run against unchanged data costs
one metadata request per leg and transfers nothing.

The matrix is `family` × `geo` — eight legs — with `max-parallel: 1`,
because DoltHub runs one import job per database at a time.

## How the import actually works

Worth knowing before changing `dolt.py`, because none of it is obvious:

- **v1alpha1, not v2.** The v2 REST API documents a nicer import (pre-signed
  multipart, no size cap) but rejects tokens from
  `dolthub.com/settings/tokens` with 401 `no token found for given API token` —
  verified with two independently generated tokens, scoped and unscoped, across
  `/user`, `/databases/{o}/{d}`, `/branches` and `/imports/uploads`. The same
  tokens authenticate v1alpha1 fine.
- **The `token` scheme, not `Bearer`.** `authorization: token <TOKEN>`.
- **`fileName` is required** in the upload `params`. Omitting it fails with an
  opaque upstream 400 that says nothing about the missing field.
- **An upload opens a pull request; it does not write to the branch.** The job
  reports success, a PR appears, and the table stays empty until that PR is
  merged. `import_csv` merges it.
- **100MB per upload.** The tract fact table is ~137MB, so large files are
  split into chunks. Every import is an upsert on the primary key, so chunking
  changes nothing about the result.
- **One import job per database at a time.** Concurrent imports fail with
  "cleaning up existing job, please wait a few minutes then try again", which is
  why the workflow matrix sets `max-parallel: 1`.
- **`release_year`, not `release`.** RELEASE is a reserved word in MySQL/Dolt
  and will not parse as a bare column name.

A county sync takes about three minutes, most of it waiting on server-side
import and merge jobs rather than transferring data.

## A note for anyone extending the fetch code

Use the bulk export endpoint (`/api/views/{id}/rows.csv?accessType=DOWNLOAD`),
not paged SoQL. One 50,000-row page of the tract dataset via `$offset` took
**435 seconds**; the entire 694 MB file via the export endpoint took **94.6**.

And `$where` is silently ignored on the export endpoint — a filtered request
returned all 229,299 county rows, identical to unfiltered. It fails open, so
filtering happens client-side.
