# K 5.W.9 — By-hand vs by-agent comparison

<!-- kata: 5.9 -->
<!-- date: 2026-08-07 -->
<!-- supervised chain: K 5.W.2–8 (logsum-sandbox, branch: (working tree)) -->
<!-- agent replay: branch agent-replay, single commit 4553f39 -->

---

## What both produced

Both the supervised chain and the async agent produced a working implementation of the full `logsum` spec:

**Implementation (`src/logsum.py`)**
Both parsed all five CLI flags (`--input`, `--output`, `--level`, `--service`, `--min-count`), absorbed positional shorthand into `--input`/`--output`, normalised `level` (strip + uppercase) and `service` (strip only), grouped by `(service, level)`, sorted by count descending, and implemented all 10 edge cases with the correct exit codes (0/1/2/3) and exact stderr messages. Both handled the exit-3 two-counter problem correctly: a single `len(counts) == 0` check cannot distinguish a header-only file from a fully-filtered file, so both used a `total_data_rows` counter to branch on the right message.

**Tests (`tests/test_logsum.py`)**
Both produced a black-box pytest suite invoking `python -m src.logsum` via subprocess with the `make_csv` fixture from `conftest.py`. Both covered grouping, normalisation, output format, filters, all 10 edge cases, exit codes, `--help`, `--output`, positional args, and `--min-count`. Supervised: 74 tests; agent: 77 tests.

**CI (`.github/workflows/ci.yml`)**
Both verified the existing CI config: `ruff check .` → `pytest -v` on Python 3.11 / ubuntu-latest. Neither changed the file.

**Provenance note**
Both produced a provenance document recording model, files read (and explicitly skipped), files changed, plan deviations, untested items, and final test count.

---

## Where the agent saved time

**Single-pass delivery with no debug cycles.** The agent produced 77/77 passing tests on its first full test run with only two minor ruff lint fixes (unused import, ambiguous variable name). The supervised chain required multiple edit-run-fix cycles spread across multiple katas (5.2 through 5.7), with explicit debugging sessions, spec re-reads, and back-and-forth on edge cases.

**Proactive cleanup.** `src/debug_temp.py` had a comment reading "Fix: delete this file entirely in the follow-up commit." The supervised chain left this as a deferred task. The agent deleted it during the ruff fix pass, preventing a CI failure that a human would have had to diagnose first.

**No spec negotiation on ambiguities.** The spec gaps — filter normalisation not specified, empty file (0 bytes) not distinguished from header-only, "no trailing newline" applying to both stdout and `--output` — were all resolved by the agent through inference without requiring a human to weigh in. Each decision was documented in `provenance-agent-replay.md` and matched what the supervised chain eventually converged on anyway.

**Finer-grained test organisation.** The agent used one class per edge case (19 classes total: `TestEdgeCase1FileNotFound`, `TestEdgeCase2MissingColumn`, etc.), making failures immediately locatable by spec section. The supervised chain grouped all edge cases into one `TestEdgeCases` class, which is more compact but harder to scan when one case fails.

---

## Where the agent went wrong or shorter

**Bug: f-string CSV generation does not handle commas in service names.**
The agent's `emit_output` builds each output row with `f"{service},{level},{count}"`. This is silently incorrect when a service name contains a comma. A service named `"my,service"` would produce `my,service,ERROR,3` — four fields — breaking any downstream CSV parser. The supervised version used `csv.writer(dest, lineterminator="\n")` which would correctly quote the field as `"my,service",ERROR,3`. No test in either suite covers this because all test data uses clean service names. Verification:

```python
# Agent approach
f"my,service,ERROR,3"      → 'my,service,ERROR,3'  # malformed: 4 fields

# Supervised approach
csv.writer → '"my,service",ERROR,3\n'  # correct: 3 fields, comma escaped
```

This is the canonical "async agent bug" — it passes all 77 tests and is wrong.

**Header whitespace not normalised in column check.**
The agent's `check_required_columns` checks `REQUIRED_COLUMNS` against `set(fieldnames)` with no whitespace stripping. The supervised version builds a `field_map = {f.strip().lower(): f for f in raw_fields}` so that a CSV with padded headers like `" level "` is still accepted. The agent's version would exit 2 with "Missing required column: level" for a padded header, despite the field being present. Neither test suite covers padded headers so this went undetected.

**No `TestStaticFixtures` class.**
The supervised suite includes five tests against `tests/fixtures/basic.csv` — a committed multi-service, multi-level fixture that tests the full grouping, sorting, and filter pipeline end-to-end on realistic data. The agent omitted this class entirely. The gap matters: the static fixture catches sort-order regressions that synthetic single-group tests cannot.

**No stdout buffering via `io.StringIO`.**
The supervised implementation buffers stdout output through `io.StringIO` before writing, which guarantees that any deferred error text never interleaves with the summary CSV. The agent writes directly to `sys.stdout.write(content)`. For this CLI this is benign, but the protection the supervised version added was a deliberate choice documented in the code.

---

## What the agent did better

