import contextlib
import io
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

from velune_trace.cli import main as cli_main
from velune_trace.cli import inspect as inspect_module
from velune_trace.cli import chunks as chunks_module
from velune_trace.cli import read as read_module
from velune_trace.cli import profile as profile_module
from velune_trace.cli import compare as compare_module
from velune_trace.cli import windowed_verify as windowed_verify_module
from velune_trace.cli import evidence_window as evidence_window_module


SAMPLE_MCAP = str(
    Path(__file__).resolve().parent.parent / "examples" / "sample.mcap"
)

MIGRATED_COMMAND_MAINS = [
    inspect_module.main,
    chunks_module.main,
    read_module.main,
    profile_module.main,
    compare_module.main,
    windowed_verify_module.main,
    evidence_window_module.main,
]


def run_dispatch(argv):
    """Call the top-level dispatcher and capture (exit_code, stdout+stderr)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        exit_code = cli_main.main(argv)
    return exit_code, buf.getvalue()


def run_direct(command_main, argv):
    """Call a command's main(argv) directly (bare argv, no dispatcher)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exit_code = command_main(argv)
    return exit_code, buf.getvalue()


def run_with_patched_sys_argv(command_main, patched_argv):
    """Call a command's main() with argv=None, relying on sys.argv fallback."""
    buf = io.StringIO()
    with mock.patch.object(sys, "argv", patched_argv):
        with contextlib.redirect_stdout(buf):
            exit_code = command_main()
    return exit_code, buf.getvalue()


def first_ranked_window_id(output):
    match = re.search(r"^1\s*\|\s*(\d+)", output, re.MULTILINE)
    assert match is not None, f"could not find rank-1 row in output:\n{output}"
    return match.group(1)


