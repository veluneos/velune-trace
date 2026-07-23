import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch
from pathlib import Path

from tools.create_sample_mcap import (
    create_sample_mcap,
)
from velune_trace.cli.validation_report import main


CORE_BUNDLE_FILES = (
    "report_manifest.json",
    "summary.md",
    "topic_profile.json",
    "evidence_windows.json",
    "SCHEMA.md",
    "shareable_anonymous_report.json",
)

MANIFEST_ARTIFACT_FILES = {
    "summary.md",
    "topic_profile.json",
    "evidence_windows.json",
    "SCHEMA.md",
    "shareable_anonymous_report.json",
}


class ValidationReportBundleIntegrationTests(unittest.TestCase):
    def test_sample_mcap_generates_complete_core_bundle(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(
                temporary_directory
            )

            sample_path = create_sample_mcap(
                temporary_root / "sample.mcap"
            )

            bundle_dir = temporary_root / "bundle"
            stdout = io.StringIO()
            stderr = io.StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main([
                    str(sample_path),
                    "--export-dir",
                    str(bundle_dir),
                ])

            self.assertEqual(
                exit_code,
                0,
                msg=stderr.getvalue(),
            )
            self.assertEqual(stderr.getvalue(), "")

            for file_name in CORE_BUNDLE_FILES:
                with self.subTest(file_name=file_name):
                    artifact_path = bundle_dir / file_name
                    self.assertTrue(artifact_path.is_file())
                    self.assertGreater(
                        artifact_path.stat().st_size,
                        0,
                    )

            manifest = json.loads(
                (bundle_dir / "report_manifest.json").read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                manifest["schema_name"],
                "velune.report_manifest",
            )
            self.assertEqual(
                manifest["schema_version"],
                "0.1.0",
            )
            self.assertTrue(
                manifest["report_bundle_id"].startswith(
                    "vrb_sha256_"
                )
            )

            self.assertEqual(
                manifest["source"]["format"],
                "mcap",
            )
            self.assertEqual(
                manifest["source"]["file_name"],
                "sample.mcap",
            )
            self.assertEqual(
                manifest["source"]["file_size_bytes"],
                sample_path.stat().st_size,
            )

            artifact_paths = {
                artifact["path"]
                for artifact in manifest["artifacts"]
            }

            self.assertEqual(
                artifact_paths,
                MANIFEST_ARTIFACT_FILES,
            )
            self.assertNotIn(
                "report_manifest.json",
                artifact_paths,
            )
            self.assertEqual(
                manifest["bundle_summary"]["artifact_count"],
                len(MANIFEST_ARTIFACT_FILES),
            )

            self.assertFalse(
                manifest["judgment_boundary"][
                    "root_cause_conclusion"
                ]
            )
            self.assertFalse(
                manifest["judgment_boundary"][
                    "fault_assignment"
                ]
            )
            self.assertFalse(
                manifest["judgment_boundary"][
                    "liability_calculation"
                ]
            )


    def test_full_empty_window_is_ranked_as_sparse_evidence(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(
                temporary_directory
            )

            input_path = temporary_root / "dropout.mcap"
            input_path.write_bytes(b"fixture")

            messages = []

            for index in range(400):
                timestamp_ns = index * 50_000_000

                if (
                    10_000_000_000
                    <= timestamp_ns
                    < 11_000_000_000
                ):
                    continue

                messages.append({
                    "topic": "/lidar_top",
                    "log_time": timestamp_ns,
                })

            bundle_dir = temporary_root / "bundle"
            stdout = io.StringIO()
            stderr = io.StringIO()

            with patch(
                "velune_trace.cli.validation_report.read_messages",
                return_value=iter(messages),
            ):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = main([
                        str(input_path),
                        "--export-dir",
                        str(bundle_dir),
                        "--window-sec",
                        "1",
                        "--top",
                        "5",
                        "--allowed-lateness-sec",
                        "2",
                    ])

            self.assertEqual(
                exit_code,
                0,
                msg=stderr.getvalue(),
            )

            evidence = json.loads(
                (
                    bundle_dir
                    / "evidence_windows.json"
                ).read_text(
                    encoding="utf-8"
                )
            )

            lidar_windows = evidence["/lidar_top"]

            self.assertLessEqual(
                len(lidar_windows),
                5,
            )

            missing_windows = [
                window
                for window in lidar_windows
                if window["count"] == 0
            ]

            self.assertGreaterEqual(
                len(missing_windows),
                1,
            )

            missing = missing_windows[0]

            self.assertEqual(
                missing["count_ratio"],
                0.0,
            )

            self.assertGreaterEqual(
                missing["max_gap_ns"],
                1_000_000_000,
            )

            self.assertLessEqual(
                missing["start_ns"],
                10_000_000_000,
            )

            self.assertGreaterEqual(
                missing["end_ns"],
                11_000_000_000,
            )

            self.assertEqual(
                missing["evidence_kind"],
                "sparse_missing_interval",
            )
            self.assertEqual(
                missing["derivation"],
                "adjacent_observed_timestamps",
            )
            self.assertEqual(
                missing["missing_window_count"],
                1,
            )
            self.assertEqual(
                missing["previous_observed_ns"],
                9_950_000_000,
            )
            self.assertEqual(
                missing["next_observed_ns"],
                11_000_000_000,
            )

            for window in lidar_windows:
                self.assertIn(
                    window["evidence_kind"],
                    {
                        "observed_window",
                        "sparse_missing_interval",
                    },
                )
                self.assertIn(
                    "derivation",
                    window,
                )
                self.assertIn(
                    "missing_window_count",
                    window,
                )

            schema = (
                bundle_dir
                / "SCHEMA.md"
            ).read_text(
                encoding="utf-8"
            )

            self.assertIn(
                "## Evidence Window Provenance",
                schema,
            )
            self.assertIn(
                "`sparse_missing_interval`",
                schema,
            )
            self.assertIn(
                "`adjacent_observed_timestamps`",
                schema,
            )
            self.assertIn(
                "`previous_observed_ns`",
                schema,
            )
            self.assertIn(
                "`next_observed_ns`",
                schema,
            )

            profile = json.loads(
                (
                    bundle_dir
                    / "topic_profile.json"
                ).read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                profile["/lidar_top"]["count"],
                380,
            )

            self.assertGreaterEqual(
                profile["/lidar_top"]["max_gap_ns"],
                1_000_000_000,
            )


if __name__ == "__main__":
    unittest.main()
