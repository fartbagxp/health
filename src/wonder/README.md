# WONDER

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
