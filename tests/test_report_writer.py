import errno
import json
import math
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from velune_trace.reporting.errors import BundleWriteError
from velune_trace.reporting.writer import (
    MANIFEST_FILENAME,
    _fsync_directory,
    write_private_report_manifest,
)


class PrivateReportManifestWriterTests(unittest.TestCase):
    def test_writes_deterministic_utf8_json_with_private_mode(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)

            manifest_path = write_private_report_manifest(
                bundle_dir=bundle_dir,
                manifest={
                    "z_field": "한글",
                    "a_field": {
                        "window_sec": 1.0,
                    },
                },
            )

            # write_private_report_manifest() resolves bundle_dir
            # (needed for the symlink-safety checks in
            # _resolve_bundle_directory()) before deriving the manifest
            # path, so the returned path is the canonical/resolved form.
            # On Windows, a tempdir path handed in by the OS/CI runner
            # can be a short 8.3 alias of a path component that is lexically
            # different from its own resolved long-path form while still
            # naming the same file -- so identity here must be checked
            # by filesystem identity, not raw string/Path equality.
            self.assertTrue(manifest_path.is_absolute())
            self.assertEqual(
                manifest_path.name,
                MANIFEST_FILENAME,
            )
            self.assertTrue(
                os.path.samefile(
                    manifest_path,
                    bundle_dir / MANIFEST_FILENAME,
                )
            )
            self.assertTrue(
                manifest_path.read_bytes().endswith(b"\n")
            )

            rendered = manifest_path.read_text(
                encoding="utf-8"
            )
            self.assertLess(
                rendered.index('"a_field"'),
                rendered.index('"z_field"'),
            )

            loaded = json.loads(rendered)
            self.assertEqual(loaded["z_field"], "한글")
            self.assertEqual(
                loaded["a_field"]["window_sec"],
                1.0,
            )

            # os.chmod's owner-only (0o600) guarantee is a POSIX-specific
            # contract -- Windows os.chmod cannot represent Unix
            # permission bits, so it is only meaningful to assert the
            # exact mode there.
            if os.name == "posix":
                mode = stat.S_IMODE(
                    manifest_path.stat().st_mode
                )
                self.assertEqual(mode, 0o600)

    def test_rejects_existing_manifest_by_default(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)
            manifest_path = (
                bundle_dir / MANIFEST_FILENAME
            )
            manifest_path.write_text(
                '{"original":true}\n',
                encoding="utf-8",
            )

            with self.assertRaises(
                BundleWriteError
            ) as context:
                write_private_report_manifest(
                    bundle_dir=bundle_dir,
                    manifest={"replacement": True},
                )

            self.assertEqual(
                context.exception.code,
                "VELUNE_BUNDLE_MANIFEST_ALREADY_EXISTS",
            )
            self.assertEqual(
                manifest_path.read_text(encoding="utf-8"),
                '{"original":true}\n',
            )

    def test_overwrite_replaces_existing_manifest(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)

            first_path = write_private_report_manifest(
                bundle_dir=bundle_dir,
                manifest={"version": 1},
            )
            second_path = write_private_report_manifest(
                bundle_dir=bundle_dir,
                manifest={"version": 2},
                overwrite=True,
            )

            self.assertEqual(first_path, second_path)
            self.assertEqual(
                json.loads(
                    second_path.read_text(encoding="utf-8")
                ),
                {"version": 2},
            )
            if os.name == "posix":
                self.assertEqual(
                    stat.S_IMODE(second_path.stat().st_mode),
                    0o600,
                )

    def test_rejects_non_boolean_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaises(
                BundleWriteError
            ) as context:
                write_private_report_manifest(
                    bundle_dir=temporary_directory,
                    manifest={},
                    overwrite=1,
                )

            self.assertEqual(
                context.exception.code,
                "VELUNE_BUNDLE_OVERWRITE_TYPE_INVALID",
            )

    def test_rejects_missing_bundle_directory(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_path = (
                Path(temporary_directory) / "missing"
            )

            with self.assertRaises(
                BundleWriteError
            ) as context:
                write_private_report_manifest(
                    bundle_dir=missing_path,
                    manifest={},
                )

            self.assertEqual(
                context.exception.code,
                "VELUNE_BUNDLE_DIRECTORY_UNAVAILABLE",
            )

    def test_rejects_bundle_directory_symbolic_link(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            real_directory = root / "real"
            link_directory = root / "link"

            real_directory.mkdir()
            link_directory.symlink_to(
                real_directory,
                target_is_directory=True,
            )

            with self.assertRaises(
                BundleWriteError
            ) as context:
                write_private_report_manifest(
                    bundle_dir=link_directory,
                    manifest={},
                )

            self.assertEqual(
                context.exception.code,
                (
                    "VELUNE_BUNDLE_"
                    "DIRECTORY_SYMLINK_FORBIDDEN"
                ),
            )

    def test_rejects_existing_manifest_symbolic_link(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)
            external_path = bundle_dir / "external.json"
            manifest_path = (
                bundle_dir / MANIFEST_FILENAME
            )

            external_path.write_text(
                '{"external":true}\n',
                encoding="utf-8",
            )
            manifest_path.symlink_to(external_path)

            with self.assertRaises(
                BundleWriteError
            ) as context:
                write_private_report_manifest(
                    bundle_dir=bundle_dir,
                    manifest={},
                    overwrite=True,
                )

            self.assertEqual(
                context.exception.code,
                (
                    "VELUNE_BUNDLE_"
                    "MANIFEST_SYMLINK_FORBIDDEN"
                ),
            )
            self.assertEqual(
                external_path.read_text(encoding="utf-8"),
                '{"external":true}\n',
            )

    def test_rejects_non_finite_numbers(self):
        invalid_values = [
            math.nan,
            math.inf,
            -math.inf,
        ]

        for invalid_value in invalid_values:
            with self.subTest(value=invalid_value):
                with tempfile.TemporaryDirectory() as (
                    temporary_directory
                ):
                    with self.assertRaises(
                        BundleWriteError
                    ) as context:
                        write_private_report_manifest(
                            bundle_dir=temporary_directory,
                            manifest={
                                "invalid": invalid_value,
                            },
                        )

                    self.assertEqual(
                        context.exception.code,
                        (
                            "VELUNE_BUNDLE_"
                            "MANIFEST_JSON_INVALID"
                        ),
                    )

    def test_rejects_non_string_mapping_keys(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaises(
                BundleWriteError
            ) as context:
                write_private_report_manifest(
                    bundle_dir=temporary_directory,
                    manifest={
                        1: "invalid-key",
                    },
                )

            self.assertEqual(
                context.exception.code,
                "VELUNE_BUNDLE_MANIFEST_JSON_INVALID",
            )

    def test_rejects_circular_manifest_structure(self):
        circular_manifest = {}
        circular_manifest["self"] = circular_manifest

        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaises(
                BundleWriteError
            ) as context:
                write_private_report_manifest(
                    bundle_dir=temporary_directory,
                    manifest=circular_manifest,
                )

            self.assertEqual(
                context.exception.code,
                "VELUNE_BUNDLE_MANIFEST_JSON_INVALID",
            )

    def test_removes_temporary_file_after_install_failure(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)

            with mock.patch(
                "velune_trace.reporting.writer.os.link",
                side_effect=OSError("simulated link failure"),
            ):
                with self.assertRaises(
                    BundleWriteError
                ) as context:
                    write_private_report_manifest(
                        bundle_dir=bundle_dir,
                        manifest={"valid": True},
                    )

            self.assertEqual(
                context.exception.code,
                "VELUNE_BUNDLE_MANIFEST_WRITE_FAILED",
            )
            self.assertFalse(
                (bundle_dir / MANIFEST_FILENAME).exists()
            )
            self.assertEqual(
                list(
                    bundle_dir.glob(
                        ".report_manifest.*.tmp"
                    )
                ),
                [],
            )

    def test_install_race_does_not_replace_existing_manifest(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)
            manifest_path = (
                bundle_dir / MANIFEST_FILENAME
            )

            def simulate_competing_writer(
                source,
                destination,
            ):
                Path(destination).write_text(
                    '{"competing":true}\n',
                    encoding="utf-8",
                )
                raise FileExistsError(
                    os.fspath(destination)
                )

            with mock.patch(
                "velune_trace.reporting.writer.os.link",
                side_effect=simulate_competing_writer,
            ):
                with self.assertRaises(
                    BundleWriteError
                ) as context:
                    write_private_report_manifest(
                        bundle_dir=bundle_dir,
                        manifest={"ours": True},
                    )

            self.assertEqual(
                context.exception.code,
                "VELUNE_BUNDLE_MANIFEST_ALREADY_EXISTS",
            )
            self.assertEqual(
                json.loads(
                    manifest_path.read_text(
                        encoding="utf-8"
                    )
                ),
                {"competing": True},
            )
            self.assertEqual(
                list(
                    bundle_dir.glob(
                        ".report_manifest.*.tmp"
                    )
                ),
                [],
            )


class DirectoryFsyncPortabilityTests(unittest.TestCase):
    """Unit coverage for _fsync_directory's platform branch.

    Two distinct kinds of test live here, and they must not be confused:

    1. Cross-platform LOGIC tests (below), which patch os.name to select
       which branch of _fsync_directory runs, but never let a real
       os.open/os.fsync/os.close syscall execute -- those are also fully
       mocked with a synthetic file descriptor. This proves the branch
       logic (call counts, error propagation, fd cleanup) is correct by
       construction on every CI platform, Windows included. Patching
       os.name does NOT change what the real OS actually supports, so a
       test that patches os.name to "posix" while still delegating to the
       real os.open would, on an actual Windows runner, hit a genuine
       Windows PermissionError from trying to open a directory that way --
       an artifact of invalid test simulation, not the thing under test.

    2. A real POSIX integration test (test_real_posix_directory_fsync_succeeds),
       which does not patch os.name or any syscall at all and only runs on
       an actual POSIX system, proving the supported path genuinely works
       against a real directory.

    Neither of these is a substitute for running the full suite on an
    actual Windows machine -- see the release report for that distinction.
    """

    def test_windows_skips_directory_fsync_without_error(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with mock.patch(
                "velune_trace.reporting.writer.os.name", "nt"
            ), mock.patch(
                "velune_trace.reporting.writer.os.open",
                side_effect=AssertionError(
                    "os.open must not be called for directory fsync "
                    "on Windows"
                ),
            ):
                _fsync_directory(Path(temporary_directory))  # must not raise

    def test_logical_posix_branch_opens_directory_exactly_once(self):
        # Regression guard: a second os.open() in the normal POSIX path
        # would leak the first file descriptor. os.open is replaced with a
        # synthetic descriptor rather than delegated to the real syscall,
        # so this exercises the branch's logic on every platform without
        # depending on what the real OS actually supports for
        # directory-open (see the class docstring).
        with tempfile.TemporaryDirectory() as temporary_directory:
            with mock.patch(
                "velune_trace.reporting.writer.os.name", "posix"
            ), mock.patch(
                "velune_trace.reporting.writer.os.open",
                return_value=999,
            ) as open_spy, mock.patch(
                "velune_trace.reporting.writer.os.fsync"
            ), mock.patch(
                "velune_trace.reporting.writer.os.close"
            ):
                _fsync_directory(Path(temporary_directory))

            self.assertEqual(open_spy.call_count, 1)

    def test_logical_posix_branch_fsyncs_the_opened_descriptor(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with mock.patch(
                "velune_trace.reporting.writer.os.name", "posix"
            ), mock.patch(
                "velune_trace.reporting.writer.os.open",
                return_value=999,
            ), mock.patch(
                "velune_trace.reporting.writer.os.fsync"
            ) as fsync_spy, mock.patch(
                "velune_trace.reporting.writer.os.close"
            ):
                _fsync_directory(Path(temporary_directory))

            fsync_spy.assert_called_once_with(999)

    @unittest.skipUnless(
        os.name == "posix",
        "exercises the real POSIX directory-fsync syscall path",
    )
    def test_real_posix_directory_fsync_succeeds(self):
        # Integration coverage, deliberately unmocked: on an actual POSIX
        # system, the supported directory-fsync path must genuinely
        # succeed against a real directory. Guarded so it only ever runs
        # where the real OS is actually POSIX.
        with tempfile.TemporaryDirectory() as temporary_directory:
            _fsync_directory(Path(temporary_directory))  # must not raise

    def test_unsupported_directory_fsync_errno_is_tolerated(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with mock.patch(
                "velune_trace.reporting.writer.os.name", "posix"
            ), mock.patch(
                "velune_trace.reporting.writer.os.open",
                side_effect=OSError(
                    errno.ENOTSUP, "directory fsync not supported here"
                ),
            ):
                _fsync_directory(Path(temporary_directory))  # must not raise

    def test_unexpected_permission_error_still_propagates(self):
        # A PermissionError with an errno OUTSIDE the recognized
        # "unsupported operation" set must not be conflated with the
        # Windows/unsupported-filesystem case -- it is a genuine access
        # problem and must surface to the caller.
        with tempfile.TemporaryDirectory() as temporary_directory:
            with mock.patch(
                "velune_trace.reporting.writer.os.name", "posix"
            ), mock.patch(
                "velune_trace.reporting.writer.os.open",
                side_effect=OSError(
                    errno.EACCES, "permission genuinely denied"
                ),
            ):
                with self.assertRaises(OSError) as context:
                    _fsync_directory(Path(temporary_directory))

            self.assertEqual(context.exception.errno, errno.EACCES)

    def test_unrelated_io_error_still_propagates(self):
        # A distinct case from EACCES above: an arbitrary I/O failure
        # (disk error, not a permission/support question) must never be
        # treated as "unsupported directory fsync". os.open is mocked to a
        # synthetic descriptor (see the class docstring) so that only the
        # fsync failure under test is exercised, on every platform.
        with tempfile.TemporaryDirectory() as temporary_directory:
            with mock.patch(
                "velune_trace.reporting.writer.os.name", "posix"
            ), mock.patch(
                "velune_trace.reporting.writer.os.open",
                return_value=999,
            ), mock.patch(
                "velune_trace.reporting.writer.os.fsync",
                side_effect=OSError(errno.EIO, "simulated disk failure"),
            ), mock.patch(
                "velune_trace.reporting.writer.os.close"
            ):
                with self.assertRaises(OSError) as context:
                    _fsync_directory(Path(temporary_directory))

            self.assertEqual(context.exception.errno, errno.EIO)

    def test_directory_fd_is_closed_even_when_fsync_raises(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with mock.patch(
                "velune_trace.reporting.writer.os.name", "posix"
            ), mock.patch(
                "velune_trace.reporting.writer.os.open",
                return_value=999,
            ), mock.patch(
                "velune_trace.reporting.writer.os.fsync",
                side_effect=OSError(errno.EIO, "simulated disk failure"),
            ), mock.patch(
                "velune_trace.reporting.writer.os.close"
            ) as close_spy:
                with self.assertRaises(OSError):
                    _fsync_directory(Path(temporary_directory))

            close_spy.assert_called_once_with(999)

    def test_full_write_still_succeeds_when_platform_reports_windows(self):
        # End-to-end confirmation: the manifest write itself, not just the
        # isolated fsync helper, completes successfully when os.name is
        # "nt" -- the actual regression this fix addresses -- and the
        # file-content fsync (a separate, unrelated call) still runs.
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)

            def fake_fsync_directory(directory):
                with mock.patch(
                    "velune_trace.reporting.writer.os.name", "nt"
                ):
                    _fsync_directory(directory)

            with mock.patch(
                "velune_trace.reporting.writer._fsync_directory",
                side_effect=fake_fsync_directory,
            ), mock.patch(
                "velune_trace.reporting.writer.os.fsync", wraps=os.fsync
            ) as fsync_spy:
                manifest_path = write_private_report_manifest(
                    bundle_dir=bundle_dir,
                    manifest={"platform": "windows"},
                )

            self.assertTrue(manifest_path.is_file())
            self.assertEqual(
                json.loads(manifest_path.read_text(encoding="utf-8")),
                {"platform": "windows"},
            )
            # The file's own content fsync (unrelated to directory fsync)
            # must still have happened exactly once.
            self.assertEqual(fsync_spy.call_count, 1)


if __name__ == "__main__":
    unittest.main()
