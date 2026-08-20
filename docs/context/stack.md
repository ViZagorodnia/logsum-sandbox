# Stack Reference — logsum-sandbox

## Language
Python 3.11 — standard library only at runtime. No third-party packages in `src/`.

## Framework
None. Pure CLI tool built with `argparse` + stdlib modules (`csv`, `collections`, `pathlib`, `sys`).

## Build / package tool
`pip` with `requirements.txt` (pinned to dev deps only: `ruff`, `pytest`).
Project metadata in `pyproject.toml` (ruff config only — no setuptools/build backend).

## Test runner
`pytest` — tests live in `tests/`, fixtures in `tests/fixtures/`.
Run with: `pytest -v`
Fixture helper: `tests/conftest.py`

## Linter
`ruff` — rules: E (pycodestyle errors) + F (pyflakes), line-length 100, target Python 3.11.
Run with: `ruff check .`

## CI
GitHub Actions (`.github/workflows/ci.yml`) — triggers on push and pull_request.
Steps: checkout → Python 3.11 setup → pip install → ruff check → pytest.

## Key architectural constraint
**Single-file CLI.** All production logic lives in `src/logsum.py`. No subpackages.
New functionality goes into that file unless explicitly approved.

## Data schema
Input CSV columns (required, exact names): `timestamp`, `level`, `service`, `message`.
Data is **synthetic only** — never real customer or production data.
Sample data: `data/events.csv`, `data/sample_events.csv`.

## Exit codes
| Code | Meaning |
|------|---------|
| 0 | Success — at least one row written |
| 1 | File not found or unreadable |
| 2 | Required column missing from CSV |
| 3 | No rows in output (empty or all filtered) |