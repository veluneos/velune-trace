import copy
import unittest

from velune_trace.private_baseline import (
    PrivateBaselineContractError,
)
from velune_trace.private_baseline.revision import (
    BASELINE_REVISION_SCHEMA_NAME,
    BASELINE_REVISION_SEMANTICS,
    PrivateBaselineRevisionError,
    build_baseline_revision,
    normalize_dimension_policy,
    validate_baseline_revision,
)


class PrivateBaselineRevisionTests(
    unittest.TestCase
):
    def baseline_id(self):
        return f"vpb_{'1' * 32}"

    def revision_id(self, digit="2"):
        return f"vpbr_{digit * 32}"

    def bundle_id(self, value):
        return (
            "vrb_sha256_"
            f"{value:064x}"
        )

    def sha256(self, value):
        return f"{value:064x}"

    def dimension_policy(self):
        return {
            "match_values": {
                "robot_model": "model-a",
                "site_id": "site-a",
            },
            "vary_keys": [
                "software_version",
                "robot_id",
            ],
            "required_keys": [
                "site_id",
                "software_version",
                "robot_model",
                "robot_id",
            ],
        }

    def membership(
        self,
        value,
        *,
        dimensions=None,
        selected_at="2026-07-20T10:00:00+09:00",
        selection_note="selected by engineer",
    ):
        return {
            "report_bundle_id": self.bundle_id(value),
            "report_manifest_sha256": (
                self.sha256(value + 100)
            ),
            "dimensions": dimensions or {
                "robot_model": "model-a",
                "site_id": "site-a",
                "robot_id": f"robot-{value}",
                "software_version": f"v{value}",
            },
            "selection": {
                "selected_by": "engineer-a",
                "selected_at": selected_at,
                "selection_note": selection_note,
            },
        }

    def build(self, **overrides):
        values = {
            "baseline_id": self.baseline_id(),
            "baseline_revision_id": (
                self.revision_id()
            ),
            "parent_revision_id": None,
            "created_at": (
                "2026-07-20T11:00:00+09:00"
            ),
            "created_by": "engineer-a",
            "dimension_policy": (
                self.dimension_policy()
            ),
            "reference_memberships": [
                self.membership(2),
                self.membership(1),
            ],
        }
        values.update(overrides)

        return build_baseline_revision(**values)

    def test_builds_frozen_revision_contract(self):
        revision = self.build()

        self.assertEqual(
            revision["schema_name"],
            BASELINE_REVISION_SCHEMA_NAME,
        )
        self.assertEqual(
            revision["schema_version"],
            "0.1.0",
        )
        self.assertEqual(
            revision["visibility"],
            "private_local_only",
        )
        self.assertEqual(
            revision["semantics"],
            BASELINE_REVISION_SEMANTICS,
        )
        self.assertTrue(
            all(
                value is False
                for value in (
                    revision[
                        "judgment_boundary"
                    ].values()
                )
            )
        )

    def test_memberships_are_sorted_and_reassigned(self):
        revision = self.build()
        memberships = revision[
            "reference_memberships"
        ]

        self.assertEqual(
            [
                membership["report_bundle_id"]
                for membership in memberships
            ],
            [
                self.bundle_id(1),
                self.bundle_id(2),
            ],
        )
        self.assertEqual(
            [
                membership["membership_id"]
                for membership in memberships
            ],
            [
                "ref_0001",
                "ref_0002",
            ],
        )

    def test_build_is_deterministic(self):
        first = self.build()
        second = self.build()

        self.assertEqual(first, second)

    def test_does_not_mutate_inputs(self):
        policy = self.dimension_policy()
        memberships = [
            self.membership(2),
            self.membership(1),
        ]

        original_policy = copy.deepcopy(policy)
        original_memberships = copy.deepcopy(
            memberships
        )

        self.build(
            dimension_policy=policy,
            reference_memberships=memberships,
        )

        self.assertEqual(
            policy,
            original_policy,
        )
        self.assertEqual(
            memberships,
            original_memberships,
        )

    def test_dimension_policy_is_canonical(self):
        policy = normalize_dimension_policy(
            self.dimension_policy()
        )

        self.assertEqual(
            list(policy["match_values"]),
            [
                "robot_model",
                "site_id",
            ],
        )
        self.assertEqual(
            policy["vary_keys"],
            [
                "robot_id",
                "software_version",
            ],
        )
        self.assertEqual(
            policy["required_keys"],
            [
                "robot_id",
                "robot_model",
                "site_id",
                "software_version",
            ],
        )

    def test_dimension_policy_normalizes_nfc(self):
        policy = normalize_dimension_policy({
            "match_values": {
                "cafe\u0301": "value\u0301",
            },
            "vary_keys": [],
            "required_keys": [
                "cafe\u0301",
            ],
        })

        self.assertEqual(
            policy,
            {
                "match_values": {
                    "caf\u00e9": "valu\u00e9",
                },
                "vary_keys": [],
                "required_keys": [
                    "caf\u00e9",
                ],
            },
        )

    def test_rejects_dimension_policy_overlap(self):
        policy = self.dimension_policy()
        policy["vary_keys"].append(
            "robot_model"
        )

        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            self.build(dimension_policy=policy)

    def test_rejects_uncovered_policy_key(self):
        policy = self.dimension_policy()
        policy["required_keys"].remove(
            "robot_id"
        )

        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            self.build(dimension_policy=policy)

    def test_rejects_duplicate_normalized_policy_key(self):
        policy = {
            "match_values": {},
            "vary_keys": [
                "caf\u00e9",
                "cafe\u0301",
            ],
            "required_keys": [
                "caf\u00e9",
            ],
        }

        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            self.build(dimension_policy=policy)

    def test_rejects_more_than_64_required_keys(self):
        required_keys = [
            f"dimension_{index:03d}"
            for index in range(65)
        ]

        policy = {
            "match_values": {},
            "vary_keys": [],
            "required_keys": required_keys,
        }

        with self.assertRaises(
            PrivateBaselineRevisionError
        ) as caught:
            normalize_dimension_policy(policy)

        self.assertEqual(
            caught.exception.code,
            (
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "DIMENSION_KEY_COUNT_EXCEEDED"
            ),
        )

    def test_accepts_exactly_64_required_keys(self):
        required_keys = [
            f"dimension_{index:03d}"
            for index in range(64)
        ]

        policy = normalize_dimension_policy({
            "match_values": {},
            "vary_keys": [],
            "required_keys": list(
                reversed(required_keys)
            ),
        })

        self.assertEqual(
            policy["required_keys"],
            required_keys,
        )

    def test_rejects_missing_required_dimension(self):
        dimensions = {
            "robot_model": "model-a",
            "site_id": "site-a",
            "robot_id": "robot-1",
        }

        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            self.build(
                reference_memberships=[
                    self.membership(
                        1,
                        dimensions=dimensions,
                    ),
                ]
            )

    def test_rejects_match_value_mismatch(self):
        dimensions = {
            "robot_model": "model-b",
            "site_id": "site-a",
            "robot_id": "robot-1",
            "software_version": "v1",
        }

        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            self.build(
                reference_memberships=[
                    self.membership(
                        1,
                        dimensions=dimensions,
                    ),
                ]
            )

    def test_preserves_explicit_additional_dimensions(self):
        dimensions = {
            "robot_model": "model-a",
            "site_id": "site-a",
            "robot_id": "robot-1",
            "software_version": "v1",
            "test_condition": "wet-floor",
        }

        revision = self.build(
            reference_memberships=[
                self.membership(
                    1,
                    dimensions=dimensions,
                ),
            ]
        )

        self.assertEqual(
            revision[
                "reference_memberships"
            ][0]["dimensions"]["test_condition"],
            "wet-floor",
        )

    def test_rejects_zero_references(self):
        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            self.build(
                reference_memberships=[],
            )

    def test_rejects_thirty_third_reference(self):
        memberships = [
            self.membership(index)
            for index in range(1, 34)
        ]

        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            self.build(
                reference_memberships=memberships,
            )

    def test_rejects_duplicate_report_bundle_id(self):
        membership = self.membership(1)

        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            self.build(
                reference_memberships=[
                    membership,
                    copy.deepcopy(membership),
                ],
            )

    def test_rejects_user_supplied_membership_id(self):
        membership = self.membership(1)
        membership["membership_id"] = (
            "ref_0001"
        )

        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            self.build(
                reference_memberships=[
                    membership,
                ],
            )

    def test_rejects_local_path_in_membership(self):
        membership = self.membership(1)
        membership["bundle_path"] = (
            "/private/reference"
        )

        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            self.build(
                reference_memberships=[
                    membership,
                ],
            )

    def test_rejects_invalid_bundle_id(self):
        membership = self.membership(1)
        membership["report_bundle_id"] = (
            "vrb_sha256_invalid"
        )

        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            self.build(
                reference_memberships=[
                    membership,
                ],
            )

    def test_rejects_uppercase_manifest_digest(self):
        membership = self.membership(1)
        membership[
            "report_manifest_sha256"
        ] = "A" * 64

        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            self.build(
                reference_memberships=[
                    membership,
                ],
            )

    def test_accepts_timezone_aware_and_z_timestamps(self):
        revision = self.build(
            created_at="2026-07-20T02:00:00Z",
            reference_memberships=[
                self.membership(
                    1,
                    selected_at=(
                        "2026-07-20T01:00:00Z"
                    ),
                ),
            ],
        )

        self.assertEqual(
            revision["created_at"],
            "2026-07-20T02:00:00Z",
        )

    def test_rejects_naive_revision_timestamp(self):
        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            self.build(
                created_at=(
                    "2026-07-20T11:00:00"
                ),
            )

    def test_rejects_naive_selection_timestamp(self):
        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            self.build(
                reference_memberships=[
                    self.membership(
                        1,
                        selected_at=(
                            "2026-07-20T10:00:00"
                        ),
                    ),
                ],
            )

    def test_parent_revision_is_preserved(self):
        parent = self.revision_id("3")
        revision = self.build(
            parent_revision_id=parent,
        )

        self.assertEqual(
            revision["parent_revision_id"],
            parent,
        )

    def test_rejects_parent_self_reference(self):
        revision_id = self.revision_id()

        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            self.build(
                baseline_revision_id=revision_id,
                parent_revision_id=revision_id,
            )

    def test_rejects_invalid_parent_revision_id(self):
        with self.assertRaises(
            PrivateBaselineContractError
        ):
            self.build(
                parent_revision_id="revision-1",
            )

    def test_normalizes_selection_note(self):
        revision = self.build(
            reference_memberships=[
                self.membership(
                    1,
                    selection_note=(
                        "cafe\u0301\r\nreviewed"
                    ),
                ),
            ],
        )

        note = revision[
            "reference_memberships"
        ][0]["selection"]["selection_note"]

        self.assertEqual(
            note,
            "caf\u00e9\nreviewed",
        )

    def test_validate_round_trip(self):
        revision = self.build()

        validated = validate_baseline_revision(
            revision
        )

        self.assertEqual(
            validated,
            revision,
        )
        self.assertIsNot(
            validated,
            revision,
        )

    def test_validate_rejects_wrong_membership_id(self):
        revision = self.build()
        revision[
            "reference_memberships"
        ][0]["membership_id"] = "ref_0002"

        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            validate_baseline_revision(revision)

    def test_validate_rejects_noncanonical_order(self):
        revision = self.build()
        revision[
            "reference_memberships"
        ].reverse()

        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            validate_baseline_revision(revision)

    def test_validate_rejects_enabled_judgment(self):
        revision = self.build()
        revision["judgment_boundary"][
            "regression_judgment"
        ] = True

        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            validate_baseline_revision(revision)

    def test_validate_rejects_unknown_top_level_field(self):
        revision = self.build()
        revision["automatic_result"] = (
            "regression"
        )

        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            validate_baseline_revision(revision)

    def test_validate_rejects_wrong_schema(self):
        revision = self.build()
        revision["schema_name"] = (
            "velune.other_revision"
        )

        with self.assertRaises(
            PrivateBaselineRevisionError
        ):
            validate_baseline_revision(revision)


if __name__ == "__main__":
    unittest.main()
