# NSSP — Emergency Department Visits

The `nssp` module queries the [NSSP BioSense Platform](https://www.cdc.gov/nssp/) (National Syndromic Surveillance Program) via the CMU Delphi Epidata API (`covidcast` endpoint). It tracks the **percentage of ED visits** attributed to COVID-19, influenza, RSV, or a combined respiratory illness index.

No API key required. Data updates weekly.

---

## Signals

| Signal      | What it measures                                 |
| ----------- | ------------------------------------------------ |
| `covid`     | % ED visits with COVID-19 diagnosis              |
| `influenza` | % ED visits with influenza diagnosis             |
| `rsv`       | % ED visits with RSV diagnosis                   |
| `combined`  | Combined respiratory illness (COVID + flu + RSV) |

---

## Geographic levels

| Level      | `--geo` value     | Notes                        |
| ---------- | ----------------- | ---------------------------- |
| National   | `nation`          | Single aggregate value       |
| State      | `state` (default) | 2-letter USPS code e.g. `ca` |
| County     | `county`          | 5-digit FIPS e.g. `06037`    |
| HHS Region | `hhs`             | HHS region number 1–10       |
| Metro area | `msa`             |                              |
| HRR        | `hrr`             | Hospital Referral Region     |

---

## Commands

### `query` — flexible single-signal query

```bash
# National COVID-19 ED visits, last 52 weeks (default)
uv run python -m nssp query covid --geo nation -f table

# Influenza by state, last 52 weeks
uv run python -m nssp query influenza --geo state --region '*' -f csv

# RSV in California
uv run python -m nssp query rsv --geo state --region ca -f table

# Specific HHS region
uv run python -m nssp query influenza --geo hhs --region 4 -f table

# Custom date range (epiweek format YYYYWW)
uv run python -m nssp query covid --geo state --region ny \
  --start 202201 --end 202360 -f csv
```

### `national` — all four signals at once

```bash
# All four signals, national, last 52 weeks
uv run python -m nssp national -f table

# Custom range
uv run python -m nssp national --start 202201 --end 202360 -f csv
```

Sample output:

```
signal       epiweek   value
covid        202501    3.2
influenza    202501    2.1
rsv          202501    0.8
combined     202501    5.9
```

### `hhs` — by HHS region

```bash
# Influenza across all 10 HHS regions
uv run python -m nssp hhs influenza -f table

# Specific region
uv run python -m nssp hhs influenza --region 4

# COVID by region, custom range
uv run python -m nssp hhs covid --start 202340 --end 202560 -f csv
```

---

## Python SDK

```python
from nssp.client import NSSPClient

client = NSSPClient()

# National COVID, last year
rows = client.fetch(
    signal="covid",
    geo_type="nation",
    geo_value="us",
)

# All states, influenza
rows = client.fetch(
    signal="influenza",
    geo_type="state",
    geo_value="*",
)

# Custom epiweek range
rows = client.fetch(
    signal="rsv",
    geo_type="state",
    geo_value="ca",
    time_values="202240-202560",
)
```

### Response fields

| Field         | Description                            |
| ------------- | -------------------------------------- |
| `signal`      | Signal name                            |
| `geo_type`    | Geographic level                       |
| `geo_value`   | Geographic code                        |
| `time_value`  | Epiweek (YYYYWW)                       |
| `value`       | % of ED visits                         |
| `stderr`      | Standard error                         |
| `sample_size` | Number of ED visits in the denominator |
| `direction`   | Trend direction vs prior week          |

---

## Multi-year collection

NSSP data via Delphi goes back to 2020 for COVID, 2021 for influenza/RSV. Collecting all available history:

```python
from nssp.client import NSSPClient

client = NSSPClient()

# Full history for all signals
for signal in ["covid", "influenza", "rsv", "combined"]:
    rows = client.fetch(
        signal=signal,
        geo_type="state",
        geo_value="*",
        time_values="202001-202660",  # epiweeks 2020 week 1 → 2026 week 60
    )
    # Save to CSV
    ...
```

No rate limit — the Delphi API doesn't enforce 15-second waits like WONDER. Fetches are typically < 2 seconds and results are cached for 24 hours.

---

## Combining with GRASP FluView

NSSP and GRASP FluView measure different things for influenza:

|           | NSSP                         | GRASP FluView ILINet                  |
| --------- | ---------------------------- | ------------------------------------- |
| Metric    | % ED visits with flu dx      | % outpatient visits with ILI symptoms |
| Coverage  | 2020–present                 | 1997–present                          |
| Geography | State, county, HHS           | National, HHS, state                  |
| Lag       | ~1 week                      | ~1 week                               |
| Notes     | Confirmed diagnosis required | Symptom-based (not lab-confirmed)     |

Use ILINet for historical trend data; use NSSP for current season monitoring with confirmed diagnoses.
