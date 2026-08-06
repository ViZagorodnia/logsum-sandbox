"""
Pytest test-suite for ``logsum`` — derived exclusively from spec.md (kata 5.2/5.3).
``src/logsum.py`` was NOT read.  Every assertion goes through the CLI black-box.

Coverage map
────────────
[G] Grouping            – spec §Grouping rule
[N] Normalisation       – spec §Normalisation rules
[S] Sorting / format    – spec §Outputs
[F] Filters             – spec §Inputs (--level / --service)
[E] Edge cases          – spec §Edge cases  (#1–#9)
[X] Exit codes          – spec §Exit codes
[O] --output flag       – spec §Inputs
[H] --help              – spec §Help flag
[P] Positional-arg      – spec §Implementation notes
"""
from __future__ import annotations

import csv
import io
import subprocess
import sys
from pathlib import Path

import pytest

# ── Path to committed fixture files ───────────────────────────────────────

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# ── CLI helpers ───────────────────────────────────────────────────────────

_CMD = [sys.executable, "-m", "src.logsum"]


def logsum(*args: str) -> subprocess.CompletedProcess:
    """Run ``python -m src.logsum <args>`` and return the CompletedProcess."""
    return subprocess.run(_CMD + list(args), capture_output=True, text=True)


def parse_output(stdout: str) -> list[dict[str, str]]:
    """Parse summary-CSV text (from stdout) into a list of row dicts."""
    return list(csv.DictReader(io.StringIO(stdout.strip())))


# ═══════════════════════════════════════════════════════════════════════════
# [G] Grouping
# ═══════════════════════════════════════════════════════════════════════════

class TestGrouping:
    """Each unique (service, level) pair → exactly one output row (§Grouping rule)."""

    def test_single_row_produces_one_group(self, make_csv):
        p = make_csv("g1.csv", ["t,ERROR,checkout-service,oops"])
        rows = parse_output(logsum("--input", str(p)).stdout)
        assert len(rows) == 1
        assert rows[0]["service"] == "checkout-service"
        assert rows[0]["level"] == "ERROR"
        assert rows[0]["count"] == "1"

    def test_identical_pairs_merged_and_counted(self, make_csv):
        p = make_csv("g2.csv", [
            "t,ERROR,svc-a,first message",
            "t,ERROR,svc-a,second message",
        ])
        rows = parse_output(logsum("--input", str(p)).stdout)
        assert len(rows) == 1
        assert rows[0]["count"] == "2"

    def test_same_service_different_levels_are_separate(self, make_csv):
        p = make_csv("g3.csv", [
            "t,ERROR,svc-a,m",
            "t,WARN,svc-a,m",
            "t,INFO,svc-a,m",
        ])
        rows = parse_output(logsum("--input", str(p)).stdout)
        assert len(rows) == 3
        assert {r["level"] for r in rows} == {"ERROR", "WARN", "INFO"}

    def test_same_level_different_services_are_separate(self, make_csv):
        p = make_csv("g4.csv", [
            "t,INFO,alpha,m",
            "t,INFO,beta,m",
            "t,INFO,gamma,m",
        ])
        rows = parse_output(logsum("--input", str(p)).stdout)
        assert len(rows) == 3
        assert {r["service"] for r in rows} == {"alpha", "beta", "gamma"}

    def test_message_content_does_not_split_groups(self, make_csv):
        """Rows differing only in message → same group."""
        p = make_csv("g5.csv", [
            "t,INFO,svc,first message",
            "t,INFO,svc,completely different message",
        ])
        rows = parse_output(logsum("--input", str(p)).stdout)
        assert len(rows) == 1
        assert rows[0]["count"] == "2"

    def test_timestamp_does_not_split_groups(self, make_csv):
        """Rows differing only in timestamp → same group."""
        p = make_csv("g6.csv", [
            "2026-01-01T00:00:00Z,INFO,svc,m",
            "2026-06-15T12:30:00Z,INFO,svc,m",
        ])
        rows = parse_output(logsum("--input", str(p)).stdout)
        assert len(rows) == 1
        assert rows[0]["count"] == "2"

    def test_count_minimum_is_one(self, make_csv):
        """The spec states minimum count value is 1 (§Aggregation)."""
        p = make_csv("g7.csv", ["t,INFO,svc,m"])
        rows = parse_output(logsum("--input", str(p)).stdout)
        assert int(rows[0]["count"]) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# [N] Normalisation
# ═══════════════════════════════════════════════════════════════════════════

