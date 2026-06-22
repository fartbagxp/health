# Example Gallery

Worked examples for WONDER queries. Copy-paste any prompt directly into:

```bash
uv run python -m wonder query "<prompt>" -f csv
```

---

## Mortality — recent (D176, provisional)

```bash
# Overall trends
uv run python -m wonder query \
  "all-cause deaths by year 2018-2024, crude rate"

uv run python -m wonder query \
  "life expectancy proxy: all-cause age-adjusted death rate by year 2018-2024"

# COVID-19
uv run python -m wonder query \
  "COVID-19 deaths by year 2020-2024, crude rate and death count"

uv run python -m wonder query \
  "COVID-19 deaths by race and ethnicity 2020-2023"

uv run python -m wonder query \
  "COVID-19 deaths by age group 2020-2023"

uv run python -m wonder query \
  "COVID-19 deaths by state 2020-2022, crude rate per 100,000"

# Overdose
uv run python -m wonder query \
  "drug overdose deaths by year 2018-2024, age-adjusted rate"

uv run python -m wonder query \
  "opioid overdose deaths (T40.0-T40.6) by state and year 2018-2024"

uv run python -m wonder query \
  "synthetic opioid deaths (T40.4) by year 2018-2024, death count"

uv run python -m wonder query \
  "stimulant overdose deaths (T43.6 cocaine + T43.62 psychostimulants) by year 2018-2024"

# Firearm
uv run python -m wonder query \
  "firearm deaths by year 2018-2024, age-adjusted rate"

uv run python -m wonder query \
  "firearm suicide deaths (X72-X74) by state 2018-2023, crude rate"

uv run python -m wonder query \
  "firearm homicide deaths (X93-X95) by race and sex 2018-2023"

uv run python -m wonder query \
  "firearm deaths by intent (suicide, homicide, unintentional) 2020-2023"

# Maternal / infant
uv run python -m wonder query \
  "maternal mortality (O00-O99) by year 2018-2024, crude rate per 100,000 live births"

uv run python -m wonder query \
  "maternal mortality by race and ethnicity 2018-2023"

uv run python -m wonder query \
  "infant mortality by state 2018-2023, crude rate per 1,000 live births"

# Suicide
uv run python -m wonder query \
  "suicide deaths by sex 2018-2024, age-adjusted rate"

uv run python -m wonder query \
  "suicide deaths by age group 2018-2023"

uv run python -m wonder query \
  "suicide deaths by method (firearm vs non-firearm) by year 2018-2024"

# Cardiovascular
uv run python -m wonder query \
  "heart disease deaths by race and sex 2018-2023, age-adjusted rate"

uv run python -m wonder query \
  "stroke deaths by state 2020-2023, age-adjusted rate"
```

---

## Mortality — final data (D157, 1999–2023)

Use D157 when you need confirmed (non-provisional) data with expanded race categories.

```bash
uv run python -m wonder query \
  "cancer death rates by year 1999-2023, age-adjusted, dataset D157"

uv run python -m wonder query \
  "lung cancer deaths by sex 1999-2023, age-adjusted rate, dataset D157"

uv run python -m wonder query \
  "HIV/AIDS deaths by year 1999-2023, dataset D157"

uv run python -m wonder query \
  "Alzheimer deaths by sex and year 2010-2023, dataset D157"

uv run python -m wonder query \
  "diabetes deaths by race 2010-2023, age-adjusted, dataset D157"
```

---

## Mortality — ICD-10 era (D77, 1999–2020)

D77 uses bridged-race categories (5 groups). Covers the full ICD-10 era with final data.

```bash
uv run python -m wonder query \
  "opioid deaths by year 1999-2020, dataset D77"

uv run python -m wonder query \
  "firearm deaths by state 2010-2020, crude rate, dataset D77"

uv run python -m wonder query \
  "suicide deaths by age group and sex 2000-2020, dataset D77"

uv run python -m wonder query \
  "infant mortality by race 1999-2020, dataset D77"
```

---

## Births / natality

