# Funding & Governance

Every dataset this repo collects is published by the CDC, but almost none of it is
*generated* there. Notifiable-disease counts, outbreak reports, enteric-pathogen
isolates, behavioral-risk estimates, vaccination coverage, vital records — these are
produced by state and local health departments and reported upward. What makes that
reporting happen is money: CDC moves appropriations down to the states, mostly through
**cooperative agreements**, and the surveillance those agreements fund is what surfaces,
years later, as the tables the other pages here query.

This page traces that loop — federal dollars down, data back up — and enumerates the
institutions in the middle. It is a governance map, not a budget: it names the funding
*mechanisms*, not dollar figures.

## The money flow

<link rel="stylesheet" href="funding-flow/funding-flow.css" />
<div id="funding-flow" class="ff-embed">
  <noscript>This interactive graph needs JavaScript enabled.</noscript>
</div>
<script src="funding-flow/funding-flow.js" defer></script>

*Pick a state to expand its real department and its county/local health departments,
pulled from the scraped directories below. Solid green edges are federal dollars flowing
down; dashed teal edges are the surveillance those programs generate, flowing back up as
the datasets this repo collects. The graph is a [Svelte Flow](https://svelte.xyflow.com/)
component compiled into the site from `frontend/`.*

## The three tiers

| Tier | Who | This repo's view |
| --- | --- | --- |
| **Federal** | CDC (plus NCHS, ATSDR, and NCI for cancer) | The APIs and bulk files every other page queries |
| **State** | 50 state health departments + DC | Enumerated from the **FSIS** directory (`state_departments.csv`) |
| **County / local** | ~3,400 local health departments (LHDs) | Enumerated from the **NACCHO** directory (`local_departments.csv`) |

Federal surveillance mostly stops at the state line (see [State & Local Sources](local.md)),
but the *institutions* that feed it run all the way down to the county. The two directories
scraped here are the roster of that middle-and-bottom tier.

## Mechanism → dataset

Each cooperative agreement or program funds a slice of state/local capacity, and that
capacity is what produces a specific dataset. The correspondence is approximate — real
appropriations are braided — but it is the honest shape of why each table exists.

| CDC mechanism | Tier funded | Surfaces in this repo as |
| --- | --- | --- |
| **ELC** — Epidemiology & Laboratory Capacity | State epidemiology + public-health labs | [NNDSS](cdc-open.md), [NORS](cdc-open.md), [BEAM](cdc-open.md), Lyme |
| **PHEP** — Public Health Emergency Preparedness | State + local ED/syndromic infrastructure | [NSSP](nssp.md) |
| **BRFSS** cooperative agreement | State behavioral-risk surveys | [PLACES](places.md) small-area estimates |
| **NPCR** — National Program of Cancer Registries | State central cancer registries | Cancer statistics (see note) |
| **§317** immunization grants | State immunization programs | [NIS](nis.md) coverage |
| **EPHT** tracking grants | State environmental-tracking programs | [EPHT](local.md) |
| **NVSS** vital-statistics cooperative | State vital-records offices | [WONDER](wonder/index.md), [WISQARS](wisqars.md) |

!!! note "SEER is not CDC-funded"
    The cancer node is a deliberate simplification. **NPCR** (CDC) funds registries in most
    states and territories and feeds *U.S. Cancer Statistics*; **[SEER](seer.md)** is a
    *parallel* program run by the **NCI**, covering a smaller set of registries. This repo
    collects SEER, so the graph points NPCR at the SEER node as the nearest cancer surface —
    the funder underneath is NCI, not CDC.

## The scraped directories

Two authoritative, machine-readable rosters are refreshed on a schedule and committed to
`data/processed/health_depts/`.

### State departments — FSIS

The [USDA FSIS directory of State Departments of Public Health and
Agriculture](https://www.fsis.usda.gov/food-safety/foodborne-illness-and-disease/resources-public-health-partners/state-departments-public)
is one static table: for each of the 50 states + DC it lists the state's home portal, its
public-health department, and its agriculture department, each with a link.

```bash
uv run python -m health_depts state -f table
```

### Local departments — NACCHO

The [NACCHO Local Health Department Directory](https://www.naccho.org/membership/lhd-directory)
lists ~3,400 county, city, and district health departments. The scraper walks all 50 states
+ DC (`?lhd-state=XX`) and captures name, address, phone, website, and social links for each.

```bash
uv run python -m health_depts local -f csv | head
uv run python -m health_depts all --out    # write both directories + summary.json
```

Both directories together are ~2 MB — small enough to commit whole, in keeping with the
[ingestion discipline](local.md#ingestion-strategy) that governs `data/`. They change slowly,
so the [`update_health_depts`](https://github.com/boris/health/actions) workflow refreshes
them monthly; the graph above rebuilds from `summary.json` on the next docs deploy (the
Svelte project in `frontend/` bakes the data in at build time).

## Caveats

- **Mechanisms, not amounts.** No dollar figures appear here. A data-backed version — real
  award amounts per state from USAspending / TAGGS — is a deliberate future extension, not
  part of this map.
- **County labels are best-effort.** The graph's county names are derived from department
  names (`"Autauga County Health Department"` → `Autauga`); non-standard names (city
  districts, combined health-and-human-services agencies) keep more of their full title.
- **Directories drift.** FSIS links and NACCHO membership go stale; treat the scrape date
  shown in the graph footer as the as-of.
