# WONDER API

## Example Queries

The following verified queries explore findings from [NCHS Data Brief No. 521: Mortality in the United States, 2023](https://www.cdc.gov/nchs/products/databriefs/db521.htm).
All queries use dataset **D176** (Provisional Mortality Statistics, 2018 through Last Week).

> **Rate limit:** CDC WONDER requires at least 15 seconds between API requests.

---

### 1. The COVID Cliff: Deaths by Hispanic Origin, 2020–2023

**File:** `queries/covid-deaths-by-race-2020-2023-req.xml`

**Question:** The data brief reports COVID-19 deaths plummeted 73% from 2022 to 2023.
Which populations bore the heaviest burden — and did the disparity close?

**Prompt used:**

```bash
COVID-19 deaths by year 2020 through 2023, grouped by Hispanic origin,
showing age-adjusted death rate per 100,000. Filter underlying cause of
death to the COVID-19 ICD chapter (U00-U99).
```

**Run it:**

```bash
uv run python -m wonder run src/wonder/queries/covid-deaths-by-race-2020-2023-req.xml -f csv
```

**Key findings:**

| Year | Hispanic/Latino AAR | Non-Hispanic AAR | Ratio |
| ---- | ------------------: | ---------------: | ----: |
| 2020 |               155.5 |             75.8 | 2.05× |
| 2021 |               151.8 |             97.5 | 1.56× |
| 2022 |                47.2 |             44.0 | 1.07× |
| 2023 |                 9.2 |             12.2 | 0.75× |

The age-adjusted rate (AAR) corrects for the fact that the Hispanic population skews younger — revealing that in 2020 and 2021 Hispanic/Latino Americans died from COVID-19 at **twice the rate** of non-Hispanic Americans once age is accounted for.
By 2023, the gap had not only closed but reversed, with non-Hispanic Americans carrying a slightly higher AAR (12.2 vs 9.2).

---

### 2. Heart vs. Cancer by Sex, 2018–2023

**File:** `queries/heart-vs-cancer-by-sex-2018-2023-req.xml`

**Question:** Heart disease (#1) and cancer (#2) together account for roughly a third of
all US deaths. How do the age-adjusted rates compare across sexes, and is the
heart disease decline holding?

**Prompt used:**

```bash
Heart disease deaths and cancer deaths by year 2018 through 2023, grouped by
sex and ICD chapter, showing age-adjusted death rate per 100,000. Filter to
Neoplasms (C00-D48) and Diseases of the circulatory system (I00-I99).
```

**Run it:**

```bash
uv run python -m wonder run src/wonder/queries/heart-vs-cancer-by-sex-2018-2023-req.xml -f csv
```

**Key findings (age-adjusted rates per 100,000):**

| Year | Men — Heart | Men — Cancer | Women — Heart | Women — Cancer |
| ---- | ----------: | -----------: | ------------: | -------------: |
| 2018 |       263.4 |        181.8 |         178.6 |          131.8 |
| 2020 |       273.5 |        175.3 |         183.1 |          127.8 |
| 2021 |       281.5 |        177.1 |         192.1 |          131.0 |
| 2023 |       263.0 |        170.1 |         180.2 |          127.3 |

Men die from heart disease at ~1.5× the rate of women. Cancer rates for both
sexes held nearly flat across the period — consistent with the data brief's
finding that cancer "remained stable." Heart disease spiked during the COVID
years (2020–2021) and partially recovered by 2023, likely reflecting
COVID-19's cardiovascular effects and disrupted preventive care.

---

### 3. Who Gets Hurt: External Cause Deaths by Age Group, 2018–2023

**File:** `queries/unintentional-injuries-by-age-2018-2023-req.xml`

**Question:** Unintentional injuries are the #3 cause of death and fell 2.7% in 2023.
Which age groups drove the pandemic-era surge and the recent retreat?

**Prompt used:**

```bash
External cause deaths (V01-Y89 ICD chapter) by year 2018 through 2023,
grouped by ten-year age group, showing crude death rate per 100,000.
```

**Run it:**

```bash
uv run python -m wonder run src/wonder/queries/unintentional-injuries-by-age-2018-2023-req.xml -f csv
```

**Key findings (crude rate per 100,000):**

| Age Group |  2018 |  2020 | 2021 (peak) |  2023 |
| --------- | ----: | ----: | ----------: | ----: |
| 15–24     |  54.6 |  66.4 |        68.8 |  60.1 |
| 25–34     |  85.9 | 105.1 |       115.3 | 100.3 |
| 35–44     |  84.5 | 105.6 |       117.3 | 114.0 |
| 45–54     |  84.4 |  97.5 |       106.4 | 103.8 |
| 75–84     | 140.1 | 142.4 |       158.3 | 150.9 |
| 85+       | 402.4 | 420.9 |       486.5 | 469.1 |

Working-age adults (25–54) and the elderly (85+) showed the steepest pandemic
surges. The 25–44 cohort, which includes the bulk of drug overdose deaths (a
major component of external-cause mortality), peaked in 2021 and has only
partially recovered. The oldest group (85+) remains far above pre-pandemic levels.

---

### 4. The Racial Mortality Gap, 2018–2023

**File:** `queries/racial-mortality-gap-2018-2023-req.xml`

**Question:** The data brief highlights large declines in age-adjusted death rates
among American Indian/Alaska Native (AIAN) populations. How do all-cause
age-adjusted rates compare across racial groups over time?

**Prompt used:**

```bash
All-cause deaths by year 2018 through 2023, grouped by race and year,
showing age-adjusted death rate per 100,000.
```

**Run it:**

```bash
uv run python -m wonder run src/wonder/queries/racial-mortality-gap-2018-2023-req.xml -f csv
```

**Key findings (age-adjusted rate per 100,000):**

| Race  |  2018 |   2020 | 2021 (peak) |  2023 | Change 2021→2023 |
| ----- | ----: | -----: | ----------: | ----: | ---------------: |
| AIAN  | 575.8 |  742.7 |       787.5 | 585.7 |           −25.6% |
| Black | 867.8 | 1086.7 |      1081.6 | 895.6 |           −17.2% |
| White | 728.3 |  829.5 |       882.7 | 758.8 |           −14.1% |
| Asian | 380.0 |  456.6 |       460.4 | 386.8 |           −16.0% |
| NHPI  | 595.2 |  731.1 |       802.1 | 637.5 |           −20.5% |

The AIAN population was hit hardest during COVID (a 37% spike from 2018 to 2021)
and has recovered most dramatically. Black Americans have consistently faced
the highest mortality burden, at roughly 18–20% above the White rate even after
age-adjustment. The 2023 data shows convergence back toward pre-pandemic
baselines across all groups, though gaps remain substantial.

---

### 5. Infant Mortality: The Flat Line, 2018–2023

**File:** `queries/infant-mortality-2018-2023-req.xml`

**Question:** The data brief reports infant mortality showed "no significant change"
from 2022 to 2023. What does the full 2018–2023 trend look like?

**Prompt used:**

```
Deaths among infants (under 1 year) by year 2018 through 2023, grouped by
year only, showing death counts and crude rate.
```

**Run it:**

```bash
uv run python -m wonder run src/wonder/queries/infant-mortality-2018-2023-req.xml -f csv
```

**Key findings:**

| Year | Infant Deaths | Rate per 100k under-1 pop |
| ---- | ------------: | ------------------------: |
| 2018 |        21,467 |                     557.8 |
| 2019 |        20,921 |                     553.0 |
| 2020 |        19,582 |                     524.3 |
| 2021 |        19,920 |                     558.8 |
| 2022 |        20,553 |                     558.0 |
| 2023 |        20,145 |                     552.1 |

While most mortality causes showed dramatic COVID-era swings, infant mortality
remained remarkably stable — dipping in 2020 (likely due to reduced infections
and elective procedures), then returning to ~558 per 100,000 and holding flat
through 2023. This plateau is notable: unlike adult mortality, which has
declined over decades, infant mortality progress in the US has stalled.

---

## Query Catalog

Ideas to try with `uv run python -m wonder query "..."`. Grouped by theme and dataset.

> **Tip:** Be specific — name the cause of death with its ICD chapter or drug group,
> the years, and how you want results grouped. Vague prompts lead to vague queries.

---

### Drug Overdose & Substance Use (D176)

**6. The Opioid Wave vs. the Stimulant Wave**

```
Drug-induced deaths by drug category (D1=all drug-induced) from 2018 to 2024,
grouped by year and drug/alcohol cause category using F_D176.V25, showing
age-adjusted rate. Set O_ucd to D176.V25.
```

_What to look for:_ Fentanyl-era opioid deaths peaked around 2021–2022; methamphetamine
and stimulant deaths have been rising separately. The drug/alcohol cause groups split
these populations.

---

**7. Fentanyl vs. Heroin: MCD Code Breakdown**

```
Opioid overdose deaths 2018–2024 grouped by year, filtering multiple cause
of death to T40.1 (heroin), T40.3 (methadone), T40.4 (synthetic narcotics
excluding methadone — i.e. fentanyl), showing death counts.
```

_What to look for:_ Heroin deaths (T40.1) declining as fentanyl (T40.4) dominates.

---

**8. Alcohol-Induced Deaths During COVID**

```
Alcohol-induced deaths from 2018 to 2023, grouped by year and sex,
showing age-adjusted rate per 100,000. Set O_ucd to D176.V25 and
filter F_D176.V25 to A1 (all alcohol-induced causes).
```

_What to look for:_ Sharp pandemic-era spike in 2020–2021, especially among
middle-aged adults, as bar closures shifted drinking home.

---

### Mental Health & Self-Harm (D176)

**9. Suicide Rates by Sex and Method, 2018–2024**

```
Suicide deaths 2018–2024 (ICD chapter X60-X84, Y87.0 — Intentional self-harm)
grouped by year and sex, showing age-adjusted rate. Filter to ICD chapter
X00-Y89 (External causes) and use the injury intent filter.
```

_What to look for:_ Male suicide rates are 3–4× female, but female rates have
been rising faster. The gun-vs-other-method breakdown changes by sex.

---

**10. Suicide Among Young Adults vs. Older Adults**

```
Intentional self-harm deaths (X60-X84) from 2018 to 2024, grouped by
ten-year age group and year, showing crude rate per 100,000.
```

_What to look for:_ Suicide in the 15–24 and 25–34 groups rose sharply
post-pandemic; older adult rates have historically been higher but
more stable.

---

### Maternal & Reproductive Health (D176)

**11. Maternal Mortality by Race, 2018–2023**

```
Maternal mortality deaths (ICD chapter O00-O99 — Pregnancy, childbirth
and the puerperium) from 2018 to 2023, grouped by year and race,
showing age-adjusted rate per 100,000.
```

_What to look for:_ Black maternal mortality is 2–3× that of white women.
The pandemic years showed a significant spike. This is a persistently high
number that exceeds most peer nations.

---

### Chronic Disease (D176)

**12. Alzheimer's & Dementia Surge by Age**

```
Alzheimer's disease deaths (ICD chapter G30) from 2018 to 2024,
grouped by ten-year age group and year, showing crude death rate.
Disable age-adjusted rates since we're grouping by age.
```

_What to look for:_ 85+ accounts for the vast majority. Did COVID-era
isolation and care disruption spike dementia deaths?

---

**13. Diabetes Mortality by Race**

```
Diabetes deaths (ICD chapter E10-E14) from 2018 to 2023, grouped by
year and race, showing age-adjusted death rate per 100,000.
```

_What to look for:_ Native American and Black populations carry
disproportionate diabetes mortality. Did COVID worsen disparities?

---

### Geography & Place (D176)

**14. Firearm Deaths by State**

```
Firearm deaths (ICD chapter W32-W34, X72-X74, X93-X95, Y22-Y24 — all
firearm causes) from 2020 to 2023 grouped by state, showing crude rate.
```

_What to look for:_ Wide variation across states, partly explained by
urban/rural composition and gun ownership rates.

---

**15. Drug Overdose Hotspots by HHS Region**

```
Drug-induced deaths 2018–2024 grouped by HHS region and year,
age-adjusted rate per 100,000, O_ucd = D176.V25.
```

_What to look for:_ Appalachian-heavy Region 3 (DC/MD/PA/VA/WV/DE)
has historically carried elevated overdose burden.

---

### Long-Term Trends — Final Data (D157)

**16. Cancer Progress: 1999–2023**

```
Cancer deaths (ICD chapter C00-D48) from 1999 to 2023 using dataset D157,
grouped by year, showing age-adjusted rate per 100,000.
```

_What to look for:_ One of public health's success stories — cancer AAR
has fallen ~32% since its 1990s peak, driven by reduced smoking and
improved treatment. COVID briefly interrupted the trend.

---

**17. HIV/AIDS: Epidemic Arc, 1999–2023**

```
HIV disease deaths (ICD chapter B20-B24) from 1999 to 2023 using dataset
D157, grouped by year and race, showing age-adjusted rate.
```

_What to look for:_ The dramatic post-antiretroviral decline from 1995–2000.
Black Americans still carry a disproportionate burden in more recent years.

---

**18. Flu & Pneumonia: A Baseline to Judge COVID**

```
Influenza and pneumonia deaths (ICD chapter J09-J18) from 1999 to 2023
using dataset D157, grouped by year, showing age-adjusted rate.
```

_What to look for:_ Seasonal variation; the 2017–18 severe flu season; the
collapse in 2020–21 when masking suppressed respiratory illness, then
resurgence in 2022. Gives context for how unusual COVID mortality was.

---

**19. The Diabetes Epidemic in Long View**

```
Diabetes deaths (ICD chapter E10-E14) from 1999 to 2023 using dataset D157,
grouped by year and sex, showing age-adjusted rate.
```

_What to look for:_ Rates rose through the 2000s as obesity increased,
then plateaued or modestly declined post-2010. Men consistently higher.

---

**20. Stroke Mortality Long-Term Decline**

```
Cerebrovascular disease deaths (ICD chapter I60-I69) from 1999 to 2023
using dataset D157, grouped by year and race, showing age-adjusted rate.
```

_What to look for:_ A long-run success story — stroke AAR fell ~35% between
1999 and 2015 due to blood pressure treatment. Racial disparities remain large.

---

### Historical Comparisons (D77, 1979–1998)

**21. The HIV/AIDS Emergence**

```
HIV disease deaths (ICD chapter 042-044 using ICD-9 codes) from 1987 to
1998 using dataset D77, grouped by year and sex, showing age-adjusted rate.
```

_What to look for:_ HIV deaths in men aged 25–44 became the leading cause
of death for that group in the early 1990s — a demographic catastrophe
with few historical parallels.

---

**22. Homicide Rates During the Crack Epidemic**

```
Homicide deaths (ICD chapter E960-E969) from 1979 to 1998 using dataset D77,
grouped by year and race, showing age-adjusted rate.
```

_What to look for:_ Homicide rates, especially for young Black men, roughly
doubled between the mid-1980s and their 1991 peak before declining
dramatically through the 1990s.

---

**23. Motor Vehicle Deaths Before Modern Safety Mandates**

```
Motor vehicle accident deaths from 1979 to 1998 using dataset D77,
grouped by year and age, showing crude rate per 100,000.
```

_What to look for:_ Steady decline through the era of seat belt laws
(1984–1995), airbag mandates, and 55 mph speed limits. Young adults
(15–24) were most affected — and most improved.

---

**24. Lung Cancer Mortality: The Smoking Cohort**

```
Lung cancer deaths (ICD-9 162) from 1979 to 1998 using dataset D77,
grouped by year and sex, showing age-adjusted rate.
```

_What to look for:_ Men's lung cancer AAR peaked around 1990 and began
declining (reflecting the 1960s smoking peak). Women's rate was still
rising through the 1990s, lagging men's smoking trends by ~20 years.

---

### Vaccine Adverse Events (D8 VAERS, 1990–present)

> **Note:** VAERS reports are **not** proof of causation. Each record is a
> report submitted to the system, not a confirmed adverse event. Rates cannot
> be calculated from counts alone (the denominator — doses administered — comes
> from separate sources). Use VAERS to identify signals, not conclusions.
>
> **API note:** D8 currently has a server-side bug affecting XML API requests.
> Query building still works; execution may require workarounds.

---

**25. The COVID Vaccine Reporting Spike**

```
VAERS reports by year received using dataset D8, grouped by year received
(D8.V2-level1) and vaccine type (D8.V14-level1), showing event counts.
All vaccines, all years.
```

_What to look for:_ A dramatic spike in total reports starting in 2021 when
COVID-19 vaccines were administered at unprecedented scale. Contextualizes
why 2021–2022 VAERS totals dwarf every prior year.

---

**26. COVID-19 vs. Flu: Serious Event Profiles**

```
VAERS reports using dataset D8, grouped by vaccine type (D8.V14-level1)
and event category (D8.V11), filtered to COVID19 and FLU vaccines only,
showing event counts. Include all years.
```

_What to look for:_ Comparison of outcome category distribution (deaths,
life-threatening, hospitalized, ER, not serious) between the two most
reported vaccine types. Controls for volume by looking at category mix.

---

**27. Deaths Reported After Vaccination by Age Group**

```
VAERS reports using dataset D8, grouped by age group (D8.V1) and
vaccine type (D8.V14-level1), filtered to event category = Death (DTH),
all years. Show event counts.
```

_What to look for:_ Which age groups account for death reports, and for
which vaccines. Elderly patients have many pre-existing conditions —
expect reports concentrated in 65+ regardless of vaccine type.

---

**28. Sex Differences in Adverse Event Reporting**

```
VAERS reports using dataset D8, grouped by sex (D8.V5) and vaccine
type (D8.V14-level1), filtered to serious events (O_show serious=Y),
showing event counts. COVID19 vaccine, all years.
```

_What to look for:_ Anaphylaxis and certain cardiac events have shown
higher female reporting rates for some vaccines; autoimmune-adjacent
reactions also trend female. Male/female count ratios per vaccine type.

---

**29. Myocarditis-Class Events: COVID Vaccine by Age and Sex**

```
VAERS reports using dataset D8, grouped by age (D8.V1) and sex (D8.V5),
filtered to vaccine type = COVID19, serious events only, year received
2021 through 2024. Show event counts.
```

_What to look for:_ Myocarditis/pericarditis signal concentrated in young
males (12–29) after mRNA vaccines — the most-discussed VAERS signal of
the COVID era. See if the age/sex profile is visible in aggregate counts.

---

**30. Onset Interval: How Quickly Do Events Occur?**

```
VAERS reports using dataset D8, grouped by onset interval (D8.V7 — days
from vaccination to onset) and vaccine type (D8.V14-level1), filtered
to COVID19 vaccine. Show event counts.
```

_What to look for:_ Most serious immune reactions occur within 0–2 days.
A long tail of reports extends weeks later — these are harder to attribute
to the vaccine causally.

---

**31. Geographic Variation in VAERS Reporting**

```
VAERS reports using dataset D8, grouped by state (D8.V12) and year
received (D8.V2-level1), filtered to COVID19 vaccine and serious events
only (V_D8.V10 = Y). Show event counts.
```

_What to look for:_ Reporting rates vary by state — partly reflecting
population size, partly healthcare access, partly reporting culture.
Normalizing by doses administered would be needed for fair comparison.

---

**32. All-Cause VAERS Trend: 1990–Present**

```
VAERS reports using dataset D8, grouped by year received (D8.V2-level1)
only, all vaccines, all event types. Show total event counts.
```

_What to look for:_ The baseline reporting rate before 2020 (~40–60k/year),
the 2021 COVID spike (~900k+), and the subsequent decline. Helps put
current numbers in historical context.

---

**33. Flu Vaccine 30-Year Trend**

```
VAERS reports for flu vaccines only (F_D8.V14 = FLU) from 1990 to 2024
using dataset D8, grouped by year received and event category, showing
event counts. Compare serious vs. non-serious over time.
```

_What to look for:_ Long baseline series for a single vaccine type — useful
as a methodological check since flu vaccine administration has stayed
relatively stable, so reporting volume should reflect coverage changes.

---

## CLI Usage

```bash
# Build a query from natural language, output XML
uv run python -m wonder build "opioid deaths by year 2018-2024" -o query.xml

# Run an existing query XML file
uv run python -m wonder run queries/opioid-overdose-deaths-2018-2024-req.xml

# Run an existing query XML file, output CSV
uv run python -m wonder run queries/opioid-overdose-deaths-2018-2024-req.xml -f csv

# Build and execute in one step
uv run python -m wonder query "opioid deaths by year 2018-2024" --save-xml opioid-overdose-deaths-2018-2024-req.xml
```

**Commands:**

| Command | Description                                             |
| ------- | ------------------------------------------------------- |
| `build` | Convert natural language to CDC WONDER XML query format |
| `run`   | Execute a pre-built CDC WONDER XML query                |
| `query` | Build and execute a query in one step                   |

**Options:**

| Option                    | Commands   | Description                              |
| ------------------------- | ---------- | ---------------------------------------- |
| `-o, --output FILE`       | build      | Output file path (default: stdout)       |
| `-f, --format {json,csv}` | run, query | Output format (default: json)            |
| `-t, --timeout SECONDS`   | run, query | Request timeout in seconds (default: 60) |
| `--save-xml FILE`         | query      | Save the generated XML query to file     |
| `-v, --verbose`           | all        | Enable verbose output                    |
