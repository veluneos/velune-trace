from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import velune_trace.private_baseline.evaluation_service as service_module
from velune_trace.private_baseline.evaluation_service import (
    PrivateBaselineEvaluationServiceError,
    evaluate_private_baseline,
)
from velune_trace.private_baseline.evaluation_writer import (
    WrittenPrivateBaselineEvaluation,
)


REFERENCE_A_ID = (
    "vrb_sha256_" + ("a" * 64)
)
REFERENCE_B_ID = (
    "vrb_sha256_" + ("b" * 64)
)
TARGET_ID = (
    "vrb_sha256_" + ("f" * 64)
)


class PrivateBaselineEvaluationServiceTests(
    unittest.TestCase
):
    def evaluation_context(self):
        return {
            "comparison_axis": "custom",
            "axis_keys": [
                "scene_id",
            ],
            "dimensions": {
                "dataset_family": "nuScenes",
                "scene_id": "target-scene",
            },
            "note": "Explicit Target Evaluation.",
        }

    def loaded_registry(self):
        memberships = [
            {
                "report_bundle_id": REFERENCE_A_ID,
                "report_manifest_sha256": (
                    "1" * 64
                ),
                "dimensions": {
                    "dataset_family": "nuScenes",
                    "scene_id": "reference-a",
                },
                "selection": {
                    "selected_by": "engineer",
                    "selected_at": (
                        "2026-07-21T10:00:00+09:00"
                    ),
                },
            },
            {
                "report_bundle_id": REFERENCE_B_ID,
                "report_manifest_sha256": (
                    "2" * 64
                ),
                "dimensions": {
                    "dataset_family": "nuScenes",
                    "scene_id": "reference-b",
                },
                "selection": {
                    "selected_by": "engineer",
                    "selected_at": (
                        "2026-07-21T10:00:00+09:00"
                    ),
                },
            },
        ]

        revision_document = {
            "baseline_revision_id": (
                "vpbr_" + ("3" * 32)
            ),
            "dimension_policy": {
                "match_values": {
                    "dataset_family": "nuScenes",
                },
                "vary_keys": [
                    "scene_id",
                ],
                "required_keys": [
                    "dataset_family",
                    "scene_id",
                ],
            },
            "reference_memberships": (
                memberships
            ),
        }

        return SimpleNamespace(
            registry={
                "baseline_id": (
                    "vpb_" + ("4" * 32)
                ),
                "current_revision_id": (
                    revision_document[
                        "baseline_revision_id"
                    ]
                ),
                "bundle_locations": {
                    REFERENCE_A_ID: "/bundle/a",
                    REFERENCE_B_ID: "/bundle/b",
                },
            },
            current_revision=SimpleNamespace(
                document=revision_document
            ),
        )

    def verified_reference(
        self,
        report_bundle_id,
        manifest_sha256,
    ):
        return SimpleNamespace(
            report_bundle_id=(
                report_bundle_id
            ),
            report_manifest_sha256=(
                manifest_sha256
            ),
            loaded_bundle=object(),
        )

    def compatible_result(self):
        return SimpleNamespace(
            is_compatible=True,
            warnings=(),
            blocking_reasons=(),
        )

    def test_orchestrates_target_after_full_preflight(
        self,
    ):
        loaded_registry = (
            self.loaded_registry()
        )

        references = [
            self.verified_reference(
                REFERENCE_A_ID,
                "1" * 64,
            ),
            self.verified_reference(
                REFERENCE_B_ID,
                "2" * 64,
            ),
        ]

        target = self.verified_reference(
            TARGET_ID,
            "5" * 64,
        )

        final_report = {
            "schema_name": (
                "velune.private_baseline_evaluation"
            ),
            "aggregate_observations": {
                "reference_count": 2,
            },
        }

        with tempfile.TemporaryDirectory() as directory:
            export_dir = (
                Path(directory) / "evaluation"
            )

            written = (
                WrittenPrivateBaselineEvaluation(
                    output_dir=export_dir,
                    report_path=(
                        export_dir
                        / "baseline_evaluation_report.json"
                    ),
                    summary_path=(
                        export_dir
                        / "baseline_evaluation_summary.md"
                    ),
                )
            )

            with (
                patch.object(
                    service_module,
                    "load_private_baseline_registry",
                    return_value=loaded_registry,
                ),
                patch.object(
                    service_module,
                    "normalize_evaluation_context",
                    return_value=(
                        self.evaluation_context()
                    ),
                ),
                patch.object(
                    service_module,
                    "_load_verified_references",
                    side_effect=[
                        references,
                        [target],
                    ],
                ) as loader,
                patch.object(
                    service_module,
                    "evaluate_bundle_compatibility",
                    side_effect=[
                        self.compatible_result(),
                        self.compatible_result(),
                    ],
                ) as compatibility,
                patch.object(
                    service_module,
                    "build_bundle_comparison",
                    side_effect=[
                        {"pair": "a"},
                        {"pair": "b"},
                    ],
                ) as comparison,
                patch.object(
                    service_module,
                    "build_private_baseline_evaluation_report",
                    return_value=final_report,
                ) as builder,
                patch.object(
                    service_module,
                    "write_private_baseline_evaluation_outputs",
                    return_value=written,
                ) as writer,
            ):
                result = (
                    evaluate_private_baseline(
                        "/baseline",
                        "/target",
                        export_dir,
                        generated_at=(
                            "2026-07-21T17:00:00+09:00"
                        ),
                        evaluation_context=(
                            self.evaluation_context()
                        ),
                    )
                )

        self.assertIs(
            result.loaded_registry,
            loaded_registry,
        )
        self.assertEqual(
            result.evaluation_report,
            final_report,
        )
        self.assertEqual(
            loader.call_count,
            2,
        )
        self.assertEqual(
            len(
                loader.call_args_list[
                    0
                ].args[0]
            ),
            2,
        )
        self.assertEqual(
            len(
                loader.call_args_list[
                    1
                ].args[0]
            ),
            1,
        )
        self.assertEqual(
            compatibility.call_count,
            2,
        )
        self.assertEqual(
            comparison.call_count,
            2,
        )
        builder.assert_called_once()
        writer.assert_called_once()

    def test_manifest_pin_mismatch_blocks_target_io(
        self,
    ):
        loaded_registry = (
            self.loaded_registry()
        )

        references = [
            self.verified_reference(
                REFERENCE_A_ID,
                "9" * 64,
            ),
            self.verified_reference(
                REFERENCE_B_ID,
                "2" * 64,
            ),
        ]

        with (
            patch.object(
                service_module,
                "load_private_baseline_registry",
                return_value=loaded_registry,
            ),
            patch.object(
                service_module,
                "normalize_evaluation_context",
                return_value=(
                    self.evaluation_context()
                ),
            ),
            patch.object(
                service_module,
                "_load_verified_references",
                return_value=references,
            ) as loader,
            patch.object(
                service_module,
                "evaluate_bundle_compatibility",
            ) as compatibility,
            patch.object(
                service_module,
                "build_bundle_comparison",
            ) as comparison,
        ):
            with self.assertRaises(
                PrivateBaselineEvaluationServiceError
            ) as caught:
                evaluate_private_baseline(
                    "/baseline",
                    "/target",
                    "/output",
                    generated_at=(
                        "2026-07-21T17:00:00+09:00"
                    ),
                    evaluation_context=(
                        self.evaluation_context()
                    ),
                )

        self.assertEqual(
            caught.exception.code,
            (
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "SERVICE_REFERENCE_MANIFEST_MISMATCH"
            ),
        )
        self.assertEqual(
            loader.call_count,
            1,
        )
        compatibility.assert_not_called()
        comparison.assert_not_called()

    def test_incompatible_pair_blocks_every_comparison(
        self,
    ):
        loaded_registry = (
            self.loaded_registry()
        )

        references = [
            self.verified_reference(
                REFERENCE_A_ID,
                "1" * 64,
            ),
            self.verified_reference(
                REFERENCE_B_ID,
                "2" * 64,
            ),
        ]

        target = self.verified_reference(
            TARGET_ID,
            "5" * 64,
        )

        incompatible = SimpleNamespace(
            is_compatible=False,
            warnings=(),
            blocking_reasons=(
                {
                    "field_path": (
                        "manifest.extraction_contract"
                    ),
                },
            ),
        )

        with (
            patch.object(
                service_module,
                "load_private_baseline_registry",
                return_value=loaded_registry,
            ),
            patch.object(
                service_module,
                "normalize_evaluation_context",
                return_value=(
                    self.evaluation_context()
                ),
            ),
            patch.object(
                service_module,
                "_load_verified_references",
                side_effect=[
                    references,
                    [target],
                ],
            ),
            patch.object(
                service_module,
                "evaluate_bundle_compatibility",
                side_effect=[
                    self.compatible_result(),
                    incompatible,
                ],
            ),
            patch.object(
                service_module,
                "build_bundle_comparison",
            ) as comparison,
            patch.object(
                service_module,
                "write_private_baseline_evaluation_outputs",
            ) as writer,
        ):
            with self.assertRaises(
                PrivateBaselineEvaluationServiceError
            ) as caught:
                evaluate_private_baseline(
                    "/baseline",
                    "/target",
                    "/output",
                    generated_at=(
                        "2026-07-21T17:00:00+09:00"
                    ),
                    evaluation_context=(
                        self.evaluation_context()
                    ),
                )

        self.assertEqual(
            caught.exception.code,
            (
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "SERVICE_PAIR_INCOMPATIBLE"
            ),
        )
        self.assertEqual(
            len(
                caught.exception.incompatibilities
            ),
            1,
        )
        comparison.assert_not_called()
        writer.assert_not_called()

    def test_missing_reference_location_blocks_bundle_io(
        self,
    ):
        loaded_registry = (
            self.loaded_registry()
        )

        loaded_registry.registry[
            "bundle_locations"
        ].pop(
            REFERENCE_B_ID
        )

        with (
            patch.object(
                service_module,
                "load_private_baseline_registry",
                return_value=loaded_registry,
            ),
            patch.object(
                service_module,
                "normalize_evaluation_context",
                return_value=(
                    self.evaluation_context()
                ),
            ),
            patch.object(
                service_module,
                "_load_verified_references",
            ) as loader,
        ):
            with self.assertRaises(
                PrivateBaselineEvaluationServiceError
            ) as caught:
                evaluate_private_baseline(
                    "/baseline",
                    "/target",
                    "/output",
                    generated_at=(
                        "2026-07-21T17:00:00+09:00"
                    ),
                    evaluation_context=(
                        self.evaluation_context()
                    ),
                )

        self.assertEqual(
            caught.exception.code,
            (
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "SERVICE_REFERENCE_LOCATION_MISSING"
            ),
        )
        loader.assert_not_called()


if __name__ == "__main__":
    unittest.main()
