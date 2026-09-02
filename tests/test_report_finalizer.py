import json
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest import mock

from velune_trace.reporting.errors import (
    ArtifactDefinitionError,
    BundleWriteError,
    EvidenceBundleError,
)
from velune_trace.reporting.finalizer import (
    FINALIZATION_STAGE_ASSEMBLY,
    FINALIZATION_STAGE_WRITE,
    FinalizedPrivateReportBundle,
    finalize_private_report_bundle,
)


class PrivateReportBundleFinalizerTests(unittest.TestCase):
    def finalization_arguments(
        self,
        bundle_dir: Path,
        *,
        overwrite_manifest: bool = False,
    ):
        return {
            "bundle_dir": bundle_dir,
            "generated_at": (
                "2026-07-14T00:00:00+00:00"
            ),
            "source": {
                "file_name": "sample.mcap",
                "file_size_bytes": 1234,
            },
            "extraction": {
                "mode": "bounded_streaming_aggregation",
                "window_sec": 1.0,
            },
            "identity_extraction": {
                "mode": "bounded_streaming_aggregation",
                "window_ns": 1_000_000_000,
            },
            "artifact_definitions": [
                {
                    "path": "topic_profile.json",
                    "role": "core_machine_readable",
                    "media_type": "application/json",
                    "source_of_truth": True,
                }
            ],
            "overwrite_manifest": overwrite_manifest,
        }

    def create_artifact(
        self,
        bundle_dir: Path,
        content: str = "{}",
    ) -> Path:
        artifact_path = (
            bundle_dir / "topic_profile.json"
        )
        artifact_path.write_text(
            content,
            encoding="utf-8",
        )
        return artifact_path

    def test_finalizes_bundle_and_writes_matching_manifest(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)
            self.create_artifact(bundle_dir)

            result = finalize_private_report_bundle(
                **self.finalization_arguments(bundle_dir)
            )

            self.assertIsInstance(
                result,
                FinalizedPrivateReportBundle,
            )
            self.assertEqual(
                result.manifest_path,
                bundle_dir / "report_manifest.json",
            )
            self.assertTrue(
                result.report_bundle_id.startswith(
                    "vrb_sha256_"
                )
            )

            saved_manifest = json.loads(
                result.manifest_path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                saved_manifest,
                result.manifest,
            )
            self.assertEqual(
                saved_manifest["report_bundle_id"],
                result.report_bundle_id,
            )

    def test_assembly_failure_uses_unified_error_contract(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)

            with self.assertRaises(
                EvidenceBundleError
            ) as context:
                finalize_private_report_bundle(
                    **self.finalization_arguments(
                        bundle_dir
                    )
                )

            error = context.exception

            self.assertIsInstance(
                error,
                ArtifactDefinitionError,
            )
            self.assertEqual(
                error.stage,
                FINALIZATION_STAGE_ASSEMBLY,
            )
            self.assertIn(
                (
                    "[STAGE] "
                    f"{FINALIZATION_STAGE_ASSEMBLY}"
                ),
                error.cli_lines(),
            )
            self.assertIsNotNone(error.__cause__)
            self.assertFalse(
                (bundle_dir / "report_manifest.json").exists()
            )

    def test_write_failure_uses_unified_error_contract(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)
            self.create_artifact(bundle_dir)

            manifest_path = (
                bundle_dir / "report_manifest.json"
            )
            manifest_path.write_text(
                '{"existing":true}\n',
                encoding="utf-8",
            )

            with self.assertRaises(
                EvidenceBundleError
            ) as context:
                finalize_private_report_bundle(
                    **self.finalization_arguments(
                        bundle_dir
                    )
                )

            error = context.exception

            self.assertIsInstance(
                error,
                BundleWriteError,
            )
            self.assertEqual(
                error.stage,
                FINALIZATION_STAGE_WRITE,
            )
            self.assertEqual(
                error.code,
                "VELUNE_BUNDLE_MANIFEST_ALREADY_EXISTS",
            )
            self.assertIn(
                (
                    "[STAGE] "
                    f"{FINALIZATION_STAGE_WRITE}"
                ),
                error.cli_lines(),
            )
            self.assertEqual(
                manifest_path.read_text(encoding="utf-8"),
                '{"existing":true}\n',
            )

    def test_explicit_overwrite_replaces_manifest(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)
            artifact_path = self.create_artifact(
                bundle_dir,
                '{"version":1}',
            )

            first = finalize_private_report_bundle(
                **self.finalization_arguments(bundle_dir)
            )

            artifact_path.write_text(
                '{"version":2}',
                encoding="utf-8",
            )

            second = finalize_private_report_bundle(
                **self.finalization_arguments(
                    bundle_dir,
                    overwrite_manifest=True,
                )
            )

            self.assertEqual(
                first.manifest_path,
                second.manifest_path,
            )
            self.assertNotEqual(
                first.report_bundle_id,
                second.report_bundle_id,
            )

            saved_manifest = json.loads(
                second.manifest_path.read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                saved_manifest["report_bundle_id"],
                second.report_bundle_id,
            )

    def test_preserves_existing_error_stage(self):
        upstream_error = ArtifactDefinitionError(
            "Upstream artifact failure",
            stage="upstream_validation",
        )

        with mock.patch(
            (
                "velune_trace.reporting.finalizer."
                "assemble_private_report_manifest"
            ),
            side_effect=upstream_error,
        ):
            with self.assertRaises(
                ArtifactDefinitionError
            ) as context:
                finalize_private_report_bundle(
                    bundle_dir="unused",
                    generated_at=(
                        "2026-07-14T00:00:00+00:00"
                    ),
                    source={},
                    extraction={},
                    identity_extraction={},
                    artifact_definitions=[],
                )

        self.assertIs(
            context.exception,
            upstream_error,
        )
        self.assertEqual(
            context.exception.stage,
            "upstream_validation",
        )

    def test_does_not_wrap_unexpected_programming_error(self):
        unexpected_error = RuntimeError(
            "simulated programming defect"
        )

        with mock.patch(
            (
                "velune_trace.reporting.finalizer."
                "assemble_private_report_manifest"
            ),
            side_effect=unexpected_error,
        ):
            with self.assertRaises(
                RuntimeError
            ) as context:
                finalize_private_report_bundle(
                    bundle_dir="unused",
                    generated_at=(
                        "2026-07-14T00:00:00+00:00"
                    ),
                    source={},
                    extraction={},
                    identity_extraction={},
                    artifact_definitions=[],
                )

        self.assertIs(
            context.exception,
            unexpected_error,
        )

    def test_result_object_is_frozen(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)
            self.create_artifact(bundle_dir)

            result = finalize_private_report_bundle(
                **self.finalization_arguments(bundle_dir)
            )

            with self.assertRaises(FrozenInstanceError):
                result.manifest_path = (
                    bundle_dir / "changed.json"
                )


if __name__ == "__main__":
    unittest.main()
