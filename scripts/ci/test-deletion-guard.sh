#!/usr/bin/env bash
set -euo pipefail

BASE_REF="${GITHUB_BASE_REF:-main}"

DELETED_TESTS=$(git diff --name-only --diff-filter=D "origin/${BASE_REF}...HEAD" \
  | grep -E '(test_|_test\.py|tests/)' || true)

if [ -z "$DELETED_TESTS" ]; then
  echo "✅ No test files deleted."
  exit 0
fi

echo "⚠️  Deleted test files detected:"
echo "$DELETED_TESTS"

COMMIT_MESSAGES=$(git log "origin/${BASE_REF}...HEAD" --format="%s %b")

if echo "$COMMIT_MESSAGES" | grep -qE "DELETE_TESTS:"; then
  echo "✅ DELETE_TESTS: token found — deletion is intentional."
  exit 0
fi

echo ""
echo "❌ Test files were deleted without DELETE_TESTS: <reason> in any commit message."
echo "   Add 'DELETE_TESTS: <reason>' to your commit message to allow this."
exit 1
