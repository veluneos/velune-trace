import copy
import unittest

from velune_trace.reporting.identity import (
    BUNDLE_ID_PREFIX,
    build_report_bundle_id,
)


SHA256_ABC = (
    "ba7816bf8f01cfea414140de5dae2223"
    "b00361a396177a9cb410ff61f20015ad"
)

SHA256_EMPTY = (
    "e3b0c44298fc1c149afbf4c8996fb924"
    "27ae41e4649b934ca495991b7852b855"
)


class ReportBundleIdentityTests(unittest.TestCase):
    def artifact(
        self,
        *,
        path="topic_profile.json",
        hash_value=SHA256_ABC,
    ):
        return {
            "path": path,
            "role": "core_machine_readable",
            "media_type": "application/json",
            "size_bytes": 3,
            "hash": {
                "algorithm": "sha256",
                "value": hash_value,
            },
            "source_of_truth": True,
        }

    def build_id(self, **overrides):
        values = {
            "bundle_schema_name": (
                "velune.evidence_report_bundle"
            ),
            "bundle_schema_version": "0.1.0",
            "engine_name": "velune_trace",
            "engine_version": "0.3.6",
            "extraction": {
                "mode": "bounded_streaming_aggregation",
                "window_ns": 1_000_000_000,
            },
            "artifacts": [self.artifact()],
        }
        values.update(overrides)
        return build_report_bundle_id(**values)

    def test_builds_full_sha256_bundle_id(self):
        bundle_id = self.build_id()

        self.assertTrue(
            bundle_id.startswith(BUNDLE_ID_PREFIX)
        )
        self.assertEqual(
            len(bundle_id),
            len(BUNDLE_ID_PREFIX) + 64,
        )

    def test_is_deterministic_for_equal_content(self):
        first = self.build_id()
        second = self.build_id()

        self.assertEqual(first, second)

    def test_artifact_input_order_does_not_change_id(self):
        first_artifact = self.artifact(
            path="topic_profile.json",
            hash_value=SHA256_ABC,
        )
        second_artifact = self.artifact(
            path="evidence_windows.json",
            hash_value=SHA256_EMPTY,
        )

        first = self.build_id(
            artifacts=[
                first_artifact,
                second_artifact,
            ]
        )
        second = self.build_id(
            artifacts=[
                second_artifact,
                first_artifact,
            ]
        )

        self.assertEqual(first, second)

    def test_artifact_hash_change_changes_id(self):
        first = self.build_id(
            artifacts=[
                self.artifact(
                    hash_value=SHA256_ABC,
                )
            ]
        )
        second = self.build_id(
            artifacts=[
                self.artifact(
                    hash_value=SHA256_EMPTY,
                )
            ]
        )

        self.assertNotEqual(first, second)

    def test_extraction_change_changes_id(self):
        first = self.build_id(
            extraction={
                "mode": "bounded_streaming_aggregation",
                "window_ns": 1_000_000_000,
            }
        )
        second = self.build_id(
            extraction={
                "mode": "bounded_streaming_aggregation",
                "window_ns": 2_000_000_000,
            }
        )

        self.assertNotEqual(first, second)

    def test_unicode_nfc_equivalence(self):
        composed = self.artifact(
            path="caf\u00e9.json",
        )
        decomposed = self.artifact(
            path="cafe\u0301.json",
        )

        composed_id = self.build_id(
            artifacts=[composed]
        )
        decomposed_id = self.build_id(
            artifacts=[decomposed]
        )

        self.assertEqual(composed_id, decomposed_id)

    def test_normalizes_hash_case(self):
        lower = self.build_id(
            artifacts=[
                self.artifact(
                    hash_value=SHA256_ABC,
                )
            ]
        )

        upper_artifact = self.artifact(
            hash_value=SHA256_ABC.upper(),
        )
        upper_artifact["hash"]["algorithm"] = "SHA256"

        upper = self.build_id(
            artifacts=[upper_artifact]
        )

        self.assertEqual(lower, upper)

    def test_does_not_mutate_inputs(self):
        extraction = {
            "mode": "bounded_streaming_aggregation",
            "nested": {
                "window_ns": 1_000_000_000,
            },
        }
        artifacts = [
            self.artifact(),
        ]

        original_extraction = copy.deepcopy(extraction)
        original_artifacts = copy.deepcopy(artifacts)

        self.build_id(
            extraction=extraction,
            artifacts=artifacts,
        )

        self.assertEqual(
            extraction,
            original_extraction,
        )
        self.assertEqual(
            artifacts,
            original_artifacts,
        )

    def test_rejects_empty_artifact_list(self):
        with self.assertRaises(ValueError):
            self.build_id(artifacts=[])

    def test_rejects_missing_artifact_path(self):
        artifact = self.artifact()
        del artifact["path"]

        with self.assertRaises(ValueError):
            self.build_id(artifacts=[artifact])

    def test_rejects_none_artifact_path(self):
        artifact = self.artifact()
        artifact["path"] = None

        with self.assertRaises(TypeError):
            self.build_id(artifacts=[artifact])

    def test_rejects_duplicate_artifact_path(self):
        artifact = self.artifact()

        with self.assertRaises(ValueError):
            self.build_id(
                artifacts=[
                    artifact,
                    copy.deepcopy(artifact),
                ]
            )

    def test_rejects_noncanonical_paths(self):
        invalid_paths = [
            ".",
            "./topic_profile.json",
            "reports//topic_profile.json",
            "reports/../topic_profile.json",
            "/topic_profile.json",
            "reports\\topic_profile.json",
            " topic_profile.json",
            "topic_profile.json ",
            "topic\nprofile.json",
        ]

        for invalid_path in invalid_paths:
            with self.subTest(path=invalid_path):
                with self.assertRaises(
                    (TypeError, ValueError)
                ):
                    self.build_id(
                        artifacts=[
                            self.artifact(
                                path=invalid_path,
                            )
                        ]
                    )

    def test_rejects_missing_required_artifact_fields(self):
        required_fields = [
            "role",
            "media_type",
            "size_bytes",
            "hash",
            "source_of_truth",
        ]

        for field_name in required_fields:
            artifact = self.artifact()
            del artifact[field_name]

            with self.subTest(field=field_name):
                with self.assertRaises(ValueError):
                    self.build_id(
                        artifacts=[artifact]
                    )

    def test_rejects_invalid_size_bytes(self):
        invalid_values = [
            -1,
            1.5,
            True,
            "3",
        ]

        for invalid_value in invalid_values:
            artifact = self.artifact()
            artifact["size_bytes"] = invalid_value

            with self.subTest(value=invalid_value):
                with self.assertRaises(ValueError):
                    self.build_id(
                        artifacts=[artifact]
                    )

    def test_rejects_invalid_hash_digest(self):
        invalid_values = [
            "",
            "abc",
            "g" * 64,
            "0" * 63,
            "0" * 65,
        ]

        for invalid_value in invalid_values:
            artifact = self.artifact()
            artifact["hash"]["value"] = invalid_value

            with self.subTest(value=invalid_value):
                with self.assertRaises(ValueError):
                    self.build_id(
                        artifacts=[artifact]
                    )

    def test_rejects_unsupported_hash_algorithm(self):
        artifact = self.artifact()
        artifact["hash"]["algorithm"] = "md5"
        artifact["hash"]["value"] = "0" * 32

        with self.assertRaises(ValueError):
            self.build_id(artifacts=[artifact])

    def test_rejects_floating_point_identity_values(self):
        with self.assertRaises(ValueError):
            self.build_id(
                extraction={
                    "window_sec": 1.0,
                }
            )

    def test_rejects_unicode_normalized_key_collision(self):
        extraction = {
            "caf\u00e9": 1,
            "cafe\u0301": 2,
        }

        with self.assertRaises(ValueError):
            self.build_id(extraction=extraction)


if __name__ == "__main__":
    unittest.main()
