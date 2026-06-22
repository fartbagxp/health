# Parameter Reference

WONDER queries are XML documents with five parameter types: **B** (group-by), **M** (measures), **F** (filters), **V** (value lists), and **O** (options/mode selectors). The LLM builder handles these automatically, but understanding the structure helps when you need to hand-edit XML or debug unexpected results.

## Parameter types overview

| Prefix | Full name     | Role                                                     |
| ------ | ------------- | -------------------------------------------------------- |
| `B_*`  | Group-by      | Columns to group results by (dimensions)                 |
| `M_*`  | Measure       | Metrics to include (death count, crude rate, AAR)        |
| `F_*`  | Filter        | Restrict to a subset (year range, state, race, ICD code) |
| `V_*`  | Value         | Multi-select list for a filter (used with `F_*`)         |
| `O_*`  | Option / mode | Mode selectors that must align with active filters       |

---

## B — Group-by parameters

`B_1` is the primary group-by; `B_2`, `B_3`, `B_4` are additional dimensions.

### D176/D157/D77 common group-by codes

| Code              | Description                             |
| ----------------- | --------------------------------------- |
| `D176.V1-level1`  | Year                                    |
| `D176.V9-level1`  | State (2-letter FIPS label)             |
| `D176.V9-level2`  | County                                  |
| `D176.V10`        | Census Region (4 regions)               |
| `D176.V27-level1` | HHS Region (10 regions)                 |
| `D176.V5`         | Age group                               |
| `D176.V6`         | Gender                                  |
| `D176.V7`         | Race (bridged, 5 groups)                |
| `D176.V8`         | Hispanic origin                         |
| `D176.V17`        | Race × Hispanic origin                  |
| `D176.V25`        | ICD-10 cause of death (chapter/section) |

!!! tip
The LLM builder sets these automatically. To see what was generated, run `wonder build` and inspect the XML.

---

## M — Measure parameters

Common measures (set to `D176.M1`, `D176.M2`, etc.):

| Code       | Measure                     |
| ---------- | --------------------------- |
| `D176.M1`  | Deaths                      |
| `D176.M2`  | Population                  |
| `D176.M3`  | Crude Rate                  |
| `D176.M31` | Standard Error (Crude Rate) |
| `D176.M32` | 95% CI — Lower (Crude Rate) |
| `D176.M33` | 95% CI — Upper (Crude Rate) |
| `D176.M4`  | Age-Adjusted Rate           |
| `D176.M41` | Standard Error (AAR)        |
| `D176.M42` | 95% CI — Lower (AAR)        |
| `D176.M43` | 95% CI — Upper (AAR)        |

---

## F — Filter parameters

Filters restrict the query. The filter parameter specifies a dimension; its value is the selected option.

### Year filter

```xml
<!-- Single year -->
<F_D176.V1 value="2023"/>

<!-- Year range -->
<F_D176.V1 value="2018" value2="2023"/>

<!-- List of years -->
<V_D176.V1 value="2020"/>
<V_D176.V1 value="2021"/>
<V_D176.V1 value="2022"/>
```

### State filter

```xml
<!-- All states -->
<F_D176.V9 value="*All*"/>

<!-- Single state (FIPS code) -->
<F_D176.V9 value="48"/>  <!-- Texas -->

<!-- Multiple states -->
<V_D176.V9 value="06"/>  <!-- California -->
<V_D176.V9 value="36"/>  <!-- New York -->
<V_D176.V9 value="48"/>  <!-- Texas -->
```

### Age filter

```xml
<!-- All ages -->
<F_D176.V5 value="*All*"/>

<!-- Specific age group -->
<F_D176.V5 value="25-34 years"/>

<!-- Custom: 25 to 64 requires listing individual bands -->
<V_D176.V5 value="25-34 years"/>
<V_D176.V5 value="35-44 years"/>
<V_D176.V5 value="45-54 years"/>
<V_D176.V5 value="55-64 years"/>
```

### Gender filter

```xml
<F_D176.V6 value="*All*"/>     <!-- all -->
<F_D176.V6 value="M"/>          <!-- male only -->
<F_D176.V6 value="F"/>          <!-- female only -->
```

### Race filter (D176/D77 bridged, 5 groups)

```xml
<F_D176.V7 value="*All*"/>
<F_D176.V7 value="1"/>   <!-- White -->
<F_D176.V7 value="2"/>   <!-- Black or African American -->
<F_D176.V7 value="3"/>   <!-- American Indian or Alaska Native -->
<F_D176.V7 value="4"/>   <!-- Asian or Pacific Islander -->
```

### Hispanic origin filter

```xml
<F_D176.V8 value="*All*"/>
<F_D176.V8 value="2135-2"/>  <!-- Hispanic or Latino -->
<F_D176.V8 value="2186-5"/>  <!-- Not Hispanic or Latino -->
```

### ICD-10 cause of death filter (MCD)

