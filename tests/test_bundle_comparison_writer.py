import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

from velune_trace.comparison.engine import (
    COMPARISON_SCHEMA_NAME,
    COMPARISON_SCHEMA_VERSION,
    COMPARISON_SEMANTICS,
    COMPARISON_VISIBILITY,
)
from velune_trace.comparison.writer import (
    COMPARISON_REPORT_FILENAME,
    COMPARISON_SUMMARY_FILENAME,
    HUMAN_JUDGMENT_BOUNDARY_STATEMENT,
    BundleComparisonWriteError,
    WrittenBundleComparison,
    render_comparison_summary,
    write_bundle_comparison_outputs,
)


class BundleComparisonWriterTests(unittest.TestCase):
    def report(self):
        return {
            "schema_name": COMPARISON_SCHEMA_NAME,
            "schema_version": (
                COMPARISON_SCHEMA_VERSION
            ),
            "visibility": COMPARISON_VISIBILITY,
            "semantics": COMPARISON_SEMANTICS,
            "generated_at": (
                "2026-07-16T12:00:00+00:00"
            ),
            "reference": {
                "report_bundle_id": (
                    "vrb_sha256_reference"
                ),
                "generated_at": (
                    "2026-07-16T10:00:00+00:00"
                ),
                "bundle_schema": {
                    "name": (
                        "velune.evidence_report_bundle"
                    ),
                    "version": "0.1.0",
                },
                "engine": {
                    "name": "velune_trace",
                    "version": "0.3.6",
                },
                "source": {
                    "format": "mcap",
                    "file_name": "reference.mcap",
                    "file_size_bytes": 100,
                },
                "extraction": {},
                "total_messages_observed": 100,
                "topic_count": 2,
            },
            "target": {
                "report_bundle_id": (
                    "vrb_sha256_target"
                ),
                "generated_at": (
                    "2026-07-16T11:00:00+00:00"
                ),
                "bundle_schema": {
                    "name": (
                        "velune.evidence_report_bundle"
                    ),
                    "version": "0.1.0",
                },
                "engine": {
                    "name": "velune_trace",
                    "version": "0.3.6",
                },
                "source": {
                    "format": "mcap",
                    "file_name": "target.mcap",
                    "file_size_bytes": 120,
                },
                "extraction": {},
                "total_messages_observed": 120,
                "topic_count": 2,
            },
            "compatibility": {
                "status": "compatible",
                "required_field_checks": [],
                "warnings": [],
                "blocking_reasons": [],
            },
            "topic_set": {
                "common_topics": ["/imu"],
                "reference_only_topics": ["/odom"],
                "target_only_topics": ["/scan"],
            },
            "topic_comparisons": [
                {
                    "topic": "/imu",
                    "reference_profile_context": {},
                    "target_profile_context": {},
                    "profile_context_comparisons": {},
                    "profile_metric_comparisons": {},
                    "timestamp_provenance": {},
                    "reference_evidence_summary": {},
                    "target_evidence_summary": {},
                    "evidence_summary_comparisons": {},
                    (
                        "evidence_summary_"
                        "non_comparable_fields"
                    ): [],
                    "changed_fields": [
                        "profile.count",
                        "profile.jitter_ns",
                    ],
                },
            ],
            "summary": {
                "reference_topic_count": 2,
                "target_topic_count": 2,
                "common_topic_count": 1,
                "reference_only_topic_count": 1,
                "target_only_topic_count": 1,
                "identical_profile_topic_count": 0,
                "changed_profile_topic_count": 1,
                (
                    "identical_evidence_summary_"
                    "topic_count"
                ): 1,
                (
                    "changed_evidence_summary_"
                    "topic_count"
                ): 0,
            },
            "excluded_from_change_evaluation": [
                "artifact_hashes",
                "bundle_local_paths",
                "generated_at",
                "output_file_modification_times",
                "report_bundle_id",
            ],
            "judgment_boundary": {
                "root_cause_conclusion": False,
                "cause_inference": False,
                "fault_assignment": False,
                "liability_calculation": False,
                "safety_certification": False,
                "safety_classification": False,
                "severity_judgment": False,
                "normality_judgment": False,
                "superiority_judgment": False,
                "regression_judgment": False,
                (
                    "automatic_regression_"
                    "judgment"
                ): False,
                (
                    "automatic_improvement_"
                    "judgment"
                ): False,
            },
        }

    def test_writes_exactly_two_private_files(self):
        with tempfile.TemporaryDirectory() as root:
            output_dir = Path(root) / "comparison"

            result = write_bundle_comparison_outputs(
                export_dir=output_dir,
                report=self.report(),
            )

            self.assertIsInstance(
                result,
                WrittenBundleComparison,
            )
            self.assertEqual(
                sorted(
                    path.name
                    for path in output_dir.iterdir()
                ),
                sorted([
                    COMPARISON_REPORT_FILENAME,
                    COMPARISON_SUMMARY_FILENAME,
                ]),
            )
            self.assertEqual(
                stat.S_IMODE(
                    output_dir.stat().st_mode
                ),
                0o700,
            )
            self.assertEqual(
                stat.S_IMODE(
                    result.report_path.stat().st_mode
                ),
                0o600,
            )
            self.assertEqual(
                stat.S_IMODE(
                    result.summary_path.stat().st_mode
                ),
                0o600,
            )
            self.assertEqual(
                json.loads(
                    result.report_path.read_text(
                        encoding="utf-8"
                    )
                ),
                self.report(),
            )

    def test_markdown_is_derived_from_report(self):
        report = self.report()
        report["summary"][
            "changed_profile_topic_count"
        ] = 7

        rendered = render_comparison_summary(
            report
        )

        self.assertIn(
            HUMAN_JUDGMENT_BOUNDARY_STATEMENT,
            rendered,
        )
        self.assertIn(
            "- Changed profile topic count: 7",
            rendered,
        )
        self.assertIn(
            "`profile.count`",
            rendered,
        )
        self.assertIn(
            "`profile.jitter_ns`",
            rendered,
        )

    def test_output_is_deterministic(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)

            first = write_bundle_comparison_outputs(
                export_dir=root_path / "first",
                report=self.report(),
            )
            second = write_bundle_comparison_outputs(
                export_dir=root_path / "second",
                report=self.report(),
            )

            self.assertEqual(
                first.report_path.read_bytes(),
                second.report_path.read_bytes(),
            )
            self.assertEqual(
                first.summary_path.read_bytes(),
                second.summary_path.read_bytes(),
            )

    def test_rejects_existing_output_directory(self):
        with tempfile.TemporaryDirectory() as root:
            output_dir = Path(root) / "comparison"
            output_dir.mkdir()
            marker = output_dir / "keep.txt"
            marker.write_text(
                "keep",
                encoding="utf-8",
            )

            with self.assertRaises(
                BundleComparisonWriteError
            ) as context:
                write_bundle_comparison_outputs(
                    export_dir=output_dir,
                    report=self.report(),
                )

            self.assertEqual(
                context.exception.code,
                (
                    "VELUNE_COMPARISON_"
                    "OUTPUT_DIRECTORY_ALREADY_EXISTS"
                ),
            )
            self.assertEqual(
                marker.read_text(encoding="utf-8"),
                "keep",
            )

    def test_rejects_output_directory_symlink(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            external = root_path / "external"
            external.mkdir()
            output_dir = root_path / "comparison"
            output_dir.symlink_to(
                external,
                target_is_directory=True,
            )

            with self.assertRaises(
                BundleComparisonWriteError
            ):
                write_bundle_comparison_outputs(
                    export_dir=output_dir,
                    report=self.report(),
                )

            self.assertEqual(
                list(external.iterdir()),
                [],
            )

    def test_rejects_incompatible_report(self):
        with tempfile.TemporaryDirectory() as root:
            output_dir = Path(root) / "comparison"
            report = self.report()
            report["compatibility"][
                "status"
            ] = "incompatible"

            with self.assertRaises(
                BundleComparisonWriteError
            ) as context:
                write_bundle_comparison_outputs(
                    export_dir=output_dir,
                    report=report,
                )

            self.assertEqual(
                context.exception.code,
                (
                    "VELUNE_COMPARISON_"
                    "REPORT_INCOMPATIBLE"
                ),
            )
            self.assertFalse(output_dir.exists())

    def test_rejects_enabled_judgment(self):
        with tempfile.TemporaryDirectory() as root:
            output_dir = Path(root) / "comparison"
            report = self.report()
            report["judgment_boundary"][
                "superiority_judgment"
            ] = True

            with self.assertRaises(
                BundleComparisonWriteError
            ) as context:
                write_bundle_comparison_outputs(
                    export_dir=output_dir,
                    report=report,
                )

            self.assertEqual(
                context.exception.code,
                (
                    "VELUNE_COMPARISON_"
                    "JUDGMENT_BOUNDARY_INVALID"
                ),
            )
            self.assertFalse(output_dir.exists())

    def test_rejects_non_finite_report_value(self):
        with tempfile.TemporaryDirectory() as root:
            output_dir = Path(root) / "comparison"
            report = self.report()
            report["target"]["metric"] = float("nan")

            with self.assertRaises(
                BundleComparisonWriteError
            ) as context:
                write_bundle_comparison_outputs(
                    export_dir=output_dir,
                    report=report,
                )

            self.assertEqual(
                context.exception.code,
                (
                    "VELUNE_COMPARISON_"
                    "JSON_VALUE_INVALID"
                ),
            )
            self.assertFalse(output_dir.exists())

    def test_rejects_unsorted_changed_fields(self):
        with tempfile.TemporaryDirectory() as root:
            output_dir = Path(root) / "comparison"
            report = self.report()
            report["topic_comparisons"][0][
                "changed_fields"
            ] = [
                "profile.jitter_ns",
                "profile.count",
            ]

            with self.assertRaises(
                BundleComparisonWriteError
            ) as context:
                write_bundle_comparison_outputs(
                    export_dir=output_dir,
                    report=report,
                )

            self.assertEqual(
                context.exception.code,
                (
                    "VELUNE_COMPARISON_"
                    "REPORT_ORDER_INVALID"
                ),
            )
            self.assertFalse(output_dir.exists())

    def test_install_failure_removes_partial_output(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            output_dir = root_path / "comparison"
            original_replace = os.replace
            call_count = 0

            def failing_replace(source, target):
                nonlocal call_count
                call_count += 1

                if call_count == 4:
                    raise OSError(
                        "simulated second install failure"
                    )

                return original_replace(
                    source,
                    target,
                )

            with mock.patch(
                "velune_trace.comparison.writer.os.replace",
                side_effect=failing_replace,
            ):
                with self.assertRaises(
                    BundleComparisonWriteError
                ) as context:
                    write_bundle_comparison_outputs(
                        export_dir=output_dir,
                        report=self.report(),
                    )

            self.assertEqual(
                context.exception.code,
                (
                    "VELUNE_COMPARISON_"
                    "OUTPUT_INSTALL_FAILED"
                ),
            )
            self.assertFalse(output_dir.exists())
            self.assertEqual(
                [
                    path
                    for path in root_path.iterdir()
                    if path.name.startswith(
                        ".comparison."
                    )
                ],
                [],
            )

    def test_result_object_is_frozen(self):
        with tempfile.TemporaryDirectory() as root:
            result = write_bundle_comparison_outputs(
                export_dir=(
                    Path(root) / "comparison"
                ),
                report=self.report(),
            )

            with self.assertRaises(
                AttributeError
            ):
                result.output_dir = Path(root)


if __name__ == "__main__":
    unittest.main()