```bash
# Recent births (D66 default, 2007–2024)
uv run python -m wonder query \
  "births by year 2010-2024, birth count and birth rate"

uv run python -m wonder query \
  "teen births (mothers aged 15-19) by state 2018-2023"

uv run python -m wonder query \
  "preterm births by race 2018-2023, percent of births"

uv run python -m wonder query \
  "low birth weight by state 2018-2023"

uv run python -m wonder query \
  "C-section delivery rate by state 2018-2023"

# Expanded race detail (D149, 2016–2024)
uv run python -m wonder query \
  "births by race and ethnicity 2016-2023, dataset D149"
```

---

## Multi-year — cross-epoch patterns

These queries span multiple datasets and require looping. See [Multi-Year Queries](multi-year.md) for the full merge pattern.

```bash
# Collect 1999–2024 in two shots (D77 then D176)
# Year 1: D77 1999–2020
uv run python -m wonder query \
  "drug overdose deaths by year 1999-2020, dataset D77" -f csv > overdose-d77.csv

sleep 16

# Year 2: D176 2021–2024
uv run python -m wonder query \
  "drug overdose deaths by year 2021-2024, dataset D176" -f csv > overdose-d176.csv

# Then merge the two CSVs in pandas / polars / awk
```

---

## All-state queries

See [All-State Queries](multi-state.md) for the cell-limit workaround patterns.

```bash
# State × year — within cell limit
uv run python -m wonder query \
  "firearm deaths by state and year 2018-2024" -f csv

uv run python -m wonder query \
  "drug overdose deaths by state and year 2018-2024, crude rate" -f csv

# State only (single metric snapshot)
uv run python -m wonder query \
  "suicide death rate by state 2020-2022, age-adjusted" -f csv

uv run python -m wonder query \
  "maternal mortality rate by state 2018-2023" -f csv
```

---

## Race and ethnicity breakdowns

```bash
uv run python -m wonder query \
  "all-cause deaths by race and Hispanic origin 2018-2023, age-adjusted rate"

uv run python -m wonder query \
  "COVID-19 deaths by race 2020-2022, crude rate per 100,000"

uv run python -m wonder query \
  "firearm homicide deaths by race 2018-2023, age-adjusted rate"

uv run python -m wonder query \
  "infant mortality by race 2018-2023, infant mortality rate"
```

---

## Age-specific queries

```bash
uv run python -m wonder query \
  "deaths by 10-year age group 2020-2023, crude rate"

uv run python -m wonder query \
  "overdose deaths in adults 25-44 by year 2015-2024"

uv run python -m wonder query \
  "firearm deaths in ages 0-17 by state 2018-2023"

uv run python -m wonder query \
  "cardiovascular deaths in ages 35-64 by sex 2018-2023, age-adjusted"
```

---

## Environment and NLDAS

```bash
uv run python -m wonder query \
  "heat wave days per year by state 1981-2010, dataset D104"

uv run python -m wonder query \
  "days with max temperature above 90F by state 1979-2011, dataset D60"

uv run python -m wonder query \
  "average PM2.5 by county in California 2003-2011, dataset D73"
```

---

## Pediatric causes

```bash
uv run python -m wonder query \
  "leading causes of death in ages 1-4 by year 2018-2023"

uv run python -m wonder query \
  "unintentional injury deaths in children under 18 by state 2018-2023"

uv run python -m wonder query \
  "SIDS deaths (R95) by year 2010-2023"

uv run python -m wonder query \
  "drowning deaths (W65-W74) in ages 0-14 by state 2018-2023"
```

---

## Building XML queries for reuse

For any query you run repeatedly, save the XML so you don't need the LLM:

```bash
# Build and save
uv run python -m wonder build \
  "drug overdose deaths by state 2024, crude rate" \
  > src/wonder/queries/overdose-by-state-2024-req.xml

# Run from file (no LLM needed)
uv run python -m wonder run \
  src/wonder/queries/overdose-by-state-2024-req.xml -f csv

# Update just the year — edit the XML file:
# <F_D176.V1 value="2024"/> → <F_D176.V1 value="2025"/>
```
