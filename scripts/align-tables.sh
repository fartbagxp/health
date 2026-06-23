#!/usr/bin/env bash
# Align all markdown tables in every *.md file under the repo.
# Uses prettier with --prose-wrap preserve so only tables are reformatted;
# surrounding prose and code blocks are left untouched.
#
# Usage:
#   ./scripts/align-tables.sh           # rewrite files in place
#   ./scripts/align-tables.sh --check   # exit 1 if any file would change (CI)
#   ./scripts/align-tables.sh --dry-run # print which files would change, no writes

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

MODE="write"
if [[ "${1:-}" == "--check" ]]; then
  MODE="check"
elif [[ "${1:-}" == "--dry-run" ]]; then
  MODE="dry-run"
fi

# Collect all .md files, excluding generated site output and venv
mapfile -t MD_FILES < <(
  find . \
    -name "*.md" \
    -not -path "./site/*" \
    -not -path "./.venv/*" \
    -not -path "./node_modules/*" \
    | sort
)

if [[ ${#MD_FILES[@]} -eq 0 ]]; then
  echo "No .md files found."
  exit 0
fi

echo "Found ${#MD_FILES[@]} markdown file(s)."

PRETTIER_OPTS=(
  --parser markdown
  --prose-wrap preserve   # reformat tables only; keep prose line breaks as-is
  --print-width 9999      # never wrap table rows mid-line
  --tab-width 2
  --end-of-line lf
)

case "$MODE" in
  write)
    npx --yes prettier "${PRETTIER_OPTS[@]}" --write "${MD_FILES[@]}"
    echo "Done. All tables aligned."
    ;;
  check)
    if npx --yes prettier "${PRETTIER_OPTS[@]}" --check "${MD_FILES[@]}"; then
      echo "All tables already aligned."
    else
      echo "Some files have unaligned tables. Run ./scripts/align-tables.sh to fix."
      exit 1
    fi
    ;;
  dry-run)
    CHANGED=()
    for f in "${MD_FILES[@]}"; do
      if ! npx --yes prettier "${PRETTIER_OPTS[@]}" --check "$f" &>/dev/null; then
        CHANGED+=("$f")
      fi
    done
    if [[ ${#CHANGED[@]} -eq 0 ]]; then
      echo "All tables already aligned."
    else
      echo "Would reformat ${#CHANGED[@]} file(s):"
      printf "  %s\n" "${CHANGED[@]}"
    fi
    ;;
esac
