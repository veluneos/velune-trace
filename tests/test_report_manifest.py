import math
import unittest

from velune_trace import __version__
from velune_trace.reporting.manifest import build_private_report_manifest


class PrivateReportManifestTests(unittest.TestCase):
    def build_manifest(self, **overrides):
        values = {
            "report_bundle_id": "vrb_test_001",
            "generated_at": "2026-07-14T00:00:00+00:00",
            "source": {
                "file_info": {
                    "name": "sample.mcap",
                    "size_bytes": 1234,
                },
                "labels": ["test", "local"],
            },
            "extraction": {
                "mode": "bounded_streaming_aggregation",
                "window_sec": 1.0,
            },
            "artifacts": [
                {
                    "path": "topic_profile.json",
                    "role": "machine_readable_source",
                    "metadata": {
                        "required": True,
                    },
                }
            ],
        }
        values.update(overrides)
        return build_private_report_manifest(**values)

    def test_builds_versioned_private_manifest(self):
        manifest = self.build_manifest()

        self.assertEqual(
            manifest["schema_name"],
            "velune.report_manifest",
        )
        self.assertEqual(manifest["schema_version"], "0.1.0")
        self.assertEqual(manifest["schema_status"], "draft")
        self.assertEqual(
            manifest["visibility"],
            "private_local_only",
        )
        self.assertEqual(
            manifest["engine"]["version"],
            __version__,
        )
        self.assertEqual(
            manifest["source_provenance_policy"][
                "fingerprint_policy"
            ],
            "private_only_if_present",
        )
        self.assertTrue(
            manifest["document_policy"][
                "machine_readable_json_source_of_truth"
            ]
        )
        self.assertFalse(
            manifest["judgment_boundary"][
                "root_cause_conclusion"
            ]
        )

    def test_accepts_and_normalizes_z_timestamp(self):
        manifest = self.build_manifest(
            generated_at="2026-07-14T00:00:00Z",
        )

        self.assertEqual(
            manifest["generated_at"],
            "2026-07-14T00:00:00+00:00",
        )

    def test_rejects_invalid_or_naive_timestamp(self):
        invalid_values = [
            "any_garbage_string",
            "2026-07-14",
            "2026-07-14T00:00:00",
        ]

        for value in invalid_values:
            with self.subTest(generated_at=value):
                with self.assertRaises(ValueError):
                    self.build_manifest(generated_at=value)

    def test_rejects_empty_bundle_id(self):
        with self.assertRaises(ValueError):
            self.build_manifest(report_bundle_id=" ")

    def test_deep_copies_nested_input_records(self):
        source = {
            "file_info": {
                "name": "sample.mcap",
            },
            "labels": ["test"],
        }
        artifact = {
            "path": "evidence_windows.json",
            "metadata": {
                "required": True,
            },
        }

        manifest = self.build_manifest(
            source=source,
            artifacts=[artifact],
        )

        source["file_info"]["name"] = "changed.mcap"
        source["labels"].append("changed")
        artifact["metadata"]["required"] = False

        self.assertEqual(
            manifest["source"]["file_info"]["name"],
            "sample.mcap",
        )
        self.assertEqual(
            manifest["source"]["labels"],
            ["test"],
        )
        self.assertTrue(
            manifest["artifacts"][0]["metadata"]["required"]
        )

    def test_rejects_non_json_values(self):
        with self.assertRaises(ValueError):
            self.build_manifest(
                source={"unsupported": {1, 2, 3}},
            )

        with self.assertRaises(ValueError):
            self.build_manifest(
                extraction={"invalid_number": math.nan},
            )


if __name__ == "__main__":
    unittest.main()
