# logsum — CLI Specification
status: draft

## Purpose

`logsum` reads a CSV log file produced by Meridian platform services and prints
a counted summary table grouped by service and log level.

## Input

| Argument | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `--input` | path | yes | — | Path to a CSV file |
| `--level` | string | no | all | Filter: ERROR, WARN, INFO |
| `--service` | string | no | all | Filter by service name |

The CSV file **must** contain these columns (order is not important):

```
timestamp, level, service, message
```

## Output

Tab-separated summary table printed to **stdout**:

```
service              ERROR  WARN  INFO  TOTAL
checkout-service         5     1     3      9
cart-api                 1     1     4      6
identity-service         1     1     3      5
```

- Rows sorted by TOTAL descending
- Header row always present
- Columns right-aligned, width = max value width + 2 spaces
- No trailing newline beyond the last row

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | File not found or unreadable |
| 2 | Missing required column in CSV |
| 3 | No rows match the active filters |

## Edge cases

1. **Empty file** (header only) → exit 3, message to stderr: `No log entries found.`
2. **Unknown level value** (e.g. `DEBUG`) → count under `OTHER`, do not crash
3. **Missing column** → exit 2, message: `Missing required column: <name>`
4. **Extra columns** → silently ignored
5. **Malformed timestamp** → row counted, timestamp not validated

## Known Meridian services (informational only)

The tool is agnostic to service names; the following appear in the reference dataset:

- `checkout-service`
- `cart-api`
- `identity-service`

## Non-functional requirements

- Pure Python 3.11+ stdlib only — no third-party dependencies
- `python logsum.py --input events.csv` must run in < 200 ms for files up to 50 000 rows
- Must be importable as a module (no top-level side effects)
