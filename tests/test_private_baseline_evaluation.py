import json
from pathlib import Path
import stat
import tempfile
import unittest

from velune_trace.private_baseline.evaluation import (
    EVALUATION_SCHEMA_NAME,
    HUMAN_JUDGMENT_BOUNDARY_STATEMENT,
    PrivateBaselineEvaluationError,
    aggregate_reference_comparisons,
    build_private_baseline_evaluation_report,
)
from velune_trace.private_baseline.evaluation_writer import (
    render_private_baseline_evaluation_summary,
    write_private_baseline_evaluation_outputs,
)


TARGET_ID = (
    "vrb_sha256_" + ("f" * 64)
)
REFERENCE_A_ID = (
    "vrb_sha256_" + ("a" * 64)
)
REFERENCE_B_ID = (
    "vrb_sha256_" + ("b" * 64)
)
GENERATED_AT = "2026-07-21T17:00:00+09:00"


class PrivateBaselineEvaluationTests(
    unittest.TestCase
):
    def comparison(
        self,
        reference_id,
        *,
        common_topics,
        reference_only_topics,
        target_only_topics,
        changed_by_topic,
        generated_at=GENERATED_AT,
    ):
        return {
            "reference_report_bundle_id": (
                reference_id
            ),
            "comparison_report": {
                "schema_name": (
                    "velune.bundle_comparison_report"
                ),
                "schema_version": "0.1.0",
                "visibility": "private_local_only",
                "semantics": (
                    "observed_comparison_only"
                ),
                "generated_at": generated_at,
                "reference": {
                    "report_bundle_id": (
                        reference_id
                    ),
                },
                "target": {
                    "report_bundle_id": TARGET_ID,
                },
                "compatibility": {
                    "status": "compatible",
                    "required_field_checks": [],
                    "warnings": [],
                    "blocking_reasons": [],
                },
                "topic_set": {
                    "common_topics": sorted(
                        common_topics
                    ),
                    "reference_only_topics": sorted(
                        reference_only_topics
                    ),
                    "target_only_topics": sorted(
                        target_only_topics
                    ),
                },
                "topic_comparisons": [
                    {
                        "topic": topic,
                        "changed_fields": sorted(
                            changed_by_topic.get(
                                topic,
                                [],
                            )
                        ),
                    }
                    for topic in sorted(
                        common_topics
                    )
                ],
                "summary": {
                    "changed_profile_topic_count": (
                        len(changed_by_topic)
                    ),
                    "changed_evidence_summary_topic_count": (
                        len(changed_by_topic)
                    ),
                },
                "excluded_from_change_evaluation": [],
                "judgment_boundary": {},
            },
        }

    def reference_comparisons(self):
        return [
            self.comparison(
                REFERENCE_A_ID,
                common_topics={
                    "/imu",
                },
                reference_only_topics={
                    "/gps",
                },
                target_only_topics={
                    "/camera",
                },
                changed_by_topic={
                    "/imu": {
                        "profile.count",
                    },
                },
            ),
            self.comparison(
                REFERENCE_B_ID,
                common_topics={
                    "/camera",
                    "/imu",
                },
                reference_only_topics=set(),
                target_only_topics=set(),
                changed_by_topic={
                    "/camera": {
                        "profile.max_gap_ns",
                    },
                    "/imu": set(),
                },
            ),
        ]

    def dimension_policy(self):
        return {
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
        }

    def evaluation_context(self):
        return {
            "comparison_axis": "custom",
            "axis_keys": [
                "scene_id",
            ],
            "dimensions": {
                "dataset_family": "nuScenes",
                "scene_id": "scene-target",
            },
            "note": (
                "Explicit Target Evaluation test."
            ),
        }

    def build_report(self):
        return (
            build_private_baseline_evaluation_report(
                evaluation_id=(
                    "vpbe_" + ("1" * 32)
                ),
                generated_at=GENERATED_AT,
                baseline_id=(
                    "vpb_" + ("2" * 32)
                ),
                baseline_revision_id=(
                    "vpbr_" + ("3" * 32)
                ),
                dimension_policy=(
                    self.dimension_policy()
                ),
                evaluation_context=(
                    self.evaluation_context()
                ),
                target_report_bundle_id=(
                    TARGET_ID
                ),
                target_report_manifest_sha256=(
                    "4" * 64
                ),
                reference_comparisons=(
                    self.reference_comparisons()
                ),
            )
        )

    def test_aggregates_changed_field_occurrence(
        self,
    ):
        aggregate = (
            aggregate_reference_comparisons(
                self.reference_comparisons()
            )
        )

        observations = {
            (
                item["topic"],
                item["field"],
            ): item
            for item in aggregate[
                "field_observations"
            ]
        }

        imu = observations[
            ("/imu", "profile.count")
        ]

        self.assertEqual(
            imu["eligible_reference_count"],
            2,
        )
        self.assertEqual(
            imu[
                "changed_against_reference_count"
            ],
            1,
        )
        self.assertEqual(
            imu[
                "unchanged_against_reference_count"
            ],
            1,
        )
        self.assertEqual(
            imu["observation_scope"],
            "some_references",
        )

        camera = observations[
            (
                "/camera",
                "profile.max_gap_ns",
            )
        ]

        self.assertEqual(
            camera["eligible_reference_count"],
            1,
        )
        self.assertEqual(
            camera["observation_scope"],
            "all_references",
        )

    def test_topic_set_includes_absent_from_both(
        self,
    ):
        aggregate = (
            aggregate_reference_comparisons(
                self.reference_comparisons()
            )
        )

        topics = {
            item["topic"]: item
            for item in aggregate[
                "topic_set_observations"
            ]
        }

        gps = topics["/gps"]

        self.assertEqual(
            gps[
                "reference_only_against_target_count"
            ],
            1,
        )
        self.assertEqual(
            gps["absent_from_both_count"],
            1,
        )

        for item in topics.values():
            self.assertEqual(
                item["common_with_target_count"]
                + item[
                    "target_only_against_reference_count"
                ]
                + item[
                    "reference_only_against_target_count"
                ]
                + item[
                    "absent_from_both_count"
                ],
                item["total_reference_count"],
            )

    def test_builds_frozen_evaluation_envelope(
        self,
    ):
        report = self.build_report()

        self.assertEqual(
            report["schema_name"],
            EVALUATION_SCHEMA_NAME,
        )
        self.assertEqual(
            report["generated_at"],
            GENERATED_AT,
        )
        self.assertEqual(
            len(
                report[
                    "reference_comparisons"
                ]
            ),
            2,
        )
        self.assertEqual(
            [
                item[
                    "reference_report_bundle_id"
                ]
                for item in report[
                    "reference_comparisons"
                ]
            ],
            sorted([
                REFERENCE_A_ID,
                REFERENCE_B_ID,
            ]),
        )
        self.assertTrue(
            all(
                value is False
                for value in report[
                    "judgment_boundary"
                ].values()
            )
        )
        self.assertNotIn(
            "review_count",
            report,
        )
        self.assertNotIn(
            "review_outcome",
            report,
        )

    def test_rejects_axis_policy_conflict(self):
        context = self.evaluation_context()
        context["axis_keys"] = [
            "dataset_family",
        ]

        with self.assertRaises(
            PrivateBaselineEvaluationError
        ) as caught:
            build_private_baseline_evaluation_report(
                evaluation_id=(
                    "vpbe_" + ("1" * 32)
                ),
                generated_at=GENERATED_AT,
                baseline_id=(
                    "vpb_" + ("2" * 32)
                ),
                baseline_revision_id=(
                    "vpbr_" + ("3" * 32)
                ),
                dimension_policy=(
                    self.dimension_policy()
                ),
                evaluation_context=context,
                target_report_bundle_id=(
                    TARGET_ID
                ),
                target_report_manifest_sha256=(
                    "4" * 64
                ),
                reference_comparisons=(
                    self.reference_comparisons()
                ),
            )

        self.assertEqual(
            caught.exception.code,
            (
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "AXIS_POLICY_CONFLICT"
            ),
        )

    def test_rejects_pairwise_timestamp_mismatch(
        self,
    ):
        comparisons = (
            self.reference_comparisons()
        )
        comparisons[0][
            "comparison_report"
        ]["generated_at"] = (
            "2026-07-21T17:01:00+09:00"
        )

        with self.assertRaises(
            PrivateBaselineEvaluationError
        ) as caught:
            build_private_baseline_evaluation_report(
                evaluation_id=(
                    "vpbe_" + ("1" * 32)
                ),
                generated_at=GENERATED_AT,
                baseline_id=(
                    "vpb_" + ("2" * 32)
                ),
                baseline_revision_id=(
                    "vpbr_" + ("3" * 32)
                ),
                dimension_policy=(
                    self.dimension_policy()
                ),
                evaluation_context=(
                    self.evaluation_context()
                ),
                target_report_bundle_id=(
                    TARGET_ID
                ),
                target_report_manifest_sha256=(
                    "4" * 64
                ),
                reference_comparisons=(
                    comparisons
                ),
            )

        self.assertEqual(
            caught.exception.code,
            (
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "PAIRWISE_TIMESTAMP_MISMATCH"
            ),
        )

    def test_renders_human_boundary(self):
        rendered = (
            render_private_baseline_evaluation_summary(
                self.build_report()
            )
        )

        self.assertIn(
            HUMAN_JUDGMENT_BOUNDARY_STATEMENT,
            rendered,
        )
        self.assertIn(
            "profile.count",
            rendered,
        )
        self.assertIn(
            "absent_from_both",
            rendered,
        )

    def test_writes_exact_two_private_files(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            export_dir = (
                Path(directory) / "evaluation"
            )

            written = (
                write_private_baseline_evaluation_outputs(
                    export_dir=export_dir,
                    report=self.build_report(),
                )
            )

            self.assertEqual(
                {
                    path.name
                    for path in export_dir.iterdir()
                },
                {
                    "baseline_evaluation_report.json",
                    "baseline_evaluation_summary.md",
                },
            )

            self.assertEqual(
                stat.S_IMODE(
                    export_dir.stat().st_mode
                ),
                0o700,
            )

            for path in (
                written.report_path,
                written.summary_path,
            ):
                self.assertEqual(
                    stat.S_IMODE(
                        path.stat().st_mode
                    ),
                    0o600,
                )

            loaded = json.loads(
                written.report_path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                loaded,
                self.build_report(),
            )

    def test_refuses_existing_output_directory(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            export_dir = (
                Path(directory) / "evaluation"
            )
            export_dir.mkdir()

            with self.assertRaises(
                PrivateBaselineEvaluationError
            ) as caught:
                write_private_baseline_evaluation_outputs(
                    export_dir=export_dir,
                    report=self.build_report(),
                )

            self.assertEqual(
                caught.exception.code,
                (
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "EXPORT_ALREADY_EXISTS"
                ),
            )


if __name__ == "__main__":
    unittest.main()
