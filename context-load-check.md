Here's a section-by-section summary of **CLAUDE.md**:

**Project context** — A small CLI tool (`src/logsum.py`) that reads a synthetic CSV (`data/events.csv`, columns: `timestamp`, `level`, `service`, `message`) and prints a counted summary table grouped by service and log level. It's part of the Meridian AI Factory kata series.

**Conventions** — Source lives in `src/`, tests in `tests/`, synthetic data in `data/`. One file per logical unit; no subpackages unless explicitly requested.

**Utilities to prefer** — Python 3.11 standard library only (`csv`, `argparse`, `collections`, `sys`). Linting via `ruff`, testing via `pytest`.

**Escalation gates** — Three hard stops: (1) pause and ask before adding any third-party dependency; (2) use only synthetic data, never real customer or production data; (3) never overwrite `spec.md` after sign-off without explicit confirmation.