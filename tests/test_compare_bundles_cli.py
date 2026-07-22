import sys
from contextlib import (
    redirect_stderr,
    redirect_stdout,
)
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from velune_trace.cli.compare_bundles import (
    INTERNAL_ERROR_EXIT_CODE,
    main,
)


class CompareBundlesCliTests(unittest.TestCase):
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

    def create_bundle(
        self,
        root: Path,
        name: str,
        *,
        count: int,
    ) -> Path:
        bundle_dir = root / name
        bundle_dir.mkdir()

        topic_profile = {
            "/imu": {
                "count": count,
                "duration_ns": 1_000_000_000,
                "avg_gap_ns": 10_000_000.0,
                "max_gap_ns": 20_000_000,
                "jitter_ns": 1_000_000.0,
                "expected_count_per_window": 100.0,
                "finalized_window_count": 1,
                "out_of_order_count": 0,
                "late_dropped_count": 0,
                "sensor_category": "imu",
                "expected_count_source": "expected_hz",
                "expected_hz": 100.0,
                "first_ns": 1_000_000_000,
                "last_ns": 2_000_000_000,
            },
        }

        evidence_windows = {
            "/imu": [
                {
                    "topic": "/imu",
                    "window": 1,
                    "start_ns": 1_000_000_000,
                    "end_ns": 2_000_000_000,
                    "count": 90,
                    "expected_count": 100.0,
                    "count_ratio": 0.9,
                    "max_gap_ns": 20_000_000,
                    "jitter_ns": 1_000_000.0,
                    "observed_irregularity_score": 2.0,
                    "score_semantics": (
                        "ranking_heuristic_only_"
                        "no_root_cause_inference"
                    ),
                },
            ],
        }

        topic_path = (
            bundle_dir / "topic_profile.json"
        )
        windows_path = (
            bundle_dir / "evidence_windows.json"
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
                "name": (
                    "velune.evidence_report_bundle"
                ),
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
                "total_messages_observed": count,
            },
            "artifacts": [
                self.artifact_record(windows_path),
                self.artifact_record(topic_path),
            ],
        }

        self.write_json(
            bundle_dir / "report_manifest.json",
            manifest,
        )

        return bundle_dir

    def test_end_to_end_writes_exactly_two_outputs(
        self,
    ):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            reference = self.create_bundle(
                root_path,
                "reference",
                count=100,
            )
            target = self.create_bundle(
                root_path,
                "target",
                count=120,
            )
            output_dir = root_path / "comparison"

            stdout = io.StringIO()
            stderr = io.StringIO()

            with mock.patch(
                (
                    "velune_trace.cli.compare_bundles."
                    "_utc_now_iso"
                ),
                return_value=(
                    "2026-07-16T12:00:00+00:00"
                ),
            ):
                with redirect_stdout(stdout):
                    with redirect_stderr(stderr):
                        exit_code = main([
                            str(reference),
                            str(target),
                            "--export-dir",
                            str(output_dir),
                        ])

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(
                sorted(
                    path.name
                    for path in output_dir.iterdir()
                ),
                [
                    "comparison_report.json",
                    "comparison_summary.md",
                ],
            )

            report = json.loads(
                (
                    output_dir
                    / "comparison_report.json"
                ).read_text(encoding="utf-8")
            )

            self.assertEqual(
                report["generated_at"],
                "2026-07-16T12:00:00+00:00",
            )
            self.assertEqual(
                report["summary"][
                    "changed_profile_topic_count"
                ],
                1,
            )
            self.assertTrue(
                all(
                    value is False
                    for value in report[
                        "judgment_boundary"
                    ].values()
                )
            )

            summary = (
                output_dir
                / "comparison_summary.md"
            ).read_text(encoding="utf-8")

            self.assertIn(
                (
                    "Velune reports observable differences "
                    "between the Reference Bundle and Target "
                    "Bundle. Engineers determine their "
                    "meaning and cause."
                ),
                summary,
            )
            self.assertIn(
                "LOCAL_ONLY_NOTICE=",
                stdout.getvalue(),
            )
            self.assertIn(
                "JUDGMENT_BOUNDARY_NOTICE=",
                stdout.getvalue(),
            )

            self.assertEqual(
                list(root_path.glob("*.mcap")),
                [],
            )

    def test_missing_bundle_uses_domain_error_contract(
        self,
    ):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            stderr = io.StringIO()

            with redirect_stderr(stderr):
                exit_code = main([
                    str(root_path / "missing-reference"),
                    str(root_path / "missing-target"),
                    "--export-dir",
                    str(root_path / "comparison"),
                ])

            rendered = stderr.getvalue()

            self.assertEqual(exit_code, 1)
            self.assertIn("[ERROR]", rendered)
            self.assertIn("[ERROR_CODE]", rendered)
            self.assertIn(
                "[STAGE] comparison_bundle_load",
                rendered,
            )
            self.assertIn("[HINT]", rendered)
            self.assertFalse(
                (root_path / "comparison").exists()
            )

    def test_existing_output_directory_is_preserved(
        self,
    ):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            reference = self.create_bundle(
                root_path,
                "reference",
                count=100,
            )
            target = self.create_bundle(
                root_path,
                "target",
                count=100,
            )
            output_dir = root_path / "comparison"
            output_dir.mkdir()
            marker = output_dir / "keep.txt"
            marker.write_text(
                "keep",
                encoding="utf-8",
            )
            stderr = io.StringIO()

            with redirect_stderr(stderr):
                exit_code = main([
                    str(reference),
                    str(target),
                    "--export-dir",
                    str(output_dir),
                ])

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                marker.read_text(encoding="utf-8"),
                "keep",
            )
            self.assertEqual(
                sorted(
                    path.name
                    for path in output_dir.iterdir()
                ),
                ["keep.txt"],
            )
            self.assertIn(
                "OUTPUT_DIRECTORY_ALREADY_EXISTS",
                stderr.getvalue(),
            )

    def test_internal_error_is_classified_without_traceback(
        self,
    ):
        stderr = io.StringIO()

        with mock.patch.dict(
            os.environ,
            {"VELUNE_DEBUG": ""},
            clear=False,
        ):
            with mock.patch(
                (
                    "velune_trace.cli.compare_bundles."
                    "load_comparison_bundle"
                ),
                side_effect=RuntimeError(
                    "unexpected defect"
                ),
            ):
                with redirect_stderr(stderr):
                    exit_code = main([
                        "reference",
                        "target",
                        "--export-dir",
                        "comparison",
                    ])

        rendered = stderr.getvalue()

        self.assertEqual(
            exit_code,
            INTERNAL_ERROR_EXIT_CODE,
        )
        self.assertIn(
            "[ERROR_CODE] VELUNE_INTERNAL_ERROR",
            rendered,
        )
        self.assertIn(
            "[ERROR_TYPE] RuntimeError",
            rendered,
        )
        self.assertIn(
            "VELUNE_DEBUG=1",
            rendered,
        )
        self.assertNotIn(
            "Traceback",
            rendered,
        )

    def test_debug_mode_preserves_full_defect(
        self,
    ):
        with mock.patch.dict(
            os.environ,
            {"VELUNE_DEBUG": "1"},
            clear=False,
        ):
            with mock.patch(
                (
                    "velune_trace.cli.compare_bundles."
                    "load_comparison_bundle"
                ),
                side_effect=RuntimeError(
                    "unexpected defect"
                ),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "unexpected defect",
                ):
                    main([
                        "reference",
                        "target",
                        "--export-dir",
                        "comparison",
                    ])

    def test_command_is_registered(self):
        from velune_trace.cli.compare_bundles import (
            main as compare_bundles_main,
        )
        from velune_trace.cli.main import COMMANDS

        self.assertIs(
            COMMANDS["compare-bundles"],
            compare_bundles_main,
        )

    def test_usage_and_wrapper_are_portable(self):
        from velune_trace.cli.main import print_usage

        stdout = io.StringIO()

        with redirect_stdout(stdout):
            print_usage()

        self.assertIn(
            "compare-bundles",
            stdout.getvalue(),
        )

        wrapper = Path("bin/velune").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "compare-bundles",
            wrapper,
        )
        self.assertIn(
            "--export-dir comparison_output",
            wrapper,
        )
        self.assertIn(
            'BASH_SOURCE[0]',
            wrapper,
        )
        self.assertIn(
            '.venv/bin/python',
            wrapper,
        )
        self.assertIn(
            'VELUNE_PYTHON',
            wrapper,
        )
        self.assertNotIn(
            'PYTHONPATH="$(pwd)',
            wrapper,
        )

    def test_wrapper_runs_outside_repository(
        self,
    ):
        wrapper = Path("bin/velune").resolve()

        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
        environment["PYTHONNOUSERSITE"] = "1"
        environment["VELUNE_PYTHON"] = (
            sys.executable
        )

        with tempfile.TemporaryDirectory() as other:
            completed = subprocess.run(
                [
                    str(wrapper),
                    "unknown-command",
                ],
                cwd=other,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(
            completed.returncode,
            2,
        )
        self.assertIn(
            "Unknown command",
            completed.stderr,
        )

    def test_export_directory_is_required(self):
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            with self.assertRaises(
                SystemExit
            ) as context:
                main([
                    "reference",
                    "target",
                ])

        self.assertEqual(
            context.exception.code,
            2,
        )
        self.assertIn(
            "--export-dir",
            stderr.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
