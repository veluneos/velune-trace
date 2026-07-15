import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

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
        repository_root = Path(__file__).resolve().parents[1]
        sample_path = repository_root / "examples" / "sample.mcap"

        self.assertTrue(sample_path.is_file())

        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory) / "bundle"
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


if __name__ == "__main__":
    unittest.main()