class TestNormalisation:
    """§Normalisation rules — applied to every row before grouping."""

    def test_level_lowercase_uppercased(self, make_csv):
        p = make_csv("n1.csv", [
            "t,info,svc,m",
            "t,warn,svc,m",
            "t,error,svc,m",
        ])
        rows = parse_output(logsum("--input", str(p)).stdout)
        assert {r["level"] for r in rows} == {"INFO", "WARN", "ERROR"}

    def test_level_mixed_case_uppercased(self, make_csv):
        p = make_csv("n2.csv", ["t,WaRn,svc,m"])
        rows = parse_output(logsum("--input", str(p)).stdout)
        assert rows[0]["level"] == "WARN"

    def test_level_whitespace_stripped_and_uppercased(self, make_csv):
        # RFC-4180 quoted fields: " warn " → value is ' warn '
        # spec example: " warn " → "WARN"
        p = make_csv("n3.csv", ['t," warn ",svc,m', 't,"  ERROR  ",svc,m'])
        rows = parse_output(logsum("--input", str(p)).stdout)
        assert {r["level"] for r in rows} == {"WARN", "ERROR"}

    def test_service_whitespace_stripped(self, make_csv):
        # spec example: " cart-api " → "cart-api"
        p = make_csv("n4.csv", [
            'T,INFO," cart-api ",m',
            "T,INFO,cart-api,m",
        ])
        rows = parse_output(logsum("--input", str(p)).stdout)
        # Both rows must collapse into one group after stripping
        assert len(rows) == 1
        assert rows[0]["service"] == "cart-api"
        assert rows[0]["count"] == "2"

    def test_service_original_casing_preserved(self, make_csv):
        p = make_csv("n5.csv", ["t,INFO,Cart-API,m"])
        rows = parse_output(logsum("--input", str(p)).stdout)
        assert rows[0]["service"] == "Cart-API"

    def test_service_grouping_is_case_sensitive(self, make_csv):
        """'Cart-API' ≠ 'cart-api' — grouping is case-sensitive on service."""
        p = make_csv("n6.csv", [
            "t,INFO,Cart-API,m",
            "t,INFO,cart-api,m",
        ])
        rows = parse_output(logsum("--input", str(p)).stdout)
        assert {r["service"] for r in rows} == {"Cart-API", "cart-api"}

    def test_malformed_timestamp_row_counted_normally(self, make_csv):
        """Edge case #6 — timestamp not validated; row is counted."""
        p = make_csv("n7.csv", [
            "NOT-A-DATE,INFO,svc,m",
            "also-bad!!,INFO,svc,m",
        ])
        result = logsum("--input", str(p))
        assert result.returncode == 0
        rows = parse_output(result.stdout)
        assert rows[0]["count"] == "2"

    def test_empty_timestamp_row_counted_normally(self, make_csv):
        """Edge case #6 — missing timestamp is not an error."""
        p = make_csv("n8.csv", [",INFO,svc,m"])
        result = logsum("--input", str(p))
        assert result.returncode == 0
        rows = parse_output(result.stdout)
        assert rows[0]["count"] == "1"

    def test_message_field_not_read(self, make_csv):
        """Varying message values never create extra groups."""
        p = make_csv("n9.csv", [
            "t,INFO,svc,alpha",
            "t,INFO,svc,beta",
            "t,INFO,svc,gamma",
        ])
        rows = parse_output(logsum("--input", str(p)).stdout)
        assert len(rows) == 1
        assert rows[0]["count"] == "3"


# ═══════════════════════════════════════════════════════════════════════════
# [S] Output sorting and format
# ═══════════════════════════════════════════════════════════════════════════

class TestOutputFormat:
    """§Outputs — column order, sort order, no first_seen/last_seen."""

    def test_header_column_order_is_service_level_count(self, make_csv):
        p = make_csv("s1.csv", ["t,INFO,svc,m"])
        result = logsum("--input", str(p))
        header = result.stdout.strip().split("\n")[0]
        assert header == "service,level,count"

    def test_sorted_by_count_descending(self, make_csv):
        p = make_csv("s2.csv",
            ["t,ERROR,alpha,m"] * 5 +
            ["t,INFO,beta,m"]  * 3 +
            ["t,WARN,gamma,m"] * 1
        )
        rows = parse_output(logsum("--input", str(p)).stdout)
        counts = [int(r["count"]) for r in rows]
        assert counts == sorted(counts, reverse=True)

    def test_output_contains_no_extra_columns(self, make_csv):
        """No first_seen, last_seen, or other v1 out-of-scope columns."""
        p = make_csv("s3.csv", ["t,INFO,svc,m"])
        rows = parse_output(logsum("--input", str(p)).stdout)
        assert set(rows[0].keys()) == {"service", "level", "count"}

    def test_no_blank_line_after_last_data_row(self, make_csv):
        """'No trailing newline beyond the last data row' (§Outputs)."""
        p = make_csv("s4.csv", ["t,INFO,svc,m"])
        result = logsum("--input", str(p))
        # Must not end with two consecutive newlines (i.e. a blank line)
        assert not result.stdout.endswith("\n\n")

    def test_exit_0_on_success(self, make_csv):
        p = make_csv("s5.csv", ["t,INFO,svc,m"])
        assert logsum("--input", str(p)).returncode == 0


