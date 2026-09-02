import unittest

from velune_trace.reporting.identity import (
    build_report_bundle_id,
)


EXPECTED_BUNDLE_ID = (
    "vrb_sha256_"
    "136aae2324f323a0990a95dc426eea8d"
    "5e6f4d51249b713292d7c19687253731"
)


class ReportBundleIdentityGoldenVectorTests(unittest.TestCase):
    def test_public_identity_algorithm_golden_vector(self):
        bundle_id = build_report_bundle_id(
            bundle_schema_name=(
                "velune.evidence_report_bundle"
            ),
            bundle_schema_version="0.1.0",
            engine_name="velune_trace",
            engine_version="0.3.6",
            extraction={
                "mode": "bounded_streaming_aggregation",
                "window_ns": 1_000_000_000,
            },
            artifacts=[
                {
                    "path": "topic_profile.json",
                    "role": "core_machine_readable",
                    "media_type": "application/json",
                    "size_bytes": 3,
                    "hash": {
                        "algorithm": "sha256",
                        "value": (
                            "ba7816bf8f01cfea414140de5dae2223"
                            "b00361a396177a9cb410ff61f20015ad"
                        ),
                    },
                    "source_of_truth": True,
                }
            ],
        )

        self.assertEqual(
            bundle_id,
            EXPECTED_BUNDLE_ID,
        )


if __name__ == "__main__":
    unittest.main()
