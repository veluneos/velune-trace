import unittest
from dataclasses import replace

from velune_trace.adapters.mcap_reader import (
    VeluneMcapReader,
)
from velune_trace.reporting.source_structural_digest import (
    build_mcap_structural_digest,
)


class SourceStructuralDigestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reader = VeluneMcapReader(
            "examples/sample.mcap"
        )
        cls.inspection = reader.inspect()
        cls.terminal = (
            reader.inspect_terminal_metadata()
        )

    def build_digest(
        self,
        *,
        inspection=None,
        terminal=None,
    ):
        return build_mcap_structural_digest(
            inspect_result=(
                inspection
                if inspection is not None
                else self.inspection
            ),
            terminal_metadata=(
                terminal
                if terminal is not None
                else self.terminal
            ),
        )

    def test_sample_digest_contract(self):
        result = self.build_digest()

        self.assertEqual(
            result["schema_name"],
            "velune.mcap_structural_digest",
        )
        self.assertEqual(
            result["schema_version"],
            "0.1.0",
        )
        self.assertEqual(
            result["kind"],
            "mcap_structural_metadata_digest",
        )
        self.assertEqual(
            result["status"],
            "ok",
        )
        self.assertEqual(
            result["warnings"],
            [],
        )
        self.assertEqual(
            result["value"],
            (
                "mcap_struct_sha256_"
                "c28fed354d92694d882133dd19cadd88"
                "c8784696ca7756b0c2e6231288de5853"
            ),
        )

        self.assertFalse(
            result["coverage"][
                "full_source_bytes_hashed"
            ]
        )
        self.assertFalse(
            result["integrity_semantics"][
                "crc_validation_performed"
            ]
        )
        self.assertFalse(
            result["integrity_semantics"][
                "payload_validation_performed"
            ]
        )
        self.assertFalse(
            result["integrity_semantics"][
                "source_authenticity_validation_performed"
            ]
        )

    def test_digest_is_independent_of_input_order(self):
        reordered = replace(
            self.inspection,
            topics=list(
                reversed(self.inspection.topics)
            ),
            chunks=list(
                reversed(self.inspection.chunks)
            ),
        )

        original = self.build_digest()
        reordered_result = self.build_digest(
            inspection=reordered
        )

        self.assertEqual(
            original,
            reordered_result,
        )

    def test_bool_is_rejected_for_integer_field(self):
        invalid = replace(
            self.inspection,
            message_count=True,
        )

        with self.assertRaisesRegex(
            TypeError,
            "message_count must be an int",
        ):
            self.build_digest(
                inspection=invalid
            )

    def test_summary_presence_mismatch_is_degraded(self):
        inconsistent_terminal = replace(
            self.terminal,
            summary_start=0,
        )

        result = self.build_digest(
            terminal=inconsistent_terminal
        )

        self.assertEqual(
            result["status"],
            "degraded",
        )
        self.assertIn(
            "MCAP_SUMMARY_PRESENCE_OFFSET_MISMATCH",
            result["warnings"],
        )
        self.assertFalse(
            result["structural_consistency"][
                "all_passed"
            ]
        )

    def test_out_of_bounds_summary_is_degraded(self):
        out_of_bounds_terminal = replace(
            self.terminal,
            summary_start=(
                self.inspection.file_size_bytes + 1
            ),
        )

        result = self.build_digest(
            terminal=out_of_bounds_terminal
        )

        self.assertEqual(
            result["status"],
            "degraded",
        )
        self.assertIn(
            "MCAP_SUMMARY_START_OUT_OF_FILE_BOUNDS",
            result["warnings"],
        )

    def test_float_is_rejected_in_topic_structure(self):
        topics = [
            dict(topic)
            for topic in self.inspection.topics
        ]
        topics[0]["channel_id"] = 1.5

        invalid = replace(
            self.inspection,
            topics=topics,
        )

        with self.assertRaisesRegex(
            TypeError,
            r"topics\[0\]\.channel_id must be an int",
        ):
            self.build_digest(
                inspection=invalid
            )


if __name__ == "__main__":
    unittest.main()
