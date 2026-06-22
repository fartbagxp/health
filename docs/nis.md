# NIS — National Immunization Survey

The `nis` module downloads and analyzes [NIS](https://www.cdc.gov/vaccines/imz-managers/nis/) (National Immunization Survey) microdata from CDC FTP. Two surveys are available: NIS-Child (19–35 months) and NIS-Teen (13–17 years).

No API key required, but downloads are ~50–200 MB per year.

---

## Surveys

| Survey | Ages | Key vaccines | Years |
|---|---|---|---|
| `child` | 19–35 months | MMR, DTaP, Hib, PCV, polio, varicella, HepB, HepA, rotavirus | 2011–present |
| `teen` | 13–17 years | HPV, Tdap, meningococcal, COVID-19 | 2011–present |

---

## Commands

### `list` — available years

```bash
uv run python -m nis list child
uv run python -m nis list teen
```

### `rates` — state-level UTD vaccination rates

```bash
# State-level MMR/DTaP/etc. coverage for 2022 (child survey)
uv run python -m nis rates child 2022 -f table

# Teen HPV coverage by state, 2023
uv run python -m nis rates teen 2023 -f table

# Single state
uv run python -m nis rates child 2022 --state California -f table
uv run python -m nis rates child 2022 --state CA -f table   # USPS code
uv run python -m nis rates child 2022 --state 06 -f table   # FIPS

# Specific vaccine columns only
uv run python -m nis rates child 2022 --vaccines P_UTDMMX P_UTDVAC -f table
```

### `national` — national-level UTD rates

```bash
# National childhood vaccination coverage, 2022
uv run python -m nis national child 2022 -f table

# Teen national rates, 2023
uv run python -m nis national teen 2023 -f table

# Specific vaccines
uv run python -m nis national child 2022 --vaccines P_UTDMMX P_UTDVAC P_UTDPOL -f table
```

### `stream` — raw respondent microdata

For custom analysis, stream the individual-level records:

```bash
# All respondents, child survey 2022
uv run python -m nis stream child 2022 -f csv > nis-child-2022-raw.csv

# Filter to California only
uv run python -m nis stream child 2022 --state CA -f csv

# Limit columns
uv run python -m nis stream teen 2023 --vaccines P_UTDHPV INCQ298A STATENAM -f csv

# First 100 records for inspection
uv run python -m nis stream child 2022 --limit 100 -f table
```

---

## Python SDK

```python
from nis.sdk import get_state_rates, get_national_rates, stream_records

# State-level UTD coverage, child 2022
states = get_state_rates(survey="child", year=2022)
# [{"state": "California", "P_UTDMMX": 0.912, "P_UTDVAC": 0.883, ...}, ...]

# National rates
national = get_national_rates(survey="child", year=2022)

# Raw microdata
for record in stream_records(survey="child", year=2022, state="CA"):
    mmr_utd = record.get("P_UTDMMX")
    # P_UTDMMX: 1 = UTD (up-to-date), 2 = not UTD
```

---

## Key vaccine column names

### Child survey (P_UTD*)

| Column | Vaccine |
|---|---|
| `P_UTDMMX` | MMR (measles, mumps, rubella) |
| `P_UTDDTP` | DTaP (≥4 doses) |
| `P_UTDHIB` | Hib (H. influenzae type b) |
| `P_UTDPCV` | PCV13 pneumococcal |
| `P_UTDPOL` | Poliovirus (≥3 doses) |
| `P_UTDVAC` | Varicella |
| `P_UTDHEP` | HepB (≥3 doses) |
| `P_UTDHEPA` | HepA (≥2 doses) |
| `P_UTDROTA` | Rotavirus |
| `P_UTDCOMB7` | Combined 7-vaccine series |

### Teen survey (P_UTD*)

| Column | Vaccine |
|---|---|
| `P_UTDHPV` | HPV (≥1 dose female initiators) |
| `P_UTDTDAP` | Tdap |
| `P_UTDMCV4` | MCV4 meningococcal (≥1 dose) |
| `P_UTDMCV4S` | MCV4 (≥2 doses, booster) |

---

## Multi-year trend analysis

```python
from nis.sdk import get_national_rates
import csv

years = list(range(2011, 2024))
all_rows = []

for year in years:
    try:
        row = get_national_rates(survey="child", year=year)
        row["year"] = year
        all_rows.append(row)
    except Exception as e:
        print(f"  {year}: {e}")

# Write to CSV for trend analysis
with open("mmr-national-trend-2011-2023.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=all_rows[0].keys())
    writer.writeheader()
    writer.writerows(all_rows)
```

!!! note "Download cache"
    NIS files are large (50–200 MB). The module caches downloads locally. The first call per year triggers a download; subsequent calls use the cached file.

---

## Combining NIS with CDC Open Data

The `cdc_open` module includes several vaccination coverage datasets that complement NIS microdata:

```bash
# NIS-Flu coverage (flu vaccine, all ages 6+ months)
uv run python -m cdc_open query flu_vaccine_coverage -f table

# BRFSS vaccination coverage (adults)
uv run python -m cdc_open query brfss_vaccination -f table
```

Use NIS for childhood/teen UTD rates with full microdata access; use CDC Open Data for flu/COVID/adult vaccines.
