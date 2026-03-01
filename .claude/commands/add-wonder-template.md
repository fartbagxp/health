# Add CDC WONDER Base Template

Generate and register a new base XML template for a CDC WONDER dataset.

## What this does

CDC WONDER queries require ~60–220 parameters. The `LLMQueryBuilder` in
`src/wonder/llm_query_builder.py` merges LLM-generated overrides onto a neutral
"base template" rather than generating the full XML from scratch. This skill
adds a new base template for a dataset that doesn't have one yet.

## When to use

When the user asks to "add a template for D{N}" or "build a template for {dataset}".

---

## Step 1 — Locate the JSON parameter file

All parameter definitions are scraped and stored as:

```bash
data/raw/wonder/query_params_D{N}.json
```

Read the file to get `page_title` and inspect `parameters.selects`,
`parameters.inputs`, and `parameters.textareas`.

---

## Step 2 — Understand the dataset type

The JSON structure is always `{ url, page_title, parameters: { selects, inputs, textareas } }`.

Inspect key families to classify the dataset:

| Family                     | How to find it                                    | Meaning                                  |
| -------------------------- | ------------------------------------------------- | ---------------------------------------- |
| `B_*` selects              | `re.match(r'^B_\d+$', name)`                      | Group-by slots (usually 2–5)             |
| `F_*` selects              | starts with `F_`                                  | Filter variables                         |
| `M_*` inputs               | starts with `M_`                                  | Measures to include                      |
| `O_*` inputs               | `O_ucd`, `O_mcd`, `O_age`, `O_race`, `O_location` | Mode selector radio buttons              |
| `O_aar` input              | present?                                          | Does dataset support age-adjusted rates? |
| `O_rate_per` select        | options?                                          | Rate denominator (1000, 100000, etc.)    |
| `VM_*` selects + textareas | starts with `VM_`                                 | Population denominators for AAR          |
| `L_*` selects              | starts with `L_`                                  | MCD cause-group list selectors           |
| `I_*` textareas            | starts with `I_`                                  | Label inputs (one per `F_*` filter)      |
| `finder-stage-*` inputs    | starts with `finder-stage-`                       | Finder mode (always `codeset`)           |

**Dataset type clues:**

- Has `O_ucd`/`O_mcd` → mortality dataset (ICD cause of death)
- Has `O_aar` → supports age-adjusted rates; template must set `O_aar_enable=false`
- Has only `M_1`, `M_2`, `M_3`; `O_rate_per` starts at `1000` → infant/birth dataset
- Has many `M_*` measures (M_11, M_12, M_21, etc.) and no `O_rate_per` → environmental dataset
- Has `O_rate_per` options `[1000, 10000, 100000, 1000000]` and birth-related variables → natality dataset
- Has `F_D{N}.V14` (vaccine) → VAERS dataset (D8)

---

## Step 3 — Run this generator script

Replace `DS_ID` with the actual dataset ID (e.g. `D177`). Run with `uv run python3`.

