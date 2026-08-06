"""
Shared pytest configuration and fixtures for logsum tests.
"""
from __future__ import annotations

from pathlib import Path

import pytest

# ── Paths ─────────────────────────────────────────────────────────────────

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ── Factory fixture ────────────────────────────────────────────────────────

@pytest.fixture
def make_csv(tmp_path):
    """
    Return a factory that writes a UTF-8 CSV file under *tmp_path*.

    Usage::

        def test_something(make_csv):
            path = make_csv("file.csv", ["t,INFO,svc,msg", "t,ERROR,svc,msg"])
            ...

    Parameters
    ----------
    filename : str
        Name of the file to create inside *tmp_path*.
    rows : list[str]
        Pre-formatted CSV data rows (no header).  Each string is written
        verbatim as one line.  Pass ``[]`` for a header-only file.
    header : str
        CSV header line.  Defaults to the four-column logsum schema.
    """

    def _factory(
        filename: str,
        rows: list[str],
        header: str = "timestamp,level,service,message",
    ) -> Path:
        p = tmp_path / filename
        parts = [header] + list(rows)
        p.write_text("\n".join(parts) + "\n", encoding="utf-8")
        return p

    return _factory