```xml
<!-- All causes -->
<F_D176.V25 value="*All*"/>

<!-- Drug overdose (all drug-induced) -->
<F_D176.V25 value="D1"/>

<!-- Opioids (T40.0-T40.6) — requires listing individual 3-char codes -->
<V_D176.V25 value="T400"/>
<V_D176.V25 value="T401"/>
<V_D176.V25 value="T402"/>
<V_D176.V25 value="T403"/>
<V_D176.V25 value="T404"/>
<V_D176.V25 value="T405"/>
<V_D176.V25 value="T406"/>

<!-- Firearms (W32-W34, X72-X74, X93-X95, Y22-Y24) -->
<V_D176.V25 value="W32"/>
<V_D176.V25 value="W33"/>
<V_D176.V25 value="W34"/>
<V_D176.V25 value="X72"/>
<!-- ... etc -->
```

---

## O — Option / mode selectors

Options are metadata flags that must match your active filters. A mismatch causes WONDER to silently ignore the filter.

### Most important O parameters

| Parameter          | Values                                           | Must match             |
| ------------------ | ------------------------------------------------ | ---------------------- |
| `O_age`            | `D176.V5` (age enabled), `*All*` (no age filter) | Active age filter      |
| `O_sex`            | `D176.V6`, `*All*`                               | Active gender filter   |
| `O_race`           | `D176.V7`, `*All*`                               | Active race filter     |
| `O_hispanicOrigin` | `D176.V8`, `*All*`                               | Active Hispanic filter |
| `O_ucd`            | `D176.V25` (UCD), `D176.V24` (MCD), `*All*`      | ICD filter mode        |
| `O_aar`            | `D176.M4` (include AAR), `*None*` (exclude)      | Age-adjusted rate      |

### AAR + age group conflict

Age-adjusted rates require WONDER to sum across age groups internally. If you group by age (`B_1 = D176.V5`), AAR cannot be computed:

```xml
<!-- WRONG: can't compute AAR when grouping by age -->
<B_1 value="D176.V5"/>
<M_D176.M4 value="D176.M4"/>  <!-- ← WONDER ignores this silently -->

<!-- RIGHT: either group by age (no AAR) or request AAR (no age grouping) -->
<B_1 value="D176.V1"/>        <!-- group by year instead -->
<M_D176.M4 value="D176.M4"/>  <!-- AAR works now -->
```

The LLM builder handles this automatically.

---

## Full XML structure for D176

Minimal valid query XML for D176:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<request-parameters>
  <!-- Dataset -->
  <parameter>
    <name>dataset_code</name>
    <value>D176</value>
  </parameter>

  <!-- Group by: year and state -->
  <parameter>
    <name>B_1</name>
    <value>D176.V1-level1</value>
  </parameter>
  <parameter>
    <name>B_2</name>
    <value>D176.V9-level1</value>
  </parameter>

  <!-- Measures: deaths and crude rate -->
  <parameter>
    <name>M_D176.M1</name>
    <value>D176.M1</value>
  </parameter>
  <parameter>
    <name>M_D176.M3</name>
    <value>D176.M3</value>
  </parameter>

  <!-- Filters -->
  <parameter>
    <name>F_D176.V1</name>
    <value>2018</value>
    <value2>2024</value2>
  </parameter>
  <parameter>
    <name>F_D176.V9</name>
    <value>*All*</value>
  </parameter>
  <parameter>
    <name>F_D176.V5</name>
    <value>*All*</value>
  </parameter>
  <parameter>
    <name>F_D176.V6</name>
    <value>*All*</value>
  </parameter>
  <parameter>
    <name>F_D176.V7</name>
    <value>*All*</value>
  </parameter>
  <parameter>
    <name>F_D176.V8</name>
    <value>*All*</value>
  </parameter>
  <parameter>
    <name>F_D176.V25</name>
    <value>*All*</value>
  </parameter>

  <!-- Options: must match active filters -->
  <parameter>
    <name>O_age</name>
    <value>*All*</value>
  </parameter>
  <parameter>
    <name>O_sex</name>
    <value>*All*</value>
  </parameter>
  <parameter>
    <name>O_race</name>
    <value>*All*</value>
  </parameter>
  <parameter>
    <name>O_hispanicOrigin</name>
    <value>*All*</value>
  </parameter>
  <parameter>
    <name>O_ucd</name>
    <value>*All*</value>
  </parameter>
  <parameter>
    <name>O_aar</name>
    <value>*None*</value>
  </parameter>
</request-parameters>
```

---

## Inspecting LLM-generated XML

To see exactly what parameters the LLM generated for any query, use `wonder build`:

```bash
uv run python -m wonder build \
  "firearm deaths by state and year 2018-2024, age-adjusted rate" \
  | python -m xml.dom.minidom /dev/stdin
```

This shows the full parameter list without executing the query — useful for debugging or saving a query for later reuse.