# ═══════════════════════════════════════════════════════════════════════════
# [F] Filters
# ═══════════════════════════════════════════════════════════════════════════

class TestFilters:
    """§Inputs — --level and --service pre-filter rows before grouping."""

    def test_level_filter_applied_after_normalisation(self, make_csv):
        """
        Normalisation (uppercase + strip) must happen BEFORE the --level filter
        is applied.  A raw value of ' error ' normalises to 'ERROR' and must
        match --level ERROR.  An impl that filtered on the raw value would
        return exit 3 here instead of one matching row.
        """
        p = make_csv("f_norm_lvl.csv", ['t," error ",svc,m', 't,info,svc,m'])
        rows = parse_output(logsum("--input", str(p), "--level", "ERROR").stdout)
        assert len(rows) == 1
        assert rows[0]["level"] == "ERROR"
        assert rows[0]["count"] == "1"

    def test_service_filter_applied_after_normalisation(self, make_csv):
        """
        Normalisation (whitespace strip) must happen BEFORE the --service
        filter is applied.  A raw service of ' cart-api ' normalises to
        'cart-api' and must match --service cart-api.
        """
        p = make_csv("f_norm_svc.csv", ['T,INFO," cart-api ",m', 'T,INFO,beta,m'])
        rows = parse_output(logsum("--input", str(p), "--service", "cart-api").stdout)
        assert len(rows) == 1
        assert rows[0]["service"] == "cart-api"

    def test_level_filter_keeps_only_matching_level(self, make_csv):
        p = make_csv("f1.csv", [
            "t,INFO,svc,m",
            "t,ERROR,svc,m",
            "t,WARN,svc,m",
        ])
        rows = parse_output(logsum("--input", str(p), "--level", "ERROR").stdout)
        assert all(r["level"] == "ERROR" for r in rows)
        assert len(rows) == 1

    def test_service_filter_keeps_only_matching_service(self, make_csv):
        p = make_csv("f2.csv", [
            "t,INFO,alpha,m",
            "t,INFO,beta,m",
            "t,ERROR,alpha,m",
        ])
        rows = parse_output(logsum("--input", str(p), "--service", "alpha").stdout)
        assert all(r["service"] == "alpha" for r in rows)
        assert len(rows) == 2

    def test_combined_level_and_service_filter(self, make_csv):
        p = make_csv("f3.csv", [
            "t,INFO,alpha,m",
            "t,ERROR,alpha,m",
            "t,INFO,beta,m",
        ])
        rows = parse_output(
            logsum("--input", str(p), "--service", "alpha", "--level", "INFO").stdout
        )
        assert len(rows) == 1
        assert rows[0]["service"] == "alpha"
        assert rows[0]["level"] == "INFO"

    def test_filtered_rows_excluded_from_count(self, make_csv):
        """count reflects only rows that survived the filter."""
        p = make_csv("f4.csv", [
            "t,ERROR,svc,m",
            "t,ERROR,svc,m",
            "t,INFO,svc,m",   # filtered out by --level ERROR
        ])
        rows = parse_output(logsum("--input", str(p), "--level", "ERROR").stdout)
        assert rows[0]["count"] == "2"


