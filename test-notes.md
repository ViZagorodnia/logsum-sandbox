# logsum — test triage notes
<!-- kata 5.3 / 5.4 -->

---

## Audit: did the test session peek at `src/logsum.py`?

**Finding: No.**
Every test name is spec-vocabulary (`test_level_whitespace_stripped_and_uppercased`,
`test_exit_3_two_paths_have_distinct_messages`, etc.).
No test references internal helper names, argparse namespaces, csv.DictWriter, or any
other implementation detail.  The session stayed black-box throughout.

---

## Missing hard edge cases (added before sign-off)

Two categories were found after all 65 original tests passed:

### 1. Filter applied after normalisation (hard interaction test)

The spec says normalisation is applied "before grouping" and `--level` / `--service`
are "pre-filters before grouping".  The spec implies both happen before grouping,
but never states their relative order.

**Risk:** an implementation could normalise output correctly yet still filter on the
raw value — producing wrong counts or missing rows.

**Tests added:**
- `TestFilters::test_level_filter_applied_after_normalisation`
  — raw `" error "` must match `--level ERROR` after normalisation
- `TestFilters::test_service_filter_applied_after_normalisation`
  — raw `" cart-api "` must match `--service cart-api` after stripping

Both pass.  The implementation normalises before filtering. ✓

---

### 2. Truly empty file (0 bytes) — spec gap

**Scenario:** `--input` points to a file that exists but contains zero bytes.

**Spec coverage:** The spec defines nine edge cases.  Edge case #3 is
"Header-only file (zero data rows)" → exit 3.  Edge case #2 is
"CSV missing a required column" → exit 2.
**Neither covers a 0-byte file.**

#### Isolation method

1. Created a 0-byte file with `p.write_bytes(b"")`.
2. Ran `python -m src.logsum --input <path>` and captured exit code + stderr.
3. Observed: `exit=2`, `stderr="Missing required column: timestamp\n"`.
4. Compared against all three candidate exits:
   - Exit 1 (file not found / unreadable) — file exists and is readable; ruled out.
   - Exit 3 (no rows) — analogy with header-only suggests this, but the file has
     no header either, so the "rows" framing doesn't fit cleanly.
   - Exit 2 (missing required column) — an empty file has zero columns, which is a
     superset of "missing required column"; consistent with the spec's intent.

#### Decision: **spec ambiguity**

| Option | Argument |
|--------|----------|
| Exit 3 | By analogy with header-only — "no data to summarise" |
| Exit 2 | Consistent — a 0-byte file technically has every required column missing |

The spec is silent.  Either exit code is defensible.
The implementation chose exit 2, which is coherent with the existing error hierarchy.

#### Resolution

Test `test_empty_file_exits_2` was written to assert the implementation's actual
behaviour (exit 2).  The docstring records the alternative hypothesis (exit 3) and
the reasoning.

If the spec is later updated to mandate exit 3 for empty files, the test is the
correct place to change — not the assertion logic.

---

## Tips checklist

| Tip | Status |
|-----|--------|
| Test names implementation helpers → session peeked at code | ✗ No impl names found |
| All tests pass but miss hardest edge case | ✓ Found two categories; both added |
| AI weakens a failing test | ✓ Avoided — `test_empty_file_exits_2` asserts exit 2 with reasoning, not exit 3 weakened to "any non-zero" |

---

*Recorded: 2026-08-06*