```python
import json, re
from pathlib import Path

DS_ID = "REPLACE_ME"
AAR_MEASURES = {'M_31', 'M_32'}

def gen_xml_param(name, values):
    if not isinstance(values, list):
        values = [values]
    lines = ["\t<parameter>", f"\t\t<name>{name}</name>"]
    for v in values:
        lines.append(f"\t\t<value>{v if v is not None else ''}</value>")
    lines.append("\t</parameter>")
    return "\n".join(lines)

with open(f'data/raw/wonder/query_params_{DS_ID}.json') as f:
    d = json.load(f)
params = d['parameters']
label = d.get('page_title', DS_ID)

selects = {s['name']: s for s in params.get('selects', [])}
all_inputs = params.get('inputs', [])
textareas = {t['name']: t for t in params.get('textareas', [])}

inputs_by_name = {}
inputs_ordered = []
for i in all_inputs:
    name = i['name']
    if name not in inputs_by_name:
        inputs_by_name[name] = []
        inputs_ordered.append(name)
    inputs_by_name[name].append(i.get('value', ''))

SKIP = {'query', 'affiliate', 'sitelimit', 'saved_id', 'tab-about', 'tab-chart',
        'tab-map', 'tab-results', 'action-Reset', 'action-Save'}
SKIP_PREFIXES = ('finder-action-', 'input_')
def should_skip(name):
    return name in SKIP or any(name.startswith(p) for p in SKIP_PREFIXES)

has_aar = 'O_aar' in inputs_by_name or 'O_aar_enable' in inputs_by_name
aar_measures_to_skip = AAR_MEASURES if has_aar else set()

o_emitted = set()
def emit_o(name, value=None):
    o_emitted.add(name)
    v = value if value is not None else (inputs_by_name[name][0] if name in inputs_by_name else '')
    return gen_xml_param(name, [v])

out = []

# B_* → *None* (only slots that exist in the form)
for name in selects:
    if re.match(r'^B_\d+$', name):
        out.append(gen_xml_param(name, ['*None*']))

# F_* → *All*
for name in selects:
    if name.startswith('F_'):
        out.append(gen_xml_param(name, ['*All*']))

# I_* textareas → ""
for name in textareas:
    if name.startswith('I_'):
        out.append(gen_xml_param(name, ['']))

# L_* → *All*
for name in selects:
    if name.startswith('L_'):
        out.append(gen_xml_param(name, ['*All*']))

# M_* → actual values (exclude M_31/M_32 only when dataset has AAR)
m_params = {}
for name in inputs_ordered:
    if name.startswith('M_') and name not in aar_measures_to_skip and not should_skip(name):
        if name not in m_params:
            m_params[name] = inputs_by_name[name][0]
def m_sort_key(k):
    n = k.split('_')[1]
    return int(n) if n.isdigit() else 999
for name in sorted(m_params.keys(), key=m_sort_key):
    out.append(gen_xml_param(name, [m_params[name]]))

# O_* output options
if 'O_rate_per' in selects:
    opts = [o['value'] for o in selects['O_rate_per'].get('options', []) if o['value'] not in ('*All*', '')]
    out.append(emit_o('O_rate_per', opts[0] if opts else '100000'))
elif 'O_rate_per' in inputs_by_name:
    out.append(emit_o('O_rate_per'))

if 'O_aar_pop' in selects or 'O_aar_pop' in inputs_by_name:
    out.append(emit_o('O_aar_pop', '0000'))

if 'O_export-format' in selects:
    out.append(emit_o('O_export-format', 'xls'))
if 'O_precision' in selects:
    out.append(emit_o('O_precision', '1'))
out.append(emit_o('O_timeout', '600'))
out.append(emit_o('O_javascript', 'on'))

if has_aar:
    out.append(emit_o('O_aar', 'aar_none'))
    out.append(emit_o('O_aar_enable', 'false'))
    out.append(emit_o('O_aar_CI', 'false'))
    out.append(emit_o('O_aar_SE', 'true'))

out.append(emit_o('O_title', ''))
if 'O_oc-sect1-request' in inputs_by_name:
    out.append(emit_o('O_oc-sect1-request', 'close'))

if has_aar:
    out.append(emit_o('O_post_pops', 'true'))
    out.append(emit_o('O_aar_nonstd', 'true'))

if 'O_location' in inputs_by_name:
    out.append(emit_o('O_location', inputs_by_name['O_location'][0]))

for name in inputs_ordered:
    if re.match(r'^O_V\d+_fmode$', name) and not should_skip(name):
        out.append(emit_o(name, inputs_by_name[name][0]))

for radio in ('O_urban', 'O_max', 'O_min', 'O_age', 'O_race', 'O_ucd', 'O_mcd'):
    if radio in inputs_by_name:
        out.append(emit_o(radio, inputs_by_name[radio][0]))

out.append(emit_o('O_change_action-Send-Export Results', 'Export Results'))
out.append(emit_o('O_show_totals', 'true'))
out.append(emit_o('O_show_zeros', 'true'))
out.append(emit_o('O_show_suppressed', 'true'))

# Catch-all: any remaining O_ inputs not yet emitted
for name in inputs_ordered:
    if name.startswith('O_') and name not in o_emitted and not should_skip(name):
        out.append(gen_xml_param(name, [inputs_by_name[name][0]]))

# VM_* selects → *All*, VM_* textareas → ""
for name in selects:
    if name.startswith('VM_'):
        out.append(gen_xml_param(name, ['*All*']))
for name in textareas:
    if name.startswith('VM_'):
        out.append(gen_xml_param(name, ['']))

# V_* selects → *All* (V6 → "00" — infant age group)
for name in selects:
    if name.startswith('V_'):
        var = name.split('.')[-1] if '.' in name else ''
        out.append(gen_xml_param(name, ['00' if var == 'V6' else '*All*']))

# V_* textareas → ""
for name in textareas:
    if name.startswith('V_'):
        out.append(gen_xml_param(name, ['']))

# action-Send, dataset_*, finder-stage-*, stage
out.append(gen_xml_param('action-Send', ['Send']))
out.append(gen_xml_param('dataset_code', [DS_ID]))
out.append(gen_xml_param('dataset_label', [label]))
out.append(gen_xml_param('dataset_vintage', ['']))
for name in inputs_ordered:
    if name.startswith('finder-stage-'):
        out.append(gen_xml_param(name, ['codeset']))
out.append(gen_xml_param('stage', ['request']))

xml = '<?xml version="1.0" encoding="UTF-8"?><request-parameters>\n'
xml += '\n'.join(out)
xml += '\n</request-parameters>\n'

out_path = Path(f'src/wonder/templates/{DS_ID}-base.xml')
out_path.write_text(xml)
print(f"Wrote {out_path} ({xml.count('<parameter>')} params)")
```