class WindowedVerifyDispatchTests(unittest.TestCase):
    """Covers cases 1-5: top-level, direct, argv=None fallback, and
    output/ranking equivalence for windowed-verify."""

    WINDOWED_VERIFY_ARGS = [
        "--topic",
        "/lidar_top",
        "--window-sec",
        "1",
        "--top",
        "5",
    ]

    def test_top_level_dispatch_succeeds(self):
        exit_code, output = run_dispatch(
            ["windowed-verify", SAMPLE_MCAP] + self.WINDOWED_VERIFY_ARGS
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("VELUNE WINDOWED VERIFY", output)

    def test_direct_module_bare_argv_succeeds(self):
        exit_code, output = run_direct(
            windowed_verify_module.main,
            [SAMPLE_MCAP] + self.WINDOWED_VERIFY_ARGS,
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("VELUNE WINDOWED VERIFY", output)

    def test_argv_none_with_patched_sys_argv_succeeds(self):
        exit_code, output = run_with_patched_sys_argv(
            windowed_verify_module.main,
            ["velune-windowed-verify", SAMPLE_MCAP] + self.WINDOWED_VERIFY_ARGS,
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("VELUNE WINDOWED VERIFY", output)

    def test_top_level_and_direct_routes_agree_on_ranking(self):
        _, dispatch_output = run_dispatch(
            ["windowed-verify", SAMPLE_MCAP] + self.WINDOWED_VERIFY_ARGS
        )
        _, direct_output = run_direct(
            windowed_verify_module.main,
            [SAMPLE_MCAP] + self.WINDOWED_VERIFY_ARGS,
        )
        self.assertEqual(
            first_ranked_window_id(dispatch_output),
            first_ranked_window_id(direct_output),
        )

    def test_known_sample_ranks_window_2_first(self):
        _, output = run_dispatch(
            ["windowed-verify", SAMPLE_MCAP] + self.WINDOWED_VERIFY_ARGS
        )
        self.assertEqual(first_ranked_window_id(output), "2")


class LegacyCommandDispatchTests(unittest.TestCase):
    """Covers cases 6-13: adjacent top-level legacy commands and
    argv=None-compatible validation-report through the dispatcher."""

    def test_top_level_inspect_succeeds(self):
        exit_code, output = run_dispatch(["inspect", SAMPLE_MCAP])
        self.assertEqual(exit_code, 0)
        self.assertIn("VELUNE INSPECT", output)

    def test_inspect_direct_module_argv_none_fallback_succeeds(self):
        exit_code, output = run_with_patched_sys_argv(
            inspect_module.main, ["velune-inspect", SAMPLE_MCAP]
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("VELUNE INSPECT", output)

    def test_top_level_chunks_succeeds(self):
        exit_code, output = run_dispatch(["chunks", SAMPLE_MCAP])
        self.assertEqual(exit_code, 0)
        self.assertIn("VELUNE CHUNKS", output)

    def test_top_level_read_succeeds(self):
        exit_code, output = run_dispatch(["read", SAMPLE_MCAP, "--chunk", "0"])
        self.assertEqual(exit_code, 0)
        self.assertIn("VELUNE READ", output)

    def test_top_level_profile_succeeds(self):
        exit_code, output = run_dispatch(
            [
                "profile",
                SAMPLE_MCAP,
                "--start-sec",
                "1700000000",
                "--end-sec",
                "1700000005",
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("VELUNE PROFILE", output)

    def test_top_level_compare_succeeds(self):
        exit_code, output = run_dispatch(
            [
                "compare",
                SAMPLE_MCAP,
                SAMPLE_MCAP,
                "--normal-start-sec",
                "1700000000",
                "--normal-end-sec",
                "1700000002",
                "--incident-start-sec",
                "1700000002",
                "--incident-end-sec",
                "1700000004",
                "--topic",
                "/lidar_top",
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("VELUNE COMPARE", output)

    def test_top_level_evidence_window_succeeds(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = str(Path(tmpdir) / "evidence.json")
            exit_code, output = run_dispatch(
                [
                    "evidence-window",
                    SAMPLE_MCAP,
                    "--topic",
                    "/lidar_top",
                    "--start-sec",
                    "1700000002",
                    "--end-sec",
                    "1700000003",
                    "--expected-count",
                    "20",
                    "--export-json",
                    export_path,
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertIn("EVIDENCE WINDOW", output)
            self.assertTrue(Path(export_path).exists())

    def test_top_level_validation_report_remains_compatible(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = str(Path(tmpdir) / "velune_report")
            exit_code, _output = run_dispatch(
                [
                    "validation-report",
                    SAMPLE_MCAP,
                    "--export-dir",
                    export_dir,
                    "--window-sec",
                    "1",
                    "--top",
                    "5",
                    "--allowed-lateness-sec",
                    "2",
                ]
            )
            self.assertEqual(exit_code, 0)


class ReadTimeWindowAndProfileSortBranchTests(unittest.TestCase):
    """Targeted coverage for two reindexed parser branches that the initial
    test pass did not exercise: read.py's --start-sec/--end-sec branch
    (argv[1]=="--start-sec", argv[2], argv[3]=="--end-sec", argv[4]) and its
    interaction with the unchanged --topic extraction, and profile.py's
    documented --sort branch (len(argv)==7, argv[5], argv[6])."""

    def test_top_level_read_time_window_route(self):
        exit_code, output = run_dispatch(
            [
                "read",
                SAMPLE_MCAP,
                "--start-sec",
                "1700000002",
                "--end-sec",
                "1700000003",
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertNotIn("Traceback", output)
        self.assertIn("VELUNE READ", output)
        self.assertIn("Mode               : time", output)
        self.assertIn("Topic Filter       : ALL", output)
        self.assertIn("Messages Read      : 119", output)

    def test_top_level_read_time_window_with_topic(self):
        exit_code, output = run_dispatch(
            [
                "read",
                SAMPLE_MCAP,
                "--start-sec",
                "1700000002",
                "--end-sec",
                "1700000003",
                "--topic",
                "/lidar_top",
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertNotIn("Traceback", output)
        self.assertIn("VELUNE READ", output)
        self.assertIn("Mode               : time", output)
        self.assertIn("Topic Filter       : /lidar_top", output)
        self.assertIn("Messages Read      : 19", output)
        self.assertNotIn("/imu", output)

    def test_top_level_profile_sort_route(self):
        exit_code, output = run_dispatch(
            [
                "profile",
                SAMPLE_MCAP,
                "--start-sec",
                "1700000000",
                "--end-sec",
                "1700000005",
                "--sort",
                "max_gap",
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertNotIn("Traceback", output)
        self.assertIn("VELUNE PROFILE", output)
        self.assertIn("Sort               : max_gap", output)
        self.assertIn("/lidar_top", output)
        self.assertIn("/imu", output)
        # /lidar_top has the larger observed max_gap in the sample data,
        # so a max_gap-descending sort must place it before /imu.
        self.assertLess(
            output.index("/lidar_top"),
            output.index("/imu"),
        )


class DispatcherErrorPathTests(unittest.TestCase):
    """Covers cases 14-17: error handling, unknown command, help, and
    exit-code propagation through the dispatcher."""

    def test_missing_windowed_verify_options_returns_existing_error_code(self):
        exit_code, output = run_dispatch(["windowed-verify", SAMPLE_MCAP])
        self.assertEqual(exit_code, 2)
        self.assertNotIn("Traceback", output)

    def test_unknown_command_returns_2(self):
        exit_code, output = run_dispatch(["bogus-command"])
        self.assertEqual(exit_code, 2)
        self.assertIn("Unknown command", output)

    def test_top_level_help_returns_0(self):
        exit_code_empty, output_empty = run_dispatch([])
        exit_code_help, output_help = run_dispatch(["--help"])
        self.assertEqual(exit_code_empty, 0)
        self.assertEqual(exit_code_help, 0)
        self.assertIn("Usage:", output_empty)
        self.assertIn("Usage:", output_help)

    def test_representative_return_code_propagates_through_dispatcher(self):
        exit_code, output = run_dispatch(
            ["inspect", "/nonexistent/path/to/file.mcap"]
        )
        self.assertEqual(exit_code, 1)
        self.assertIn("VELUNE INSPECT ERROR", output)
        self.assertNotIn("Traceback", output)


class MigratedCommandContractTests(unittest.TestCase):
    """Covers cases 18-19: every migrated command accepts an explicit bare
    argv list and preserves the argv=None -> sys.argv[1:] fallback, without
    raising TypeError (the original defect)."""

    def test_every_migrated_command_accepts_explicit_bare_argv(self):
        for command_main in MIGRATED_COMMAND_MAINS:
            with self.subTest(command=command_main.__module__):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    exit_code = command_main([])
                output = buf.getvalue()
                self.assertEqual(exit_code, 2)
                self.assertIn("[ERROR]", output)
                self.assertNotIn("Traceback", output)

    def test_every_migrated_command_preserves_argv_none_fallback(self):
        for command_main in MIGRATED_COMMAND_MAINS:
            with self.subTest(command=command_main.__module__):
                with mock.patch.object(sys, "argv", ["velune-cli"]):
                    buf = io.StringIO()
                    with contextlib.redirect_stdout(buf):
                        exit_code = command_main()
                output = buf.getvalue()
                self.assertEqual(exit_code, 2)
                self.assertIn("[ERROR]", output)
                self.assertNotIn("Traceback", output)


if __name__ == "__main__":
    unittest.main()
