# logsum-multitenant — Spec Audit
<!-- isolation-tier: B — spec pasted into a fresh session; no prior context of this feature -->
<!-- auditor-prompt: "Find three requirements this spec silently omits." -->

---

## Isolation tier

**Tier B** — spec text was pasted into a clean session that had no knowledge of
the logsum codebase, existing tests, or authoring intent.

---

## Raw audit findings

The following three findings were returned by the isolated session:

---

**Finding 1 — Section: Integrations / §API key store**

> The spec says the service fails closed when the key store is unavailable (all
> requests return 401). It does not say what "unavailable" means in observable
> terms: is a Redis connection timeout of 1 s sufficient? 5 s? What happens to
> a request that is already in-flight when the store goes down mid-lookup? An
> implementation that blocks indefinitely waiting for Redis will silently
> degrade P95 latency past the 300 ms budget without ever surfacing a 503.
> There is no timeout budget for the key-store lookup anywhere in the spec.

---

**Finding 2 — Section: Concurrency**

> The spec states there is no per-tenant concurrency cap and defers rate
> limiting to LOGSUM-11 without specifying what observable behaviour a client
> gets today when the worker pool is saturated specifically by one tenant's
> requests. A client that sends 100 simultaneous requests has no way to
> distinguish "your request is queued" from "server is down" — both look like
> a slow response until the 503 arrives at queue depth 50. The spec does not
> define a request timeout (how long a queued request waits before the server
> returns 503 proactively) nor document this in the 503 response body.

---

**Finding 3 — Section: Behaviour / AC-1**

> AC-1 specifies the happy-path response shape but does not state what value
> `total_input_rows` holds when `level` or `service` filters are active. Does
> it count rows before or after filtering? If it counts before filtering, a
> client cannot detect whether a filter was applied. If it counts after, the
> field is redundant with `sum(row.count for row in rows)`. The ambiguity means
> two compliant implementations will disagree, breaking any client that uses
> this field for audit or reconciliation.

---

## Resolution

### Finding 1 — Key-store lookup timeout

**INCORPORATE** — added to §5 Integrations:

> The key-store lookup must complete within **200 ms**. If the store does not
> respond within that window the request is failed closed: the service returns
> 401 (not 503) so that a store outage is not distinguishable from an invalid
> key by external observers.

---

### Finding 2 — Queued-request timeout and 503 detail

**INCORPORATE** — added to §2 Concurrency:

> A request that enters the pending queue but is not dispatched to a worker
> within **10 s** is abandoned and the server returns 503 with body
> `{"error": "overloaded", "detail": "request wait timeout"}` and a
> `Retry-After: 5` header.

---

### Finding 3 — `total_input_rows` semantics

**INCORPORATE** — clarified in §1 AC-1:

> `total_input_rows` is the count of data rows read from the CSV **before** any
> filter is applied. `filtered_count` is the count of rows that survived all
> active filters. Filter effectiveness = `filtered_count / total_input_rows`.

---

## Spec patches applied

All three findings were incorporated. `spec.md` updated in §1 AC-1, §2
Concurrency, and §5 Integrations.
