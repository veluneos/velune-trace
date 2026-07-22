import tempfile
import unittest
from pathlib import Path

from velune_trace.adapters.mcap_reader import (
    VeluneFileNotFoundError,
    VeluneInvalidMcapError,
    VeluneMcapReader,
)


class McapTerminalMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repository_root = Path(__file__).resolve().parents[1]
        cls.sample_path = (
            cls.repository_root
            / "examples"
            / "sample.mcap"
        )

    def test_reads_recorded_terminal_metadata(self):
        metadata = VeluneMcapReader(
            self.sample_path
        ).inspect_terminal_metadata()

        self.assertEqual(metadata.summary_start, 15_193)
        self.assertEqual(
            metadata.summary_offset_start,
            15_610,
        )
        self.assertEqual(
            metadata.summary_crc,
            2_108_641_127,
        )
        self.assertEqual(metadata.data_section_crc, 0)

        self.assertTrue(
            metadata.summary_crc_recorded
        )
        self.assertFalse(
            metadata.data_section_crc_recorded
        )

    def test_rejects_missing_file(self):
        missing_path = (
            self.repository_root
            / "examples"
            / "missing-terminal-test.mcap"
        )

        with self.assertRaises(
            VeluneFileNotFoundError
        ):
            VeluneMcapReader(
                missing_path
            ).inspect_terminal_metadata()

    def test_rejects_invalid_trailing_magic(self):
        source_bytes = self.sample_path.read_bytes()

        with tempfile.TemporaryDirectory() as directory:
            corrupt_path = (
                Path(directory) / "corrupt.mcap"
            )
            corrupt_path.write_bytes(
                source_bytes[:-8] + b"NOT_MCAP"
            )

            with self.assertRaises(
                VeluneInvalidMcapError
            ) as context:
                VeluneMcapReader(
                    corrupt_path
                ).inspect_terminal_metadata()

        self.assertIn(
            "trailing MCAP0 magic",
            str(context.exception),
        )


if __name__ == "__main__":
    unittest.main()