# ═══════════════════════════════════════════════════════════════════════════
# [E] Edge cases
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Direct mapping to the nine numbered edge cases in §Edge cases."""

    # Edge case #5 — unknown level value
    def test_unknown_level_kept_as_is(self, make_csv):
        p = make_csv("e5a.csv", ["t,DEBUG,svc,m", "t,TRACE,svc,m"])
        rows = parse_output(logsum("--input", str(p)).stdout)
        assert {r["level"] for r in rows} == {"DEBUG", "TRACE"}

    def test_unknown_level_not_collapsed_to_other(self, make_csv):
        """Unknown levels are NOT collapsed to 'OTHER' (spec is explicit)."""
        p = make_csv("e5b.csv", ["t,debug,svc,m"])
        rows = parse_output(logsum("--input", str(p)).stdout)
        assert "OTHER" not in {r["level"] for r in rows}
        assert rows[0]["level"] == "DEBUG"

    # Edge case #6 — malformed / missing timestamp (covered in Normalisation too)
    def test_malformed_timestamp_row_not_skipped(self, make_csv):
        p = make_csv("e6.csv", ["GARBAGE-TIMESTAMP,WARN,svc,m"])
        result = logsum("--input", str(p))
        assert result.returncode == 0
        rows = parse_output(result.stdout)
        assert rows[0]["count"] == "1"

    # Edge case #7 — extra columns
    def test_extra_columns_silently_ignored(self, make_csv):
        p = make_csv(
            "e7.csv",
            ["t,INFO,svc,m,xval,yval"],
            header="timestamp,level,service,message,extra1,extra2",
        )
        result = logsum("--input", str(p))
        assert result.returncode == 0
        rows = parse_output(result.stdout)
        assert rows[0]["count"] == "1"
        # Extra columns must NOT bleed into output
        assert set(rows[0].keys()) == {"service", "level", "count"}

    def test_input_column_order_irrelevant(self, make_csv):
        """§Input CSV schema: 'order is not important'."""
        p = make_csv(
            "e7b.csv",
            ["m,svc,INFO,t"],
            header="message,service,level,timestamp",
        )
        result = logsum("--input", str(p))
        assert result.returncode == 0
        rows = parse_output(result.stdout)
        assert rows[0]["service"] == "svc"
        assert rows[0]["level"] == "INFO"

    # Edge case #8 — empty level field
    def test_empty_level_kept_as_empty_string(self, make_csv):
        p = make_csv("e8.csv", ["t,,svc,m", "t,,svc,m"])
        result = logsum("--input", str(p))
        assert result.returncode == 0
        rows = parse_output(result.stdout)
        assert len(rows) == 1
        assert rows[0]["level"] == ""
        assert rows[0]["count"] == "2"

    def test_empty_level_not_mapped_to_other(self, make_csv):
        p = make_csv("e8b.csv", ["t,,svc,m"])
        rows = parse_output(logsum("--input", str(p)).stdout)
        assert rows[0]["level"] != "OTHER"

    # Edge case #9 — duplicate header row in body
    def test_duplicate_header_row_treated_as_data(self, make_csv):
        """Header repeated in body → level='level' → normalised → 'LEVEL' in output."""
        p = make_csv("e9.csv", [
            "t,INFO,svc,m",
            "timestamp,level,service,message",   # header row appearing as data
        ])
        result = logsum("--input", str(p))
        assert result.returncode == 0
        rows = parse_output(result.stdout)
        levels = {r["level"] for r in rows}
        assert "LEVEL" in levels   # 'level' uppercased → 'LEVEL'


# ═══════════════════════════════════════════════════════════════════════════
# [X] Exit codes and error messages
# ═══════════════════════════════════════════════════════════════════════════

class TestExitCodes:
    """§Exit codes and §Edge cases #1–#4."""

    # Exit 1 — file not found or permission denied (edge case #1)
    def test_file_not_found_exits_1(self, tmp_path):
        result = logsum("--input", str(tmp_path / "nonexistent.csv"))
        assert result.returncode == 1

    def test_file_not_found_error_on_stderr(self, tmp_path):
        path = str(tmp_path / "nonexistent.csv")
        result = logsum("--input", path)
        assert "Error:" in result.stderr
        assert "nonexistent.csv" in result.stderr

    def test_file_not_found_stdout_is_empty(self, tmp_path):
        result = logsum("--input", str(tmp_path / "nope.csv"))
        assert result.stdout == ""

    # Exit 2 — required column missing (edge case #2)
    @pytest.mark.parametrize("missing_col,header", [
        ("level",     "timestamp,service,message"),
        ("service",   "timestamp,level,message"),
        ("timestamp", "level,service,message"),
        ("message",   "timestamp,level,service"),
    ])
    def test_missing_required_column_exits_2(self, make_csv, missing_col, header):
        p = make_csv(f"miss_{missing_col}.csv", ["a,b,c"], header=header)
        result = logsum("--input", str(p))
        assert result.returncode == 2

    @pytest.mark.parametrize("missing_col,header", [
        ("level",     "timestamp,service,message"),
        ("service",   "timestamp,level,message"),
        ("timestamp", "level,service,message"),
        ("message",   "timestamp,level,service"),
    ])
    def test_missing_required_column_stderr_names_it(self, make_csv, missing_col, header):
        p = make_csv(f"miss2_{missing_col}.csv", ["a,b,c"], header=header)
        result = logsum("--input", str(p))
        assert "Missing required column" in result.stderr
        assert missing_col in result.stderr

    # Spec gap: truly empty file (0 bytes) — not covered by edge cases #1–#9
    def test_empty_file_exits_2(self, tmp_path):
        """
        Edge case not listed in the spec: a file that exists but is 0 bytes.
        The spec covers 'header-only' (exit 3) and 'missing required column'
        (exit 2) but says nothing about an empty file.

        First hypothesis: exit 3 (by analogy with header-only).
        Observed behaviour: exit 2, stderr 'Missing required column: timestamp'.
        Decision: spec ambiguity — see test-notes.md.
        Test asserts the implementation's actual (exit-2) behaviour.
        """
        p = tmp_path / "empty.csv"
        p.write_bytes(b"")
        result = logsum("--input", str(p))
        assert result.returncode == 2
        assert "Missing required column" in result.stderr

    # Exit 3 — header-only (edge case #3)
    def test_header_only_exits_3(self, make_csv):
        p = make_csv("headeronly.csv", [])
        result = logsum("--input", str(p))
        assert result.returncode == 3

    def test_header_only_stderr_says_no_log_entries_found(self, make_csv):
        p = make_csv("headeronly2.csv", [])
        result = logsum("--input", str(p))
        assert "No log entries found." in result.stderr

    # Exit 3 — all rows filtered out (edge case #4)
    def test_all_rows_filtered_exits_3(self, make_csv):
        p = make_csv("allfiltered.csv", ["t,INFO,svc,m"])
        result = logsum("--input", str(p), "--level", "ERROR")
        assert result.returncode == 3

    def test_all_rows_filtered_stderr_active_filters_message(self, make_csv):
        p = make_csv("allfiltered2.csv", ["t,INFO,svc,m"])
        result = logsum("--input", str(p), "--level", "ERROR")
        assert "No log entries match the active filters." in result.stderr

    def test_exit_3_two_paths_have_distinct_messages(self, make_csv):
        """
        The spec requires two separate counters for exit-3 (§Implementation notes).
        Header-only → "No log entries found."
        All filtered → "No log entries match the active filters."
        These must not be confused.
        """
        p_header = make_csv("e3h.csv", [])
        p_filter = make_csv("e3f.csv", ["t,INFO,svc,m"])

        r_header = logsum("--input", str(p_header))
        r_filter = logsum("--input", str(p_filter), "--level", "ERROR")

        # header-only path
        assert "No log entries found." in r_header.stderr
        assert "active filters" not in r_header.stderr

        # all-filtered path
        assert "No log entries match the active filters." in r_filter.stderr
        assert "No log entries found." not in r_filter.stderr

    # Streams must never be mixed (§Stderr vs stdout)
    def test_error_messages_go_to_stderr_not_stdout(self, tmp_path):
        result = logsum("--input", str(tmp_path / "missing.csv"))
        assert result.stdout == ""
        assert result.stderr.strip() != ""

    def test_success_output_goes_to_stdout_not_stderr(self, make_csv):
        p = make_csv("streams.csv", ["t,INFO,svc,m"])
        result = logsum("--input", str(p))
        assert "service,level,count" in result.stdout
        assert result.stderr == ""


