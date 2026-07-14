import tempfile
import unittest
from pathlib import Path

from velune_trace.reporting.bundle import (
    assemble_private_report_manifest,
)
from velune_trace.reporting.errors import (
    ArtifactDefinitionError,
    BundleAssemblyError,
)


class PrivateReportBundleAssemblyTests(unittest.TestCase):
    def artifact_definition(
        self,
        path: str,
        *,
        role: str = "core_machine_readable",
        media_type: str = "application/json",
        source_of_truth: bool = True,
    ):
        return {
            "path": path,
            "role": role,
            "media_type": media_type,
            "source_of_truth": source_of_truth,
        }

    def assemble(
        self,
        bundle_dir: Path,
        *,
        generated_at: str = (
            "2026-07-14T00:00:00+00:00"
        ),
        extraction=None,
        identity_extraction=None,
        artifact_definitions=None,
    ):
        if extraction is None:
            extraction = {
                "mode": "bounded_streaming_aggregation",
                "window_sec": 1.0,
            }

        if identity_extraction is None:
            identity_extraction = {
                "mode": "bounded_streaming_aggregation",
                "window_ns": 1_000_000_000,
            }

        if artifact_definitions is None:
            artifact_definitions = [
                self.artifact_definition(
                    "topic_profile.json"
                )
            ]

        return assemble_private_report_manifest(
            bundle_dir=bundle_dir,
            generated_at=generated_at,
            source={
                "file_name": "sample.mcap",
                "file_size_bytes": 1234,
            },
            extraction=extraction,
            identity_extraction=identity_extraction,
            artifact_definitions=artifact_definitions,
        )

    def test_assembles_manifest_and_allows_float_metadata(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)

            topic_path = bundle_dir / "topic_profile.json"
            topic_path.write_text("{}", encoding="utf-8")

            summary_path = bundle_dir / "summary.md"
            summary_path.write_text(
                "# Summary\n",
                encoding="utf-8",
            )

            manifest = self.assemble(
                bundle_dir,
                extraction={
                    "mode": "bounded_streaming_aggregation",
                    "window_sec": 1.0,
                    "allowed_lateness_sec": 2.0,
                },
                artifact_definitions=[
                    self.artifact_definition(
                        "summary.md",
                        role="derived_human_readable",
                        media_type="text/markdown",
                        source_of_truth=False,
                    ),
                    self.artifact_definition(
                        "topic_profile.json",
                    ),
                ],
            )

            self.assertTrue(
                manifest["report_bundle_id"].startswith(
                    "vrb_sha256_"
                )
            )
            self.assertEqual(
                [
                    artifact["path"]
                    for artifact in manifest["artifacts"]
                ],
                [
                    "summary.md",
                    "topic_profile.json",
                ],
            )
            self.assertEqual(
                manifest["extraction"]["window_sec"],
                1.0,
            )
            self.assertEqual(
                manifest["bundle_summary"][
                    "artifact_count"
                ],
                2,
            )
            self.assertEqual(
                manifest["bundle_summary"][
                    "total_artifact_size_bytes"
                ],
                (
                    topic_path.stat().st_size
                    + summary_path.stat().st_size
                ),
            )
            self.assertFalse(
                manifest["bundle_summary"][
                    "raw_runtime_logs_included"
                ]
            )
            self.assertEqual(
                manifest["bundle_summary"][
                    "artifact_hashing_mode"
                ],
                "sequential_bounded_memory_streaming",
            )

    def test_artifact_order_does_not_change_bundle_id(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)

            (bundle_dir / "topic_profile.json").write_text(
                "{}",
                encoding="utf-8",
            )
            (bundle_dir / "evidence_windows.json").write_text(
                "{}",
                encoding="utf-8",
            )

            topic = self.artifact_definition(
                "topic_profile.json"
            )
            windows = self.artifact_definition(
                "evidence_windows.json"
            )

            first = self.assemble(
                bundle_dir,
                artifact_definitions=[
                    topic,
                    windows,
                ],
            )
            second = self.assemble(
                bundle_dir,
                artifact_definitions=[
                    windows,
                    topic,
                ],
            )

            self.assertEqual(
                first["report_bundle_id"],
                second["report_bundle_id"],
            )

    def test_artifact_content_change_changes_bundle_id(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)
            artifact_path = bundle_dir / "topic_profile.json"

            artifact_path.write_text(
                '{"count":1}',
                encoding="utf-8",
            )
            first = self.assemble(bundle_dir)

            artifact_path.write_text(
                '{"count":2}',
                encoding="utf-8",
            )
            second = self.assemble(bundle_dir)

            self.assertNotEqual(
                first["report_bundle_id"],
                second["report_bundle_id"],
            )

    def test_generated_at_does_not_directly_change_bundle_id(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)

            (bundle_dir / "topic_profile.json").write_text(
                "{}",
                encoding="utf-8",
            )

            first = self.assemble(
                bundle_dir,
                generated_at=(
                    "2026-07-14T00:00:00+00:00"
                ),
            )
            second = self.assemble(
                bundle_dir,
                generated_at=(
                    "2026-07-15T00:00:00+00:00"
                ),
            )

            self.assertEqual(
                first["report_bundle_id"],
                second["report_bundle_id"],
            )
            self.assertNotEqual(
                first["generated_at"],
                second["generated_at"],
            )

    def test_does_not_write_manifest_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)

            (bundle_dir / "topic_profile.json").write_text(
                "{}",
                encoding="utf-8",
            )

            self.assemble(bundle_dir)

            self.assertFalse(
                (bundle_dir / "report_manifest.json").exists()
            )

    def test_missing_artifact_uses_domain_error(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)

            with self.assertRaises(
                ArtifactDefinitionError
            ) as context:
                self.assemble(bundle_dir)

            self.assertEqual(
                context.exception.code,
                (
                    "VELUNE_BUNDLE_"
                    "ARTIFACT_INSPECTION_FAILED"
                ),
            )
            self.assertIsNotNone(
                context.exception.__cause__
            )

    def test_duplicate_artifact_path_uses_domain_error(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)

            (bundle_dir / "topic_profile.json").write_text(
                "{}",
                encoding="utf-8",
            )

            definition = self.artifact_definition(
                "topic_profile.json"
            )

            with self.assertRaises(
                ArtifactDefinitionError
            ) as context:
                self.assemble(
                    bundle_dir,
                    artifact_definitions=[
                        definition,
                        dict(definition),
                    ],
                )

            self.assertEqual(
                context.exception.code,
                (
                    "VELUNE_BUNDLE_"
                    "ARTIFACT_PATH_DUPLICATE"
                ),
            )

    def test_float_identity_metadata_uses_domain_error(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)

            (bundle_dir / "topic_profile.json").write_text(
                "{}",
                encoding="utf-8",
            )

            with self.assertRaises(
                BundleAssemblyError
            ) as context:
                self.assemble(
                    bundle_dir,
                    identity_extraction={
                        "window_sec": 1.0,
                    },
                )

            self.assertEqual(
                context.exception.code,
                "VELUNE_BUNDLE_IDENTITY_INVALID",
            )
            self.assertIn(
                "integer base units",
                context.exception.hint,
            )
            self.assertIsNotNone(
                context.exception.__cause__
            )

    def test_invalid_generated_at_uses_domain_error(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)

            (bundle_dir / "topic_profile.json").write_text(
                "{}",
                encoding="utf-8",
            )

            with self.assertRaises(
                BundleAssemblyError
            ) as context:
                self.assemble(
                    bundle_dir,
                    generated_at="not-a-timestamp",
                )

            self.assertEqual(
                context.exception.code,
                "VELUNE_BUNDLE_MANIFEST_INVALID",
            )
            self.assertIsNotNone(
                context.exception.__cause__
            )

    def test_rejects_report_manifest_self_reference(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)

            manifest_path = (
                bundle_dir / "report_manifest.json"
            )
            manifest_path.write_text(
                "{}",
                encoding="utf-8",
            )

            with self.assertRaises(
                ArtifactDefinitionError
            ) as context:
                self.assemble(
                    bundle_dir,
                    artifact_definitions=[
                        self.artifact_definition(
                            "report_manifest.json"
                        )
                    ],
                )

            self.assertEqual(
                context.exception.code,
                "VELUNE_BUNDLE_MANIFEST_SELF_REFERENCE",
            )
            self.assertIn(
                "after all other Bundle artifacts",
                context.exception.hint,
            )

    def test_rejects_raw_runtime_log_artifacts(self):
        invalid_paths = [
            "incident_run.mcap",
            "rosbag2_0.db3",
            "legacy_run.bag",
            "runtime.sqlite3",
        ]

        for invalid_path in invalid_paths:
            with self.subTest(path=invalid_path):
                with tempfile.TemporaryDirectory() as (
                    temporary_directory
                ):
                    bundle_dir = Path(temporary_directory)

                    (bundle_dir / invalid_path).write_bytes(
                        b"raw-runtime-log"
                    )

                    with self.assertRaises(
                        ArtifactDefinitionError
                    ) as context:
                        self.assemble(
                            bundle_dir,
                            artifact_definitions=[
                                self.artifact_definition(
                                    invalid_path,
                                    role="raw_runtime_log",
                                    media_type=(
                                        "application/octet-stream"
                                    ),
                                    source_of_truth=True,
                                )
                            ],
                        )

                    self.assertEqual(
                        context.exception.code,
                        (
                            "VELUNE_BUNDLE_"
                            "RAW_LOG_ARTIFACT_FORBIDDEN"
                        ),
                    )
                    self.assertIn(
                        "Keep MCAP, rosbag2",
                        context.exception.hint,
                    )

    def test_rejects_invalid_artifact_definition_contract(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)

            (bundle_dir / "topic_profile.json").write_text(
                "{}",
                encoding="utf-8",
            )

            invalid_definitions = [
                (
                    {
                        "path": "topic_profile.json",
                        "media_type": "application/json",
                        "source_of_truth": True,
                    },
                    "VELUNE_BUNDLE_ARTIFACT_FIELDS_MISSING",
                ),
                (
                    {
                        **self.artifact_definition(
                            "topic_profile.json"
                        ),
                        "unexpected": True,
                    },
                    (
                        "VELUNE_BUNDLE_"
                        "ARTIFACT_FIELDS_UNSUPPORTED"
                    ),
                ),
                (
                    {
                        **self.artifact_definition(
                            "topic_profile.json"
                        ),
                        "source_of_truth": 1,
                    },
                    (
                        "VELUNE_BUNDLE_"
                        "SOURCE_OF_TRUTH_TYPE"
                    ),
                ),
            ]

            for definition, expected_code in (
                invalid_definitions
            ):
                with self.subTest(
                    expected_code=expected_code
                ):
                    with self.assertRaises(
                        ArtifactDefinitionError
                    ) as context:
                        self.assemble(
                            bundle_dir,
                            artifact_definitions=[
                                definition
                            ],
                        )

                    self.assertEqual(
                        context.exception.code,
                        expected_code,
                    )


if __name__ == "__main__":
    unittest.main()
