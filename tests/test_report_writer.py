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

            self.assertEqual(
                manifest_path,
                bundle_dir / MANIFEST_FILENAME,
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


if __name__ == "__main__":
    unittest.main()
