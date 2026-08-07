"""
logsum — CLI tool for summarising Meridian platform CSV log files.

Reads a UTF-8 CSV log file with columns (timestamp, level, service, message),
groups rows by (service, level) after normalisation, and writes a summary CSV
sorted by count descending.

Exit codes:
    0 — Success; at least one output row written.
    1 — File not found or unreadable.
    2 — Required column missing from CSV.
    3 — No rows in output (empty file or all rows filtered out).
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path


# ── Constants ──────────────────────────────────────────────────────────────

REQUIRED_COLUMNS = ["timestamp", "level", "service", "message"]
OUTPUT_HEADER = ["service", "level", "count"]


# ── Argument parsing ───────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser (does not parse yet)."""
    parser = argparse.ArgumentParser(
        prog="logsum",
        description=(
            "Summarise a Meridian platform CSV log file by service and level."
        ),
    )
    # Positional shorthand: bare args are absorbed into --input / --output
    parser.add_argument(
        "positionals",
        nargs="*",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--input",
        dest="input",
        default=None,
        metavar="PATH",
        help="Path to a UTF-8 CSV log file (required).",
    )
    parser.add_argument(
        "--output",
        dest="output",
        default=None,
        metavar="PATH",
        help="Write summary CSV to this file instead of stdout.",
    )
    parser.add_argument(
        "--level",
        dest="level",
        default=None,
        metavar="LEVEL",
        help="Pre-filter rows to this log level (case-insensitive).",
    )
    parser.add_argument(
        "--service",
        dest="service",
        default=None,
        metavar="NAME",
        help="Pre-filter rows to this service name (case-sensitive after strip).",
    )
    parser.add_argument(
        "--min-count",
        dest="min_count",
        type=int,
        default=None,
        metavar="N",
        help="Only output groups whose count is >= N (post-aggregation).",
    )
    return parser


def resolve_args(argv: list[str] | None = None) -> argparse.Namespace:
    """
    Parse *argv* and absorb bare positionals into --input / --output
    when those flags are absent.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Absorb leftover positionals into --input then --output
    remaining = list(args.positionals)
    if remaining and args.input is None:
        args.input = remaining.pop(0)
    if remaining and args.output is None:
        args.output = remaining.pop(0)

    return args


# ── I/O helpers ────────────────────────────────────────────────────────────

def open_input_file(path: str):
    """
    Attempt to open *path* for reading.

    Returns ``(file_obj, None)`` on success or ``(None, error_message)`` on
    failure.  The error message matches the spec format:
        Error: cannot open '<path>': <os message>
    """
    try:
        return open(path, encoding="utf-8", newline=""), None
    except OSError as exc:
        return None, f"Error: cannot open '{path}': {exc.strerror}"


def emit_output(rows: list[tuple[str, str, int]], output_path: str | None) -> None:
    """
    Write the summary CSV rows to *output_path* (or stdout if None).

    The spec requires:
      - Fixed column order: service, level, count
      - Sorted by count descending (caller's responsibility)
      - No trailing newline beyond the last data row
    """
    lines = [",".join(OUTPUT_HEADER)]
    for service, level, count in rows:
        lines.append(f"{service},{level},{count}")
    content = "\n".join(lines)

    if output_path is None:
        sys.stdout.write(content)
    else:
        Path(output_path).write_text(content, encoding="utf-8")


# ── Core logic ─────────────────────────────────────────────────────────────

def normalise_row(raw: dict[str, str]) -> tuple[str, str]:
    """
    Return the normalised ``(service, level)`` key for a CSV row.

    Normalisation rules (spec §Normalisation rules):
      - level:   strip whitespace, then convert to UPPERCASE
      - service: strip whitespace only; preserve original casing
    """
    level = raw["level"].strip().upper()
    service = raw["service"].strip()
    return service, level


def check_required_columns(fieldnames: list[str] | None) -> str | None:
    """
    Verify all required columns are present.

    Returns the name of the first missing column, or *None* if all present.
    Fieldnames are matched exactly (no whitespace stripping of header names).
    """
    present = set(fieldnames or [])
    for col in REQUIRED_COLUMNS:
        if col not in present:
            return col
    return None


def aggregate(
    file_obj,
    level_filter: str | None,
    service_filter: str | None,
) -> tuple[Counter, int, str | None]:
    """
    Read the CSV from *file_obj*, normalise, filter, and count groups.

    Parameters
    ----------
    file_obj:
        Open file object positioned at the beginning.
    level_filter:
        If set, only rows whose normalised level equals this (uppercased +
        stripped) value are counted.
    service_filter:
        If set, only rows whose normalised service equals this (stripped)
        value are counted.

    Returns
    -------
    counts:
        Counter mapping ``(service, level)`` tuples to row counts.
    total_data_rows:
        Number of body rows read (before any filter).
    missing_col:
        Name of the first missing required column, or *None* if all present.
    """
    reader = csv.DictReader(file_obj)

    # Force the header to be read; fieldnames is None for a truly empty file.
    missing = check_required_columns(reader.fieldnames)
    if missing is not None:
        return Counter(), 0, missing

    # Normalise the filter values once up front.
    norm_level_filter = level_filter.strip().upper() if level_filter is not None else None
    norm_service_filter = service_filter.strip() if service_filter is not None else None

    counts: Counter = Counter()
    total_data_rows = 0

    for row in reader:
        total_data_rows += 1
        service, level = normalise_row(row)

        if norm_level_filter is not None and level != norm_level_filter:
            continue
        if norm_service_filter is not None and service != norm_service_filter:
            continue

        counts[(service, level)] += 1

    return counts, total_data_rows, None


def apply_min_count(counts: Counter, min_count: int) -> Counter:
    """Return a new Counter containing only groups with count >= *min_count*."""
    return Counter({k: v for k, v in counts.items() if v >= min_count})


def sorted_rows(counts: Counter) -> list[tuple[str, str, int]]:
    """Return ``[(service, level, count), ...]`` sorted by count descending."""
    return [
        (svc, lvl, cnt)
        for (svc, lvl), cnt in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    ]


# ── Entry point ────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    """Run logsum and return an exit code."""
    args = resolve_args(argv)

    # --input is logically required; checked after positional absorption.
    if args.input is None:
        print("logsum: error: --input is required", file=sys.stderr)
        return 1

    # Open the input file (exit 1 on any OS error).
    file_obj, open_error = open_input_file(args.input)
    if open_error is not None:
        print(open_error, file=sys.stderr)
        return 1

    try:
        counts, total_data_rows, missing_col = aggregate(
            file_obj,
            level_filter=args.level,
            service_filter=args.service,
        )
    finally:
        file_obj.close()

    # Exit 2: required column missing.
    if missing_col is not None:
        print(f"Missing required column: {missing_col}", file=sys.stderr)
        return 2

    # Apply post-aggregation --min-count filter.
    if args.min_count is not None:
        counts = apply_min_count(counts, args.min_count)

    # Exit 3: no rows to output.
    if not counts:
        if total_data_rows == 0:
            # Edge case 3: header-only file (or truly empty).
            print("No log entries found.", file=sys.stderr)
        else:
            # Edge cases 4 & 10: filters eliminated all rows / groups.
            print("No log entries match the active filters.", file=sys.stderr)
        return 3

    # Write the summary CSV (exit 0).
    emit_output(sorted_rows(counts), args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
