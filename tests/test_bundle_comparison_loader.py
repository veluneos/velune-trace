import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

from velune_trace.comparison.loader import (
    BundleComparisonLoadError,
    EVIDENCE_WINDOWS_FILENAME,
    MANIFEST_FILENAME,
    TOPIC_PROFILE_FILENAME,
    load_comparison_bundle,
)


class BundleComparisonLoaderTests(unittest.TestCase):
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
        content = path.read_bytes()

        return {
            "path": path.name,
            "role": "core_machine_readable",
            "media_type": "application/json",
            "size_bytes": len(content),
            "hash": {
                "algorithm": "sha256",
                "value": hashlib.sha256(
                    content
                ).hexdigest(),
            },
            "source_of_truth": True,
        }

    def create_bundle(
        self,
        root: Path,
        *,
        topic_profile=None,
        evidence_windows=None,
        artifacts_transform=None,
    ) -> Path:
        bundle_dir = root / "bundle"
        bundle_dir.mkdir()

        if topic_profile is None:
            topic_profile = {
                "/imu": {
                    "count": 100,
                    "avg_gap_ns": 10_000_000,
                },
            }

        if evidence_windows is None:
            evidence_windows = {
                "/imu": [
                    {
                        "topic": "/imu",
                        "window": 1,
                        "count": 50,
                        "observed_irregularity_score": 1.5,
                    },
                ],
            }

        topic_path = (
            bundle_dir / TOPIC_PROFILE_FILENAME
        )
        evidence_path = (
            bundle_dir / EVIDENCE_WINDOWS_FILENAME
        )

        self.write_json(
            topic_path,
            topic_profile,
        )
        self.write_json(
            evidence_path,
            evidence_windows,
        )

        artifacts = [
            self.artifact_record(evidence_path),
            self.artifact_record(topic_path),
        ]

        if artifacts_transform is not None:
            artifacts = artifacts_transform(
                artifacts
            )

        manifest = {
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
                "mode": (
                    "bounded_streaming_aggregation"
                ),
                "semantics": (
                    "observed_timing_metadata_only"
                ),
                "timestamp_unit": "nanoseconds_int",
                "window_sec": 1.0,
                "allowed_lateness_sec": 2.0,
                "top": 5,
            },
            "artifacts": artifacts,
        }

        self.write_json(
            bundle_dir / MANIFEST_FILENAME,
            manifest,
        )

        return bundle_dir

    def assert_load_error(
        self,
        expected_code: str,
        callback,
    ) -> BundleComparisonLoadError:
        with self.assertRaises(
            BundleComparisonLoadError
        ) as context:
            callback()

        self.assertEqual(
            context.exception.code,
            expected_code,
        )
        self.assertEqual(
            context.exception.stage,
            "comparison_bundle_load",
        )
        self.assertIsNotNone(
            context.exception.hint
        )

        return context.exception

    def test_loads_verified_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle_dir = self.create_bundle(
                Path(directory)
            )

            loaded = load_comparison_bundle(
                bundle_dir
            )

            self.assertEqual(
                loaded.bundle_dir,
                bundle_dir.resolve(),
            )
            self.assertEqual(
                loaded.topic_profile["/imu"]["count"],
                100,
            )
            self.assertEqual(
                loaded.evidence_windows[
                    "/imu"
                ][0]["window"],
                1,
            )
            self.assertEqual(
                sorted(loaded.artifacts_by_path),
                [
                    EVIDENCE_WINDOWS_FILENAME,
                    TOPIC_PROFILE_FILENAME,
                ],
            )

    def test_rejects_missing_bundle_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"

            self.assert_load_error(
                (
                    "VELUNE_COMPARISON_"
                    "BUNDLE_DIRECTORY_UNAVAILABLE"
                ),
                lambda: load_comparison_bundle(
                    missing
                ),
            )

    def test_rejects_bundle_directory_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle_dir = self.create_bundle(root)
            link = root / "bundle-link"
            link.symlink_to(
                bundle_dir,
                target_is_directory=True,
            )

            self.assert_load_error(
                (
                    "VELUNE_COMPARISON_"
                    "BUNDLE_DIRECTORY_SYMLINK_FORBIDDEN"
                ),
                lambda: load_comparison_bundle(link),
            )

    def test_rejects_missing_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle_dir = self.create_bundle(
                Path(directory)
            )
            (
                bundle_dir / MANIFEST_FILENAME
            ).unlink()

            self.assert_load_error(
                (
                    "VELUNE_COMPARISON_"
                    "REQUIRED_FILE_MISSING"
                ),
                lambda: load_comparison_bundle(
                    bundle_dir
                ),
            )

    def test_rejects_required_artifact_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle_dir = self.create_bundle(root)

            topic_path = (
                bundle_dir / TOPIC_PROFILE_FILENAME
            )
            external_path = root / "external.json"

            external_path.write_bytes(
                topic_path.read_bytes()
            )
            topic_path.unlink()
            topic_path.symlink_to(external_path)

            self.assert_load_error(
                (
                    "VELUNE_COMPARISON_"
                    "REQUIRED_FILE_SYMLINK_FORBIDDEN"
                ),
                lambda: load_comparison_bundle(
                    bundle_dir
                ),
            )

    def test_rejects_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle_dir = self.create_bundle(
                Path(directory)
            )

            (
                bundle_dir / TOPIC_PROFILE_FILENAME
            ).write_text(
                "{invalid-json",
                encoding="utf-8",
            )

            self.assert_load_error(
                (
                    "VELUNE_COMPARISON_"
                    "ARTIFACT_SIZE_MISMATCH"
                ),
                lambda: load_comparison_bundle(
                    bundle_dir
                ),
            )

    def test_rejects_non_finite_json_number(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle_dir = self.create_bundle(
                Path(directory)
            )
            topic_path = (
                bundle_dir / TOPIC_PROFILE_FILENAME
            )

            topic_path.write_text(
                '{"/imu":{"count":NaN}}\n',
                encoding="utf-8",
            )

            manifest_path = (
                bundle_dir / MANIFEST_FILENAME
            )
            manifest = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )

            for artifact in manifest["artifacts"]:
                if (
                    artifact["path"]
                    == TOPIC_PROFILE_FILENAME
                ):
                    artifact.update(
                        self.artifact_record(topic_path)
                    )

            self.write_json(
                manifest_path,
                manifest,
            )

            self.assert_load_error(
                (
                    "VELUNE_COMPARISON_"
                    "JSON_INVALID"
                ),
                lambda: load_comparison_bundle(
                    bundle_dir
                ),
            )

    def test_rejects_undeclared_required_artifact(self):
        def remove_topic(artifacts):
            return [
                artifact
                for artifact in artifacts
                if (
                    artifact["path"]
                    != TOPIC_PROFILE_FILENAME
                )
            ]

        with tempfile.TemporaryDirectory() as directory:
            bundle_dir = self.create_bundle(
                Path(directory),
                artifacts_transform=remove_topic,
            )

            self.assert_load_error(
                (
                    "VELUNE_COMPARISON_"
                    "ARTIFACT_UNDECLARED"
                ),
                lambda: load_comparison_bundle(
                    bundle_dir
                ),
            )

    def test_rejects_duplicate_artifact_path(self):
        def duplicate_topic(artifacts):
            topic = next(
                artifact
                for artifact in artifacts
                if (
                    artifact["path"]
                    == TOPIC_PROFILE_FILENAME
                )
            )
            return [
                *artifacts,
                dict(topic),
            ]

        with tempfile.TemporaryDirectory() as directory:
            bundle_dir = self.create_bundle(
                Path(directory),
                artifacts_transform=(
                    duplicate_topic
                ),
            )

            self.assert_load_error(
                (
                    "VELUNE_COMPARISON_"
                    "MANIFEST_ARTIFACT_DUPLICATE"
                ),
                lambda: load_comparison_bundle(
                    bundle_dir
                ),
            )

    def test_rejects_artifact_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle_dir = self.create_bundle(
                Path(directory)
            )

            topic_path = (
                bundle_dir / TOPIC_PROFILE_FILENAME
            )
            original_size = topic_path.stat().st_size

            replacement = b"x" * original_size
            topic_path.write_bytes(replacement)

            self.assert_load_error(
                (
                    "VELUNE_COMPARISON_"
                    "ARTIFACT_HASH_MISMATCH"
                ),
                lambda: load_comparison_bundle(
                    bundle_dir
                ),
            )

    def test_rejects_artifact_size_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle_dir = self.create_bundle(
                Path(directory)
            )

            topic_path = (
                bundle_dir / TOPIC_PROFILE_FILENAME
            )
            topic_path.write_text(
                "{}\n",
                encoding="utf-8",
            )

            self.assert_load_error(
                (
                    "VELUNE_COMPARISON_"
                    "ARTIFACT_SIZE_MISMATCH"
                ),
                lambda: load_comparison_bundle(
                    bundle_dir
                ),
            )

    def test_rejects_unsupported_hash_algorithm(self):
        def replace_algorithm(artifacts):
            copied = [
                {
                    **artifact,
                    "hash": dict(artifact["hash"]),
                }
                for artifact in artifacts
            ]
            copied[0]["hash"]["algorithm"] = "md5"
            return copied

        with tempfile.TemporaryDirectory() as directory:
            bundle_dir = self.create_bundle(
                Path(directory),
                artifacts_transform=(
                    replace_algorithm
                ),
            )

            self.assert_load_error(
                (
                    "VELUNE_COMPARISON_"
                    "ARTIFACT_HASH_ALGORITHM_UNSUPPORTED"
                ),
                lambda: load_comparison_bundle(
                    bundle_dir
                ),
            )

    def test_rejects_invalid_topic_profile_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle_dir = self.create_bundle(
                root,
                topic_profile={
                    "/imu": [],
                },
            )

            self.assert_load_error(
                (
                    "VELUNE_COMPARISON_"
                    "TOPIC_PROFILE_STRUCTURE_INVALID"
                ),
                lambda: load_comparison_bundle(
                    bundle_dir
                ),
            )

    def test_rejects_invalid_evidence_window_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle_dir = self.create_bundle(
                Path(directory),
                evidence_windows={
                    "/imu": {},
                },
            )

            self.assert_load_error(
                (
                    "VELUNE_COMPARISON_"
                    "EVIDENCE_WINDOWS_STRUCTURE_INVALID"
                ),
                lambda: load_comparison_bundle(
                    bundle_dir
                ),
            )

    def test_rejects_invalid_manifest_artifact_list(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle_dir = self.create_bundle(
                Path(directory)
            )
            manifest_path = (
                bundle_dir / MANIFEST_FILENAME
            )
            manifest = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )
            manifest["artifacts"] = {}

            self.write_json(
                manifest_path,
                manifest,
            )

            self.assert_load_error(
                (
                    "VELUNE_COMPARISON_"
                    "MANIFEST_ARTIFACTS_INVALID"
                ),
                lambda: load_comparison_bundle(
                    bundle_dir
                ),
            )


if __name__ == "__main__":
    unittest.main()
