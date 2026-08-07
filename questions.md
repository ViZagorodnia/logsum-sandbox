# questions.md — Kata 5.8

Three questions about the `logsum` repo, each answered with exact file:line citations
and a verification verdict.

---

## Q1 — Where is the grouping rule?

**Files read:** `spec.md`, `src/logsum.py`

**Answer:**
The group key is the two-field tuple `(service, level)` after normalisation.
Every unique pair produces exactly one output row. Grouping is case-sensitive on
`service` (original casing preserved) and effectively case-insensitive on `level`
(because the normalisation step converts `level` to UPPERCASE before grouping, so
two rows with `"warn"` and `"WARN"` land in the same group). Timestamp and message
values never split groups.

**Citations:**
- `spec.md:92` — "The group key is the tuple `(service, level)` after normalisation."
- `spec.md:96–97` — "Grouping is case-sensitive on `service` and case-insensitive on
  `level` (because `level` is already uppercased by the normalisation step)."
- `src/logsum.py:153` — `counts[(service_norm, level_norm)] += 1` — the Counter is keyed
  on the normalised pair, directly implementing the spec rule.

**Unverifiable:** Nothing — the spec rule and its implementation are both directly readable.

---

## Q2 — How is missing level handled?

**Files read:** `spec.md`, `src/logsum.py`

**Answer:**
"Missing level" covers two distinct scenarios:

**Scenario A — the `level` column is absent from the CSV header entirely.**
The tool exits with code 2 and prints `Missing required column: level` to stderr.
No output is written.

**Scenario B — the `level` column exists but a data row has an empty value.**
The empty string is processed by `_norm_level`: `"".strip().upper()` remains `""`.
The row is counted normally under a group keyed `(service, "")` — the empty string
is kept as-is in the output and is NOT mapped to `OTHER`.

**Citations:**
- `spec.md:122` — edge case #2: "CSV missing a required column — Exit 2; stderr:
  `Missing required column: <column-name>`" (scenario A)
- `spec.md:128` — edge case #8: "Empty `level` field (blank string after normalisation)
  — Treated as unknown level; kept as empty string `""` in output" (scenario B)
- `spec.md:84–86` — "Unknown level values … are kept as-is in the output … They are
  **not** collapsed into `OTHER`." (applies to both unknown and empty levels)
- `src/logsum.py:95–97` — `_norm_level` returns `raw.strip().upper()` — empty string
  stays `""`
- `src/logsum.py:144` — `level_norm = _norm_level(row.get(lv_col, ""))` — if a row is
  somehow missing the field at runtime, it defaults to `""` before normalisation

**Unverifiable:** Nothing — all paths are directly traceable in source and spec.

---

## Q3 — How do I run tests and CI locally?

**Files read:** `.github/workflows/ci.yml`, `requirements.txt`, `CLAUDE.md`, `ci-notes.md`

**Answer:**
From the repo root (same directory as `src/`, `tests/`, `requirements.txt`):

```
pip install -r requirements.txt   # installs ruff and pytest
ruff check .                       # linter — must pass before tests in CI
pytest -v                          # full test suite
```

CI runs these two steps in exactly this order on Python 3.11 on ubuntu-latest.
There is no editable-install step (`pip install -e .`) in the workflow — the tests
invoke `python -m src.logsum` directly, which works because `src/` has an
`__init__.py` and pytest is run from the repo root.

**Citations:**
- `requirements.txt:1–2` — the only two dependencies: `ruff`, `pytest`
- `.github/workflows/ci.yml:18` — `python-version: "3.11"`
- `.github/workflows/ci.yml:21` — `run: pip install -r requirements.txt`
- `.github/workflows/ci.yml:24` — `run: ruff check .`
- `.github/workflows/ci.yml:27` — `run: pytest -v`
- `ci-notes.md:6–7` — "Steps: ruff check . → pytest -v / Python: 3.11"
- `CLAUDE.md:16–17` — "Linter: `ruff` / Test runner: `pytest`"

**Unverifiable:** Whether a strictly Python-3.11 interpreter is required locally — the
spec says stdlib only, but no `.python-version` file or `pyenv` config enforces this
for local runs. Tests likely pass on 3.10+ since only standard syntax is used.

---

## Verification

Each citation was opened and the actual line content compared against the claim.
Two off-by-4 errors were found in Q1; both were corrected above.

| Q | Citation (as written) | Claim | Actual line | Verdict |
|---|---|---|---|---|
| Q1 | `spec.md:92` *(was :96)* | "The group key is the tuple `(service, level)` after normalisation." | Line 92: "The group key is the tuple `(service, level)` after normalisation." | ✅ correct after fix (was **off-by-4**) |
| Q1 | `spec.md:96–97` *(was :100–101)* | "Grouping is case-sensitive on `service` and case-insensitive on `level`…" | Lines 96–97: "Grouping is case-sensitive on `service` and case-insensitive on `level` (because `level` is already uppercased by the normalisation step)." | ✅ correct after fix (was **off-by-4**) |
| Q1 | `src/logsum.py:153` | Counter keyed on `(service_norm, level_norm)` | `counts[(service_norm, level_norm)] += 1` | ✅ correct |
| Q2 | `spec.md:84–86` | Unknown levels not collapsed to OTHER | Lines 84–86: "Unknown level values … are kept as-is … **not** collapsed into `OTHER`." | ✅ correct |
| Q2 | `spec.md:122` | Edge case #2 — missing column → exit 2 | `\| 2 \| CSV missing a required column \| Exit 2; stderr: Missing required column: …` | ✅ correct |
| Q2 | `spec.md:128` | Edge case #8 — empty level kept as `""` | `\| 8 \| Empty \`level\` field (blank string after normalisation) \| Treated as unknown level; kept as empty string …` | ✅ correct |
| Q2 | `src/logsum.py:95–97` | `_norm_level` strips and uppercases | `def _norm_level(raw: str) -> str:` → `return raw.strip().upper()` | ✅ correct |
| Q2 | `src/logsum.py:144` | `row.get(lv_col, "")` default | `level_norm = _norm_level(row.get(lv_col, ""))` | ✅ correct |
| Q3 | `requirements.txt:1–2` | `ruff`, `pytest` | `ruff` / `pytest` | ✅ correct |
| Q3 | `.github/workflows/ci.yml:18` | `python-version: "3.11"` | `          python-version: "3.11"` | ✅ correct |
| Q3 | `.github/workflows/ci.yml:21` | `pip install -r requirements.txt` | `        run: pip install -r requirements.txt` | ✅ correct |
| Q3 | `.github/workflows/ci.yml:24` | `ruff check .` | `        run: ruff check .` | ✅ correct |
| Q3 | `.github/workflows/ci.yml:27` | `pytest -v` | `        run: pytest -v` | ✅ correct |
| Q3 | `ci-notes.md:6–7` | "Steps: ruff check . → pytest -v / Python: 3.11" | `- Steps: ruff check . → pytest -v` / `- Python: 3.11` | ✅ correct |
| Q3 | `CLAUDE.md:16–17` | Linter: ruff / Test runner: pytest | `- Linter: \`ruff\`` / `- Test runner: \`pytest\`` | ✅ correct |

### Summary

15 citations checked. 2 off-by-4 errors found in Q1 (both pointing 4 lines too high
because the initial drafting mentally skipped over 4 lines of the Normalisation table
above the Grouping rule section). The substance of both claims was correct; only the
line numbers drifted.

**Fix applied:** Q1 citations corrected from `spec.md:96` → `spec.md:92` and
`spec.md:100–101` → `spec.md:96–97`.

---

*Written: 2026-08-07 | Kata 5.8*
