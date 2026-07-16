import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from velune_trace.comparison.engine import (
    COMPARISON_SCHEMA_NAME,
    EVIDENCE_SCORE_SEMANTICS,
    BundleComparisonEngineError,
    build_bundle_comparison,
    compare_numeric_values,
)
from velune_trace.comparison.loader import (
    EVIDENCE_WINDOWS_FILENAME,
    MANIFEST_FILENAME,
    TOPIC_PROFILE_FILENAME,
    load_comparison_bundle,
)


class BundleComparisonEngineTests(unittest.TestCase):
    def write_json(
        self,
        path: Path,
        value,
    ) -> None:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
        )
        path.write_text(
            f"{rendered}\n",
            encoding="utf-8",
        )

    def artifact_record(
        self,
        path: Path,
    ) -> dict:
        payload = path.read_bytes()

        return {
            "path": path.name,
            "role": "core_machine_readable",
            "media_type": "application/json",
            "size_bytes": len(payload),
            "hash": {
                "algorithm": "sha256",
                "value": hashlib.sha256(
                    payload
                ).hexdigest(),
            },
            "source_of_truth": True,
        }

    def profile(
        self,
        *,
        count=100,
        duration_ns=1_000_000_000,
        avg_gap_ns=10_000_000.0,
        max_gap_ns=20_000_000,
        jitter_ns=1_000_000.0,
        expected_count_per_window=100.0,
        finalized_window_count=1,
        out_of_order_count=0,
        late_dropped_count=0,
        sensor_category="imu",
        expected_count_source="expected_hz",
        expected_hz=100.0,
        first_ns=1_000_000_000,
        last_ns=2_000_000_000,
    ):
        return {
            "count": count,
            "duration_ns": duration_ns,
            "avg_gap_ns": avg_gap_ns,
            "max_gap_ns": max_gap_ns,
            "jitter_ns": jitter_ns,
            "expected_count_per_window": (
                expected_count_per_window
            ),
            "finalized_window_count": (
                finalized_window_count
            ),
            "out_of_order_count": (
                out_of_order_count
            ),
            "late_dropped_count": (
                late_dropped_count
            ),
            "sensor_category": sensor_category,
            "expected_count_source": (
                expected_count_source
            ),
            "expected_hz": expected_hz,
            "first_ns": first_ns,
            "last_ns": last_ns,
        }

    def window(
        self,
        *,
        score=2.0,
        count_ratio=0.9,
        max_gap_ns=20_000_000,
        jitter_ns=1_000_000.0,
        start_ns=1_000_000_000,
        end_ns=2_000_000_000,
        window=1,
        score_semantics=EVIDENCE_SCORE_SEMANTICS,
    ):
        return {
            "topic": "/imu",
            "window": window,
            "start_ns": start_ns,
            "end_ns": end_ns,
            "count": 90,
            "expected_count": 100.0,
            "count_ratio": count_ratio,
            "max_gap_ns": max_gap_ns,
            "jitter_ns": jitter_ns,
            "observed_irregularity_score": score,
            "score_semantics": score_semantics,
        }

    def create_bundle(
        self,
        root: Path,
        name: str,
        *,
        topic_profile=None,
        evidence_windows=None,
        manifest_transform=None,
    ) -> Path:
        bundle_dir = root / name
        bundle_dir.mkdir()

        if topic_profile is None:
            topic_profile = {
                "/imu": self.profile(),
            }

        if evidence_windows is None:
            evidence_windows = {
                "/imu": [
                    self.window(),
                ],
            }

        topic_path = (
            bundle_dir / TOPIC_PROFILE_FILENAME
        )
        windows_path = (
            bundle_dir / EVIDENCE_WINDOWS_FILENAME
        )

        self.write_json(
            topic_path,
            topic_profile,
        )
        self.write_json(
            windows_path,
            evidence_windows,
        )

        manifest = {
            "schema_name": "velune.report_manifest",
            "schema_version": "0.1.0",
            "bundle_schema": {
                "name": "velune.evidence_report_bundle",
                "version": "0.1.0",
            },
            "report_bundle_id": (
                f"vrb_sha256_{name}_"
                + ("0" * 32)
            ),
            "generated_at": (
                "2026-07-16T00:00:00+00:00"
            ),
            "engine": {
                "name": "velune_trace",
                "version": "0.3.6",
            },
            "source": {
                "format": "mcap",
                "file_name": f"{name}.mcap",
                "file_size_bytes": 1234,
            },
            "extraction": {
                "semantics": (
                    "observed_timing_metadata_only"
                ),
                "mode": (
                    "bounded_streaming_aggregation"
                ),
                "timestamp_unit": "nanoseconds_int",
                "window_sec": 1.0,
                "allowed_lateness_sec": 2.0,
                "top": 5,
                "total_messages_observed": sum(
                    profile["count"]
                    for profile in (
                        topic_profile.values()
                    )
                ),
            },
            "artifacts": [
                self.artifact_record(windows_path),
                self.artifact_record(topic_path),
            ],
        }

        if manifest_transform is not None:
            manifest_transform(manifest)

        self.write_json(
            bundle_dir / MANIFEST_FILENAME,
            manifest,
        )

        return bundle_dir

    def load_pair(
        self,
        *,
        reference_profile=None,
        target_profile=None,
        reference_windows=None,
        target_windows=None,
        reference_manifest_transform=None,
        target_manifest_transform=None,
    ):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)

        reference_dir = self.create_bundle(
            root,
            "reference",
            topic_profile=reference_profile,
            evidence_windows=reference_windows,
            manifest_transform=(
                reference_manifest_transform
            ),
        )
        target_dir = self.create_bundle(
            root,
            "target",
            topic_profile=target_profile,
            evidence_windows=target_windows,
            manifest_transform=(
                target_manifest_transform
            ),
        )

        return (
            temporary,
            load_comparison_bundle(reference_dir),
            load_comparison_bundle(target_dir),
        )

    def build(
        self,
        reference,
        target,
    ):
        return build_bundle_comparison(
            reference,
            target,
            generated_at=(
                "2026-07-16T12:00:00+00:00"
            ),
        )

    def test_numeric_comparison_finite_ratio(self):
        result = compare_numeric_values(100, 120)

        self.assertEqual(
            result,
            {
                "reference": 100,
                "target": 120,
                "delta": 20,
                "ratio": 1.2,
                "ratio_state": "finite",
            },
        )

    def test_numeric_comparison_both_zero(self):
        result = compare_numeric_values(0, 0)

        self.assertEqual(result["delta"], 0)
        self.assertEqual(result["ratio"], 1.0)
        self.assertEqual(
            result["ratio_state"],
            "both_zero",
        )

    def test_numeric_comparison_reference_zero(self):
        result = compare_numeric_values(0, 5)

        self.assertEqual(result["delta"], 5)
        self.assertIsNone(result["ratio"])
        self.assertEqual(
            result["ratio_state"],
            "reference_zero",
        )

    def test_identical_bundles_build_report(self):
        temporary, reference, target = (
            self.load_pair()
        )

        try:
            report = self.build(reference, target)

            self.assertEqual(
                report["schema_name"],
                COMPARISON_SCHEMA_NAME,
            )
            self.assertEqual(
                report["semantics"],
                "observed_comparison_only",
            )
            self.assertEqual(
                report["topic_set"]["common_topics"],
                ["/imu"],
            )
            self.assertEqual(
                report["topic_comparisons"][0][
                    "changed_fields"
                ],
                [],
            )
            self.assertEqual(
                report["summary"][
                    "identical_profile_topic_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    (
                        "identical_evidence_summary_"
                        "topic_count"
                    )
                ],
                1,
            )
            self.assertEqual(
                report["judgment_boundary"],
                {
                    "cause_inference": False,
                    "severity_judgment": False,
                    "normality_judgment": False,
                    "superiority_judgment": False,
                    "regression_judgment": False,
                    "fault_assignment": False,
                    "liability_calculation": False,
                    "safety_classification": False,
                    "automatic_improvement_label": False,
                },
            )

            json.dumps(
                report,
                allow_nan=False,
                sort_keys=True,
            )
        finally:
            temporary.cleanup()

    def test_topic_sets_are_sorted_and_classified(self):
        reference_profile = {
            "/z": self.profile(),
            "/a": self.profile(),
        }
        target_profile = {
            "/z": self.profile(),
            "/b": self.profile(),
        }
        reference_windows = {
            "/z": [self.window()],
            "/a": [self.window()],
        }
        target_windows = {
            "/z": [self.window()],
            "/b": [self.window()],
        }

        temporary, reference, target = (
            self.load_pair(
                reference_profile=reference_profile,
                target_profile=target_profile,
                reference_windows=reference_windows,
                target_windows=target_windows,
            )
        )

        try:
            report = self.build(reference, target)

            self.assertEqual(
                report["topic_set"],
                {
                    "common_topics": ["/z"],
                    "reference_only_topics": ["/a"],
                    "target_only_topics": ["/b"],
                },
            )
            self.assertEqual(
                report["summary"][
                    "reference_topic_count"
                ],
                2,
            )
            self.assertEqual(
                report["summary"][
                    "target_topic_count"
                ],
                2,
            )
            self.assertEqual(
                report["summary"][
                    "common_topic_count"
                ],
                1,
            )
        finally:
            temporary.cleanup()

    def test_profile_metric_changes_are_calculated(self):
        reference_profile = {
            "/imu": self.profile(
                count=100,
                jitter_ns=1.0,
            ),
        }
        target_profile = {
            "/imu": self.profile(
                count=120,
                jitter_ns=2.0,
            ),
        }

        temporary, reference, target = (
            self.load_pair(
                reference_profile=reference_profile,
                target_profile=target_profile,
            )
        )

        try:
            report = self.build(reference, target)
            topic = report["topic_comparisons"][0]

            self.assertEqual(
                topic[
                    "profile_metric_comparisons"
                ]["count"]["delta"],
                20,
            )
            self.assertEqual(
                topic[
                    "profile_metric_comparisons"
                ]["count"]["ratio"],
                1.2,
            )
            self.assertEqual(
                topic["changed_fields"],
                [
                    "profile.count",
                    "profile.jitter_ns",
                ],
            )
            self.assertEqual(
                report["summary"][
                    "changed_profile_topic_count"
                ],
                1,
            )
        finally:
            temporary.cleanup()

    def test_context_changes_are_recorded(self):
        reference_profile = {
            "/imu": self.profile(
                expected_hz=100.0,
            ),
        }
        target_profile = {
            "/imu": self.profile(
                expected_hz=50.0,
            ),
        }

        temporary, reference, target = (
            self.load_pair(
                reference_profile=reference_profile,
                target_profile=target_profile,
            )
        )

        try:
            topic = self.build(
                reference,
                target,
            )["topic_comparisons"][0]

            comparison = topic[
                "profile_context_comparisons"
            ]["expected_hz"]

            self.assertTrue(comparison["changed"])
            self.assertEqual(
                comparison["reference"],
                100.0,
            )
            self.assertEqual(
                comparison["target"],
                50.0,
            )
            self.assertIn(
                "context.expected_hz",
                topic["changed_fields"],
            )
        finally:
            temporary.cleanup()

    def test_absolute_timestamps_are_provenance_only(
        self,
    ):
        reference_profile = {
            "/imu": self.profile(
                first_ns=100,
                last_ns=200,
            ),
        }
        target_profile = {
            "/imu": self.profile(
                first_ns=1000,
                last_ns=2000,
            ),
        }

        temporary, reference, target = (
            self.load_pair(
                reference_profile=reference_profile,
                target_profile=target_profile,
            )
        )

        try:
            topic = self.build(
                reference,
                target,
            )["topic_comparisons"][0]

            provenance = topic[
                "timestamp_provenance"
            ]

            self.assertEqual(
                provenance["changed_fields"],
                ["first_ns", "last_ns"],
            )
            self.assertTrue(
                provenance[
                    "excluded_from_delta_and_ratio"
                ]
            )
            self.assertEqual(
                topic["changed_fields"],
                [],
            )
        finally:
            temporary.cleanup()

    def test_windows_are_summarized_without_alignment(
        self,
    ):
        reference_windows = {
            "/imu": [
                self.window(
                    score=1.0,
                    count_ratio=0.8,
                    max_gap_ns=10,
                    jitter_ns=2.0,
                    start_ns=100,
                    window=1,
                ),
                self.window(
                    score=3.0,
                    count_ratio=0.6,
                    max_gap_ns=30,
                    jitter_ns=4.0,
                    start_ns=200,
                    window=2,
                ),
            ],
        }
        target_windows = {
            "/imu": [
                self.window(
                    score=3.0,
                    count_ratio=0.6,
                    max_gap_ns=30,
                    jitter_ns=4.0,
                    start_ns=9000,
                    window=99,
                ),
                self.window(
                    score=1.0,
                    count_ratio=0.8,
                    max_gap_ns=10,
                    jitter_ns=2.0,
                    start_ns=8000,
                    window=98,
                ),
            ],
        }

        temporary, reference, target = (
            self.load_pair(
                reference_windows=reference_windows,
                target_windows=target_windows,
            )
        )

        try:
            topic = self.build(
                reference,
                target,
            )["topic_comparisons"][0]

            self.assertEqual(
                topic[
                    "reference_evidence_summary"
                ],
                topic["target_evidence_summary"],
            )
            self.assertEqual(
                topic[
                    "evidence_summary_non_comparable_fields"
                ],
                [],
            )
            self.assertNotIn(
                "evidence_summary",
                " ".join(topic["changed_fields"]),
            )
        finally:
            temporary.cleanup()

    def test_empty_windows_are_not_falsely_aligned(self):
        reference_windows = {
            "/imu": [],
        }
        target_windows = {
            "/imu": [self.window()],
        }

        temporary, reference, target = (
            self.load_pair(
                reference_windows=reference_windows,
                target_windows=target_windows,
            )
        )

        try:
            topic = self.build(
                reference,
                target,
            )["topic_comparisons"][0]

            self.assertEqual(
                topic[
                    "reference_evidence_summary"
                ]["selected_window_count"],
                0,
            )
            self.assertEqual(
                topic[
                    "target_evidence_summary"
                ]["selected_window_count"],
                1,
            )
            self.assertEqual(
                topic[
                    "evidence_summary_non_comparable_fields"
                ],
                [
                    "max_jitter_ns",
                    "max_max_gap_ns",
                    (
                        "max_observed_"
                        "irregularity_score"
                    ),
                    (
                        "mean_observed_"
                        "irregularity_score"
                    ),
                    "min_count_ratio",
                ],
            )
        finally:
            temporary.cleanup()

    def test_incompatible_bundles_are_rejected(self):
        def change_target(manifest):
            manifest["extraction"]["top"] = 10

        temporary, reference, target = (
            self.load_pair(
                target_manifest_transform=(
                    change_target
                ),
            )
        )

        try:
            with self.assertRaises(
                BundleComparisonEngineError
            ) as context:
                self.build(reference, target)

            self.assertEqual(
                context.exception.code,
                (
                    "VELUNE_COMPARISON_"
                    "BUNDLES_INCOMPATIBLE"
                ),
            )
            self.assertIn(
                "extraction.top",
                str(context.exception),
            )
        finally:
            temporary.cleanup()

    def test_invalid_score_semantics_are_rejected(self):
        target_windows = {
            "/imu": [
                self.window(
                    score_semantics="root_cause_score",
                ),
            ],
        }

        temporary, reference, target = (
            self.load_pair(
                target_windows=target_windows,
            )
        )

        try:
            with self.assertRaises(
                BundleComparisonEngineError
            ) as context:
                self.build(reference, target)

            self.assertEqual(
                context.exception.code,
                (
                    "VELUNE_COMPARISON_"
                    "SCORE_SEMANTICS_INVALID"
                ),
            )
        finally:
            temporary.cleanup()

    def test_missing_profile_metric_is_rejected(self):
        invalid_profile = self.profile()
        del invalid_profile["jitter_ns"]

        temporary, reference, target = (
            self.load_pair(
                target_profile={
                    "/imu": invalid_profile,
                },
            )
        )

        try:
            with self.assertRaises(
                BundleComparisonEngineError
            ) as context:
                self.build(reference, target)

            self.assertEqual(
                context.exception.code,
                (
                    "VELUNE_COMPARISON_"
                    "FIELD_MISSING"
                ),
            )
            self.assertIn(
                "jitter_ns",
                str(context.exception),
            )
        finally:
            temporary.cleanup()

    def test_inconsistent_bundle_topic_sets_rejected(
        self,
    ):
        target_profile = {
            "/imu": self.profile(),
            "/scan": self.profile(
                sensor_category="lidar",
            ),
        }
        target_windows = {
            "/imu": [self.window()],
        }

        temporary, reference, target = (
            self.load_pair(
                target_profile=target_profile,
                target_windows=target_windows,
            )
        )

        try:
            with self.assertRaises(
                BundleComparisonEngineError
            ) as context:
                self.build(reference, target)

            self.assertEqual(
                context.exception.code,
                (
                    "VELUNE_COMPARISON_"
                    "BUNDLE_TOPIC_SET_INCONSISTENT"
                ),
            )
        finally:
            temporary.cleanup()

    def test_generated_at_requires_timezone(self):
        temporary, reference, target = (
            self.load_pair()
        )

        try:
            with self.assertRaises(
                BundleComparisonEngineError
            ) as context:
                build_bundle_comparison(
                    reference,
                    target,
                    generated_at=(
                        "2026-07-16T12:00:00"
                    ),
                )

            self.assertEqual(
                context.exception.code,
                (
                    "VELUNE_COMPARISON_"
                    "GENERATED_AT_INVALID"
                ),
            )
        finally:
            temporary.cleanup()

    def test_report_is_deterministic_for_fixed_inputs(
        self,
    ):
        temporary, reference, target = (
            self.load_pair()
        )

        try:
            first = self.build(reference, target)
            second = self.build(reference, target)

            self.assertEqual(first, second)
            self.assertEqual(
                json.dumps(
                    first,
                    allow_nan=False,
                    sort_keys=True,
                ),
                json.dumps(
                    second,
                    allow_nan=False,
                    sort_keys=True,
                ),
            )
        finally:
            temporary.cleanup()

    def test_rejects_invalid_input_types(self):
        temporary, reference, target = (
            self.load_pair()
        )

        try:
            with self.assertRaises(TypeError):
                build_bundle_comparison(
                    {},
                    target,
                    generated_at=(
                        "2026-07-16T12:00:00+00:00"
                    ),
                )

            with self.assertRaises(TypeError):
                build_bundle_comparison(
                    reference,
                    {},
                    generated_at=(
                        "2026-07-16T12:00:00+00:00"
                    ),
                )
        finally:
            temporary.cleanup()


if __name__ == "__main__":
    unittest.main()
