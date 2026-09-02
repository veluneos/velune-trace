import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from mcap.reader import make_reader

from tools.build_mcap_benchmark_corpus import (
    build_corpus,
)
from tools.create_sample_mcap import (
    create_sample_mcap,
)
from velune_trace.adapters.mcap_reader import (
    VeluneMcapReader,
)


class McapBenchmarkCorpusBuilderTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.temporary_directory = (
            tempfile.TemporaryDirectory()
        )

        cls.sample_path = create_sample_mcap(
            Path(cls.temporary_directory.name)
            / "sample.mcap"
        )

        cls.sample_inspection = VeluneMcapReader(
            cls.sample_path
        ).inspect()

    @classmethod
    def tearDownClass(cls):
        cls.temporary_directory.cleanup()

    def test_builds_replicated_real_payload_corpus(
        self,
    ):
        target_size_bytes = (
            self.sample_path.stat().st_size * 2
        )

        with tempfile.TemporaryDirectory() as directory:
            output_path = (
                Path(directory)
                / "benchmark-corpus.mcap"
            )

            progress_output = io.StringIO()

            with redirect_stdout(progress_output):
                result = build_corpus(
                    source_paths=[
                        self.sample_path
                    ],
                    output_path=output_path,
                    target_size_bytes=(
                        target_size_bytes
                    ),
                    segment_gap_ns=1_000_000_000,
                    overwrite=False,
                )

            inspection = VeluneMcapReader(
                output_path
            ).inspect()

            with output_path.open("rb") as stream:
                metadata_records = list(
                    make_reader(
                        stream
                    ).iter_metadata()
                )

            metadata_by_name = {
                record.name: dict(
                    record.metadata
                )
                for record in metadata_records
            }

            corpus_metadata = metadata_by_name[
                "velune-benchmark-corpus"
            ]
            build_summary = metadata_by_name[
                (
                    "velune-benchmark-corpus-"
                    "build-summary"
                )
            ]

            segment_count = int(
                build_summary["segment_count"]
            )
            expected_messages = (
                self.sample_inspection.message_count
                * segment_count
            )

            self.assertGreaterEqual(
                inspection.file_size_bytes,
                target_size_bytes,
            )
            self.assertGreaterEqual(
                segment_count,
                2,
            )
            self.assertEqual(
                inspection.message_count,
                expected_messages,
            )
            self.assertEqual(
                result["total_messages"],
                expected_messages,
            )
            self.assertEqual(
                inspection.schema_count,
                self.sample_inspection.schema_count,
            )
            self.assertEqual(
                inspection.channel_count,
                self.sample_inspection.channel_count,
            )
            self.assertEqual(
                len(metadata_records),
                segment_count + 2,
            )
            self.assertEqual(
                corpus_metadata["corpus_kind"],
                "replicated_real_payload",
            )
            self.assertEqual(
                corpus_metadata[
                    "unique_continuous_drive"
                ],
                "false",
            )
            self.assertEqual(
                build_summary[
                    (
                        "logical_segment_ranges_"
                        "non_overlapping"
                    )
                ],
                "true",
            )
            self.assertEqual(
                build_summary[
                    "physical_record_order_preserved"
                ],
                "true",
            )


if __name__ == "__main__":
    unittest.main()