**Cleaner module architecture.** The agent's `main()` returns an `int` exit code and the entry point calls `sys.exit(main())`. This makes `main()` unit-testable without subprocess. The supervised version calls `sys.exit()` directly inside `summarise()`, coupling the function to the process lifecycle.

**Smaller, single-purpose helpers.** The agent decomposed the work into: `build_parser`, `resolve_args`, `open_input_file`, `emit_output`, `normalise_row`, `check_required_columns`, `aggregate`, `apply_min_count`, `sorted_rows`, `main` — 10 functions, most under 15 lines. The supervised version had 9 functions but some (`summarise`) were longer and mixed the aggregation, filter, and write concerns. `apply_min_count` as a named function is especially clean.

**Self-auditing on the refactor pass.** The agent caught its own redundant `matched_rows` counter during the self-review step and removed it before completing. In the supervised chain, the analogous comment-removal decisions were made by the human reviewer during the refactor kata (5.6) and required a dedicated audit document (`refactor-notes.md`).

**`open_input_file` as an explicit error path.** The agent wrapped `open()` in a helper that returns `(file_obj, None)` or `(None, error_message)`. This is a functional-style error-handling pattern that makes the error path visible in `main()` without a bare `try/except`. The supervised version's `try: fh = open(...) except OSError` block is correct but buries the error path inside `summarise()`.

---

## What I learned about supervised vs async

**The supervised chain produced the spec, not just the code.** The most important artefacts from K 5.W.2–8 are not the 250 lines of `logsum.py` or the 74 tests — they are the annotations that accreted onto `spec.md` during the work: the Implementation notes section documenting the exit-3 two-counter trap, the positional-shorthand decision, the signed-off date. The async agent read those notes and used them. Without the supervised chain, the agent would have had to discover the exit-3 trap on its own (it probably would have — but without a record of why it matters).

**Async agents are fast and structurally correct but produce latent correctness bugs.** The f-string/csv.writer difference is not a logic error — the agent understood the spec correctly. It is a representation error: the agent chose a simpler representation that happened to be wrong for inputs the tests never exercised. A human supervisor reviewing the code would have asked "what happens if a service name has a comma?" and caught it in seconds. In the supervised chain, `csv.writer` was the first-draft choice precisely because a reviewer knows that service names in real systems sometimes have commas.

**Async agents don't negotiate spec gaps; they document their guesses.** Every spec ambiguity the agent encountered (filter normalisation, empty file behaviour, trailing newline) was resolved by inference and logged in the provenance note. That is the right pattern for async work. But the inference is only as good as the spec context — and the supervised chain is what built that context. The agent's correct handling of filter normalisation was possible because the spec's Implementation notes section (written during the supervised chain) gave it the right framing.

**Test coverage hides different things in supervised vs async work.** Both suites have 74–77 tests and pass green. But the supervised suite includes `TestStaticFixtures` (realistic multi-service data) because the supervised session ran the CLI against real data and wanted a regression guard. The agent's suite omits this because it never ran the tool interactively — it only ran pytest. Green-on-synthetic is weaker than green-on-realistic.

**The supervised chain produced a traceable decision log; the agent produced a delivery.** `refactor-notes.md`, `provenance-min-count.md`, `questions.md`, `test-notes.md` together explain why the code looks the way it does and what alternatives were considered. The agent's `provenance-agent-replay.md` explains what it did but not the reasoning behind each choice. For a production system, the supervised trail is more valuable for the next engineer.

---

## What I would do differently next time

**Give the agent an explicit CSV-safety instruction.** The prompt should include: "When writing CSV output, use `csv.writer` — do not build CSV rows with string formatting or f-strings, because service names may contain commas." One sentence prevents the class of bug that passes 77 tests and is still wrong.

**Require a static fixture test.** Add to the prompt: "Include a `TestStaticFixtures` class that runs the tool against `tests/fixtures/basic.csv` and asserts sort order and at least three known (service, level) pairs." This ensures the agent tests against the same realistic reference data the supervised suite uses.

**Set a header-normalisation assertion.** Add: "The column-presence check must strip leading/trailing whitespace from header names before comparing, consistent with how data values are normalised." This closes the padded-header gap without requiring a specific test case for it.

**Use the agent for the first 80%, supervise the last 20%.** The agent is excellent at: reading a signed-off spec, producing a structurally complete implementation, writing a test class per spec section, following a known pattern (positional shorthand, two-counter exit-3). It is weak at: choosing safe representations for output (csv.writer vs f-string), producing tests against realistic fixture data, and deciding what not to infer. The optimal workflow is: agent produces draft → human reviews output-generation code specifically → human adds realistic fixture tests → merge.

**Write the agent prompt as precisely as the spec.** The supervised spec went through multiple iterations before sign-off. The agent prompt I wrote was a single pass. If the prompt had specified "use `csv.writer` for output", "normalise column header names before checking presence", and "include a static fixture smoke test", the agent's output would have been production-ready. The lesson is that prompt quality for async agents requires the same rigour as spec quality for supervised work.

---

*Written: 2026-08-07 | Kata 5.9*
