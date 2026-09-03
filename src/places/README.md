# `places` — CDC PLACES

Small-area estimates of 49 measures for every US county, place, census tract
and ZCTA — all seven pages of CDC's PLACES portal.

Two families, because the portal is two CDC products. **PLACES proper** is 40
BRFSS-modeled measures in six categories: Health Outcomes, Prevention, Health
Risk Behaviors, Health Status, Disability, and Health-Related Social Needs.
**Non-Medical Factors** is 9 more, derived from the 5-year ACS. They share the
`measure` and `category` dimensions and keep separate fact tables; `datasets.py`
documents why they cannot merge (different Connecticut geography vintage,
different uncertainty column, different version key).

## Why this module is different

Every other archive in this repo commits its CSVs to git. PLACES cannot: the
eight datasets are ~7.9M rows / ~1.7GB, and the census-tract export alone is
694MB — past GitHub's 100MB hard limit.

So the data goes to the public Dolt database
[`fartbagxp/cdc-places`](https://www.dolthub.com/repositories/fartbagxp/cdc-places),
and only small derived slices are committed under `data/processed/places/`.

## Two things worth knowing before changing the fetch code

**Use the bulk export endpoint, not paged SoQL.** `cdc_open.download`'s
`$offset` pagination took **435 seconds for a single 50,000-row page** of the
tract dataset, and Socrata's `$offset` degrades as the offset grows. The export
endpoint pulled the whole 694MB file in **94.6 seconds**. That is why
`client.py` does not reuse `_fetch_csv_paginated()`.

**`$where` is silently ignored on the export endpoint.** Asking for one state
returned all 229,299 county rows, byte-identical to unfiltered. It fails open,
so all filtering happens client-side in `transform.py`. The `/resource/`
endpoint honors `$where` correctly — it is just slow.

## Layout

| File           | Does                                                         |
| -------------- | ------------------------------------------------------------ |
| `datasets.py`  | Registry: Socrata id, geography, version, expected row count |
| `client.py`    | Streaming download from the bulk export endpoint             |
| `transform.py` | Splits the long format into fact + dimension CSVs, streaming |
| `schema.sql`   | Dolt DDL for the ten tables                                  |
| `dolt.py`      | DoltHub v1alpha1 API — import without cloning                |
| `sync.py`      | Orchestrates one family/geography pair end to end            |
| `derive.py`    | Builds the committed slices health-charts reads              |
| `main.py`      | CLI                                                          |

## Usage

```bash
uv run python -m places list                  # the registry
uv run python -m places status                # has CDC published newer data than the mirror has?
uv run python -m places sync --geo county     # mirror one PLACES geography
uv run python -m places sync --all            # every PLACES geography
uv run python -m places sync --all --family nmf    # Non-Medical Factors
uv run python -m places sync --all --family both   # all seven portal pages
uv run python -m places derive                # rebuild the committed CSVs
uv run python -m places query "select count(*) from measurement"
```

`sync` needs `DOLTHUB_TOKEN` (a personal access token from
[dolthub.com/settings/tokens](https://www.dolthub.com/settings/tokens)).
`CDC_DATA_APP_TOKEN` is optional and only raises rate limits. Reads need no
credential at all — the database is public, which is what lets health-charts
query it from the browser.

## Schema

`measurement` is the PLACES fact table; `location`, `location_population`,
`measure` and `category` are dimensions. `nmf_measurement` is the Non-Medical
Factors fact table, keyed `(period, geo_level, location_id, measure_id)`, with
`nmf_location`, `nmf_location_population` and `nmf_release_meta` beside it. Eleven of the source's twenty-four columns are
redundant per row — population is constant per `(location, year)` with zero
violations across all 229,298 county rows, and geolocation is constant per
location — so hoisting them takes the fact table from ~239 bytes/row to ~45.

`release_year` is part of every measurement key, so backfilling an older
release is a pure insert and re-importing one upserts rather than duplicating.
(It is `release_year` because RELEASE is a reserved word in MySQL/Dolt.)

The import path speaks DoltHub's **v1alpha1** API, not v2: v2 rejects tokens
issued by `dolthub.com/settings/tokens`. Uploads open a pull request rather than
writing to the branch, so `import_csv` merges it; files are capped at 100MB so
large tables are chunked; and only one import job runs per database at a time,
which is why the workflow matrix is serialized.

## Querying it from a browser

The DoltHub SQL API sends CORS headers and needs no key, but has two limits
that shape every query: it **caps responses at 1000 rows** (reported as a
status, not an error) and enforces a **~55 second query deadline**.

The deadline is the one that bites. Measured against the live database:

| Query                                                  | Time          |
| ------------------------------------------------------ | ------------- |
| `measurement` on a PK prefix (one location, 40 rows)   | 0.5s          |
| `nmf_measurement` on a PK prefix (9 rows)              | 0.4s          |
| Whole `measure` / `category` dimension                 | 0.1s          |
| `location` by PK-prefix `LIKE '01073%'` (189 rows)     | 0.1s          |
| `nmf_measurement` joined to `measure` (1.34M rows)     | 0.5s          |
| **`measurement` joined to `measure` (6.6M rows)**      | **times out** |
| **`geo_level` combined with a secondary-index column** | **times out** |

So: do not join against the 6.6M-row PLACES fact table — read the 49-row
`measure` table (or the committed `measures.csv`) and join client-side. The same
join against the 1.34M-row `nmf_measurement` is fine, so this is a size limit
rather than a shape rule, and it gives no warning when you cross it. Joining
client-side works at every size, which is why it is the standing advice.

And do not mix the primary key's leading column with an indexed non-key column:
`WHERE county_fips='01073'` takes 0.8s while
`WHERE geo_level='tract' AND county_fips='01073'` exceeds the deadline, for the
same 189 rows, on a table of 149k. Reproduces on `nmf_location` too. Both
indexes exist and are correct.

Endpoint:

```
https://www.dolthub.com/api/v1alpha1/fartbagxp/cdc-places/main?q=<urlencoded>
```

That cap is why the national-scale chart payloads stay in
`data/processed/places/` as committed CSVs, and live SQL is used for drill-down
(one county's 49 measures fits comfortably).