---

## Step 4 — Register the dataset in `llm_query_builder.py`

**4a. Add to `TEMPLATE_DATASETS`:**

```python
# In src/wonder/llm_query_builder.py, find TEMPLATE_DATASETS and add:
"D{N}",  # {short description}
```

**4b. Add to the module docstring** (dataset list at top of file).

**4c. If the dataset has AAR and age variables, add them to `AGE_VARIABLES`:**

```python
# Only needed for datasets where O_aar_enable exists AND V5/V51/V52/V6 are age group variables
"D{N}.V5", "D{N}.V51", "D{N}.V52", "D{N}.V6",
```

**4d. Update the system prompt dataset list** — find the block under `## Process` and
add an entry under the appropriate category (mortality / infant / natality / environmental / VAERS).

**4e. Update the tool schema** — find the `dataset_id` description string and append
`'D{N}' ({label}),`.

---

## Step 5 — Verify

```bash
uv run python3 -c "
from wonder.llm_query_builder import TEMPLATE_DATASETS
from pathlib import Path
templates_dir = Path('src/wonder/templates')
missing = [ds for ds in TEMPLATE_DATASETS if not (templates_dir / f'{ds}-base.xml').exists()]
print(f'Total: {len(TEMPLATE_DATASETS)} | Missing: {missing or \"none\"}')
"
```

---

## Key neutralisation rules (reference)

| Parameter family  | Template value           | Exception                                 |
| ----------------- | ------------------------ | ----------------------------------------- |
| `B_1..B_N`        | `*None*`                 | —                                         |
| `F_*` selects     | `*All*`                  | —                                         |
| `I_*` textareas   | `""`                     | —                                         |
| `L_*` selects     | `*All*`                  | —                                         |
| `M_*` inputs      | actual measure code      | Exclude `M_31`/`M_32` when `has_aar=True` |
| `V_*` selects     | `*All*`                  | `V6` (infant age) → `"00"`                |
| `V_*` textareas   | `""`                     | —                                         |
| `VM_*` selects    | `*All*`                  | —                                         |
| `VM_*` textareas  | `""`                     | —                                         |
| `finder-stage-*`  | `codeset`                | —                                         |
| `O_aar_enable`    | `false`                  | Only include if `has_aar=True`            |
| `O_aar`           | `aar_none`               | Only include if `has_aar=True`            |
| `O_ucd`           | first radio value        | Only if present (mortality datasets)      |
| `O_mcd`           | first radio value        | Only if present (MCD datasets)            |
| `O_age`           | first radio value        | Only if present                           |
| `O_race`          | first radio value        | Only if present                           |
| `O_location`      | first radio value        | Only if present                           |
| `O_rate_per`      | first non-`*All*` option | Skip entirely if not in form              |
| `O_precision`     | `1`                      | Skip if not in form                       |
| `O_export-format` | `xls`                    | Skip if not in form                       |

## Known dataset-specific quirks

- **D74** (Compressed 1968–1978): `O_rate_per=1000`, no `O_ucd`, ICD-8 codes
- **D77/D76/D141/D74/D16/D140**: bridged race via `V8`, no `O_race` selector
- **D104**: only 2 B\_ slots
- **D8** (VAERS): XML API has a persistent CDC server bug — queries build correctly but cannot execute via CLI
- **D149/D192**: M\_ names use 3-digit zero-padded format (`M_002`, `M_070`, etc.)
- Environmental datasets (D60/D61/D73/D80/D81/D104): no `O_rate_per`, all M\_ measures are statistical summaries (mean/min/max/CI) — include ALL of them regardless of M_31/M_32
