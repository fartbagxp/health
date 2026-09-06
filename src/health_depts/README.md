# health_depts — State & local health department directories

Scrapes the two authoritative directories of the U.S. public-health **state and
county tier**, and renders the federal → state → county **money-flow graph** that
ties them to the datasets this repo collects.

Every other source here is federal. This module enumerates the *institutions*
underneath the federal tier — the 50 state health departments and the ~3,400
county/local health departments — and shows, in [`docs/funding.md`](../../docs/funding.md),
how CDC cooperative-agreement dollars reach them and how the surveillance they run
surfaces as the federal datasets collected elsewhere in this repo.

## Sources

| Directory | What it is | Rows | Module |
| --- | --- | --- | --- |
| [FSIS State Departments](https://www.fsis.usda.gov/food-safety/foodborne-illness-and-disease/resources-public-health-partners/state-departments-public) | State public-health + agriculture departments | 50 + DC | `fsis.py` |
| [NACCHO LHD Directory](https://www.naccho.org/membership/lhd-directory) | County/city/district local health departments | ~3,400 | `naccho.py` |

Both sit behind bot protection that rejects plain `requests` and `WebFetch` with a
403, so `client.py` fetches with `curl-cffi` Chrome impersonation — the same
dependency the rest of the repo already ships. NACCHO is walked one state at a time
(`?lhd-state=XX`) so each row gets an authoritative state code; the bare directory
URL returns nothing and an *unrecognised* state code returns the full national list,
so neither is used.

## CLI

```bash
uv run python -m health_depts state              # FSIS state depts (table)
uv run python -m health_depts local -f csv        # NACCHO local depts (CSV)
uv run python -m health_depts all --out           # scrape both, write to data/processed/
```

`--out` writes to `data/processed/health_depts/`:

| File | Contents |
| --- | --- |
| `state_departments.{csv,json}` | FSIS rows (state, dept names, URLs) |
| `local_departments.{csv,json}` | NACCHO rows (name, county, city, state, zip, phone, website, socials) |
| `summary.json` | Per-state rollup (FSIS dept name + county-dept list) — the blob inlined into the graph |

Together ~2 MB, committed whole (well under the 95 MB workflow guard).

## The money-flow graph

`summary.json` feeds the interactive federal → state → county money-flow graph, built
with [Svelte Flow](https://svelte.xyflow.com/) in [`frontend/`](../../frontend/) and
embedded on the docs front page and [Funding & Governance](../../docs/funding.md). The
graph imports `summary.json` at build time (baked in, no runtime fetch) and draws
animated edges — green for federal dollars down, teal for data reported up — with a
state selector that expands that state's real department and its scraped counties. See
[`frontend/README.md`](../../frontend/README.md) for the build.

## Cadence

The [`update_health_depts`](../../.github/workflows/update_health_depts.yml) workflow
runs monthly (`all --out`) and commits the refreshed `data/processed/health_depts/`.
The directories change slowly, so monthly is plenty; the data commit triggers the docs
deploy, which recompiles the graph from the new `summary.json`.
