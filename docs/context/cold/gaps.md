# Gap Log — logsum-sandbox
_Last updated: 2026-08-20_

This file lists honest gaps in the documented context.
Another engineer reading this in under one minute should know: what we know, what we don't, and where to look.

---

## Gap 1 — Dependency versions not pinned
`requirements.txt` lists `ruff` and `pytest` without version constraints.
Running `pip install -r requirements.txt` at different times may produce different tool versions.
**Where to look:** `requirements.txt` — consider adding `ruff==x.y.z` and `pytest==x.y.z`.

## Gap 2 — No synthetic data generator documented
`data/events.csv` and `data/sample_events.csv` exist, but there is no script or instructions for regenerating them.
If a test needs a specific edge-case dataset, it's unclear how to produce it consistently.
**Where to look:** `data/` — a `generate_fixtures.py` or a note in `spec.md` would close this gap.

## Gap 3 — `src/__pycache__` is committed to the repo
Compiled `.pyc` files appear in the tree under `src/__pycache__/` and `tests/__pycache__/`.
These should typically be in `.gitignore` to avoid noise in diffs.
**Where to look:** `.gitignore` — add `**/__pycache__/` and `**/*.pyc`.

## Gap 4 — No local dev setup instructions
There is no `CONTRIBUTING.md` or setup section in `README`.
A new engineer has no documented path from `git clone` to `pytest` passing locally.
**Where to look:** root of repo — a short "Getting started" block would close this.