import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from velune_trace.comparison.compatibility import (
    BLOCKING_FIELD_PATHS,
    COMPATIBLE_STATUS,
    INCOMPATIBLE_STATUS,
    WARNING_FIELD_PATHS,
    evaluate_bundle_compatibility,
)
from velune_trace.comparison.loader import (
    EVIDENCE_WINDOWS_FILENAME,
    MANIFEST_FILENAME,
    TOPIC_PROFILE_FILENAME,
    load_comparison_bundle,
)


class BundleComparisonCompatibilityTests(
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

    def base_manifest(
        self,
        artifacts,
    ) -> dict:
        return {
            "schema_name": "velune.report_manifest",
            "schema_version": "0.1.0",
            "bundle_schema": {
                "name": "velune.evidence_report_bundle",
                "version": "0.1.0",
            },
            "report_bundle_id": (
                "vrb_sha256_"
                + ("0" * 64)
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
                "file_name": "sample.mcap",
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
                "total_messages_observed": 100,
            },
            "artifacts": artifacts,
        }

    def create_bundle(
        self,
        root: Path,
        name: str,
        *,
        manifest_transform=None,
    ) -> Path:
        bundle_dir = root / name
        bundle_dir.mkdir()

        topic_path = (
            bundle_dir / TOPIC_PROFILE_FILENAME
        )
        windows_path = (
            bundle_dir / EVIDENCE_WINDOWS_FILENAME
        )

        self.write_json(
            topic_path,
            {
                "/imu": {
                    "count": 100,
                    "avg_gap_ns": 10_000_000,
                },
            },
        )
        self.write_json(
            windows_path,
            {
                "/imu": [
                    {
                        "topic": "/imu",
                        "window": 1,
                        "count": 50,
                    },
                ],
            },
        )

        manifest = self.base_manifest([
            self.artifact_record(windows_path),
            self.artifact_record(topic_path),
        ])

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
        reference_transform=None,
        target_transform=None,
    ):
        temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        root = Path(temporary_directory.name)

        reference_dir = self.create_bundle(
            root,
            "reference",
            manifest_transform=reference_transform,
        )
        target_dir = self.create_bundle(
            root,
            "target",
            manifest_transform=target_transform,
        )

        reference = load_comparison_bundle(
            reference_dir
        )
        target = load_comparison_bundle(target_dir)

        return temporary_directory, reference, target

    def set_nested(
        self,
        document,
        field_path,
        value,
    ):
        segments = field_path.split(".")
        current = document

        for segment in segments[:-1]:
            current = current[segment]

        current[segments[-1]] = value

    def remove_nested(
        self,
        document,
        field_path,
    ):
        segments = field_path.split(".")
        current = document

        for segment in segments[:-1]:
            current = current[segment]

        del current[segments[-1]]

    def alternate_value(
        self,
        field_path,
    ):
        values = {
            "schema_name": "velune.other_manifest",
            "schema_version": "9.9.9",
            "bundle_schema.name": (
                "velune.other_bundle"
            ),
            "bundle_schema.version": "9.9.9",
            "engine.name": "other_engine",
            "extraction.semantics": (
                "other_observation_semantics"
            ),
            "extraction.mode": "other_mode",
            "extraction.timestamp_unit": (
                "microseconds_int"
            ),
            "extraction.window_sec": 2.0,
            "extraction.allowed_lateness_sec": 3.0,
            "extraction.top": 10,
        }

        return values[field_path]

    def test_identical_contracts_are_compatible(self):
        temporary, reference, target = (
            self.load_pair()
        )

        try:
            result = evaluate_bundle_compatibility(
                reference,
                target,
            )

            self.assertTrue(result.is_compatible)
            self.assertEqual(
                result.status,
                COMPATIBLE_STATUS,
            )
            self.assertEqual(
                result.blocking_reasons,
                (),
            )
            self.assertEqual(result.warnings, ())
            self.assertEqual(
                len(result.required_field_checks),
                len(BLOCKING_FIELD_PATHS),
            )
            self.assertTrue(
                all(
                    check["match"]
                    for check in (
                        result.required_field_checks
                    )
                )
            )
        finally:
            temporary.cleanup()

    def test_each_blocking_field_mismatch_rejects(self):
        for field_path in BLOCKING_FIELD_PATHS:
            with self.subTest(field=field_path):
                def change_target(manifest):
                    self.set_nested(
                        manifest,
                        field_path,
                        self.alternate_value(
                            field_path
                        ),
                    )

                temporary, reference, target = (
                    self.load_pair(
                        target_transform=change_target,
                    )
                )

                try:
                    result = (
                        evaluate_bundle_compatibility(
                            reference,
                            target,
                        )
                    )

                    self.assertFalse(
                        result.is_compatible
                    )
                    self.assertEqual(
                        result.status,
                        INCOMPATIBLE_STATUS,
                    )
                    self.assertEqual(
                        [
                            reason["field"]
                            for reason in (
                                result.blocking_reasons
                            )
                        ],
                        [field_path],
                    )
                    reason = (
                        result.blocking_reasons[0]
                    )
                    self.assertEqual(
                        reason["code"],
                        (
                            "VELUNE_COMPARISON_"
                            "REQUIRED_FIELD_MISMATCH"
                        ),
                    )
                    self.assertIn(
                        field_path,
                        reason["message"],
                    )
                finally:
                    temporary.cleanup()

    def test_missing_blocking_field_rejects(self):
        field_path = "extraction.timestamp_unit"

        def remove_target_field(manifest):
            self.remove_nested(
                manifest,
                field_path,
            )

        temporary, reference, target = (
            self.load_pair(
                target_transform=remove_target_field,
            )
        )

        try:
            result = evaluate_bundle_compatibility(
                reference,
                target,
            )
            reason = result.blocking_reasons[0]

            self.assertEqual(
                result.status,
                INCOMPATIBLE_STATUS,
            )
            self.assertEqual(
                reason["code"],
                (
                    "VELUNE_COMPARISON_"
                    "REQUIRED_FIELD_MISSING"
                ),
            )
            self.assertEqual(
                reason["field"],
                field_path,
            )
            self.assertIn(
                field_path,
                reason["message"],
            )
        finally:
            temporary.cleanup()

    def test_invalid_blocking_field_rejects(self):
        def change_target(manifest):
            manifest["extraction"]["top"] = True

        temporary, reference, target = (
            self.load_pair(
                target_transform=change_target,
            )
        )

        try:
            result = evaluate_bundle_compatibility(
                reference,
                target,
            )
            reason = result.blocking_reasons[0]

            self.assertEqual(
                reason["code"],
                (
                    "VELUNE_COMPARISON_"
                    "REQUIRED_FIELD_INVALID"
                ),
            )
            self.assertEqual(
                reason["field"],
                "extraction.top",
            )
            self.assertFalse(
                reason["target_valid"]
            )
            self.assertIn(
                "extraction.top",
                reason["message"],
            )
        finally:
            temporary.cleanup()

    def test_numeric_contract_difference_is_exact(self):
        def change_target(manifest):
            manifest["extraction"][
                "allowed_lateness_sec"
            ] = 2.000000000001

        temporary, reference, target = (
            self.load_pair(
                target_transform=change_target,
            )
        )

        try:
            result = evaluate_bundle_compatibility(
                reference,
                target,
            )

            self.assertFalse(result.is_compatible)
            self.assertEqual(
                result.blocking_reasons[0]["field"],
                "extraction.allowed_lateness_sec",
            )
        finally:
            temporary.cleanup()

    def test_equivalent_int_and_float_are_compatible(
        self,
    ):
        def change_target(manifest):
            manifest["extraction"]["window_sec"] = 1

        temporary, reference, target = (
            self.load_pair(
                target_transform=change_target,
            )
        )

        try:
            result = evaluate_bundle_compatibility(
                reference,
                target,
            )

            self.assertTrue(result.is_compatible)
        finally:
            temporary.cleanup()

    def test_engine_version_difference_is_warning(self):
        def change_target(manifest):
            manifest["engine"]["version"] = "0.4.0"

        temporary, reference, target = (
            self.load_pair(
                target_transform=change_target,
            )
        )

        try:
            result = evaluate_bundle_compatibility(
                reference,
                target,
            )
            warning = result.warnings[0]

            self.assertTrue(result.is_compatible)
            self.assertEqual(len(result.warnings), 1)
            self.assertEqual(
                warning["code"],
                (
                    "VELUNE_COMPARISON_"
                    "ENGINE_VERSION_DIFFERENCE"
                ),
            )
            self.assertEqual(
                warning["field"],
                "engine.version",
            )
            self.assertEqual(
                warning["reason"],
                "value_difference",
            )
            self.assertEqual(
                warning["reference"],
                "0.3.6",
            )
            self.assertEqual(
                warning["target"],
                "0.4.0",
            )
            self.assertTrue(
                warning["reference_present"]
            )
            self.assertTrue(
                warning["target_present"]
            )
            self.assertTrue(
                warning["reference_valid"]
            )
            self.assertTrue(
                warning["target_valid"]
            )
            self.assertIn(
                "engine.version",
                warning["message"],
            )
        finally:
            temporary.cleanup()

    def test_source_format_difference_is_warning(self):
        def change_target(manifest):
            manifest["source"]["format"] = "rosbag2"

        temporary, reference, target = (
            self.load_pair(
                target_transform=change_target,
            )
        )

        try:
            result = evaluate_bundle_compatibility(
                reference,
                target,
            )
            warning = result.warnings[0]

            self.assertTrue(result.is_compatible)
            self.assertEqual(
                warning["code"],
                (
                    "VELUNE_COMPARISON_"
                    "SOURCE_FORMAT_DIFFERENCE"
                ),
            )
            self.assertEqual(
                warning["field"],
                "source.format",
            )
            self.assertEqual(
                warning["reference"],
                "mcap",
            )
            self.assertEqual(
                warning["target"],
                "rosbag2",
            )
        finally:
            temporary.cleanup()

    def test_one_sided_warning_field_missing_warns(
        self,
    ):
        def change_target(manifest):
            del manifest["engine"]["version"]

        temporary, reference, target = (
            self.load_pair(
                target_transform=change_target,
            )
        )

        try:
            result = evaluate_bundle_compatibility(
                reference,
                target,
            )
            warning = result.warnings[0]

            self.assertTrue(result.is_compatible)
            self.assertEqual(
                warning["code"],
                (
                    "VELUNE_COMPARISON_"
                    "WARNING_FIELD_UNAVAILABLE"
                ),
            )
            self.assertEqual(
                warning["field"],
                "engine.version",
            )
            self.assertEqual(
                warning["reason"],
                "missing_or_invalid",
            )
            self.assertTrue(
                warning["reference_present"]
            )
            self.assertFalse(
                warning["target_present"]
            )
            self.assertTrue(
                warning["reference_valid"]
            )
            self.assertFalse(
                warning["target_valid"]
            )
            self.assertEqual(
                warning["reference"],
                "0.3.6",
            )
            self.assertIsNone(
                warning["target"]
            )
        finally:
            temporary.cleanup()

    def test_both_warning_fields_missing_warns(self):
        def remove_reference(manifest):
            del manifest["engine"]["version"]

        def remove_target(manifest):
            del manifest["engine"]["version"]

        temporary, reference, target = (
            self.load_pair(
                reference_transform=remove_reference,
                target_transform=remove_target,
            )
        )

        try:
            result = evaluate_bundle_compatibility(
                reference,
                target,
            )
            warning = result.warnings[0]

            self.assertTrue(result.is_compatible)
            self.assertEqual(
                warning["field"],
                "engine.version",
            )
            self.assertFalse(
                warning["reference_present"]
            )
            self.assertFalse(
                warning["target_present"]
            )
            self.assertFalse(
                warning["reference_valid"]
            )
            self.assertFalse(
                warning["target_valid"]
            )
        finally:
            temporary.cleanup()

    def test_allowed_provenance_differences_do_not_block(
        self,
    ):
        def change_target(manifest):
            manifest["generated_at"] = (
                "2026-07-17T00:00:00+00:00"
            )
            manifest["report_bundle_id"] = (
                "vrb_sha256_"
                + ("1" * 64)
            )
            manifest["source"]["file_name"] = (
                "target.mcap"
            )
            manifest["source"]["file_size_bytes"] = (
                999999
            )
            manifest["extraction"][
                "total_messages_observed"
            ] = 999

        temporary, reference, target = (
            self.load_pair(
                target_transform=change_target,
            )
        )

        try:
            result = evaluate_bundle_compatibility(
                reference,
                target,
            )

            self.assertTrue(result.is_compatible)
            self.assertEqual(
                result.blocking_reasons,
                (),
            )
        finally:
            temporary.cleanup()

    def test_blocking_checks_use_contract_order(self):
        def change_target(manifest):
            manifest["schema_name"] = "different"
            manifest["extraction"]["top"] = 10
            manifest["engine"]["name"] = "other"

        temporary, reference, target = (
            self.load_pair(
                target_transform=change_target,
            )
        )

        try:
            result = evaluate_bundle_compatibility(
                reference,
                target,
            )

            expected = [
                field
                for field in BLOCKING_FIELD_PATHS
                if field in {
                    "schema_name",
                    "engine.name",
                    "extraction.top",
                }
            ]

            self.assertEqual(
                [
                    reason["field"]
                    for reason in (
                        result.blocking_reasons
                    )
                ],
                expected,
            )
        finally:
            temporary.cleanup()

    def test_warning_order_is_deterministic(self):
        def change_target(manifest):
            manifest["engine"]["version"] = "0.4.0"
            manifest["source"]["format"] = "rosbag2"

        temporary, reference, target = (
            self.load_pair(
                target_transform=change_target,
            )
        )

        try:
            result = evaluate_bundle_compatibility(
                reference,
                target,
            )

            self.assertEqual(
                [
                    warning["field"]
                    for warning in result.warnings
                ],
                list(WARNING_FIELD_PATHS),
            )
        finally:
            temporary.cleanup()

    def test_as_dict_returns_json_ready_structure(self):
        temporary, reference, target = (
            self.load_pair()
        )

        try:
            result = evaluate_bundle_compatibility(
                reference,
                target,
            )
            rendered = result.as_dict()

            self.assertEqual(
                rendered["status"],
                COMPATIBLE_STATUS,
            )
            self.assertIsInstance(
                rendered["required_field_checks"],
                list,
            )
            self.assertIsInstance(
                rendered["warnings"],
                list,
            )
            self.assertIsInstance(
                rendered["blocking_reasons"],
                list,
            )

            json.dumps(
                rendered,
                allow_nan=False,
                sort_keys=True,
            )
        finally:
            temporary.cleanup()

    def test_rejects_invalid_reference_type(self):
        temporary, _, target = self.load_pair()

        try:
            with self.assertRaises(TypeError):
                evaluate_bundle_compatibility(
                    {},
                    target,
                )
        finally:
            temporary.cleanup()

    def test_rejects_invalid_target_type(self):
        temporary, reference, _ = (
            self.load_pair()
        )

        try:
            with self.assertRaises(TypeError):
                evaluate_bundle_compatibility(
                    reference,
                    {},
                )
        finally:
            temporary.cleanup()


if __name__ == "__main__":
    unittest.main()
