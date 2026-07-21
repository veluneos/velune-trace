import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from velune_trace.private_baseline import (
    build_private_baseline_judgment_boundary,
)
from velune_trace.private_baseline.registry import (
    BASELINE_REGISTRY_FILENAME,
    BASELINE_REGISTRY_SCHEMA_NAME,
    BASELINE_REGISTRY_SEMANTICS,
    PrivateBaselineRegistryError,
    load_private_baseline_registry,
)
from velune_trace.private_baseline.revision import (
    build_baseline_revision,
)


class PrivateBaselineRegistryTests(
    unittest.TestCase
):
    def baseline_id(self, digit="1"):
        return f"vpb_{digit * 32}"

    def revision_id(self, digit="2"):
        return f"vpbr_{digit * 32}"

    def evaluation_id(self, digit="3"):
        return f"vpbe_{digit * 32}"

    def review_id(self, digit="4"):
        return f"vpbrr_{digit * 32}"

    def bundle_id(self, value=1):
        return (
            "vrb_sha256_"
            f"{value:064x}"
        )

    def write_json(
        self,
        path: Path,
        value,
    ) -> bytes:
        payload = (
            json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        ).encode("utf-8")

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.write_bytes(payload)

        return payload

    def record_entry(
        self,
        root: Path,
        relative_path: str,
        document,
        *,
        record_id: str,
    ) -> dict:
        payload = self.write_json(
            root / relative_path,
            document,
        )

        return {
            "record_id": record_id,
            "relative_path": relative_path,
            "size_bytes": len(payload),
            "sha256": hashlib.sha256(
                payload
            ).hexdigest(),
        }

    def raw_record_entry(
        self,
        root: Path,
        relative_path: str,
        payload: bytes,
        *,
        record_id: str,
    ) -> dict:
        path = root / relative_path
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.write_bytes(payload)

        return {
            "record_id": record_id,
            "relative_path": relative_path,
            "size_bytes": len(payload),
            "sha256": hashlib.sha256(
                payload
            ).hexdigest(),
        }

    def revision_document(
        self,
        *,
        baseline_id=None,
        revision_id=None,
        parent_revision_id=None,
    ):
        baseline_id = (
            baseline_id or self.baseline_id()
        )
        revision_id = (
            revision_id or self.revision_id()
        )

        return build_baseline_revision(
            baseline_id=baseline_id,
            baseline_revision_id=revision_id,
            parent_revision_id=parent_revision_id,
            created_at=(
                "2026-07-20T10:00:00+09:00"
            ),
            created_by="engineer-a",
            dimension_policy={
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
            },
            reference_memberships=[
                {
                    "report_bundle_id": (
                        self.bundle_id()
                    ),
                    "report_manifest_sha256": (
                        "a" * 64
                    ),
                    "dimensions": {
                        "robot_model": "model-a",
                        "software_version": "v1",
                    },
                    "selection": {
                        "selected_by": "engineer-a",
                        "selected_at": (
                            "2026-07-20T09:00:00"
                            "+09:00"
                        ),
                        "selection_note": "",
                    },
                },
            ],
        )

    def evaluation_document(
        self,
        *,
        baseline_id=None,
        revision_id=None,
        evaluation_id=None,
    ):
        return {
            "schema_name": (
                "velune.private_baseline_evaluation"
            ),
            "schema_version": "0.1.0",
            "visibility": "private_local_only",
            "semantics": (
                "observed_against_user_selected_"
                "reference_set"
            ),
            "evaluation_id": (
                evaluation_id or self.evaluation_id()
            ),
            "generated_at": (
                "2026-07-20T11:00:00+09:00"
            ),
            "baseline_id": (
                baseline_id or self.baseline_id()
            ),
            "baseline_revision_id": (
                revision_id or self.revision_id()
            ),
            "evaluation_context": {},
            "target": {},
            "reference_comparisons": [],
            "aggregate_observations": {},
            "judgment_boundary": (
                build_private_baseline_judgment_boundary()
            ),
        }

    def review_document(
        self,
        *,
        baseline_id=None,
        revision_id=None,
        evaluation_id=None,
        review_id=None,
    ):
        return {
            "schema_name": (
                "velune.private_baseline_review"
            ),
            "schema_version": "0.1.0",
            "visibility": "private_local_only",
            "semantics": (
                "human_authored_review_record"
            ),
            "review_record_id": (
                review_id or self.review_id()
            ),
            "created_at": (
                "2026-07-20T12:00:00+09:00"
            ),
            "baseline_id": (
                baseline_id or self.baseline_id()
            ),
            "baseline_revision_id": (
                revision_id or self.revision_id()
            ),
            "evaluation_id": (
                evaluation_id or self.evaluation_id()
            ),
            "review_scope": "evaluation",
            "subject": {},
            "label_source": "human",
            "label": "reviewed",
            "reviewer": "engineer-a",
            "notes": "",
            "supersedes_review_record_id": None,
        }

    def registry_document(
        self,
        *,
        revisions,
        evaluations=None,
        reviews=None,
        baseline_id=None,
        current_revision_id=None,
        bundle_locations=None,
    ):
        return {
            "schema_name": (
                BASELINE_REGISTRY_SCHEMA_NAME
            ),
            "schema_version": "0.1.0",
            "visibility": "private_local_only",
            "semantics": (
                BASELINE_REGISTRY_SEMANTICS
            ),
            "baseline_id": (
                baseline_id or self.baseline_id()
            ),
            "display_name": "Private Baseline A",
            "created_at": (
                "2026-07-20T10:00:00+09:00"
            ),
            "current_revision_id": (
                current_revision_id
                or self.revision_id()
            ),
            "revisions": revisions,
            "evaluations": evaluations or [],
            "reviews": reviews or [],
            "bundle_locations": (
                bundle_locations or {}
            ),
        }

    def create_valid_root(
        self,
        root: Path,
        *,
        include_evaluation=False,
        include_review=False,
        bundle_locations=None,
    ):
        revision_entry = self.record_entry(
            root,
            (
                "revisions/"
                f"{self.revision_id()}/"
                "baseline_revision.json"
            ),
            self.revision_document(),
            record_id=self.revision_id(),
        )

        evaluation_entries = []
        review_entries = []

        if include_evaluation or include_review:
            evaluation_entries.append(
                self.record_entry(
                    root,
                    (
                        "evaluations/"
                        f"{self.evaluation_id()}/"
                        "baseline_evaluation_report.json"
                    ),
                    self.evaluation_document(),
                    record_id=self.evaluation_id(),
                )
            )

        if include_review:
            review_entries.append(
                self.record_entry(
                    root,
                    (
                        "reviews/"
                        f"{self.review_id()}.json"
                    ),
                    self.review_document(),
                    record_id=self.review_id(),
                )
            )

        registry = self.registry_document(
            revisions=[revision_entry],
            evaluations=evaluation_entries,
            reviews=review_entries,
            bundle_locations=bundle_locations,
        )

        self.write_json(
            root / BASELINE_REGISTRY_FILENAME,
            registry,
        )

        return registry

    def assert_registry_error(
        self,
        code,
        callback,
    ):
        with self.assertRaises(
            PrivateBaselineRegistryError
        ) as caught:
            callback()

        self.assertEqual(
            caught.exception.code,
            code,
        )
        self.assertEqual(
            caught.exception.stage,
            "private_baseline_registry",
        )

    def test_loads_valid_registry_and_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_valid_root(root)

            loaded = load_private_baseline_registry(
                root
            )

            self.assertEqual(
                loaded.registry["baseline_id"],
                self.baseline_id(),
            )
            self.assertEqual(
                set(loaded.revisions_by_id),
                {
                    self.revision_id(),
                },
            )
            self.assertEqual(
                loaded.current_revision.record_id,
                self.revision_id(),
            )

    def test_loads_valid_evaluation_and_review_envelopes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_valid_root(
                root,
                include_review=True,
            )

            loaded = load_private_baseline_registry(
                root
            )

            self.assertEqual(
                set(loaded.evaluations_by_id),
                {
                    self.evaluation_id(),
                },
            )
            self.assertEqual(
                set(loaded.reviews_by_id),
                {
                    self.review_id(),
                },
            )

    def test_bundle_location_does_not_need_to_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nonexistent = (
                root / "not-present-bundle"
            )

            self.create_valid_root(
                root,
                bundle_locations={
                    self.bundle_id(): str(nonexistent),
                },
            )

            loaded = load_private_baseline_registry(
                root
            )

            self.assertEqual(
                loaded.registry[
                    "bundle_locations"
                ][self.bundle_id()],
                str(nonexistent),
            )

    def test_display_name_is_normalized_to_nfc(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = self.create_valid_root(root)
            registry["display_name"] = (
                "Cafe\u0301 Baseline"
            )
            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            loaded = load_private_baseline_registry(
                root
            )

            self.assertEqual(
                loaded.registry["display_name"],
                "Caf\u00e9 Baseline",
            )

    def test_rejects_missing_root(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "ROOT_UNAVAILABLE"
                ),
                lambda: load_private_baseline_registry(
                    missing
                ),
            )

    def test_rejects_root_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = parent / "root"
            root.mkdir()
            self.create_valid_root(root)

            link = parent / "root-link"
            link.symlink_to(
                root,
                target_is_directory=True,
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "ROOT_SYMLINK_FORBIDDEN"
                ),
                lambda: load_private_baseline_registry(
                    link
                ),
            )

    def test_rejects_missing_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "REGISTRY_MISSING"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_registry_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / "external.json"
            self.write_json(
                external,
                {},
            )

            (
                root / BASELINE_REGISTRY_FILENAME
            ).symlink_to(external)

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "REGISTRY_SYMLINK_FORBIDDEN"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_invalid_registry_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (
                root / BASELINE_REGISTRY_FILENAME
            ).write_text(
                "{invalid-json",
                encoding="utf-8",
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "JSON_INVALID"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_duplicate_registry_json_key(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (
                root / BASELINE_REGISTRY_FILENAME
            ).write_text(
                (
                    '{"schema_name":"first",'
                    '"schema_name":"second"}'
                ),
                encoding="utf-8",
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "JSON_INVALID"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_nonfinite_registry_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (
                root / BASELINE_REGISTRY_FILENAME
            ).write_text(
                '{"value":NaN}',
                encoding="utf-8",
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "JSON_INVALID"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_unexpected_registry_field(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = self.create_valid_root(root)
            registry["automatic_recovery"] = True
            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "UNEXPECTED_FIELD"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_wrong_registry_semantics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = self.create_valid_root(root)
            registry["semantics"] = (
                "automatic_baseline_model"
            )
            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "CONTRACT_CONSTANT_INVALID"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_naive_registry_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = self.create_valid_root(root)
            registry["created_at"] = (
                "2026-07-20T10:00:00"
            )
            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "TIMESTAMP_TIMEZONE_REQUIRED"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_empty_revision_array(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = self.registry_document(
                revisions=[],
            )
            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "REVISION_REQUIRED"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_unknown_current_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = self.create_valid_root(root)
            registry["current_revision_id"] = (
                self.revision_id("9")
            )
            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "CURRENT_REVISION_MISSING"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_loads_valid_parent_revision_lineage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            root_revision_id = self.revision_id("2")
            child_revision_id = self.revision_id("5")

            root_entry = self.record_entry(
                root,
                (
                    "revisions/"
                    f"{root_revision_id}/"
                    "baseline_revision.json"
                ),
                self.revision_document(
                    revision_id=root_revision_id,
                ),
                record_id=root_revision_id,
            )

            child_entry = self.record_entry(
                root,
                (
                    "revisions/"
                    f"{child_revision_id}/"
                    "baseline_revision.json"
                ),
                self.revision_document(
                    revision_id=child_revision_id,
                    parent_revision_id=(
                        root_revision_id
                    ),
                ),
                record_id=child_revision_id,
            )

            registry = self.registry_document(
                revisions=[
                    root_entry,
                    child_entry,
                ],
                current_revision_id=(
                    child_revision_id
                ),
            )

            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            loaded = load_private_baseline_registry(
                root
            )

            self.assertEqual(
                loaded.current_revision.record_id,
                child_revision_id,
            )

    def test_rejects_unknown_parent_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            root_revision_id = self.revision_id("2")
            child_revision_id = self.revision_id("5")
            missing_parent_id = self.revision_id("9")

            root_entry = self.record_entry(
                root,
                (
                    "revisions/"
                    f"{root_revision_id}/"
                    "baseline_revision.json"
                ),
                self.revision_document(
                    revision_id=root_revision_id,
                ),
                record_id=root_revision_id,
            )

            child_entry = self.record_entry(
                root,
                (
                    "revisions/"
                    f"{child_revision_id}/"
                    "baseline_revision.json"
                ),
                self.revision_document(
                    revision_id=child_revision_id,
                    parent_revision_id=(
                        missing_parent_id
                    ),
                ),
                record_id=child_revision_id,
            )

            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                self.registry_document(
                    revisions=[
                        root_entry,
                        child_entry,
                    ],
                    current_revision_id=(
                        child_revision_id
                    ),
                ),
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "REVISION_PARENT_MISSING"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_multiple_root_revisions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            first_revision_id = self.revision_id("2")
            second_revision_id = self.revision_id("5")

            first_entry = self.record_entry(
                root,
                (
                    "revisions/"
                    f"{first_revision_id}/"
                    "baseline_revision.json"
                ),
                self.revision_document(
                    revision_id=first_revision_id,
                ),
                record_id=first_revision_id,
            )

            second_entry = self.record_entry(
                root,
                (
                    "revisions/"
                    f"{second_revision_id}/"
                    "baseline_revision.json"
                ),
                self.revision_document(
                    revision_id=second_revision_id,
                ),
                record_id=second_revision_id,
            )

            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                self.registry_document(
                    revisions=[
                        first_entry,
                        second_entry,
                    ],
                ),
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "REVISION_ROOT_COUNT_INVALID"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_revision_parent_cycle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            root_revision_id = self.revision_id("2")
            first_cycle_id = self.revision_id("5")
            second_cycle_id = self.revision_id("6")

            root_entry = self.record_entry(
                root,
                (
                    "revisions/"
                    f"{root_revision_id}/"
                    "baseline_revision.json"
                ),
                self.revision_document(
                    revision_id=root_revision_id,
                ),
                record_id=root_revision_id,
            )

            first_cycle_entry = self.record_entry(
                root,
                (
                    "revisions/"
                    f"{first_cycle_id}/"
                    "baseline_revision.json"
                ),
                self.revision_document(
                    revision_id=first_cycle_id,
                    parent_revision_id=(
                        second_cycle_id
                    ),
                ),
                record_id=first_cycle_id,
            )

            second_cycle_entry = self.record_entry(
                root,
                (
                    "revisions/"
                    f"{second_cycle_id}/"
                    "baseline_revision.json"
                ),
                self.revision_document(
                    revision_id=second_cycle_id,
                    parent_revision_id=(
                        first_cycle_id
                    ),
                ),
                record_id=second_cycle_id,
            )

            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                self.registry_document(
                    revisions=[
                        root_entry,
                        first_cycle_entry,
                        second_cycle_entry,
                    ],
                ),
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "REVISION_LINEAGE_CYCLE"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_absolute_record_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = self.create_valid_root(root)
            registry["revisions"][0][
                "relative_path"
            ] = "/tmp/revision.json"
            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RELATIVE_PATH_ABSOLUTE"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = self.create_valid_root(root)
            registry["revisions"][0][
                "relative_path"
            ] = "../revision.json"
            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RELATIVE_PATH_NONCANONICAL"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_noncanonical_record_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = self.create_valid_root(root)
            registry["revisions"][0][
                "relative_path"
            ] = (
                "revisions//"
                f"{self.revision_id()}/"
                "baseline_revision.json"
            )
            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RELATIVE_PATH_NONCANONICAL"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_record_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            revision_path = (
                root
                / "revisions"
                / self.revision_id()
                / "baseline_revision.json"
            )
            revision_path.parent.mkdir(
                parents=True
            )

            external = root / "external.json"
            payload = self.write_json(
                external,
                self.revision_document(),
            )

            revision_path.symlink_to(external)

            entry = {
                "record_id": self.revision_id(),
                "relative_path": (
                    "revisions/"
                    f"{self.revision_id()}/"
                    "baseline_revision.json"
                ),
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(
                    payload
                ).hexdigest(),
            }

            registry = self.registry_document(
                revisions=[entry],
            )
            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RECORD_SYMLINK_FORBIDDEN"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_parent_directory_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / "external-records"
            revision_dir = (
                external / self.revision_id()
            )
            revision_dir.mkdir(
                parents=True
            )

            payload = self.write_json(
                revision_dir
                / "baseline_revision.json",
                self.revision_document(),
            )

            (
                root / "revisions"
            ).symlink_to(
                external,
                target_is_directory=True,
            )

            entry = {
                "record_id": self.revision_id(),
                "relative_path": (
                    "revisions/"
                    f"{self.revision_id()}/"
                    "baseline_revision.json"
                ),
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(
                    payload
                ).hexdigest(),
            }

            registry = self.registry_document(
                revisions=[entry],
            )
            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RECORD_SYMLINK_FORBIDDEN"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_missing_record_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = {
                "record_id": self.revision_id(),
                "relative_path": (
                    "revisions/"
                    f"{self.revision_id()}/"
                    "baseline_revision.json"
                ),
                "size_bytes": 1,
                "sha256": "0" * 64,
            }

            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                self.registry_document(
                    revisions=[entry],
                ),
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RECORD_PATH_UNAVAILABLE"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_record_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative_path = (
                "revisions/"
                f"{self.revision_id()}/"
                "baseline_revision.json"
            )
            (
                root / relative_path
            ).mkdir(
                parents=True
            )

            entry = {
                "record_id": self.revision_id(),
                "relative_path": relative_path,
                "size_bytes": 0,
                "sha256": hashlib.sha256(
                    b""
                ).hexdigest(),
            }

            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                self.registry_document(
                    revisions=[entry],
                ),
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RECORD_FILE_TYPE_INVALID"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_record_size_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = self.create_valid_root(root)
            registry["revisions"][0][
                "size_bytes"
            ] += 1
            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RECORD_SIZE_MISMATCH"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_record_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = self.create_valid_root(root)
            registry["revisions"][0][
                "sha256"
            ] = "0" * 64
            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RECORD_HASH_MISMATCH"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_invalid_record_json_after_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = self.raw_record_entry(
                root,
                (
                    "revisions/"
                    f"{self.revision_id()}/"
                    "baseline_revision.json"
                ),
                b"{invalid-json",
                record_id=self.revision_id(),
            )

            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                self.registry_document(
                    revisions=[entry],
                ),
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "JSON_INVALID"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_duplicate_record_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = self.create_valid_root(root)
            registry["revisions"].append(
                dict(registry["revisions"][0])
            )
            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RECORD_ID_DUPLICATE"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_duplicate_record_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = self.create_valid_root(root)
            duplicate = dict(
                registry["revisions"][0]
            )
            duplicate["record_id"] = (
                self.revision_id("9")
            )
            registry["revisions"].append(duplicate)
            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RECORD_PATH_DUPLICATE"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_internal_record_id_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = self.record_entry(
                root,
                (
                    "revisions/"
                    f"{self.revision_id()}/"
                    "baseline_revision.json"
                ),
                self.revision_document(
                    revision_id=self.revision_id("9"),
                ),
                record_id=self.revision_id(),
            )

            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                self.registry_document(
                    revisions=[entry],
                ),
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RECORD_IDENTIFIER_MISMATCH"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_revision_from_other_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = self.record_entry(
                root,
                (
                    "revisions/"
                    f"{self.revision_id()}/"
                    "baseline_revision.json"
                ),
                self.revision_document(
                    baseline_id=self.baseline_id("9"),
                ),
                record_id=self.revision_id(),
            )

            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                self.registry_document(
                    revisions=[entry],
                ),
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RECORD_BASELINE_ID_MISMATCH"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_revision_in_evaluation_array(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            revision_entry = self.record_entry(
                root,
                (
                    "revisions/"
                    f"{self.revision_id()}/"
                    "baseline_revision.json"
                ),
                self.revision_document(),
                record_id=self.revision_id(),
            )

            wrong_entry = self.record_entry(
                root,
                (
                    "evaluations/"
                    f"{self.evaluation_id()}/"
                    "baseline_evaluation_report.json"
                ),
                self.revision_document(),
                record_id=self.evaluation_id(),
            )

            registry = self.registry_document(
                revisions=[revision_entry],
                evaluations=[wrong_entry],
            )
            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "REQUIRED_FIELD_MISSING"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_evaluation_unknown_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            revision_entry = self.record_entry(
                root,
                (
                    "revisions/"
                    f"{self.revision_id()}/"
                    "baseline_revision.json"
                ),
                self.revision_document(),
                record_id=self.revision_id(),
            )

            evaluation_entry = self.record_entry(
                root,
                (
                    "evaluations/"
                    f"{self.evaluation_id()}/"
                    "baseline_evaluation_report.json"
                ),
                self.evaluation_document(
                    revision_id=self.revision_id("9"),
                ),
                record_id=self.evaluation_id(),
            )

            registry = self.registry_document(
                revisions=[revision_entry],
                evaluations=[evaluation_entry],
            )
            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RECORD_REFERENCE_MISSING"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_review_unknown_evaluation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            revision_entry = self.record_entry(
                root,
                (
                    "revisions/"
                    f"{self.revision_id()}/"
                    "baseline_revision.json"
                ),
                self.revision_document(),
                record_id=self.revision_id(),
            )

            review_entry = self.record_entry(
                root,
                (
                    "reviews/"
                    f"{self.review_id()}.json"
                ),
                self.review_document(),
                record_id=self.review_id(),
            )

            registry = self.registry_document(
                revisions=[revision_entry],
                reviews=[review_entry],
            )
            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RECORD_REFERENCE_MISSING"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_review_revision_mismatch_with_evaluation(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            root_revision_id = self.revision_id("2")
            child_revision_id = self.revision_id("5")

            root_revision_entry = self.record_entry(
                root,
                (
                    "revisions/"
                    f"{root_revision_id}/"
                    "baseline_revision.json"
                ),
                self.revision_document(
                    revision_id=root_revision_id,
                ),
                record_id=root_revision_id,
            )

            child_revision_entry = self.record_entry(
                root,
                (
                    "revisions/"
                    f"{child_revision_id}/"
                    "baseline_revision.json"
                ),
                self.revision_document(
                    revision_id=child_revision_id,
                    parent_revision_id=(
                        root_revision_id
                    ),
                ),
                record_id=child_revision_id,
            )

            evaluation_entry = self.record_entry(
                root,
                (
                    "evaluations/"
                    f"{self.evaluation_id()}/"
                    "baseline_evaluation_report.json"
                ),
                self.evaluation_document(
                    revision_id=root_revision_id,
                ),
                record_id=self.evaluation_id(),
            )

            review_entry = self.record_entry(
                root,
                (
                    "reviews/"
                    f"{self.review_id()}.json"
                ),
                self.review_document(
                    revision_id=child_revision_id,
                    evaluation_id=self.evaluation_id(),
                ),
                record_id=self.review_id(),
            )

            registry = self.registry_document(
                revisions=[
                    root_revision_entry,
                    child_revision_entry,
                ],
                evaluations=[
                    evaluation_entry,
                ],
                reviews=[
                    review_entry,
                ],
                current_revision_id=(
                    child_revision_id
                ),
            )

            self.write_json(
                root / BASELINE_REGISTRY_FILENAME,
                registry,
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "REVIEW_EVALUATION_REVISION_MISMATCH"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_invalid_bundle_location_key(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_valid_root(
                root,
                bundle_locations={
                    "bundle-1": "/tmp/bundle",
                },
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "REPORT_BUNDLE_ID_INVALID"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )

    def test_rejects_non_string_bundle_location(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_valid_root(
                root,
                bundle_locations={
                    self.bundle_id(): 123,
                },
            )

            self.assert_registry_error(
                (
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "BUNDLE_LOCATION_INVALID"
                ),
                lambda: load_private_baseline_registry(
                    root
                ),
            )


if __name__ == "__main__":
    unittest.main()
