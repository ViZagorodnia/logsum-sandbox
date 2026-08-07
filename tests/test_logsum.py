"""
Black-box test suite for logsum, derived from spec.md alone.

All tests invoke ``python -m src.logsum`` via subprocess and check
stdout, stderr, and exit codes without reading the implementation.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


# ── Helpers ────────────────────────────────────────────────────────────────

PYTHON = sys.executable


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run logsum with *args* and return the CompletedProcess result."""
    cmd = [PYTHON, "-m", "src.logsum", *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def run_from_project(tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    """Run logsum from the project root (needed for -m src.logsum to resolve)."""
    project_root = Path(__file__).parent.parent
    return run(*args, cwd=project_root)


def logsum(*args: str) -> subprocess.CompletedProcess:
    """Convenience wrapper that runs from the project root."""
    project_root = Path(__file__).parent.parent
    return run(*args, cwd=project_root)


# ── Basic smoke test ───────────────────────────────────────────────────────

class TestHelp:
    def test_help_exits_zero(self):
        result = logsum("--help")
        assert result.returncode == 0

    def test_help_goes_to_stdout(self):
        result = logsum("--help")
        assert "logsum" in result.stdout.lower() or "usage" in result.stdout.lower()

    def test_help_stderr_empty(self):
        result = logsum("--help")
        assert result.stderr == ""


# ── Output format ──────────────────────────────────────────────────────────

class TestOutputFormat:
    def test_header_row(self, make_csv):
        csv_path = make_csv("f.csv", ["t,INFO,svc-a,msg"])
        result = logsum("--input", str(csv_path))
        assert result.stdout.startswith("service,level,count\n")

    def test_column_order_service_level_count(self, make_csv):
        csv_path = make_csv("f.csv", ["t,ERROR,svc-x,msg"])
        result = logsum("--input", str(csv_path))
        lines = result.stdout.splitlines()
        assert lines[0] == "service,level,count"
        assert lines[1] == "svc-x,ERROR,1"

    def test_no_trailing_newline(self, make_csv):
        csv_path = make_csv("f.csv", ["t,INFO,svc,msg"])
        result = logsum("--input", str(csv_path))
        assert not result.stdout.endswith("\n")

    def test_single_row_output(self, make_csv):
        csv_path = make_csv("f.csv", ["t,WARN,my-svc,m"])
        result = logsum("--input", str(csv_path))
        assert result.stdout == "service,level,count\nmy-svc,WARN,1"

    def test_exit_code_zero_on_success(self, make_csv):
        csv_path = make_csv("f.csv", ["t,INFO,svc,msg"])
        result = logsum("--input", str(csv_path))
        assert result.returncode == 0

    def test_stderr_empty_on_success(self, make_csv):
        csv_path = make_csv("f.csv", ["t,INFO,svc,msg"])
        result = logsum("--input", str(csv_path))
        assert result.stderr == ""


# ── Grouping and aggregation ───────────────────────────────────────────────

class TestGrouping:
    def test_two_rows_same_group_count_2(self, make_csv):
        csv_path = make_csv("f.csv", ["t,ERROR,svc,m", "t,ERROR,svc,m2"])
        result = logsum("--input", str(csv_path))
        lines = result.stdout.splitlines()
        assert lines[1] == "svc,ERROR,2"

    def test_two_groups_different_level(self, make_csv):
        csv_path = make_csv("f.csv", ["t,INFO,svc,m", "t,ERROR,svc,m"])
        result = logsum("--input", str(csv_path))
        lines = result.stdout.splitlines()
        assert len(lines) == 3  # header + 2 groups

    def test_two_groups_different_service(self, make_csv):
        csv_path = make_csv("f.csv", ["t,INFO,svc-a,m", "t,INFO,svc-b,m"])
        result = logsum("--input", str(csv_path))
        lines = result.stdout.splitlines()
        assert len(lines) == 3  # header + 2 groups

    def test_sort_descending_by_count(self, make_csv):
        rows = [
            "t,INFO,svc,m",       # 1 INFO
            "t,ERROR,svc,m",
            "t,ERROR,svc,m",
            "t,ERROR,svc,m",      # 3 ERROR
        ]
        csv_path = make_csv("f.csv", rows)
        result = logsum("--input", str(csv_path))
        lines = result.stdout.splitlines()
        # First data row must have highest count
        parts_first = lines[1].split(",")
        parts_second = lines[2].split(",")
        assert int(parts_first[2]) >= int(parts_second[2])

    def test_sort_highest_count_first(self, make_csv):
        rows = ["t,INFO,svc,m"] * 5 + ["t,ERROR,svc,m"] * 2
        csv_path = make_csv("f.csv", rows)
        result = logsum("--input", str(csv_path))
        lines = result.stdout.splitlines()
        assert lines[1] == "svc,INFO,5"
        assert lines[2] == "svc,ERROR,2"

    def test_multi_service_multi_level(self, make_csv):
        rows = [
            "t,ERROR,checkout,m",
            "t,ERROR,checkout,m",
            "t,INFO,checkout,m",
            "t,WARN,cart,m",
            "t,INFO,cart,m",
            "t,INFO,cart,m",
        ]
        csv_path = make_csv("f.csv", rows)
        result = logsum("--input", str(csv_path))
        lines = result.stdout.splitlines()
        counts = {(row.split(",")[0], row.split(",")[1]): int(row.split(",")[2])
                  for row in lines[1:]}
        assert counts[("checkout", "ERROR")] == 2
        assert counts[("checkout", "INFO")] == 1
        assert counts[("cart", "WARN")] == 1
        assert counts[("cart", "INFO")] == 2


# ── Normalisation ──────────────────────────────────────────────────────────

class TestNormalisation:
    def test_level_uppercased(self, make_csv):
        csv_path = make_csv("f.csv", ["t,error,svc,m"])
        result = logsum("--input", str(csv_path))
        assert "svc,ERROR,1" in result.stdout

    def test_level_mixed_case_uppercased(self, make_csv):
        csv_path = make_csv("f.csv", ["t,Error,svc,m"])
        result = logsum("--input", str(csv_path))
        assert "ERROR" in result.stdout

    def test_level_with_leading_trailing_whitespace(self, make_csv):
        csv_path = make_csv("f.csv", ["t, warn ,svc,m"])
        result = logsum("--input", str(csv_path))
        assert "svc,WARN,1" in result.stdout

    def test_service_whitespace_stripped(self, make_csv):
        csv_path = make_csv("f.csv", ["t,INFO, cart-api ,m"])
        result = logsum("--input", str(csv_path))
        assert "cart-api,INFO,1" in result.stdout

    def test_service_casing_preserved(self, make_csv):
        csv_path = make_csv("f.csv", ["t,INFO,MyService,m"])
        result = logsum("--input", str(csv_path))
        assert "MyService,INFO,1" in result.stdout

    def test_normalised_rows_merge_into_same_group(self, make_csv):
        # "warn" and " WARN " should both normalise to WARN for the same svc
        csv_path = make_csv("f.csv", ["t,warn,svc,m", "t, WARN ,svc,m"])
        result = logsum("--input", str(csv_path))
        lines = result.stdout.splitlines()
        # Should be 1 data row with count 2
        assert len(lines) == 2
        assert lines[1] == "svc,WARN,2"


# ── Filters ────────────────────────────────────────────────────────────────

class TestFilters:
    def test_level_filter_keeps_matching_rows(self, make_csv):
        csv_path = make_csv("f.csv", ["t,ERROR,svc,m", "t,INFO,svc,m"])
        result = logsum("--input", str(csv_path), "--level", "ERROR")
        assert "svc,ERROR,1" in result.stdout
        assert "INFO" not in result.stdout

    def test_level_filter_case_insensitive(self, make_csv):
        csv_path = make_csv("f.csv", ["t,ERROR,svc,m", "t,INFO,svc,m"])
        result = logsum("--input", str(csv_path), "--level", "error")
        assert "ERROR" in result.stdout
        assert "INFO" not in result.stdout

    def test_service_filter_keeps_matching_rows(self, make_csv):
        csv_path = make_csv("f.csv", ["t,INFO,svc-a,m", "t,INFO,svc-b,m"])
        result = logsum("--input", str(csv_path), "--service", "svc-a")
        assert "svc-a,INFO,1" in result.stdout
        assert "svc-b" not in result.stdout

    def test_service_filter_case_sensitive(self, make_csv):
        csv_path = make_csv("f.csv", ["t,INFO,SvcA,m", "t,INFO,svca,m"])
        result = logsum("--input", str(csv_path), "--service", "SvcA")
        assert "SvcA,INFO,1" in result.stdout
        assert "svca" not in result.stdout

    def test_combined_level_and_service_filter(self, make_csv):
        csv_path = make_csv("f.csv", [
            "t,ERROR,svc-a,m",
            "t,INFO,svc-a,m",
            "t,ERROR,svc-b,m",
        ])
        result = logsum("--input", str(csv_path), "--level", "ERROR", "--service", "svc-a")
        assert result.stdout == "service,level,count\nsvc-a,ERROR,1"

    def test_min_count_filters_low_count_groups(self, make_csv):
        rows = ["t,INFO,svc,m"] * 3 + ["t,WARN,svc,m"]
        csv_path = make_csv("f.csv", rows)
        result = logsum("--input", str(csv_path), "--min-count", "2")
        assert "INFO" in result.stdout
        assert "WARN" not in result.stdout

    def test_min_count_1_keeps_all_groups(self, make_csv):
        csv_path = make_csv("f.csv", ["t,INFO,svc,m", "t,WARN,svc,m"])
        result = logsum("--input", str(csv_path), "--min-count", "1")
        lines = result.stdout.splitlines()
        assert len(lines) == 3  # header + 2 groups

    def test_min_count_exact_boundary_included(self, make_csv):
        rows = ["t,ERROR,svc,m"] * 3
        csv_path = make_csv("f.csv", rows)
        result = logsum("--input", str(csv_path), "--min-count", "3")
        assert "svc,ERROR,3" in result.stdout

    def test_min_count_exact_boundary_excluded(self, make_csv):
        rows = ["t,ERROR,svc,m"] * 2
        csv_path = make_csv("f.csv", rows)
        result = logsum("--input", str(csv_path), "--min-count", "3")
        assert result.returncode == 3

    def test_level_filter_exit_0_when_matches(self, make_csv):
        csv_path = make_csv("f.csv", ["t,ERROR,svc,m"])
        result = logsum("--input", str(csv_path), "--level", "ERROR")
        assert result.returncode == 0

    def test_service_filter_exit_0_when_matches(self, make_csv):
        csv_path = make_csv("f.csv", ["t,INFO,svc,m"])
        result = logsum("--input", str(csv_path), "--service", "svc")
        assert result.returncode == 0


# ── Edge case 1: File not found / permission denied ────────────────────────

class TestEdgeCase1FileNotFound:
    def test_exit_code_1_on_missing_file(self):
        result = logsum("--input", "/nonexistent/path/file.csv")
        assert result.returncode == 1

    def test_stderr_error_format_missing_file(self):
        result = logsum("--input", "/nonexistent/path/file.csv")
        assert result.stderr.startswith("Error: cannot open '/nonexistent/path/file.csv':")

    def test_stderr_includes_os_message(self):
        result = logsum("--input", "/nonexistent/path/file.csv")
        # The OS error message (e.g. "No such file or directory") should appear
        assert len(result.stderr.strip()) > len("Error: cannot open '/nonexistent/path/file.csv': ")

    def test_stdout_empty_on_file_error(self):
        result = logsum("--input", "/nonexistent/path/file.csv")
        assert result.stdout == ""


# ── Edge case 2: Missing required column ──────────────────────────────────

class TestEdgeCase2MissingColumn:
    def test_exit_code_2_missing_level(self, make_csv):
        csv_path = make_csv("f.csv", [], header="timestamp,service,message")
        result = logsum("--input", str(csv_path))
        assert result.returncode == 2

    def test_stderr_missing_column_name(self, make_csv):
        csv_path = make_csv("f.csv", [], header="timestamp,service,message")
        result = logsum("--input", str(csv_path))
        assert result.stderr.strip() == "Missing required column: level"

    def test_exit_code_2_missing_service(self, make_csv):
        csv_path = make_csv("f.csv", [], header="timestamp,level,message")
        result = logsum("--input", str(csv_path))
        assert result.returncode == 2

    def test_stderr_missing_service_column(self, make_csv):
        csv_path = make_csv("f.csv", [], header="timestamp,level,message")
        result = logsum("--input", str(csv_path))
        assert result.stderr.strip() == "Missing required column: service"

    def test_stdout_empty_on_missing_column(self, make_csv):
        csv_path = make_csv("f.csv", [], header="timestamp,service,message")
        result = logsum("--input", str(csv_path))
        assert result.stdout == ""


# ── Edge case 3: Header-only file ─────────────────────────────────────────

class TestEdgeCase3HeaderOnly:
    def test_exit_code_3_header_only(self, make_csv):
        csv_path = make_csv("f.csv", [])
        result = logsum("--input", str(csv_path))
        assert result.returncode == 3

    def test_stderr_no_log_entries_found(self, make_csv):
        csv_path = make_csv("f.csv", [])
        result = logsum("--input", str(csv_path))
        assert result.stderr.strip() == "No log entries found."

    def test_stdout_empty_header_only(self, make_csv):
        csv_path = make_csv("f.csv", [])
        result = logsum("--input", str(csv_path))
        assert result.stdout == ""


# ── Edge case 4: All rows filtered out ────────────────────────────────────

class TestEdgeCase4AllFiltered:
    def test_exit_code_3_level_filter_removes_all(self, make_csv):
        csv_path = make_csv("f.csv", ["t,INFO,svc,m"])
        result = logsum("--input", str(csv_path), "--level", "ERROR")
        assert result.returncode == 3

    def test_stderr_no_match_active_filters_level(self, make_csv):
        csv_path = make_csv("f.csv", ["t,INFO,svc,m"])
        result = logsum("--input", str(csv_path), "--level", "ERROR")
        assert result.stderr.strip() == "No log entries match the active filters."

    def test_exit_code_3_service_filter_removes_all(self, make_csv):
        csv_path = make_csv("f.csv", ["t,INFO,svc-a,m"])
        result = logsum("--input", str(csv_path), "--service", "svc-b")
        assert result.returncode == 3

    def test_stderr_no_match_active_filters_service(self, make_csv):
        csv_path = make_csv("f.csv", ["t,INFO,svc-a,m"])
        result = logsum("--input", str(csv_path), "--service", "svc-b")
        assert result.stderr.strip() == "No log entries match the active filters."

    def test_different_message_for_header_only_vs_filtered(self, make_csv):
        # Header-only → "No log entries found."
        header_only = make_csv("h.csv", [])
        r_empty = logsum("--input", str(header_only))
        # Rows exist but filtered → different message
        has_rows = make_csv("r.csv", ["t,INFO,svc,m"])
        r_filtered = logsum("--input", str(has_rows), "--level", "WARN")
        assert r_empty.stderr.strip() != r_filtered.stderr.strip()
        assert r_empty.stderr.strip() == "No log entries found."
        assert r_filtered.stderr.strip() == "No log entries match the active filters."


# ── Edge case 5: Unknown level value ──────────────────────────────────────

class TestEdgeCase5UnknownLevel:
    def test_debug_level_kept_as_is(self, make_csv):
        csv_path = make_csv("f.csv", ["t,DEBUG,svc,m"])
        result = logsum("--input", str(csv_path))
        assert "svc,DEBUG,1" in result.stdout
        assert result.returncode == 0

    def test_trace_level_kept_as_is(self, make_csv):
        csv_path = make_csv("f.csv", ["t,TRACE,svc,m"])
        result = logsum("--input", str(csv_path))
        assert "svc,TRACE,1" in result.stdout

    def test_unknown_level_not_collapsed_to_other(self, make_csv):
        csv_path = make_csv("f.csv", ["t,VERBOSE,svc,m"])
        result = logsum("--input", str(csv_path))
        assert "OTHER" not in result.stdout
        assert "VERBOSE" in result.stdout


# ── Edge case 6: Malformed/missing timestamp ──────────────────────────────

class TestEdgeCase6Timestamp:
    def test_empty_timestamp_row_still_counted(self, make_csv):
        csv_path = make_csv("f.csv", [",INFO,svc,m"])
        result = logsum("--input", str(csv_path))
        assert "svc,INFO,1" in result.stdout
        assert result.returncode == 0

    def test_invalid_timestamp_row_still_counted(self, make_csv):
        csv_path = make_csv("f.csv", ["not-a-date,WARN,svc,m"])
        result = logsum("--input", str(csv_path))
        assert "svc,WARN,1" in result.stdout


# ── Edge case 7: Extra columns silently ignored ────────────────────────────

class TestEdgeCase7ExtraColumns:
    def test_extra_column_ignored(self, make_csv):
        csv_path = make_csv(
            "f.csv",
            ["t,INFO,svc,msg,extra-value"],
            header="timestamp,level,service,message,extra",
        )
        result = logsum("--input", str(csv_path))
        assert "svc,INFO,1" in result.stdout
        assert result.returncode == 0

    def test_multiple_extra_columns_ignored(self, make_csv):
        csv_path = make_csv(
            "f.csv",
            ["t,WARN,svc,msg,x,y,z"],
            header="timestamp,level,service,message,col1,col2,col3",
        )
        result = logsum("--input", str(csv_path))
        assert "svc,WARN,1" in result.stdout


# ── Edge case 8: Empty level field ────────────────────────────────────────

class TestEdgeCase8EmptyLevel:
    def test_empty_level_kept_as_empty_string(self, make_csv):
        csv_path = make_csv("f.csv", ["t,,svc,m"])
        result = logsum("--input", str(csv_path))
        assert result.returncode == 0
        # Empty level → group key has empty string for level
        lines = result.stdout.splitlines()
        # The level column in output should be empty: "svc,,1"
        assert any(line.startswith("svc,,") for line in lines[1:])

    def test_whitespace_only_level_becomes_empty(self, make_csv):
        csv_path = make_csv("f.csv", ["t,   ,svc,m"])
        result = logsum("--input", str(csv_path))
        # After strip+uppercase of "   " → ""
        lines = result.stdout.splitlines()
        assert any(line.startswith("svc,,") for line in lines[1:])


# ── Edge case 9: Duplicate header row in body ─────────────────────────────

class TestEdgeCase9DuplicateHeader:
    def test_header_row_in_body_treated_as_data(self, make_csv):
        csv_path = make_csv("f.csv", [
            "timestamp,level,service,message",  # duplicate header in body
            "t,INFO,svc,m",
        ])
        result = logsum("--input", str(csv_path))
        assert result.returncode == 0
        # "level" becomes "LEVEL" after normalisation, "service" stays "service"
        assert "service,LEVEL,1" in result.stdout

    def test_real_data_row_still_counted(self, make_csv):
        csv_path = make_csv("f.csv", [
            "timestamp,level,service,message",
            "t,INFO,svc,m",
        ])
        result = logsum("--input", str(csv_path))
        assert "svc,INFO,1" in result.stdout


# ── Edge case 10: --min-count removes all groups ──────────────────────────

class TestEdgeCase10MinCountAllFiltered:
    def test_exit_code_3_all_groups_below_min_count(self, make_csv):
        rows = ["t,INFO,svc,m"] * 2
        csv_path = make_csv("f.csv", rows)
        result = logsum("--input", str(csv_path), "--min-count", "5")
        assert result.returncode == 3

    def test_stderr_active_filters_message_for_min_count(self, make_csv):
        rows = ["t,INFO,svc,m"] * 2
        csv_path = make_csv("f.csv", rows)
        result = logsum("--input", str(csv_path), "--min-count", "5")
        assert result.stderr.strip() == "No log entries match the active filters."

    def test_stdout_empty_when_min_count_removes_all(self, make_csv):
        csv_path = make_csv("f.csv", ["t,INFO,svc,m"])
        result = logsum("--input", str(csv_path), "--min-count", "10")
        assert result.stdout == ""


# ── --output flag ─────────────────────────────────────────────────────────

class TestOutputFlag:
    def test_output_flag_writes_to_file(self, make_csv, tmp_path):
        csv_path = make_csv("in.csv", ["t,INFO,svc,m"])
        out_path = tmp_path / "out.csv"
        result = logsum("--input", str(csv_path), "--output", str(out_path))
        assert result.returncode == 0
        assert out_path.exists()

    def test_output_flag_file_content_matches_stdout_format(self, make_csv, tmp_path):
        csv_path = make_csv("in.csv", ["t,ERROR,svc,m", "t,ERROR,svc,m"])
        out_path = tmp_path / "out.csv"
        logsum("--input", str(csv_path), "--output", str(out_path))
        content = out_path.read_text(encoding="utf-8")
        assert content == "service,level,count\nsvc,ERROR,2"

    def test_stdout_empty_when_output_flag_used(self, make_csv, tmp_path):
        csv_path = make_csv("in.csv", ["t,INFO,svc,m"])
        out_path = tmp_path / "out.csv"
        result = logsum("--input", str(csv_path), "--output", str(out_path))
        assert result.stdout == ""

    def test_output_file_no_trailing_newline(self, make_csv, tmp_path):
        csv_path = make_csv("in.csv", ["t,INFO,svc,m"])
        out_path = tmp_path / "out.csv"
        logsum("--input", str(csv_path), "--output", str(out_path))
        content = out_path.read_text(encoding="utf-8")
        assert not content.endswith("\n")


# ── Positional argument shorthand ─────────────────────────────────────────

class TestPositionalShorthand:
    def test_bare_positional_as_input(self, make_csv):
        csv_path = make_csv("f.csv", ["t,INFO,svc,m"])
        result = logsum(str(csv_path))
        assert result.returncode == 0
        assert "svc,INFO,1" in result.stdout

    def test_two_positionals_as_input_and_output(self, make_csv, tmp_path):
        csv_path = make_csv("in.csv", ["t,WARN,svc,m"])
        out_path = tmp_path / "out.csv"
        result = logsum(str(csv_path), str(out_path))
        assert result.returncode == 0
        assert out_path.exists()
        assert "svc,WARN,1" in out_path.read_text(encoding="utf-8")

    def test_positional_input_with_level_flag(self, make_csv):
        csv_path = make_csv("f.csv", ["t,INFO,svc,m", "t,WARN,svc,m"])
        result = logsum(str(csv_path), "--level", "INFO")
        assert result.returncode == 0
        assert "INFO" in result.stdout
        assert "WARN" not in result.stdout


# ── Sorting tie-breaking ───────────────────────────────────────────────────

class TestSorting:
    def test_three_groups_sorted_desc(self, make_csv):
        rows = (
            ["t,ERROR,svc,m"] * 5
            + ["t,WARN,svc,m"] * 3
            + ["t,INFO,svc,m"] * 1
        )
        csv_path = make_csv("f.csv", rows)
        result = logsum("--input", str(csv_path))
        lines = result.stdout.splitlines()[1:]  # skip header
        counts = [int(row.split(",")[2]) for row in lines]
        assert counts == sorted(counts, reverse=True)

    def test_single_group_one_row(self, make_csv):
        csv_path = make_csv("f.csv", ["t,DEBUG,my-svc,m"])
        result = logsum("--input", str(csv_path))
        assert result.stdout == "service,level,count\nmy-svc,DEBUG,1"

    def test_large_count_first(self, make_csv):
        rows = ["t,INFO,svc,m"] * 100 + ["t,ERROR,svc,m"]
        csv_path = make_csv("f.csv", rows)
        result = logsum("--input", str(csv_path))
        lines = result.stdout.splitlines()
        assert lines[1].endswith(",100")
        assert lines[2].endswith(",1")


# ── Spec example data ──────────────────────────────────────────────────────

class TestSpecExample:
    """Verify the exact example from spec.md produces the expected output."""

    SPEC_ROWS = [
        "2026-08-01T08:00:01Z,INFO,identity-service,Token issued for user u-1042",
        "2026-08-01T08:01:15Z,ERROR,checkout-service,Payment gateway timeout",
        "2026-08-01T08:01:25Z,WARN,cart-api,Cart session not found cs-9900",
    ]

    def test_spec_example_exit_zero(self, make_csv):
        csv_path = make_csv("spec.csv", self.SPEC_ROWS)
        result = logsum("--input", str(csv_path))
        assert result.returncode == 0

    def test_spec_example_three_groups(self, make_csv):
        csv_path = make_csv("spec.csv", self.SPEC_ROWS)
        result = logsum("--input", str(csv_path))
        lines = result.stdout.splitlines()
        assert len(lines) == 4  # header + 3 groups

    def test_spec_example_correct_services(self, make_csv):
        csv_path = make_csv("spec.csv", self.SPEC_ROWS)
        result = logsum("--input", str(csv_path))
        assert "identity-service" in result.stdout
        assert "checkout-service" in result.stdout
        assert "cart-api" in result.stdout

    def test_spec_example_header_first(self, make_csv):
        csv_path = make_csv("spec.csv", self.SPEC_ROWS)
        result = logsum("--input", str(csv_path))
        assert result.stdout.startswith("service,level,count\n")
