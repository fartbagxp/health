# WONDER Template

## Query Template Skill

The skill is live at .claude/commands/add-wonder-template.md. Here's how it works:

Usage in a future session with no context:
 /add-wonder-template
 Then tell Claude which dataset: "Add a template for D155"

What the skill gives a fresh Claude:

1. How to find and read the JSON parameter file
2. A classification guide (mortality vs infant/birth vs natality vs environmental vs VAERS) based on which O* radio buttons and M* patterns exist
3. The complete, copy-paste-ready generator script — just change DS_ID
4. Step-by-step instructions for the 4 places in llm_query_builder.py to update (TEMPLATE_DATASETS, module docstring, AGE_VARIABLES if needed, system prompt, tool schema)
5. The verification command
6. A reference table of all neutralisation rules
7. All known dataset-specific quirks as a reference
