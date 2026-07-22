import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from velune_trace.comparison import (
    BundleComparisonLoadError,
)
from velune_trace.comparison.loader import (
    MANIFEST_FILENAME,
    TOPIC_PROFILE_FILENAME,
)
from velune_trace.private_baseline.errors import (
    PrivateBaselineContractError,
)
import velune_trace.private_baseline.service as service_module
from velune_trace.private_baseline.service import (
    CreatedPrivateBaseline,
    PrivateBaselineServiceError,
    create_private_baseline,
)
from velune_trace.reporting import (
    finalize_private_report_bundle,
)


class PrivateBaselineServiceTests(
    unittest.TestCase
):
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

    def create_bundle(
        self,
        root: Path,
        name: str,
        *,
        payload_marker: int,
        window_sec: float = 1.0,
        engine_version: str | None = None,
        source_format: str = "mcap",
    ) -> Path:
        bundle_dir = root / name
        bundle_dir.mkdir()

        topic_path = (
            bundle_dir
            / "topic_profile.json"
        )
        windows_path = (
            bundle_dir
            / "evidence_windows.json"
        )

        self.write_json(
            topic_path,
            {
                "/imu": {
                    "count": (
                        100 + payload_marker
                    ),
                    "duration_ns": 1_000_000_000,
                    "avg_gap_ns": 10_000_000,
                    "max_gap_ns": 20_000_000,
                    "jitter_ns": 1_000_000,
                    "expected_count_per_window": 100,
                    "finalized_window_count": 1,
                    "out_of_order_count": 0,
                    "late_dropped_count": 0,
                    "sensor_category": "imu",
                    "expected_count_source": "configured",
                    "expected_hz": 100,
                    "first_ns": 0,
                    "last_ns": 1_000_000_000,
                },
            },
        )

        self.write_json(
            windows_path,
            {
                "/imu": [
                    {
                        "window_id": 0,
                        "start_ns": 0,
                        "end_ns": 1_000_000_000,
                        "count": (
                            100 + payload_marker
                        ),
                        "max_gap_ns": 20_000_000,
                        "jitter_ns": 1_000_000,
                        "count_ratio": 1.0,
                        "observed_irregularity_score": 0.0,
                    },
                ],
            },
        )

        finalized = (
            finalize_private_report_bundle(
                bundle_dir=bundle_dir,
                generated_at=(
                    "2026-07-20T10:00:00+09:00"
                ),
                source={
                    "format": source_format,
                    "file_name": f"{name}.mcap",
                    "file_size_bytes": 1234,
                    "messages_included": False,
                    "raw_payload_included": False,
                },
                extraction={
                    "semantics": (
                        "observed_timing_metadata_only"
                    ),
                    "mode": (
                        "bounded_streaming_aggregation"
                    ),
                    "timestamp_unit": (
                        "nanoseconds_int"
                    ),
                    "window_sec": window_sec,
                    "allowed_lateness_sec": 2.0,
                    "top": 5,
                    "total_messages_observed": (
                        100 + payload_marker
                    ),
                },
                identity_extraction={
                    "semantics": (
                        "observed_timing_metadata_only"
                    ),
                    "mode": (
                        "bounded_streaming_aggregation"
                    ),
                    "timestamp_unit": (
                        "nanoseconds_int"
                    ),
                    "window_ns": int(
                        window_sec
                        * 1_000_000_000
                    ),
                    "allowed_lateness_ns": (
                        2_000_000_000
                    ),
                    "top": 5,
                },
                artifact_definitions=[
                    {
                        "path": (
                            "topic_profile.json"
                        ),
                        "role": (
                            "core_machine_readable"
                        ),
                        "media_type": (
                            "application/json"
                        ),
                        "source_of_truth": True,
                    },
                    {
                        "path": (
                            "evidence_windows.json"
                        ),
                        "role": (
                            "core_machine_readable"
                        ),
                        "media_type": (
                            "application/json"
                        ),
                        "source_of_truth": True,
                    },
                ],
            )
        )

        if engine_version is not None:
            manifest = copy.deepcopy(
                finalized.manifest
            )
            manifest["engine"]["version"] = (
                engine_version
            )
            self.write_json(
                bundle_dir / MANIFEST_FILENAME,
                manifest,
            )

        return bundle_dir

    def dimension_policy(self):
        return {
            "match_values": {
                "robot_model": "model-a",
            },
            "vary_keys": [
                "software_version",
            ],
            "required_keys": [
                "robot_model",
                "software_version",
            ],
        }

    def reference(
        self,
        bundle_dir: Path,
        *,
        software_version: str,
    ):
        return {
            "bundle_dir": bundle_dir,
            "dimensions": {
                "robot_model": "model-a",
                "software_version": (
                    software_version
                ),
            },
            "selection": {
                "selected_by": "engineer-a",
                "selected_at": (
                    "2026-07-20T09:00:00+09:00"
                ),
                "selection_note": "",
            },
        }

    def create(
        self,
        parent: Path,
        references,
    ):
        with patch(
            "velune_trace.private_baseline."
            "contract.secrets.token_hex",
            return_value="9" * 32,
        ):
            return create_private_baseline(
                parent,
                display_name=(
                    "Private Baseline A"
                ),
                created_at=(
                    "2026-07-20T10:00:00+09:00"
                ),
                created_by="engineer-a",
                dimension_policy=(
                    self.dimension_policy()
                ),
                references=references,
            )

    def assert_service_error(
        self,
        expected_code,
        callback,
    ):
        with self.assertRaises(
            PrivateBaselineServiceError
        ) as caught:
            callback()

        self.assertEqual(
            caught.exception.code,
            expected_code,
        )
        self.assertEqual(
            caught.exception.stage,
            "private_baseline_service",
        )

        return caught.exception

    def test_creates_baseline_from_verified_references(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundles = root / "bundles"
            output = root / "output"
            bundles.mkdir()
            output.mkdir()

            first = self.create_bundle(
                bundles,
                "reference-a",
                payload_marker=1,
            )
            second = self.create_bundle(
                bundles,
                "reference-b",
                payload_marker=2,
            )

            result = self.create(
                output,
                [
                    self.reference(
                        first,
                        software_version="v1",
                    ),
                    self.reference(
                        second,
                        software_version="v2",
                    ),
                ],
            )

            self.assertIsInstance(
                result,
                CreatedPrivateBaseline,
            )
            self.assertEqual(
                len(
                    result.loaded_registry
                    .current_revision
                    .document[
                        "reference_memberships"
                    ]
                ),
                2,
            )

    def test_loads_each_reference_exactly_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundles = root / "bundles"
            output = root / "output"
            bundles.mkdir()
            output.mkdir()

            paths = [
                self.create_bundle(
                    bundles,
                    "reference-a",
                    payload_marker=1,
                ),
                self.create_bundle(
                    bundles,
                    "reference-b",
                    payload_marker=2,
                ),
            ]

            original = (
                service_module
                .load_comparison_bundle
            )

            with patch.object(
                service_module,
                "load_comparison_bundle",
                wraps=original,
            ) as loader:
                self.create(
                    output,
                    [
                        self.reference(
                            path,
                            software_version=(
                                f"v{index}"
                            ),
                        )
                        for index, path in enumerate(
                            paths,
                            start=1,
                        )
                    ],
                )

            self.assertEqual(
                loader.call_count,
                len(paths),
            )

    def test_pins_physical_manifest_sha256(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundles = root / "bundles"
            output = root / "output"
            bundles.mkdir()
            output.mkdir()

            bundle = self.create_bundle(
                bundles,
                "reference-a",
                payload_marker=1,
            )

            expected = hashlib.sha256(
                (
                    bundle / MANIFEST_FILENAME
                ).read_bytes()
            ).hexdigest()

            result = self.create(
                output,
                [
                    self.reference(
                        bundle,
                        software_version="v1",
                    ),
                ],
            )

            membership = (
                result.loaded_registry
                .current_revision.document[
                    "reference_memberships"
                ][0]
            )

            self.assertEqual(
                membership[
                    "report_manifest_sha256"
                ],
                expected,
            )

    def test_records_verified_bundle_locations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundles = root / "bundles"
            output = root / "output"
            bundles.mkdir()
            output.mkdir()

            bundle = self.create_bundle(
                bundles,
                "reference-a",
                payload_marker=1,
            )

            result = self.create(
                output,
                [
                    self.reference(
                        bundle,
                        software_version="v1",
                    ),
                ],
            )

            membership = (
                result.loaded_registry
                .current_revision.document[
                    "reference_memberships"
                ][0]
            )
            bundle_id = membership[
                "report_bundle_id"
            ]

            self.assertEqual(
                result.loaded_registry.registry[
                    "bundle_locations"
                ][bundle_id],
                str(bundle.resolve()),
            )

    def test_excludes_local_path_from_membership(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundles = root / "bundles"
            output = root / "output"
            bundles.mkdir()
            output.mkdir()

            bundle = self.create_bundle(
                bundles,
                "reference-a",
                payload_marker=1,
            )

            result = self.create(
                output,
                [
                    self.reference(
                        bundle,
                        software_version="v1",
                    ),
                ],
            )

            membership = (
                result.loaded_registry
                .current_revision.document[
                    "reference_memberships"
                ][0]
            )

            self.assertNotIn(
                "bundle_dir",
                membership,
            )
            self.assertNotIn(
                str(bundle.resolve()),
                json.dumps(
                    membership,
                    ensure_ascii=False,
                ),
            )

    def test_preserves_compatibility_warnings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundles = root / "bundles"
            output = root / "output"
            bundles.mkdir()
            output.mkdir()

            first = self.create_bundle(
                bundles,
                "reference-a",
                payload_marker=1,
                engine_version="0.3.6",
            )
            second = self.create_bundle(
                bundles,
                "reference-b",
                payload_marker=2,
                engine_version="0.3.7",
            )

            result = self.create(
                output,
                [
                    self.reference(
                        first,
                        software_version="v1",
                    ),
                    self.reference(
                        second,
                        software_version="v2",
                    ),
                ],
            )

            self.assertTrue(
                result.compatibility_warnings
            )
            self.assertTrue(
                all(
                    "warning" in warning
                    for warning in (
                        result.compatibility_warnings
                    )
                )
            )

    def test_blocks_incompatible_references_before_install(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundles = root / "bundles"
            output = root / "output"
            bundles.mkdir()
            output.mkdir()

            first = self.create_bundle(
                bundles,
                "reference-a",
                payload_marker=1,
                window_sec=1.0,
            )
            second = self.create_bundle(
                bundles,
                "reference-b",
                payload_marker=2,
                window_sec=2.0,
            )

            error = self.assert_service_error(
                (
                    "VELUNE_PRIVATE_BASELINE_SERVICE_"
                    "REFERENCES_INCOMPATIBLE"
                ),
                lambda: self.create(
                    output,
                    [
                        self.reference(
                            first,
                            software_version="v1",
                        ),
                        self.reference(
                            second,
                            software_version="v2",
                        ),
                    ],
                ),
            )

            self.assertTrue(
                error.incompatibilities
            )
            self.assertEqual(
                list(output.iterdir()),
                [],
            )

    def test_collects_all_incompatible_anchor_pairs(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundles = root / "bundles"
            output = root / "output"
            bundles.mkdir()
            output.mkdir()

            paths = [
                self.create_bundle(
                    bundles,
                    "reference-a",
                    payload_marker=1,
                    window_sec=1.0,
                ),
                self.create_bundle(
                    bundles,
                    "reference-b",
                    payload_marker=2,
                    window_sec=2.0,
                ),
                self.create_bundle(
                    bundles,
                    "reference-c",
                    payload_marker=3,
                    window_sec=3.0,
                ),
            ]

            error = self.assert_service_error(
                (
                    "VELUNE_PRIVATE_BASELINE_SERVICE_"
                    "REFERENCES_INCOMPATIBLE"
                ),
                lambda: self.create(
                    output,
                    [
                        self.reference(
                            path,
                            software_version=(
                                f"v{index}"
                            ),
                        )
                        for index, path in enumerate(
                            paths,
                            start=1,
                        )
                    ],
                ),
            )

            self.assertEqual(
                len(error.incompatibilities),
                2,
            )
            self.assertEqual(
                list(output.iterdir()),
                [],
            )

    def test_rejects_duplicate_bundle_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundles = root / "bundles"
            output = root / "output"
            bundles.mkdir()
            output.mkdir()

            first = self.create_bundle(
                bundles,
                "reference-a",
                payload_marker=1,
            )
            second = self.create_bundle(
                bundles,
                "reference-b",
                payload_marker=1,
            )

            self.assert_service_error(
                (
                    "VELUNE_PRIVATE_BASELINE_SERVICE_"
                    "REFERENCE_BUNDLE_DUPLICATE"
                ),
                lambda: self.create(
                    output,
                    [
                        self.reference(
                            first,
                            software_version="v1",
                        ),
                        self.reference(
                            second,
                            software_version="v2",
                        ),
                    ],
                ),
            )

            self.assertEqual(
                list(output.iterdir()),
                [],
            )

    def test_rejects_empty_reference_list(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)

            self.assert_service_error(
                (
                    "VELUNE_PRIVATE_BASELINE_SERVICE_"
                    "REFERENCE_REQUIRED"
                ),
                lambda: self.create(
                    output,
                    [],
                ),
            )

            self.assertEqual(
                list(output.iterdir()),
                [],
            )

    def test_rejects_thirty_third_before_load(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)

            references = [
                {
                    "bundle_dir": f"/missing/{index}",
                    "dimensions": {
                        "robot_model": "model-a",
                        "software_version": (
                            f"v{index}"
                        ),
                    },
                    "selection": {
                        "selected_by": "engineer-a",
                        "selected_at": (
                            "2026-07-20T09:00:00"
                            "+09:00"
                        ),
                    },
                }
                for index in range(33)
            ]

            with patch.object(
                service_module,
                "load_comparison_bundle",
            ) as loader:
                self.assert_service_error(
                    (
                        "VELUNE_PRIVATE_BASELINE_SERVICE_"
                        "REFERENCE_LIMIT_EXCEEDED"
                    ),
                    lambda: self.create(
                        output,
                        references,
                    ),
                )

            loader.assert_not_called()

    def test_rejects_missing_reference_field(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)

            self.assert_service_error(
                (
                    "VELUNE_PRIVATE_BASELINE_SERVICE_"
                    "REFERENCE_FIELD_MISSING"
                ),
                lambda: self.create(
                    output,
                    [
                        {
                            "bundle_dir": "/tmp/bundle",
                            "dimensions": {},
                        },
                    ],
                ),
            )

    def test_rejects_unexpected_reference_field(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)

            self.assert_service_error(
                (
                    "VELUNE_PRIVATE_BASELINE_SERVICE_"
                    "REFERENCE_FIELD_UNEXPECTED"
                ),
                lambda: self.create(
                    output,
                    [
                        {
                            "bundle_dir": "/tmp/bundle",
                            "dimensions": {},
                            "selection": {},
                            "automatic_weight": 1,
                        },
                    ],
                ),
            )

    def test_rejects_malformed_report_bundle_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundles = root / "bundles"
            output = root / "output"
            bundles.mkdir()
            output.mkdir()

            bundle = self.create_bundle(
                bundles,
                "reference-a",
                payload_marker=1,
            )

            manifest_path = (
                bundle / MANIFEST_FILENAME
            )
            manifest = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )
            manifest["report_bundle_id"] = (
                "bundle-invalid"
            )
            self.write_json(
                manifest_path,
                manifest,
            )

            self.assert_service_error(
                (
                    "VELUNE_PRIVATE_BASELINE_SERVICE_"
                    "REPORT_BUNDLE_ID_INVALID"
                ),
                lambda: self.create(
                    output,
                    [
                        self.reference(
                            bundle,
                            software_version="v1",
                        ),
                    ],
                ),
            )

            self.assertEqual(
                list(output.iterdir()),
                [],
            )

    def test_tampered_artifact_blocks_install(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundles = root / "bundles"
            output = root / "output"
            bundles.mkdir()
            output.mkdir()

            bundle = self.create_bundle(
                bundles,
                "reference-a",
                payload_marker=1,
            )

            topic_path = (
                bundle / TOPIC_PROFILE_FILENAME
            )
            original_size = (
                topic_path.stat().st_size
            )
            topic_path.write_bytes(
                b"x" * original_size
            )

            with self.assertRaises(
                BundleComparisonLoadError
            ):
                self.create(
                    output,
                    [
                        self.reference(
                            bundle,
                            software_version="v1",
                        ),
                    ],
                )

            self.assertEqual(
                list(output.iterdir()),
                [],
            )

    def test_does_not_mutate_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundles = root / "bundles"
            output = root / "output"
            bundles.mkdir()
            output.mkdir()

            bundle = self.create_bundle(
                bundles,
                "reference-a",
                payload_marker=1,
            )

            policy = self.dimension_policy()
            references = [
                self.reference(
                    bundle,
                    software_version="v1",
                ),
            ]

            original_policy = copy.deepcopy(
                policy
            )
            original_references = copy.deepcopy(
                references
            )

            with patch(
                "velune_trace.private_baseline."
                "contract.secrets.token_hex",
                return_value="9" * 32,
            ):
                create_private_baseline(
                    output,
                    display_name=(
                        "Private Baseline A"
                    ),
                    created_at=(
                        "2026-07-20T10:00:00"
                        "+09:00"
                    ),
                    created_by="engineer-a",
                    dimension_policy=policy,
                    references=references,
                )

            self.assertEqual(
                policy,
                original_policy,
            )
            self.assertEqual(
                references,
                original_references,
            )

    def test_strict_private_input_fails_before_load(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)

            references = [
                {
                    "bundle_dir": "/missing/bundle",
                    "dimensions": {
                        "robot_model": "model-a",
                        "software_version": "v1",
                    },
                    "selection": {
                        "selected_by": (
                            " engineer-a "
                        ),
                        "selected_at": (
                            "2026-07-20T09:00:00"
                            "+09:00"
                        ),
                    },
                },
            ]

            with patch.object(
                service_module,
                "load_comparison_bundle",
            ) as loader:
                with self.assertRaises(
                    PrivateBaselineContractError
                ):
                    self.create(
                        output,
                        references,
                    )

            loader.assert_not_called()

    def test_manifest_change_after_load_blocks_install(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundles = root / "bundles"
            output = root / "output"
            bundles.mkdir()
            output.mkdir()

            bundle = self.create_bundle(
                bundles,
                "reference-a",
                payload_marker=1,
            )

            original_loader = (
                service_module
                .load_comparison_bundle
            )

            def load_then_change(path):
                loaded = original_loader(path)
                manifest_path = (
                    loaded.bundle_dir
                    / MANIFEST_FILENAME
                )
                manifest = json.loads(
                    manifest_path.read_text(
                        encoding="utf-8"
                    )
                )
                manifest["generated_at"] = (
                    "2026-07-20T11:00:00+09:00"
                )
                self.write_json(
                    manifest_path,
                    manifest,
                )
                return loaded

            with patch.object(
                service_module,
                "load_comparison_bundle",
                side_effect=load_then_change,
            ):
                self.assert_service_error(
                    (
                        "VELUNE_PRIVATE_BASELINE_SERVICE_"
                        "MANIFEST_CHANGED_DURING_"
                        "VERIFICATION"
                    ),
                    lambda: self.create(
                        output,
                        [
                            self.reference(
                                bundle,
                                software_version="v1",
                            ),
                        ],
                    ),
                )

            self.assertEqual(
                list(output.iterdir()),
                [],
            )


if __name__ == "__main__":
    unittest.main()
