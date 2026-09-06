"""
health_depts CLI — scrape the U.S. public-health department directories that
feed the federal -> state -> county funding-flow graph.

Usage:
    uv run python -m health_depts state            # FSIS state depts
    uv run python -m health_depts local -f csv      # NACCHO local (county) depts
    uv run python -m health_depts all --out         # both -> data/processed/

The funding-flow graph is built separately from the scraped summary.json by the
Svelte project in frontend/ (see frontend/README.md).
"""

import argparse
import csv
import io
import json
import sys
from pathlib import Path

from health_depts import fsis, naccho

PROCESSED_DIR = Path("data/processed/health_depts")


def _print_output(rows: list[dict], fmt: str, cols: list[str] | None = None) -> None:
    if not rows:
        print("No results.")
        return
    if fmt == "json":
        print(json.dumps(rows, indent=2, default=str))
        return
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        print(buf.getvalue(), end="")
        return
    # table
    cols = cols or list(rows[0].keys())
    cols = [c for c in cols if c in rows[0]]
    widths = {c: max(len(c), max(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    header = "  ".join(c.ljust(widths[c]) for c in cols)
    print(header)
    print("-" * len(header))
    for r in rows:
        print("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols))


def _write_processed(states: list[dict], locals_: list[dict]) -> dict:
    """Write CSV + JSON directories and a compact per-state summary blob."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    _write_table(PROCESSED_DIR / "state_departments.csv", states, fsis.FIELDS)
    (PROCESSED_DIR / "state_departments.json").write_text(json.dumps(states, indent=2))
    _write_table(PROCESSED_DIR / "local_departments.csv", locals_, naccho.FIELDS)
    (PROCESSED_DIR / "local_departments.json").write_text(json.dumps(locals_, indent=2))

    summary = build_summary(states, locals_)
    (PROCESSED_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def _write_table(path: Path, rows: list[dict], fields: list[str]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_summary(states: list[dict], locals_: list[dict]) -> dict:
    """Per-state rollup: FSIS dept name + the state's NACCHO county depts.

    This is the exact structure inlined into the funding-flow graph, so it is
    kept compact (labels only, no addresses).
    """
    # index FSIS public-health dept name by state *name* (FSIS lists names, not codes)
    ph_by_name = {s["state"]: s.get("public_health_dept", "") for s in states}

    by_state: dict[str, dict] = {}
    for lhd in locals_:
        code = lhd["state"]
        by_state.setdefault(code, {"counties": []})
        by_state[code]["counties"].append(lhd["county"] or lhd["name"])

    out: dict[str, dict] = {}
    for code, name in naccho.STATE_NAMES.items():
        counties = sorted(set(by_state.get(code, {}).get("counties", [])))
        out[code] = {
            "name": name,
            "dept": ph_by_name.get(name, ""),
            "county_count": len(counties),
            "counties": counties,
        }
    return {
        "generated_states": len(states),
        "generated_locals": len(locals_),
        "states": out,
    }


def cmd_state(args):
    rows = fsis.scrape_state_departments()
    if args.out:
        locals_ = naccho.scrape_local_departments()
        _write_processed(rows, locals_)
        print(
            f"Wrote {len(rows)} state + {len(locals_)} local depts to {PROCESSED_DIR}"
        )
        return
    _print_output(
        rows, args.format, cols=["state", "public_health_dept", "agriculture_dept"]
    )


def cmd_local(args):
    rows = naccho.scrape_local_departments()
    _print_output(rows, args.format, cols=["name", "county", "city", "state", "phone"])


def cmd_all(args):
    states = fsis.scrape_state_departments()
    locals_ = naccho.scrape_local_departments()
    if args.out:
        summary = _write_processed(states, locals_)
        print(
            f"Wrote {summary['generated_states']} state + "
            f"{summary['generated_locals']} local depts to {PROCESSED_DIR}"
        )
    else:
        print(f"FSIS states: {len(states)}   NACCHO locals: {len(locals_)}")


def main():
    parser = argparse.ArgumentParser(
        prog="health_depts",
        description="Scrape U.S. public-health department directories "
        "(state via FSIS, local via NACCHO)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    _fmt = {"choices": ["table", "json", "csv"], "default": "table"}

    p_state = sub.add_parser("state", help="FSIS state health/agriculture depts")
    p_state.add_argument("-f", "--format", **_fmt)
    p_state.add_argument("--out", action="store_true", help="write to data/processed/")
    p_state.set_defaults(func=cmd_state)

    p_local = sub.add_parser("local", help="NACCHO local (county) health depts")
    p_local.add_argument("-f", "--format", **_fmt)
    p_local.set_defaults(func=cmd_local)

    p_all = sub.add_parser("all", help="scrape both directories")
    p_all.add_argument("--out", action="store_true", help="write to data/processed/")
    p_all.set_defaults(func=cmd_all)

    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as e:  # noqa: BLE001
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
