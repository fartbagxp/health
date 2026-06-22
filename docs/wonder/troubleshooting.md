# Troubleshooting

Common WONDER query errors and how to fix them.

---

## "More than 75,000 cells requested"

**Error message:** `The data request has exceeded the limit of 75,000 cells.`

**Cause:** Your combination of group-by dimensions and filter ranges would return too many rows.

**Fix:** Reduce the result size. Strategies in order of preference:

1. **Query one year at a time** and loop with `time.sleep(16)` between calls:

   ```python
   for year in range(2018, 2025):
       rows = client.query_with_llm(f"... by state {year} ...")
   ```

2. **Remove one group-by dimension** — e.g., drop sex or race from a state × year query.

3. **Filter to fewer states** — query one region or a handful of states at once.

4. **Use a coarser age grouping** — 10-year bands instead of 5-year bands.

See [All-State Queries](multi-state.md) for the full size table.

---

## "15 second rate limit" / connection refused

**Error:** HTTP 429, `Too Many Requests`, or immediate connection failure on the second query.

**Cause:** WONDER enforces at least 15 seconds between requests from the same IP.

**Fix:** Always sleep between queries:

```python
import time
time.sleep(16)  # 1 second margin
```

If a script fails mid-run and you restart quickly, WONDER may still be timing out your IP. Wait 30 seconds before retrying.

---

## Suppressed values in output

**Symptom:** Some rows show `"Suppressed"` instead of a number for Deaths.

**Cause:** NCHS suppresses counts below 10 to protect privacy. Common in small states, rare causes, or narrow age/race groups.

**This is expected behavior.** Handle it in your code:

```python
def safe_float(val):
    if str(val).strip() in ("Suppressed", "Missing", "Not Applicable", ""):
        return None
    try:
        return float(str(val).replace(",", ""))
    except ValueError:
        return None
```

If you need estimates for suppressed cells, consider switching to a coarser grouping (fewer dimensions) or using CDC Wonder's suppression-less datasets where available.

---

## Wrong or empty results — silent filter mismatch

**Symptom:** Query succeeds but returns all-cause totals instead of the filtered cause, or returns zeros.

**Cause:** `O_ucd` or `O_race` mode selector doesn't match the active filter. WONDER silently ignores the filter.

**Fix:** Use `wonder build` to inspect the XML and verify the `O_*` parameters match:

```bash
uv run python -m wonder build "your query here" | grep -A2 "O_ucd\|O_race\|O_age"
```

Expected alignment:

| If you filter    | Then O\_ must be                           |
| ---------------- | ------------------------------------------ |
| ICD cause (UCD)  | `O_ucd = D176.V25` (or dataset equivalent) |
| ICD cause (MCD)  | `O_ucd = D176.V24`                         |
| No ICD filter    | `O_ucd = *All*`                            |
| Race             | `O_race = D176.V7`                         |
| No race filter   | `O_race = *All*`                           |
| Age group        | `O_age = D176.V5`                          |
| No age filter    | `O_age = *All*`                            |
| Gender           | `O_sex = D176.V6`                          |
| No gender filter | `O_sex = *All*`                            |

---

## Age-adjusted rate missing / blank

**Symptom:** AAR column is blank or WONDER returns an error about age-adjusted rates.

**Cause 1:** You're grouping by age group. AAR cannot be computed when the result is split by age.

**Fix:** Remove age from group-by, or request crude rate instead:

```bash
# Wrong: group by age + request AAR
uv run python -m wonder query "deaths by age group 2020, age-adjusted rate"

# Right: group by something else
uv run python -m wonder query "deaths by year 2020, age-adjusted rate"
# or
uv run python -m wonder query "deaths by age group 2020, crude rate"
```

**Cause 2:** Small population in the cell. WONDER requires a minimum population to compute AAR. If the denominator is too small, AAR is suppressed.

---

## D27 natality 500 error

**Symptom:** Natality query for 2003–2006 returns a server 500 error.

**Cause:** Dataset D27 requires a full base template with all required parameters populated. It's stricter than D66.

**Fix:** Use `wonder build` to generate the XML (the LLM includes all required parameters), then submit it with `wonder run` rather than the query shortcut:

```bash
uv run python -m wonder build \
  "births by state 2003-2006, dataset D27" \
  > births-2003-2006-req.xml

uv run python -m wonder run births-2003-2006-req.xml -f csv
```

---

## VAERS (D8) queries fail

**Symptom:** All VAERS queries return an error or an empty response regardless of parameters.

**Cause:** There is a known server-side bug in WONDER's XML API for D8.

**Fix:** The XML API doesn't work for VAERS. Instead:

1. Generate the XML: `uv run python -m wonder build "VAERS query..." > vaers-query.xml`
2. Go to [WONDER VAERS web interface](https://wonder.cdc.gov/vaers.html)
3. Paste or import the XML manually

---

## "No data found" for valid query

**Symptom:** WONDER returns 0 rows for a query that should have results.

**Common causes:**

1. **Year out of range for dataset** — e.g., asking D176 for 2017 (it starts 2018). Check the [Dataset Reference](datasets.md).

2. **Cause code not valid for dataset** — ICD-10 codes work in D77/D176; ICD-9 codes work in D16. Mixing eras returns nothing.

3. **State FIPS code wrong** — D176 uses 2-digit FIPS (`48` for Texas), not abbreviations.

4. **Age group label doesn't match exactly** — WONDER age group labels are very specific. Use `*All*` and let the LLM pick the right label.

---

## LLM-generated XML has syntax errors

**Symptom:** `wonder run` fails to parse the XML file.

**Fix:** Validate with Python's built-in XML parser:

```bash
python -c "import xml.etree.ElementTree as ET; ET.parse('my-query.xml')"
```

If it fails, the XML is malformed. Regenerate with `wonder build` using a clearer prompt.

---

## Slow queries / timeouts

WONDER queries typically take 2–10 seconds. If a query hangs:

1. The WONDER server occasionally goes down for maintenance (usually weekday mornings). Check [wonder.cdc.gov](https://wonder.cdc.gov) directly.

2. Very large results (near the 75,000-cell limit) take longer. Try reducing dimensions first.

3. The default timeout is 60 seconds. Override for large queries:
   ```python
   from wonder.client import WonderClient
   client = WonderClient(timeout=120)
   ```

---

## Comparing D77 and D176 on overlapping years (2018–2020)

D77 (final) and D176 (provisional) both cover 2018–2020. Expect small differences:

- D176 2018–2020 values may differ from D77 by 1–5% due to late-arriving death certificates
- For publications, prefer D157 or D77 for confirmed final data
- For trend monitoring, D176 is fine

Use [priority-based merging](multi-year.md#merging-results-when-epochs-overlap) when combining datasets.
