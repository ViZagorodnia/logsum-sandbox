# KATA 5.5 — intentional ruff violation for CI red demo
# ruff will flag F401: 'os' imported but unused
# Fix: delete this file entirely in the follow-up commit.

import os  # F401 violation — CI will fail here. Fix: delete this file.

KATA_NOTE = "This file triggers F401 so the first CI run fails."
