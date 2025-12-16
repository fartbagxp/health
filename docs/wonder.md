# Wonder

## Project Context

Scrape and build queries to the wonder.cdc.gov endpoint.

## Key Commands

- `uv sync` - Install dependencies
- `uv run pytest` - Run tests
- `uv run pre-commit run --all-files` - Run linters
- `uv add <package>` - Add dependency
- `uv add --dev <package>` - Add dev dependency

## Project Structure

```bash
uv run python -m src.wonder.crawl.py  # Crawl website to create a list of all links
uv run python -m src.wonder.scanner.py  # Scan Wonder to create dataset mapping between links
uv run python -m src.wonder.query --range 1-250 # Find all query parameters for each dataset
uv run python -m src.wonder.catalog # Catalog all dataset to a catalog
```
