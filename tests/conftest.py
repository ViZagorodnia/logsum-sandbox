"""
Shared pytest fixtures for the logsum test suite.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def make_csv(tmp_path: Path):
    """
    Factory fixture that creates a temporary CSV file.

    Usage:
        csv_path = make_csv("filename.csv", ["row1col1,row1col2,...", ...])

    The file is automatically prefixed with the required header line:
        timestamp,level,service,message
    """
    def _make(filename: str, data_rows: list[str]) -> Path:
        path = tmp_path / filename
        header = "timestamp,level,service,message"
        lines = [header] + data_rows
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    return _make