# ═══════════════════════════════════════════════════════════════════════════
# [O] --output flag
# ═══════════════════════════════════════════════════════════════════════════

class TestOutputFlag:
    """§Inputs: --output writes summary CSV to file instead of stdout."""

    def test_output_flag_creates_file(self, make_csv, tmp_path):
        src = make_csv("in.csv", ["t,INFO,svc,m"])
        out = tmp_path / "out.csv"
        result = logsum("--input", str(src), "--output", str(out))
        assert result.returncode == 0
        assert out.exists()

    def test_output_flag_file_has_correct_content(self, make_csv, tmp_path):
        src = make_csv("in2.csv", ["t,INFO,svc,m", "t,INFO,svc,m"])
        out = tmp_path / "out2.csv"
        logsum("--input", str(src), "--output", str(out))
        rows = list(csv.DictReader(out.open(encoding="utf-8")))
        assert len(rows) == 1
        assert rows[0]["service"] == "svc"
        assert rows[0]["level"] == "INFO"
        assert rows[0]["count"] == "2"

    def test_output_flag_suppresses_stdout(self, make_csv, tmp_path):
        src = make_csv("in3.csv", ["t,INFO,svc,m"])
        out = tmp_path / "out3.csv"
        result = logsum("--input", str(src), "--output", str(out))
        assert result.stdout == ""

    def test_no_output_flag_writes_to_stdout(self, make_csv):
        src = make_csv("stdout.csv", ["t,INFO,svc,m"])
        result = logsum("--input", str(src))
        assert "service,level,count" in result.stdout


