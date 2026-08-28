# logsum-multitenant — Feature Specification
<!-- feature-id: logsum-multitenant -->
<!-- status: draft -->
<!-- kata: 5.W -->

---

## 1. Behaviour

An operator of the Meridian platform wants to submit a CSV log file over HTTP
and receive a grouped summary without installing any local tooling. The
`logsum-multitenant` service exposes a single HTTP endpoint: `POST /summarise`.
The caller authenticates with an API key, uploads a UTF-8 CSV file as
`multipart/form-data`, and optionally passes `level`, `service`, and `min_count`
query parameters. The service runs the same normalise-group-count logic as the
`logsum` CLI and returns a JSON response containing the summary rows sorted by
count descending. Tenant identity is derived from the API key; no row or key
from one tenant is visible to another.

### Acceptance criteria

**AC-1 — Happy path summary**
Given a valid API key in the `X-Api-Key` header and a well-formed CSV with at
least one data row attached as `file`,
when the client POSTs to `/summarise`,
then the service responds 200 with `Content-Type: application/json` and a body
of the form `{"rows": [{"service": "...", "level": "...", "count": N}, ...],
"total_input_rows": N, "filtered_count": N}`, rows sorted by count descending.
`total_input_rows` is the count of data rows read from the CSV **before** any
filter (`level`, `service`, `min_count`) is applied. `filtered_count` is the
count of rows that survived all active filters and contributed to at least one
output group. Filter effectiveness = `filtered_count / total_input_rows`.

**AC-2 — Missing required CSV column**
Given a valid API key and a CSV that is syntactically valid but is missing one
of the required columns (`timestamp`, `level`, `service`, `message`),
when the client POSTs to `/summarise`,
then the service responds 422 with body
`{"error": "missing_column", "detail": "<column-name>"}`.

**AC-3 — Payload exceeds size limit**
Given a valid API key and a request body larger than 8 MB,
when the client POSTs to `/summarise`,
then the service responds 413 with body `{"error": "payload_too_large"}` before
any CSV parsing begins.

**AC-4 — Unauthenticated request**
Given a request with no `X-Api-Key` header (or an unrecognised key),
when the client POSTs to `/summarise`,
then the service responds 401 with body `{"error": "unauthorized"}` and does
not process the file.

---

## 2. Concurrency

Each HTTP request is handled independently in its own call frame; there is no
shared mutable state between requests. The aggregation logic (normalise →
filter → count) operates entirely on data passed in via the request body and
has no side-effects on process-level variables. Two simultaneous requests from
the same tenant — or from different tenants — will never observe each other's
in-flight counters.

Worker concurrency is controlled at the server level (e.g. `--workers N` for a
WSGI/ASGI server). The service queues incoming requests up to a maximum of 50
pending connections beyond active workers; once that limit is reached the
server returns 503 before the request handler is invoked. There is no per-tenant
concurrency cap in v1, which means a single tenant can consume the full worker
pool (see Boundaries §per-tenant rate limiting, deferred to LOGSUM-11).

A request that enters the pending queue but is not dispatched to a worker within
**10 s** is abandoned: the server returns 503 with body
`{"error": "overloaded", "detail": "request wait timeout"}` and a
`Retry-After: 5` header. This prevents indefinite blocking for clients that do
not set their own timeouts.

---

## 3. Errors

The following conditions are recognised as invalid and produce structured JSON
error responses. All error bodies share the shape
`{"error": "<code>", "detail": "<optional human string>"}`.

| HTTP status | `error` code | Trigger |
|-------------|--------------|---------|
| 400 | `bad_request` | Multipart form is malformed or the `file` field is absent |
| 401 | `unauthorized` | `X-Api-Key` header absent or key not found in the key store |
| 413 | `payload_too_large` | Request body > 8 MB (checked before any parsing) |
| 422 | `missing_column` | CSV parses but lacks a required column; `detail` names the first missing column |
| 422 | `parse_error` | File bytes are not valid UTF-8 or not parseable as CSV |
| 422 | `no_rows` | CSV is syntactically valid and has all required columns but contains zero data rows (header-only) |
| 503 | `overloaded` | Pending-connection queue is full |

All 4xx and 5xx responses include a `Retry-After` header only for 503. The
`detail` field is omitted for 401 responses (no information leakage about key
existence).

---

## 4. Boundaries

**Empty CSV (header-only):** A file that contains only the header row and no
data rows is not an error in CSV-parsing terms but produces no output. The
service returns 422 `no_rows` rather than 200 with an empty list, to distinguish
"file was valid but empty" from a successful zero-match filter (which returns 200).

**Oversized file:** The Content-Length header (if present) is checked before
buffering. If absent, the server reads up to 8 MB + 1 byte; the first byte
beyond the limit aborts reading and returns 413. No partial CSV is processed.

**Malformed CSV / invalid encoding:** Any file that raises a `csv.Error` or a
`UnicodeDecodeError` during parsing returns 422 `parse_error`. The raw exception
message is truncated to 200 characters and placed in `detail`.

**All rows filtered out:** When `level` or `service` query params match no rows,
or when `min_count` eliminates all groups, the service returns 200 with
`{"rows": [], "total_input_rows": N, "filtered_count": 0}`. This differs from
the CLI (which exits 3) because a 200 with an empty list is the correct HTTP
idiom for "query succeeded, result set is empty".

**Large valid file (1 MB–8 MB):** Accepted and processed normally. Expected
P95 latency remains ≤ 300 ms (see NFR budget).

**`min_count` = 0 or negative:** Treated as "no filter" (same behaviour as
omitting the parameter entirely). The value is clamped to 1 internally if
positive.

---

## 5. Integrations

**API key store** — the only external dependency in v1. The service looks up
the `X-Api-Key` value in a key-value store (default: an in-process dict loaded
from a YAML file at startup; production target: Redis). If the store is
unavailable at request time the service fails closed: all requests return 401
rather than bypassing authentication. Key rotation (adding/removing keys)
requires a process restart in v1 (live reload deferred to LOGSUM-12).

The key-store lookup must complete within **200 ms** (measured from the moment
the HTTP handler begins, not including network time to the client). If the store
does not respond within that window the service returns 401 — not 503 — so that
a store outage is not distinguishable from an invalid key by external observers.

**No other external services.** Log aggregation, persistence, and downstream
alerting are out of scope for v1. The service does not write output files to
disk; all results are returned in the HTTP response body.

---

## 6. NFR budget

```
NFR budget:
- Latency:             P95 ≤ 300 ms for files up to 1 MB; P99 ≤ 800 ms for files up to 8 MB
- Payload size:        Max inbound request body = 8 MB; max JSON response body = 512 KB
- Error behavior:      Non-5xx error rate under normal load < 0.1%; 5xx rate < 0.01%
- Cost/complexity:     Zero third-party runtime dependencies (pure Python 3.11 stdlib + WSGI server)
- Throughput:          ≥ 20 req/s sustained on a single worker for 1 MB files
- Startup time:        Cold-start (key store load + server bind) ≤ 2 s
```

---

## Out of scope (v1)

- Per-tenant rate limiting (deferred: LOGSUM-11)
- Live API key rotation without restart (deferred: LOGSUM-12)
- Persistent storage of summaries
- Streaming / chunked CSV upload
- Output formats other than JSON
- `first_seen` / `last_seen` timestamps in output
- Async / background processing (all requests are synchronous)
- HTTPS termination (handled by a reverse proxy)
