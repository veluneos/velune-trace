import hashlib
import tempfile
import unittest
from pathlib import Path

from velune_trace.reporting.artifacts import (
    READ_CHUNK_SIZE,
    build_artifact_record,
)


class ReportArtifactTests(unittest.TestCase):
    def test_builds_relative_artifact_record(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)
            artifact_path = bundle_dir / "topic_profile.json"
            artifact_path.write_bytes(b"abc")

            record = build_artifact_record(
                bundle_dir=bundle_dir,
                artifact_path=artifact_path,
                role="core_machine_readable",
                media_type="application/json",
                source_of_truth=True,
            )

            self.assertEqual(record["path"], "topic_profile.json")
            self.assertEqual(
                record["role"],
                "core_machine_readable",
            )
            self.assertEqual(
                record["media_type"],
                "application/json",
            )
            self.assertEqual(record["size_bytes"], 3)
            self.assertEqual(
                record["hash"],
                {
                    "algorithm": "sha256",
                    "value": (
                        "ba7816bf8f01cfea414140de5dae2223"
                        "b00361a396177a9cb410ff61f20015ad"
                    ),
                },
            )
            self.assertTrue(record["source_of_truth"])

    def test_hashes_multiple_read_chunks_and_counts_bytes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)
            artifact_path = bundle_dir / "large.json"

            content = b"a" * (READ_CHUNK_SIZE + 17)
            artifact_path.write_bytes(content)

            record = build_artifact_record(
                bundle_dir=bundle_dir,
                artifact_path=artifact_path,
                role="core_machine_readable",
                media_type="application/json",
                source_of_truth=True,
            )

            self.assertEqual(
                record["size_bytes"],
                len(content),
            )
            self.assertEqual(
                record["hash"]["value"],
                hashlib.sha256(content).hexdigest(),
            )

    def test_supports_nested_bundle_path(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)
            schemas_dir = bundle_dir / "schemas"
            schemas_dir.mkdir()

            artifact_path = schemas_dir / "report.schema.json"
            artifact_path.write_text("{}", encoding="utf-8")

            record = build_artifact_record(
                bundle_dir=bundle_dir,
                artifact_path=artifact_path,
                role="schema",
                media_type="application/schema+json",
                source_of_truth=True,
            )

            self.assertEqual(
                record["path"],
                "schemas/report.schema.json",
            )

    def test_normalizes_hash_algorithm_name(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)
            artifact_path = bundle_dir / "summary.md"
            artifact_path.write_text("# Summary", encoding="utf-8")

            record = build_artifact_record(
                bundle_dir=bundle_dir,
                artifact_path=artifact_path,
                role="derived_human_readable",
                media_type="text/markdown",
                source_of_truth=False,
                hash_algorithm="SHA256",
            )

            self.assertEqual(
                record["hash"]["algorithm"],
                "sha256",
            )

    def test_rejects_unsupported_hash_algorithm(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)
            artifact_path = bundle_dir / "summary.md"
            artifact_path.write_text("# Summary", encoding="utf-8")

            with self.assertRaises(ValueError):
                build_artifact_record(
                    bundle_dir=bundle_dir,
                    artifact_path=artifact_path,
                    role="derived_human_readable",
                    media_type="text/markdown",
                    source_of_truth=False,
                    hash_algorithm="md5",
                )

    def test_rejects_file_outside_bundle(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            bundle_dir = root / "bundle"
            bundle_dir.mkdir()

            outside_path = root / "outside.json"
            outside_path.write_text("{}", encoding="utf-8")

            with self.assertRaises(ValueError):
                build_artifact_record(
                    bundle_dir=bundle_dir,
                    artifact_path=outside_path,
                    role="core_machine_readable",
                    media_type="application/json",
                    source_of_truth=True,
                )

    def test_rejects_artifact_symbolic_link(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)

            target_path = bundle_dir / "target.json"
            target_path.write_text("{}", encoding="utf-8")

            link_path = bundle_dir / "link.json"
            link_path.symlink_to(target_path.name)

            with self.assertRaises(ValueError):
                build_artifact_record(
                    bundle_dir=bundle_dir,
                    artifact_path=link_path,
                    role="core_machine_readable",
                    media_type="application/json",
                    source_of_truth=True,
                )

    def test_rejects_bundle_directory_symbolic_link(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            real_bundle_dir = root / "real_bundle"
            real_bundle_dir.mkdir()

            linked_bundle_dir = root / "linked_bundle"
            linked_bundle_dir.symlink_to(
                real_bundle_dir,
                target_is_directory=True,
            )

            artifact_path = real_bundle_dir / "summary.md"
            artifact_path.write_text("# Summary", encoding="utf-8")

            with self.assertRaises(ValueError):
                build_artifact_record(
                    bundle_dir=linked_bundle_dir,
                    artifact_path=artifact_path,
                    role="derived_human_readable",
                    media_type="text/markdown",
                    source_of_truth=False,
                )

    def test_rejects_missing_artifact(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)
            missing_path = bundle_dir / "missing.json"

            with self.assertRaises(ValueError):
                build_artifact_record(
                    bundle_dir=bundle_dir,
                    artifact_path=missing_path,
                    role="core_machine_readable",
                    media_type="application/json",
                    source_of_truth=True,
                )

    def test_rejects_non_boolean_source_of_truth(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)
            artifact_path = bundle_dir / "summary.md"
            artifact_path.write_text("# Summary", encoding="utf-8")

            with self.assertRaises(TypeError):
                build_artifact_record(
                    bundle_dir=bundle_dir,
                    artifact_path=artifact_path,
                    role="derived_human_readable",
                    media_type="text/markdown",
                    source_of_truth=1,
                )

    def test_rejects_empty_role_and_media_type(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            bundle_dir = Path(temporary_directory)
            artifact_path = bundle_dir / "summary.md"
            artifact_path.write_text("# Summary", encoding="utf-8")

            invalid_values = [
                {
                    "role": " ",
                    "media_type": "text/markdown",
                },
                {
                    "role": "derived_human_readable",
                    "media_type": " ",
                },
            ]

            for values in invalid_values:
                with self.subTest(**values):
                    with self.assertRaises(ValueError):
                        build_artifact_record(
                            bundle_dir=bundle_dir,
                            artifact_path=artifact_path,
                            role=values["role"],
                            media_type=values["media_type"],
                            source_of_truth=False,
                        )


if __name__ == "__main__":
    unittest.main()
