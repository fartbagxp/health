# SEER

[SEER*Explorer](https://seer.cancer.gov/statistics-network/explorer/) (Surveillance, Epidemiology, and End Results) is NCI's cancer statistics system. The `seer` module queries the same JSON endpoints the SEER*Explorer web app uses to render its charts — undocumented, but public and unauthenticated.

No API key required.

---

## Cancer site catalog

SEER*Explorer covers 70+ cancer sites (plus special subtypes like HR+/HER2+ Breast Cancer, or histology-based lung/esophagus subtypes). List or search them:

```bash
uv run python -m seer sites
uv run python -m seer sites --search breast
```

```
    55  Breast
   620  HR+/HER2+ Breast Cancer (Female only)
   621  HR-/HER2+ Breast Cancer (Female only)
   622  HR+/HER2- Breast Cancer (Female only)
   623  HR-/HER2- Breast Cancer (Female only)
```

Use the numeric `code` as `--site` in the commands below.

---

## Mortality (death rates) by year

```bash
# Female breast cancer mortality, 2000-present
uv run python -m seer mortality --site 55 --sex female -f csv

# Lung cancer mortality by race
uv run python -m seer mortality --site 47 --compare-by race -f csv

# Long-term trend (1975-present) for all cancer sites combined
uv run python -m seer mortality --site 1 --long-term -f csv
```

Returns one row per year (or per year × compared dimension), with `rate` (per 100,000), `count`, confidence interval bounds, and a model-smoothed `modeled_rate`.

---

## Incidence by year

Same shape as `mortality`, but for SEER incidence (new diagnoses) rather than deaths. Supports an additional `--stage` filter.

```bash
uv run python -m seer incidence --site 55 --stage 104 -f csv   # localized-stage breast cancer
```

---

## Mortality by age group

```bash
uv run python -m seer by-age --site 1 -f csv
uv run python -m seer by-age --site 47 --compare-by sex -f csv
```

Returns one row per age group (`age_range` code, e.g. `205` = ages 25-29) instead of per year.

---

## Comparing cancer sites

```bash
uv run python -m seer compare-sites 55 47 66 -f csv   # breast, lung, prostate
```

---

## Parameters

| Flag           | Values                                                                 |
| -------------- | ----------------------------------------------------------------------|
| `--sex`        | `both`, `male`, `female`                                               |
| `--race`       | `1` All Races/Ethnicities, `2` White, `3` Black, `4` Non-Hisp. Asian/PI, `5` Non-Hisp. AI/AN, `6` Hispanic, `8` Non-Hisp. White, `9` Non-Hisp. Black |
| `--age-range`  | `1` All Ages, `9` <50, `6` <65, `141` 50-64, `157` 65+, `16` <15, `11` <40, `62` 15-39, `122` 40-64, `160` 65-74, `166` 75+ |
| `--stage`      | `101` All Stages, `102` In Situ, `103` All Invasive, `104` Localized, `105` Regional, `106` Distant, `107` Unstaged (incidence only) |
| `--compare-by` | `sex`, `race`, `age_range` — return one series per value instead of a single fixed value |

---

## Python SDK

```python
from seer.sdk import (
    list_cancer_sites,
    search_cancer_sites,
    get_mortality_trend,
    get_incidence_trend,
    get_mortality_by_age,
    compare_sites_mortality,
)

search_cancer_sites("breast")
rows = get_mortality_trend(site=55, sex="female")
rows = get_mortality_trend(site=47, compare_by="race")
rows = compare_sites_mortality([55, 47, 66])
```

---

## Bundled data snapshots

SEER only re-releases its underlying data **once a year** (typically in spring), unlike CDC Open Data/WISQARS/WONDER which get updated much more often — so instead of querying live on every use, this repo also bundles pre-fetched CSV snapshots under `data/raw/seer/`, refreshed by a monthly GitHub workflow:

| File                    | Contents                                                              |
| ----------------------- | ---------------------------------------------------------------------|
| `var_formats.json`      | Cancer site catalog + sex/race/age/stage/rate-type label vocabularies |
| `mortality_by_year.csv` | U.S. mortality rate/count by year, for every cataloged site, by sex   |
| `mortality_by_age.csv`  | U.S. mortality rate/count by age group, for every cataloged site, by sex |

Refresh manually:

```bash
uv run python -m seer.download                # catalog + both CSV snapshots
uv run python -m seer.download --catalog-only # just the site/label catalog
```
