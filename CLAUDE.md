# CLAUDE.md

## Project context
Tiny CLI (`src/logsum.py`) that reads `data/events.csv` — synthetic logs with
columns `timestamp,level,service,message` — and prints a counted summary table
grouped by service and log level. Part of the Meridian AI Factory kata series.

## Conventions
- Source code: `src/`
- Tests: `tests/`
- Data (synthetic only): `data/`
- One file per logical unit; no subpackages unless asked.

## Utilities to prefer
- Python 3.11 standard library only (`csv`, `argparse`, `collections`, `sys`)
- Linter: `ruff`
- Test runner: `pytest`

## Escalation gates
- Stop before adding any third-party dependency; ask first.
- Use synthetic data only — never real customer or production data.
- Never overwrite `spec.md` after sign-off without explicit confirmation.
