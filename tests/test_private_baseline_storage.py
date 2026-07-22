import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from velune_trace.private_baseline import (
    PrivateBaselineContractError,
)
import velune_trace.private_baseline.storage as storage_module
from velune_trace.private_baseline.storage import (
    PrivateBaselineStorageError,
    _install_initial_private_baseline,
)


class PrivateBaselineStorageTests(
    unittest.TestCase
):
    def dimension_policy(self):
        return {
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
        }

    def membership(self, value=1):
        return {
            "report_bundle_id": (
                "vrb_sha256_"
                f"{value:064x}"
            ),
            "report_manifest_sha256": (
                f"{value + 100:064x}"
            ),
            "dimensions": {
                "robot_model": "model-a",
                "software_version": f"v{value}",
            },
            "selection": {
                "selected_by": "engineer-a",
                "selected_at": (
                    "2026-07-20T09:00:00+09:00"
                ),
                "selection_note": "",
            },
        }

    def default_arguments(self):
        return {
            "display_name": "Private Baseline A",
            "created_at": (
                "2026-07-20T10:00:00+09:00"
            ),
            "created_by": "engineer-a",
            "dimension_policy": (
                self.dimension_policy()
            ),
            "reference_memberships": [
                self.membership(),
            ],
            "bundle_locations": {},
        }

    def create(
        self,
        parent: Path,
        **overrides,
    ):
        arguments = self.default_arguments()
        arguments.update(overrides)

        with patch(
            "velune_trace.private_baseline."
            "contract.secrets.token_hex",
            return_value="1" * 32,
        ):
            return _install_initial_private_baseline(
                parent,
                **arguments,
            )

    def assert_storage_error(
        self,
        expected_code,
        callback,
    ):
        with self.assertRaises(
            PrivateBaselineStorageError
        ) as caught:
            callback()

        self.assertEqual(
            caught.exception.code,
            expected_code,
        )
        self.assertEqual(
            caught.exception.stage,
            "private_baseline_storage",
        )

    def test_creates_valid_initial_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            loaded = self.create(parent)

            self.assertEqual(
                loaded.registry["baseline_id"],
                f"vpb_{'1' * 32}",
            )
            self.assertEqual(
                loaded.current_revision.record_id,
                f"vpbr_{'1' * 32}",
            )
            self.assertEqual(
                loaded.registry["evaluations"],
                [],
            )
            self.assertEqual(
                loaded.registry["reviews"],
                [],
            )

    def test_creates_expected_directory_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            loaded = self.create(Path(directory))
            root = loaded.root_dir
            revision_id = (
                loaded.current_revision.record_id
            )

            expected = {
                "baseline_registry.json",
                "revisions",
                "evaluations",
                "reviews",
            }

            self.assertEqual(
                {
                    child.name
                    for child in root.iterdir()
                },
                expected,
            )
            self.assertTrue(
                (
                    root
                    / "revisions"
                    / revision_id
                    / "baseline_revision.json"
                ).is_file()
            )

    def test_applies_private_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            loaded = self.create(Path(directory))
            root = loaded.root_dir
            revision_path = (
                loaded.current_revision.path
            )

            directory_paths = [
                root,
                root / "revisions",
                root / "evaluations",
                root / "reviews",
                revision_path.parent,
            ]

            file_paths = [
                root / "baseline_registry.json",
                revision_path,
            ]

            for path in directory_paths:
                self.assertEqual(
                    stat.S_IMODE(
                        path.stat().st_mode
                    ),
                    0o700,
                )

            for path in file_paths:
                self.assertEqual(
                    stat.S_IMODE(
                        path.stat().st_mode
                    ),
                    0o600,
                )

    def test_serialization_is_deterministic(self):
        with tempfile.TemporaryDirectory() as first:
            with tempfile.TemporaryDirectory() as second:
                first_loaded = self.create(
                    Path(first)
                )
                second_loaded = self.create(
                    Path(second)
                )

                self.assertEqual(
                    (
                        first_loaded.root_dir
                        / "baseline_registry.json"
                    ).read_bytes(),
                    (
                        second_loaded.root_dir
                        / "baseline_registry.json"
                    ).read_bytes(),
                )
                self.assertEqual(
                    first_loaded.current_revision.path
                    .read_bytes(),
                    second_loaded.current_revision.path
                    .read_bytes(),
                )

    def test_bundle_location_may_not_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            missing = parent / "missing-bundle"
            bundle_id = (
                self.membership()[
                    "report_bundle_id"
                ]
            )

            loaded = self.create(
                parent,
                bundle_locations={
                    bundle_id: str(missing),
                },
            )

            self.assertEqual(
                loaded.registry[
                    "bundle_locations"
                ][bundle_id],
                str(missing),
            )

    def test_collision_moves_to_next_baseline_candidate(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)

            first_id = f"vpb_{'a' * 32}"
            existing = parent / first_id
            existing.mkdir()
            sentinel = existing / "sentinel.txt"
            sentinel.write_text(
                "do-not-overwrite",
                encoding="utf-8",
            )

            with patch(
                "velune_trace.private_baseline."
                "contract.secrets.token_hex",
                side_effect=[
                    "a" * 32,
                    "b" * 32,
                    "c" * 32,
                ],
            ):
                loaded = _install_initial_private_baseline(
                    parent,
                    **self.default_arguments(),
                )

            self.assertEqual(
                loaded.registry["baseline_id"],
                f"vpb_{'b' * 32}",
            )
            self.assertEqual(
                loaded.current_revision.record_id,
                f"vpbr_{'c' * 32}",
            )
            self.assertEqual(
                sentinel.read_text(
                    encoding="utf-8"
                ),
                "do-not-overwrite",
            )

    def test_exhausted_candidates_do_not_overwrite(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            existing = parent / f"vpb_{'a' * 32}"
            existing.mkdir()
            sentinel = existing / "sentinel.txt"
            sentinel.write_text(
                "preserved",
                encoding="utf-8",
            )

            with patch(
                "velune_trace.private_baseline."
                "contract.secrets.token_hex",
                return_value="a" * 32,
            ):
                self.assert_storage_error(
                    (
                        "VELUNE_PRIVATE_BASELINE_STORAGE_"
                        "IDENTIFIER_CLAIM_EXHAUSTED"
                    ),
                    lambda: _install_initial_private_baseline(
                        parent,
                        **self.default_arguments(),
                    ),
                )

            self.assertEqual(
                sentinel.read_text(
                    encoding="utf-8"
                ),
                "preserved",
            )
            self.assertEqual(
                list(parent.iterdir()),
                [existing],
            )

    def test_revision_claim_retries_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            existing = parent / f"vpbr_{'a' * 32}"
            existing.mkdir()

            with patch(
                "velune_trace.private_baseline."
                "contract.secrets.token_hex",
                side_effect=[
                    "a" * 32,
                    "b" * 32,
                ],
            ):
                identifier, claimed = (
                    storage_module
                    ._claim_generated_directory(
                        parent,
                        identifier_kind=(
                            "baseline_revision"
                        ),
                    )
                )

            self.assertEqual(
                identifier,
                f"vpbr_{'b' * 32}",
            )
            self.assertEqual(
                claimed,
                parent / identifier,
            )

    def test_rejects_missing_parent_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"

            self.assert_storage_error(
                (
                    "VELUNE_PRIVATE_BASELINE_STORAGE_"
                    "PARENT_UNAVAILABLE"
                ),
                lambda: self.create(missing),
            )

    def test_rejects_parent_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real_parent = root / "real"
            real_parent.mkdir()
            link = root / "link"
            link.symlink_to(
                real_parent,
                target_is_directory=True,
            )

            self.assert_storage_error(
                (
                    "VELUNE_PRIVATE_BASELINE_STORAGE_"
                    "PARENT_SYMLINK_FORBIDDEN"
                ),
                lambda: self.create(link),
            )

            self.assertEqual(
                list(real_parent.iterdir()),
                [],
            )

    def test_rejects_parent_file(self):
        with tempfile.TemporaryDirectory() as directory:
            parent_file = (
                Path(directory) / "parent.txt"
            )
            parent_file.write_text(
                "not-a-directory",
                encoding="utf-8",
            )

            self.assert_storage_error(
                (
                    "VELUNE_PRIVATE_BASELINE_STORAGE_"
                    "PARENT_TYPE_INVALID"
                ),
                lambda: self.create(parent_file),
            )

    def test_invalid_display_name_creates_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)

            with self.assertRaises(
                PrivateBaselineContractError
            ):
                self.create(
                    parent,
                    display_name=" invalid ",
                )

            self.assertEqual(
                list(parent.iterdir()),
                [],
            )

    def test_naive_timestamp_creates_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)

            with self.assertRaises(
                PrivateBaselineContractError
            ):
                self.create(
                    parent,
                    created_at=(
                        "2026-07-20T10:00:00"
                    ),
                )

            self.assertEqual(
                list(parent.iterdir()),
                [],
            )

    def test_thirty_third_reference_creates_nothing(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            memberships = [
                self.membership(index)
                for index in range(1, 34)
            ]

            with self.assertRaises(
                PrivateBaselineContractError
            ):
                self.create(
                    parent,
                    reference_memberships=(
                        memberships
                    ),
                )

            self.assertEqual(
                list(parent.iterdir()),
                [],
            )

    def test_invalid_bundle_location_creates_nothing(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)

            with self.assertRaises(
                PrivateBaselineContractError
            ):
                self.create(
                    parent,
                    bundle_locations={
                        "invalid-bundle-id": (
                            "/tmp/bundle"
                        ),
                    },
                )

            self.assertEqual(
                list(parent.iterdir()),
                [],
            )

    def test_revision_write_failure_cleans_root(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)

            with patch.object(
                storage_module,
                "_write_new_file_atomically",
                side_effect=OSError(
                    "injected revision failure"
                ),
            ):
                self.assert_storage_error(
                    (
                        "VELUNE_PRIVATE_BASELINE_STORAGE_"
                        "CREATE_FAILED"
                    ),
                    lambda: self.create(parent),
                )

            self.assertEqual(
                list(parent.iterdir()),
                [],
            )

    def test_registry_write_failure_cleans_root(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            original = (
                storage_module
                ._write_new_file_atomically
            )
            call_count = 0

            def fail_second_call(path, payload):
                nonlocal call_count
                call_count += 1

                if call_count == 2:
                    raise OSError(
                        "injected registry failure"
                    )

                return original(path, payload)

            with patch.object(
                storage_module,
                "_write_new_file_atomically",
                side_effect=fail_second_call,
            ):
                self.assert_storage_error(
                    (
                        "VELUNE_PRIVATE_BASELINE_STORAGE_"
                        "CREATE_FAILED"
                    ),
                    lambda: self.create(parent),
                )

            self.assertEqual(
                list(parent.iterdir()),
                [],
            )

    def test_post_validation_failure_cleans_root(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)

            with patch.object(
                storage_module,
                "load_private_baseline_registry",
                side_effect=RuntimeError(
                    "injected validation failure"
                ),
            ):
                self.assert_storage_error(
                    (
                        "VELUNE_PRIVATE_BASELINE_STORAGE_"
                        "POST_INSTALL_VALIDATION_FAILED"
                    ),
                    lambda: self.create(parent),
                )

            self.assertEqual(
                list(parent.iterdir()),
                [],
            )

    def test_atomic_writer_refuses_existing_target(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            target = parent / "record.json"
            target.write_bytes(b"original")

            self.assert_storage_error(
                (
                    "VELUNE_PRIVATE_BASELINE_STORAGE_"
                    "FILE_ALREADY_EXISTS"
                ),
                lambda: (
                    storage_module
                    ._write_new_file_atomically(
                        target,
                        b"replacement",
                    )
                ),
            )

            self.assertEqual(
                target.read_bytes(),
                b"original",
            )

    def test_atomic_writer_applies_private_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "record.json"

            storage_module._write_new_file_atomically(
                target,
                b"{}\n",
            )

            self.assertEqual(
                stat.S_IMODE(
                    target.stat().st_mode
                ),
                0o600,
            )

    def test_no_temporary_files_remain(self):
        with tempfile.TemporaryDirectory() as directory:
            loaded = self.create(Path(directory))

            hidden_paths = [
                path
                for path in loaded.root_dir.rglob("*")
                if path.name.startswith(".")
            ]

            self.assertEqual(
                hidden_paths,
                [],
            )

    def test_does_not_mutate_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            policy = self.dimension_policy()
            memberships = [
                self.membership(),
            ]
            locations = {
                self.membership()[
                    "report_bundle_id"
                ]: "/tmp/reference",
            }

            original_policy = copy.deepcopy(policy)
            original_memberships = copy.deepcopy(
                memberships
            )
            original_locations = copy.deepcopy(
                locations
            )

            self.create(
                parent,
                dimension_policy=policy,
                reference_memberships=memberships,
                bundle_locations=locations,
            )

            self.assertEqual(
                policy,
                original_policy,
            )
            self.assertEqual(
                memberships,
                original_memberships,
            )
            self.assertEqual(
                locations,
                original_locations,
            )

    def test_registry_and_revision_share_created_at(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            loaded = self.create(Path(directory))

            self.assertEqual(
                loaded.registry["created_at"],
                loaded.current_revision.document[
                    "created_at"
                ],
            )

    def test_registry_digest_matches_revision_file(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            loaded = self.create(Path(directory))
            payload = (
                loaded.current_revision.path
                .read_bytes()
            )

            self.assertEqual(
                loaded.registry["revisions"][0][
                    "size_bytes"
                ],
                len(payload),
            )
            self.assertEqual(
                loaded.registry["revisions"][0][
                    "sha256"
                ],
                hashlib.sha256(
                    payload
                ).hexdigest(),
            )

    def test_parent_contains_only_created_baseline(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            loaded = self.create(parent)

            self.assertEqual(
                list(parent.iterdir()),
                [
                    loaded.root_dir,
                ],
            )

    def test_returns_loaded_current_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            loaded = self.create(Path(directory))

            registry_payload = json.loads(
                (
                    loaded.root_dir
                    / "baseline_registry.json"
                ).read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                loaded.current_revision.record_id,
                registry_payload[
                    "current_revision_id"
                ],
            )


if __name__ == "__main__":
    unittest.main()
