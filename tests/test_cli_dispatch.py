import contextlib
import io
import re
import sys
import tempfile
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


# Every test in this module needs one sample MCAP. It is generated once,
# lazily, into a module-owned temporary directory -- never into the
# source tree -- via unittest's native setUpModule()/tearDownModule()
# hooks (recognized by both `unittest` and `pytest`). setUpModule() runs
# only when this module's tests are actually executed, never as a side
# effect of merely importing the module (e.g. for static analysis or
# documentation tooling), and the temporary directory is unique per test
# run, so a fresh clone, a read-only checkout, and concurrent separate
# test processes each get their own isolated, disposable copy.
_SAMPLE_MCAP_DIR = None
SAMPLE_MCAP_PATH = None
SAMPLE_MCAP = None


def setUpModule():
    global _SAMPLE_MCAP_DIR, SAMPLE_MCAP_PATH, SAMPLE_MCAP

    from tools.create_sample_mcap import create_sample_mcap

    _SAMPLE_MCAP_DIR = tempfile.TemporaryDirectory(
        prefix="velune-test-cli-dispatch-"
    )
    SAMPLE_MCAP_PATH = Path(_SAMPLE_MCAP_DIR.name) / "sample.mcap"
    create_sample_mcap(SAMPLE_MCAP_PATH)
    SAMPLE_MCAP = str(SAMPLE_MCAP_PATH)


def tearDownModule():
    if _SAMPLE_MCAP_DIR is not None:
        _SAMPLE_MCAP_DIR.cleanup()

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


class SampleMcapFixtureLifecycleTests(unittest.TestCase):
    """Covers the fixture-isolation guarantee this whole module depends

    on: the sample MCAP is generated into a temporary directory by
    setUpModule(), never into the source tree, and every other test class
    below can rely on SAMPLE_MCAP already being a valid, readable file."""

    def test_sample_lives_outside_the_repository_tree(self):
        repo_root = Path(__file__).resolve().parent.parent
        self.assertNotIn(repo_root, SAMPLE_MCAP_PATH.parents)

    def test_sample_mcap_is_readable_by_inspect(self):
        exit_code, output = run_dispatch(["inspect", SAMPLE_MCAP])
        self.assertEqual(exit_code, 0)
        self.assertNotIn("Traceback", output)
        self.assertIn("/lidar_top", output)
        self.assertIn("/imu", output)

    def test_generator_recreates_a_missing_sample_at_an_arbitrary_path(self):
        # Exercises the same generation logic setUpModule() relies on,
        # against a separate, disposable path -- never SAMPLE_MCAP_PATH
        # itself, which every other test class in this module depends on
        # remaining intact for the rest of the run.
        from tools.create_sample_mcap import create_sample_mcap

        with tempfile.TemporaryDirectory() as temporary_directory:
            candidate_path = (
                Path(temporary_directory) / "examples" / "sample.mcap"
            )
            self.assertFalse(candidate_path.exists())

            create_sample_mcap(candidate_path)

            self.assertTrue(candidate_path.is_file())


