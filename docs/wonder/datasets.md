# Dataset Reference

All 26 WONDER datasets. Specify a dataset in your prompt with `dataset D77` or `dataset D176`.

## Mortality

| Dataset  | Name                                       | Years        | ICD    | Notes                                                |
| -------- | ------------------------------------------ | ------------ | ------ | ---------------------------------------------------- |
| **D176** | Provisional Mortality Statistics           | 2018–present | ICD-10 | Updates weekly; default for recent queries           |
| **D157** | Final Multiple Cause of Death, Single Race | 2018–2023    | ICD-10 | Confirmed final; expanded race categories (8 groups) |
| **D77**  | Multiple Cause of Death, 1999–2020         | 1999–2020    | ICD-10 | Final data; bridged race (5 groups)                  |
| **D76**  | Underlying Cause of Death, 1999–2020       | 1999–2020    | ICD-10 | UCD only; same years as D77                          |
| **D16**  | Compressed Mortality, 1979–1998            | 1979–1998    | ICD-9  | Returns hierarchical (merged-cell) rows              |
| **D74**  | Compressed Mortality, 1968–1978            | 1968–1978    | ICD-8  | Oldest mortality data                                |

!!! tip "Which mortality dataset?" - **Most current data**: D176 (provisional, updates weekly) - **Confirmed 2018–2023**: D157 (final, expanded race) - **Long ICD-10 span**: D77 (1999–2020, final) - **ICD-9 era**: D16 (1979–1998) - **Cross-era time series**: See [Multi-Year Queries](multi-year.md)

## Natality (Births)

| Dataset  | Name                  | Years        | Notes                                                                   |
| -------- | --------------------- | ------------ | ----------------------------------------------------------------------- |
| **D192** | Natality, Provisional | 2023–present | Updates monthly                                                         |
| **D149** | Natality, 2016–2024   | 2016–2024    | Expanded race/ethnicity detail                                          |
| **D66**  | Natality, 2007–2024   | 2007–2024    | Default for recent births                                               |
| **D27**  | Natality, 2003–2006   | 2003–2006    | Requires full base template (see [Troubleshooting](troubleshooting.md)) |
| **D10**  | Natality, 1995–2002   | 1995–2002    |                                                                         |

## Infant Mortality

| Dataset  | Name                                 | Years     | Notes                    |
| -------- | ------------------------------------ | --------- | ------------------------ |
| **D159** | Linked Birth/Infant Death, 2017–2023 | 2017–2023 | Expanded race categories |
| **D69**  | Linked Birth/Infant Death, 2007–2023 | 2007–2023 | Default                  |
| **D31**  | Linked Birth/Infant Death, 2003–2006 | 2003–2006 |                          |
| **D18**  | Linked Birth/Infant Death, 1999–2002 | 1999–2002 |                          |
| **D23**  | Linked Birth/Infant Death, 1995–1998 | 1995–1998 |                          |

## Cancer (SEER/NCI)

| Dataset | Name                  | Years        | Notes                                       |
| ------- | --------------------- | ------------ | ------------------------------------------- |
| **D57** | SEER Incidence        | varies       | Cancer incidence by site                    |
| **D43** | NPCR Cancer Incidence | varies       | CDC's National Program of Cancer Registries |
| **D53** | Cancer Mortality      | 1969–present | NCHS cancer mortality                       |

## AIDS/HIV (CDC)

| Dataset | Name           | Years        | Notes                   |
| ------- | -------------- | ------------ | ----------------------- |
| **D58** | HIV Diagnoses  | 2008–present | New HIV diagnoses       |
| **D56** | HIV Prevalence | varies       | Persons living with HIV |

## Sexually Transmitted Infections

| Dataset | Name             | Years        | Notes                          |
| ------- | ---------------- | ------------ | ------------------------------ |
| **D37** | STD Surveillance | 2007–present | Chlamydia, gonorrhea, syphilis |

## Environmental

| Dataset  | Name                                | Years     | Notes                          |
| -------- | ----------------------------------- | --------- | ------------------------------ |
| **D104** | Heat Wave Days                      | 1981–2010 | County-level extreme heat days |
| **D80**  | Daily Sunlight (NLDAS)              | 1979–2011 | Solar radiation by county      |
| **D81**  | Daily Precipitation (NLDAS)         | 1979–2011 |                                |
| **D60**  | Daily Air Temp & Heat Index (NLDAS) | 1979–2011 |                                |
| **D73**  | Fine Particulate Matter PM2.5       | 2003–2011 | Air quality by county          |

## Immunization / VAERS

| Dataset | Name                                           | Notes                                                                                                    |
| ------- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| **D8**  | VAERS (Vaccine Adverse Event Reporting System) | XML API has a server-side bug — generate XML with `wonder build`, submit manually via the VAERS web form |

---

## Dataset selection cheat sheet

```
Goal                                       Dataset
──────────────────────────────────────────────────────────
Mortality right now (2024)                 D176
Mortality 2018-2023 confirmed              D157
Mortality 1999-2020 ICD-10                D77
Mortality 1979-1998 ICD-9                 D16
Births 2007-present                        D66
Births expanded race 2016-present          D149
Infant mortality 2007-present              D69
Cancer incidence                           D57 / D43
HIV diagnoses                              D58
STDs                                       D37
Air quality / environment                  D60 / D73 / D80
VAERS                                      D8 (manual web form)
```

---

## ICD crosswalk — common causes

When querying across ICD-9 (D16) and ICD-10 (D77+) eras, cause groupings differ:

| Cause               | ICD-9 codes (D16)                                       | ICD-10 codes (D77+)                                 |
| ------------------- | ------------------------------------------------------- | --------------------------------------------------- |
| All-cause mortality | all                                                     | all                                                 |
| Heart disease       | 390–398, 402, 404–429                                   | I00–I09, I11, I13, I20–I51                          |
| Cancer (all)        | 140–208                                                 | C00–C97                                             |
| Stroke              | 430–438                                                 | I60–I69                                             |
| Diabetes            | 250                                                     | E10–E14                                             |
| HIV/AIDS            | 042–044                                                 | B20–B24                                             |
| Drug overdose (all) | E850–E858, E950.0–E950.5                                | X40–X44, X60–X64, X85, Y10–Y14                      |
| Opioid overdose     | E850.0–E850.2, E935.0–E935.2                            | T40.0–T40.6                                         |
| Synthetic opioids   | —                                                       | T40.4                                               |
| Firearm (all)       | E922, E955.0–E955.4, E965.0–E965.4, E970                | W32–W34, X72–X74, X93–X95, Y22–Y24                  |
| Suicide (all)       | E950–E959                                               | X60–X84, Y87.0                                      |
| Homicide (all)      | E960–E969                                               | X85–Y09, Y87.1                                      |
| Motor vehicle       | E810–E825                                               | V02–V89                                             |
| Maternal            | 630–676                                                 | O00–O99                                             |
| SIDS                | 798.0                                                   | R95                                                 |
| Alcohol-induced     | 291, 303, 305.0, 357.5, 425.5, 535.3, 571.0–571.3, E860 | F10, G31.2, G62.1, I42.6, K29.2, K70, K73, K74, X45 |

!!! warning "1999 ICD discontinuity"
The ICD-9 → ICD-10 transition in 1999 causes real discontinuities in many cause-specific time series. The CDC publishes [comparability ratios](https://www.cdc.gov/nchs/nvss/mortality/comparability.htm) to bridge some causes, but others can't be directly compared. All-cause totals are comparable.
