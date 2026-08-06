# logsum — CLI Specification
<!-- status: signed-off -->
<!-- kata: 5.2 -->

---

## Goal

`logsum` reads a CSV log file produced by Meridian platform services and writes
a one-row-per-group summary CSV counting events by service and log level.
The tool gives operators a quick, scriptable breakdown of which service is
generating the most errors without requiring a log-aggregation platform.

---

## Inputs

### Positional / flag arguments

| Flag | Type | Required | Default | Notes |
|------|------|----------|---------|-------|
| `--input` | path | **yes** | — | Path to a UTF-8 CSV file |
| `--output` | path | no | stdout | Write summary CSV here instead of stdout |
| `--level` | string | no | all | Pre-filter rows to a single level before grouping |
| `--service` | string | no | all | Pre-filter rows to a single service before grouping |

### Input CSV schema

The CSV **must** contain exactly these four column headers (order is not important,
extra columns are silently ignored):

```
timestamp, level, service, message
```

Example input (`data/events.csv`):

```
timestamp,level,service,message
2026-08-01T08:00:01Z,INFO,identity-service,Token issued for user u-1042
2026-08-01T08:01:15Z,ERROR,checkout-service,Payment gateway timeout — retry 1/3
2026-08-01T08:01:25Z,WARN,cart-api,Cart session not found cs-9900
```

---

## Outputs

### Summary CSV

One header row followed by one data row per unique `(service, level)` group,
sorted by `count` descending.

```
service,level,count
checkout-service,ERROR,5
checkout-service,WARN,2
checkout-service,INFO,2
cart-api,INFO,4
cart-api,WARN,1
cart-api,ERROR,1
identity-service,INFO,3
identity-service,WARN,1
identity-service,ERROR,1
```

Column order is fixed: `service`, `level`, `count`.
No trailing newline beyond the last data row.

---

## Normalisation rules

Applied to every row **before** grouping:

| Field | Rule |
|-------|------|
| `level` | Strip leading/trailing whitespace; convert to UPPERCASE. Example: `" warn "` → `"WARN"` |
| `service` | Strip leading/trailing whitespace; preserve original casing. Example: `" cart-api "` → `"cart-api"` |
| `timestamp` | Not validated; stored as-is for future use but not used in grouping or output |
| `message` | Not read; field is accepted but ignored entirely |

Unknown level values (anything that is not `INFO`, `WARN`, or `ERROR` after
normalisation) are kept as-is in the output (e.g. `DEBUG`, `TRACE`). They are
**not** collapsed into `OTHER`.

---

## Grouping rule

The group key is the tuple `(service, level)` after normalisation.

- Each unique `(service, level)` pair produces exactly one output row.
- Two rows with `service = "cart-api"` and `level = "ERROR"` belong to the same group regardless of their `timestamp` or `message` content.
- Grouping is case-sensitive on `service` and case-insensitive on `level`
  (because `level` is already uppercased by the normalisation step).

---

## Aggregation

For each group the tool computes:

| Output column | Rule |
|---------------|------|
| `count` | Integer count of rows in the group; minimum value is 1 |

`first_seen` and `last_seen` are **not** computed in v1 (see Out of scope).

Rows excluded by `--level` or `--service` filters are not counted.

---

## Edge cases

| # | Scenario | Behaviour |
|---|----------|-----------|
| 1 | File not found or permission denied | Exit 1; stderr: `Error: cannot open '<path>': <os message>` |
| 2 | CSV missing a required column | Exit 2; stderr: `Missing required column: <column-name>` |
| 3 | Header-only file (zero data rows) | Exit 3; stderr: `No log entries found.` |
| 4 | All rows filtered out by `--level` or `--service` | Exit 3; stderr: `No log entries match the active filters.` |
| 5 | Unknown level value after normalisation | Row counted under its own level label (e.g. `DEBUG`); no warning |
| 6 | Malformed or missing timestamp | Row is counted normally; timestamp is not validated |
| 7 | Extra columns in the CSV | Silently ignored |
| 8 | Empty `level` field (blank string after normalisation) | Treated as unknown level; kept as empty string `""` in output |
| 9 | Duplicate header row in body | Treated as a data row; `level = "level"` will appear in output |

---

## CLI

```
logsum --input <path> [--output <path>] [--level <LEVEL>] [--service <name>]
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success — at least one output row written |
| 1 | File not found or unreadable |
| 2 | Required column missing from CSV |
| 3 | No rows in output (empty file or all rows filtered out) |

### Help flag

`logsum --help` prints usage to stdout and exits 0.

### Stderr vs stdout

All error messages go to **stderr**. The summary CSV goes to **stdout** (or to
`--output` if provided). These two streams must never be mixed.

---

## Out of scope (v1)

The following are explicitly **not** part of this specification:

- `first_seen` / `last_seen` timestamps in output
- Sorting by any column other than `count` descending
- JSON, JSONL, TSV, or any non-CSV input formats
- Reading from stdin (`-` as `--input`)
- Multi-file input (globbing, concatenation)
- Real-time / streaming / tail mode
- Log rotation or archiving
- Colour output or interactive TUI
- Any third-party library dependency (pure Python 3.11 stdlib only)
- Timestamp validation or timezone normalisation
- Deduplication of identical log lines

---

## Signed off

VN — 2026-08-06

---

## Implementation notes

*Kata 5.3 — added 2026-08-06*

**Surprise: exit-code 3 needs two separate counters.**
The spec defines two different Exit-3 messages: "No log entries found." (header-only
file) vs "No log entries match the active filters." (rows exist but all filtered out).
A single `len(counts) == 0` check cannot distinguish them — the AI's first draft used
only one counter and always printed the "no entries" message even when the real cause
was a filter mismatch. The fix was to track `total_data_rows` (before filters) and
`matched_rows` (after filters) separately and branch on both.

**Decision: positional shorthand accepted alongside `--input` / `--output`.**
The CLI spec defines `--input` as a required flag, but the kata run command uses bare
positionals (`python -m src.logsum data/sample_events.csv data/summary.csv`).
Rather than reject the positional form, the parser absorbs positional args into
`--input` / `--output` when the flags are absent — keeping both invocation styles
valid without changing the spec contract.
