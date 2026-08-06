# CI Notes — Kata 5.5

## Workflow
- File: `.github/workflows/ci.yml`
- Triggers: push, pull_request
- Steps: ruff check . → pytest -v
- Python: 3.11

---

## Run 1 — RED ❌

**PR:** https://github.com/ViZagorodnia/logsum-sandbox/pull/1

**Cause (AI diagnosis):**
```
src/debug_temp.py:5:8: F401 `os` imported but unused
```
Bug is in **code** (not workflow, not test): unused import in `src/debug_temp.py`.

**Fix applied:** deleted `src/debug_temp.py`

---

## Run 2 — GREEN ✅

**CI run link:** https://github.com/ViZagorodnia/logsum-sandbox/actions/runs/31123755227

**What ran:**
- `ruff check .` → passed, 0 violations
- `pytest -v` → passed, N tests collected

---

## Key observation
CI is a server-side gate that runs independent of my local machine.
It caught a lint error I intentionally introduced.
Red → diagnosed → fixed → green: kata outcome achieved.
