# Agent Replay Provenance

## Run metadata

- **Model**: claude-sonnet-4-6
- **Branch**: agent-replay
- **Date**: 2026-08-07

---

## Files read

| File | Status |
|------|--------|
| `spec.md` | Read in full — single source of truth |
| `tests/conftest.py` | Read — needed to understand `make_csv` fixture |
| `pyproject.toml` | Read — confirmed ruff lint rules (E, F) |
| `requirements.txt` | Read — confirmed deps: ruff, pytest |
| `.github/workflows/ci.yml` | Read — verified CI steps |
| `src/__init__.py` | Read — confirmed package marker exists |

### Supervised files explicitly skipped

| File | Reason |
|------|--------|
| `src/logsum.py` | **Not read** — replay must be independent |
| `tests/test_logsum.py` | **Not read** — replay must be independent |

---

## Files changed

| File | Action |
|------|--------|
| `src/logsum.py` | Overwritten with fresh implementation |
| `tests/test_logsum.py` | Overwritten with fresh test suite |
| `src/debug_temp.py` | Deleted — file was a deliberate ruff F401 demo artifact with comment "Fix: delete this file entirely in the follow-up commit" |

---

## Implementation decisions

### Two-counter exit-3 distinction
The spec's Implementation notes explicitly flag this as a trap: a single `len(counts) == 0`
check cannot distinguish "header-only file" from "rows existed but were filtered out."
Solution: `aggregate()` returns `(counts, total_data_rows, missing_col)`. In `main`, the
branch is `if total_data_rows == 0: "No log entries found." else: "No log entries match
the active filters."` This covers edge cases 3, 4, and 10 with a single discriminator.

### Positional shorthand
`build_parser` registers a hidden `nargs="*"` positional slot. `resolve_args` then absorbs
them into `--input` / `--output` when those flags are absent. `--input` is NOT marked
`required=True` in argparse because that would reject the positional-only invocation style
before absorption can happen.

### No trailing newline
Output uses `"\n".join(lines)` rather than iterating with `print()`. Since service names
in the Meridian domain never contain commas, the manual f-string format is safe and avoids
pulling in csv.writer's line-terminator complexity.

### Refactor pass (Step 5)
After first draft: removed `matched_rows` counter from `aggregate()` — it was computed and
returned but never consumed in `main`. The `total_data_rows` counter alone is sufficient to
discriminate all three exit-3 scenarios (header-only / level-service filter / min-count filter).

---

## CI check (Step 4)

`.github/workflows/ci.yml` runs `ruff check .` and `pytest -v`. Both pass on this branch
with no changes to the CI config itself. The pre-existing `src/debug_temp.py` (which
deliberately imported `os` to trigger F401) was blocking ruff; it was deleted as the file's
own comment instructed.

---

## Plan deviations

None significant. The implementation followed the spec linearly. The only deviation from
a naively literal reading was normalising the `--level` and `--service` *filter* values
(strip/uppercase) before comparing against normalised row values — the spec doesn't
explicitly say to normalise filter arguments, but without this `--level warn` would fail
to match rows with `level = "WARN"`.

---

## Untested items (with reasons)

| Item | Reason untested |
|------|-----------------|
| Permission-denied (exit 1 variant) | Creating a truly unreadable file reliably in a tmp_path environment is platform-sensitive and would require root/chmod operations |
| Truly empty file (0 bytes, no header) | `make_csv` always writes at least a header line; would require a separate `tmp_path.write_bytes(b"")` fixture; treated as missing-column under the spec anyway |
| `--output` path that is unwritable | Same platform-sensitivity as permission-denied input; spec doesn't define a distinct exit code for write errors |
| Column order variants in CSV header | Spec says "order is not important" — tested implicitly via the required-column checks but not with permuted headers |

---

## Final test run

```
77 passed in 3.93s
```

---

## Spec ambiguities encountered

1. **Filter normalisation not explicitly specified.** The spec says `--level` filters "to a single level" but doesn't say whether the filter value itself is normalised before comparison. Given that level values are normalised to UPPERCASE before grouping, it is only sensible to normalise the filter value too. Implemented as: `level_filter.strip().upper()`.

2. **Completely empty file (0 bytes).** Not distinguished from "missing required column" in the spec. The spec's edge case 3 says "Header-only file" → exit 3, but a 0-byte file has no header at all. Treated as exit 2 (missing column) because `csv.DictReader.fieldnames` returns `None`, which fails the required-column check.

3. **"No trailing newline beyond the last data row"** — it is ambiguous whether this applies only to stdout or also to `--output` files. Implemented consistently for both.

---

## Notable differences from a supervised human-guided session

- **debug_temp.py deletion**: A supervised session would likely have caught this on the first CI run and deleted it in a follow-up commit. The replay deleted it proactively once ruff flagged it.
- **Fewer micro-iterations**: A human-guided session typically has a back-and-forth "first draft → run tests → fix one thing at a time." The replay produced 77/77 passing tests on the first full test run with only two minor ruff lint fixes required (unused import, ambiguous variable name).
- **`matched_rows` was drafted then refactored away**: The spec's Implementation notes about two counters led to an initial draft with three counters (`total_data_rows`, `matched_rows`, `counts`). A human reviewer would likely catch the redundancy immediately; the agent caught it on the self-review pass.
- **Test count**: 77 tests vs what a supervised session with incremental feedback might produce (likely similar range, but test naming and grouping could differ).
