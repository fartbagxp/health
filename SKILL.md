# Health Development Skill

## Project Context

Scrape and build queries to an official public health endpoints under a .gov domain.\

CDC WONDER queries documented in `docs/wonder.md`.

## Key Commands

- `uv sync` - Install dependencies
- `uv run pytest` - Run tests
- `uv run pre-commit run --all-files` - Run linters
- `uv add <package>` - Add dependency
- `uv add --dev <package>` - Add dev dependency

## Project Structure

```bash
uv run python main.py  # Main code
```

## Development Workflow

1. Make changes
2. Run pre-commit hooks automatically on commit
3. Tests run via uv run python script
4. Modify github actions
5. Update README.md to remove non-relevance.

## Important Notes

- Always support a CLI interface
- Use CDC WONDER resources from wonder.cdc.gov
- Use uv best practices

## Configuration Files

Refer to pyproject.toml and .pre-commit-config.yaml in this directory for exact setup.