class RepositorySampleNonInterferenceTests(unittest.TestCase):
    """The fixture-isolation invariant is NON-INTERFERENCE, not absence: a

    developer may legitimately keep a local, gitignored
    examples/sample.mcap. This suite proves running the test suite neither
    requires nor depends on that file and, whether or not it happens to
    already exist, never creates, deletes, or modifies it. It intentionally
    does not assert the file must be absent (a real, pre-existing local
    sample is not a test failure) nor that it must be present (a fresh
    clone has none)."""

    def _repo_sample_path(self):
        return Path(__file__).resolve().parent.parent / "examples" / "sample.mcap"

    def test_clean_checkout_stays_clean_after_isolated_tests_run(self):
        repo_sample_path = self._repo_sample_path()
        if repo_sample_path.exists():
            self.skipTest(
                "a repository examples/sample.mcap already exists locally; "
                "non-interference with a pre-existing sample is covered by "
                "test_preexisting_repository_sample_is_left_untouched"
            )

        exit_code, _output = run_dispatch(["inspect", SAMPLE_MCAP])
        self.assertEqual(exit_code, 0)

        self.assertFalse(
            repo_sample_path.exists(),
            "running the test suite must never create a repository sample "
            "where none existed before",
        )

    def test_preexisting_repository_sample_is_left_untouched(self):
        import hashlib

        repo_sample_path = self._repo_sample_path()
        already_present = repo_sample_path.exists()

        if not already_present:
            # Manufacture the "developer already has a local sample" case
            # reproducibly in a disposable clone. A real pre-existing file
            # belonging to the user is never deleted -- only a placeholder
            # this test itself created is cleaned up afterward.
            repo_sample_path.parent.mkdir(parents=True, exist_ok=True)
            repo_sample_path.write_bytes(
                b"synthetic placeholder for non-interference test\n"
            )
            self.addCleanup(repo_sample_path.unlink)

        before_bytes = repo_sample_path.read_bytes()
        before_hash = hashlib.sha256(before_bytes).hexdigest()
        before_mtime_ns = repo_sample_path.stat().st_mtime_ns

        exit_code, _output = run_dispatch(["inspect", SAMPLE_MCAP])
        self.assertEqual(exit_code, 0)

        after_bytes = repo_sample_path.read_bytes()
        after_hash = hashlib.sha256(after_bytes).hexdigest()
        after_mtime_ns = repo_sample_path.stat().st_mtime_ns

        self.assertEqual(before_bytes, after_bytes)
        self.assertEqual(before_hash, after_hash)
        self.assertEqual(before_mtime_ns, after_mtime_ns)


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

    def test_summary_distinguishes_total_full_and_displayed_windows(self):
        # Locks in the disambiguated wording only -- no JSON/export field
        # is asserted here, because none changed.
        _, output = run_dispatch(
            ["windowed-verify", SAMPLE_MCAP] + self.WINDOWED_VERIFY_ARGS
        )
        self.assertIn("Total observed windows :", output)
        self.assertIn("Full windows ranked    :", output)
        self.assertIn("Top windows displayed  :", output)

    def test_export_json_schema_unchanged_from_v0_5_1(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = str(Path(tmpdir) / "windowed.json")
            exit_code, _output = run_dispatch(
                [
                    "windowed-verify",
                    SAMPLE_MCAP,
                    "--topic",
                    "/lidar_top",
                    "--window-sec",
                    "1",
                    "--top",
                    "2",
                    "--export-json",
                    export_path,
                ]
            )
            self.assertEqual(exit_code, 0)

            report = json.loads(Path(export_path).read_text())

            # Exact v0.5.1 field set -- neither more nor fewer keys.
            self.assertEqual(
                set(report.keys()),
                {
                    "command",
                    "semantics",
                    "notes",
                    "file",
                    "topic",
                    "window_sec",
                    "total_windows",
                    "ranked_full_windows",
                    "top",
                    "baseline",
                    "ranked_windows",
                    "all_windows",
                },
            )
            self.assertNotIn("top_ranked_windows", report)

            # "ranked_windows" remains every ranked full window, NOT
            # sliced to --top -- unchanged v0.5.1 behavior, confirmed
            # against OmniLink's own real archive (top=5, 7 full windows,
            # len(ranked_windows) == 7).
            self.assertEqual(
                len(report["ranked_windows"]),
                report["ranked_full_windows"],
            )
            self.assertGreater(
                len(report["ranked_windows"]),
                report["top"],
            )


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


class InputPathPortabilityTests(unittest.TestCase):
    """Failure-class hardening: paths containing spaces or non-ASCII

    characters are a real, externally-reachable class of filesystem-path
    bug (adjacent to, though distinct from, OmniLink's two findings).
    Covers both a plain read command (inspect) and the command whose
    export path was the subject of the CLI contract audit
    (windowed-verify)."""

    def _copy_sample_into(self, directory_name):
        import shutil
        import tempfile

        temporary_root = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_root.cleanup)

        target_dir = Path(temporary_root.name) / directory_name
        target_dir.mkdir(parents=True)
        target_path = target_dir / "sample.mcap"
        shutil.copyfile(SAMPLE_MCAP, target_path)
        return target_path

    def test_space_containing_path_is_readable(self):
        target_path = self._copy_sample_into("Velune Test Data")
        exit_code, output = run_dispatch(["inspect", str(target_path)])
        self.assertEqual(exit_code, 0)
        self.assertNotIn("Traceback", output)

    def test_unicode_path_is_readable(self):
        target_path = self._copy_sample_into("테스트 데이터")
        exit_code, output = run_dispatch(["inspect", str(target_path)])
        self.assertEqual(exit_code, 0)
        self.assertNotIn("Traceback", output)

    def test_space_containing_path_windowed_verify_and_export(self):
        import tempfile

        target_path = self._copy_sample_into("Velune Test Data")
        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = str(
                Path(tmpdir) / "Velune Export Dir" / "windowed.json"
            )
            (Path(tmpdir) / "Velune Export Dir").mkdir()
            exit_code, output = run_dispatch(
                [
                    "windowed-verify",
                    str(target_path),
                    "--topic",
                    "/lidar_top",
                    "--window-sec",
                    "1",
                    "--top",
                    "5",
                    "--export-json",
                    export_path,
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertNotIn("Traceback", output)
            self.assertTrue(Path(export_path).is_file())

    def test_relative_path_is_readable(self):
        import os as os_module

        target_path = self._copy_sample_into("relative-path-case")
        original_cwd = os_module.getcwd()
        os_module.chdir(target_path.parent)
        self.addCleanup(os_module.chdir, original_cwd)

        exit_code, output = run_dispatch(["inspect", target_path.name])
        self.assertEqual(exit_code, 0)
        self.assertNotIn("Traceback", output)


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
