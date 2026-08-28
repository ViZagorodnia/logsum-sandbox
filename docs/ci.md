# CI Gates

## Test-File Deletion Guard

**Workflow:** `.github/workflows/ci.yml` — job `test-deletion-guard`  
**Script:** `scripts/ci/test-deletion-guard.sh`

### What it enforces

PRs that delete files matching `test_*.py`, `*_test.py`, or anything under `tests/`
must include `DELETE_TESTS: <reason>` in at least one commit message.
If the token is absent, the check fails and the PR cannot be merged.

This gate exists because AI-assisted PRs (Claude, Cursor, Copilot) can silently
delete test files during refactors or "cleanup" passes without explicit human intent.
A required server-side check catches this regardless of which tool opened the PR
or whether the engineer's local hooks are configured.

**What it does NOT catch:** renaming or moving test files (not a deletion),
reducing test coverage without removing files, or test files stored outside
the `tests/` directory with non-standard naming.

**Limitation:** the check matches file names only — a file named `test_utils.py`
that contains no actual tests will still trigger the guard.

---

### Admin step — make the check required on GitHub

```
Settings → Branches → Branch protection rules → Edit "main"
→ "Require status checks to pass before merging"
→ Search for: test-deletion-guard
→ Add → Save changes
```

> **Note:** the status check only appears in the search box after at least one
> PR has run the workflow. Push a draft PR first if the check isn't showing up.

---

### Rollout checklist

| Step | UI path | Who | Done |
|------|---------|-----|------|
| Open branch protection rules | Settings → Branches → Edit `main` | Repo admin | ☐ |
| Enable required status checks | "Require status checks to pass" checkbox | Repo admin | ☐ |
| Add the check | Search `test-deletion-guard`, click Add | Repo admin | ☐ |
| Save | "Save changes" button | Repo admin | ☐ |