# ═══════════════════════════════════════════════════════════════════════════
# [H] --help
# ═══════════════════════════════════════════════════════════════════════════

class TestHelp:
    """§Help flag: prints usage to stdout and exits 0."""

    def test_help_exits_0(self):
        assert logsum("--help").returncode == 0

    def test_help_writes_to_stdout(self):
        result = logsum("--help")
        assert result.stdout.strip() != ""

    def test_help_not_on_stderr(self):
        result = logsum("--help")
        # Significant usage text must land on stdout, not stderr
        assert len(result.stdout) > len(result.stderr)


# ═══════════════════════════════════════════════════════════════════════════
# [P] Positional-arg shorthand (§Implementation notes, kata 5.3)
# ═══════════════════════════════════════════════════════════════════════════

class TestPositionalArgs:
    """Bare positionals are absorbed into --input / --output when flags absent."""

    def test_positional_input_only(self, make_csv):
        """``python -m src.logsum <path>`` (no --input flag)."""
        p = make_csv("pos1.csv", ["t,INFO,svc,m"])
        result = subprocess.run(
            [sys.executable, "-m", "src.logsum", str(p)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        rows = parse_output(result.stdout)
        assert rows[0]["service"] == "svc"

    def test_positional_input_and_output(self, make_csv, tmp_path):
        """``python -m src.logsum <input> <output>`` (no flags)."""
        src = make_csv("pos2.csv", ["t,INFO,svc,m"])
        out = tmp_path / "pos_out.csv"
        result = subprocess.run(
            [sys.executable, "-m", "src.logsum", str(src), str(out)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert out.exists()


# ═══════════════════════════════════════════════════════════════════════════
# Static fixture smoke-test
# ═══════════════════════════════════════════════════════════════════════════

class TestStaticFixtures:
    """End-to-end smoke test against the committed fixtures/basic.csv."""

    def test_basic_fixture_exits_0(self):
        p = FIXTURES_DIR / "basic.csv"
        if not p.exists():
            pytest.skip("fixtures/basic.csv not found")
        assert logsum("--input", str(p)).returncode == 0

    def test_basic_fixture_count_order(self):
        """Output must be sorted by count descending."""
        p = FIXTURES_DIR / "basic.csv"
        if not p.exists():
            pytest.skip("fixtures/basic.csv not found")
        rows = parse_output(logsum("--input", str(p)).stdout)
        counts = [int(r["count"]) for r in rows]
        assert counts == sorted(counts, reverse=True)

    def test_basic_fixture_known_groups_present(self):
        """Known (service, level) pairs from fixtures/basic.csv must appear."""
        p = FIXTURES_DIR / "basic.csv"
        if not p.exists():
            pytest.skip("fixtures/basic.csv not found")
        rows = parse_output(logsum("--input", str(p)).stdout)
        pairs = {(r["service"], r["level"]) for r in rows}
        assert ("checkout-service", "ERROR") in pairs
        assert ("identity-service", "INFO") in pairs
        assert ("cart-api", "WARN") in pairs

    def test_basic_fixture_level_filter(self):
        """--level ERROR returns only ERROR rows."""
        p = FIXTURES_DIR / "basic.csv"
        if not p.exists():
            pytest.skip("fixtures/basic.csv not found")
        rows = parse_output(logsum("--input", str(p), "--level", "ERROR").stdout)
        assert rows
        assert all(r["level"] == "ERROR" for r in rows)

    def test_basic_fixture_service_filter(self):
        """--service cart-api returns only cart-api rows."""
        p = FIXTURES_DIR / "basic.csv"
        if not p.exists():
            pytest.skip("fixtures/basic.csv not found")
        rows = parse_output(
            logsum("--input", str(p), "--service", "cart-api").stdout
        )
        assert rows
        assert all(r["service"] == "cart-api" for r in rows)
