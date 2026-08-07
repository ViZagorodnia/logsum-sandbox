"""logsum — CLI log summariser (Meridian AI Factory, Kata 5.3)

Reads a UTF-8 CSV file produced by Meridian platform services and writes
a one-row-per-group summary CSV counting events by service and log level,
sorted by count descending.

Spec: spec.md (signed off 2026-08-06)
Stdlib only: csv, argparse, collections, sys, io  — no third-party packages.

Usage:
    python -m src.logsum --input <path> [--output <path>] \\
                         [--level <LEVEL>] [--service <name>]
    python -m src.logsum <input> [<output>]          # positional shorthand
"""

import argparse
import collections
import csv
import io
import sys

OUTPUT_COLUMNS: tuple[str, ...] = ("service", "level", "count")
REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {"timestamp", "level", "service", "message"}
)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="logsum",
        description="Count Meridian log events by service and level.",
    )
    p.add_argument(
        "--input",
        metavar="PATH",
        default=None,
        help="Path to a UTF-8 CSV log file (required)",
    )
    p.add_argument(
        "--output",
        metavar="PATH",
        default=None,
        help="Write summary CSV to PATH instead of stdout",
    )
    p.add_argument(
        "--level",
        metavar="LEVEL",
        default=None,
        help="Pre-filter rows to a single log level before grouping",
    )
    p.add_argument(
        "--service",
        metavar="NAME",
        default=None,
        help="Pre-filter rows to a single service name before grouping",
    )
    # Hidden positional shorthand: logsum INPUT [OUTPUT]
    p.add_argument("positional_args", nargs="*", help=argparse.SUPPRESS)
    return p


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = _make_parser()
    args = parser.parse_args(argv)

    # Absorb positional shorthand when flags were not supplied
    pos = args.positional_args
    if pos:
        if args.input is None:
            args.input = pos[0]
        if args.output is None and len(pos) >= 2:
            args.output = pos[1]

    if args.input is None:
        parser.error("--input is required")

    return args


# ---------------------------------------------------------------------------
# Normalisation  (spec §Normalisation rules)
# ---------------------------------------------------------------------------

def _norm_level(raw: str) -> str:
    """Strip leading/trailing whitespace; convert to UPPERCASE."""
    return raw.strip().upper()


def _norm_service(raw: str) -> str:
    """Strip leading/trailing whitespace; preserve original casing."""
    return raw.strip()


# ---------------------------------------------------------------------------
# Core logic helpers
# ---------------------------------------------------------------------------

def _resolve_columns(reader: csv.DictReader) -> tuple[str, str]:
    """Return (lv_col, sv_col) raw header names, or exit(2) on bad headers."""
    raw_fields = reader.fieldnames
    if not raw_fields:
        # Completely empty file — no header at all
        print("Missing required column: timestamp", file=sys.stderr)
        sys.exit(2)

    # Build normalised → raw header map to handle whitespace-padded headers
    field_map: dict[str, str] = {f.strip().lower(): f for f in raw_fields}

    missing = REQUIRED_COLUMNS - set(field_map)
    if missing:
        print(f"Missing required column: {sorted(missing)[0]}", file=sys.stderr)
        sys.exit(2)

    return field_map["level"], field_map["service"]


def _aggregate(
    reader: csv.DictReader,
    lv_col: str,
    sv_col: str,
    level_filter_norm: str | None,
    service_filter_norm: str | None,
) -> tuple[collections.Counter, int, int]:
    """Count (service, level) pairs; return (counts, total_rows, matched_rows)."""
    counts: collections.Counter[tuple[str, str]] = collections.Counter()
    total_data_rows = 0
    matched_rows = 0

    for row in reader:
        total_data_rows += 1

        service_norm = _norm_service(row.get(sv_col, ""))
        level_norm = _norm_level(row.get(lv_col, ""))

        # Apply pre-filters (spec §Inputs — --level / --service flags)
        # Unknown level values are NOT collapsed to OTHER (spec §Normalisation rules)
        if level_filter_norm is not None and level_norm != level_filter_norm:
            continue
        if service_filter_norm is not None and service_norm != service_filter_norm:
            continue

        counts[(service_norm, level_norm)] += 1
        matched_rows += 1

    return counts, total_data_rows, matched_rows


def _write_csv(dest, sorted_groups) -> None:
    """Write the summary CSV header and data rows to *dest*."""
    writer = csv.writer(dest, lineterminator="\n")
    writer.writerow(OUTPUT_COLUMNS)
    for (service, level), count in sorted_groups:
        writer.writerow([service, level, count])


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def summarise(
    input_path: str,
    output_path: str | None,
    level_filter: str | None,
    service_filter: str | None,
) -> None:
    """Read input CSV, aggregate, write summary CSV.  Exits on any error."""
    level_filter_norm = _norm_level(level_filter) if level_filter is not None else None
    service_filter_norm = _norm_service(service_filter) if service_filter is not None else None

    try:
        fh = open(input_path, newline="", encoding="utf-8")
    except OSError as exc:
        print(
            f"Error: cannot open '{input_path}': {exc.strerror}",
            file=sys.stderr,
        )
        sys.exit(1)

    with fh:
        reader = csv.DictReader(fh)
        lv_col, sv_col = _resolve_columns(reader)
        counts, total_data_rows, matched_rows = _aggregate(
            reader, lv_col, sv_col, level_filter_norm, service_filter_norm
        )

    if total_data_rows == 0:
        # Edge case 3: header-only file — no data rows at all
        print("No log entries found.", file=sys.stderr)
        sys.exit(3)

    if matched_rows == 0:
        # Edge case 4: rows exist but all were filtered out
        print("No log entries match the active filters.", file=sys.stderr)
        sys.exit(3)

    sorted_groups = sorted(counts.items(), key=lambda kv: -kv[1])

    if output_path is None:
        # Stdout: buffer to avoid mixing with any deferred error text
        buf = io.StringIO()
        _write_csv(buf, sorted_groups)
        sys.stdout.write(buf.getvalue())
    else:
        try:
            with open(output_path, "w", encoding="utf-8", newline="") as out_fh:
                _write_csv(out_fh, sorted_groups)
        except OSError as exc:
            print(
                f"Error: cannot open '{output_path}': {exc.strerror}",
                file=sys.stderr,
            )
            sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    summarise(
        input_path=args.input,
        output_path=args.output,
        level_filter=args.level,
        service_filter=args.service,
    )


if __name__ == "__main__":
    main()
