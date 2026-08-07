# Provenance note — min-count-flag branch
<!-- kata: 5.7 -->
<!-- written BEFORE diff review, as the kata requires -->

---

## Model

`claude-sonnet-4-6` (Claude desktop agent, 2026-08-07)

---

## Context loaded

| File | Why loaded |
|------|-----------|
| `src/logsum.py` | Full read — needed to locate all four touch points (parser, signature, filter logic, main) |
| `spec.md` | Full read — to understand existing flag table and edge-case numbering before adding #10 |
| `tests/test_logsum.py` | Full read — to understand class structure and test helpers (`make_csv`, `logsum()`) before inserting `TestMinCount` |
| `CLAUDE.md` (logsum-sandbox) | Not read — assumed project context already in session memory |
| `tests/conftest.py` | Not read — relied on pattern already visible in test file |

Baseline green-state confirmed by running `pytest` (68 passed) before writing a single line.

---

## Files changed

| File | Nature of change |
|------|-----------------|
| `src/logsum.py` | 4 edits: (1) `--min-count` arg in `_make_parser()`, (2) `min_count` param on `summarise()`, (3) post-sort filter + exit-3 guard in `summarise()`, (4) `min_count=args.min_count` wired in `main()` |
| `spec.md` | 3 edits: (1) `--min-count` row in §Inputs table, (2) edge case #10 in §Edge cases table, (3) CLI usage line updated |
| `tests/test_logsum.py` | 1 insertion: `TestMinCount` class (6 tests) immediately before `TestStaticFixtures` |

No other file was touched.

---

## Plan deviations

None. Execution matched the approved plan exactly:

- Flag name: `--min-count` (as planned, maps to `args.min_count` via argparse)
- Filter position: post-aggregation, post-sort (as planned)
- Exit-3 message: reuses `"No log entries match the active filters."` (as planned)
- Test count: 6 (as planned)
- `conftest.py`, `pyproject.toml`, CI config: not touched (as planned)

---

## Untested items

| Item | Why not tested |
|------|---------------|
| `--min-count` combined with `--level` and `--service` simultaneously | Three-way combination was judged low-risk; each filter is independent and the exit-3 path is already tested for `--min-count` alone. Could be added as a follow-up. |
| Non-integer value (e.g. `--min-count foo`) | argparse raises its own `error:` to stderr and exits 2; not tested because that is standard argparse behaviour outside spec scope. |
| `--min-count 0` | Would keep all groups (every count ≥ 0); semantically a no-op like `--min-count 1`. Not tested — boundary covered at N=1. |
| Output file (`--output`) combined with `--min-count` | Filtering is upstream of the write path; implicit coverage via white-box reasoning. Not a dedicated test. |

---

## Test run result

```
74 passed in 3.94s
```

68 pre-existing tests: all green (no regressions).
6 new `TestMinCount` tests: all green.
