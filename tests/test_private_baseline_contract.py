import copy
import unittest
from unittest.mock import patch

import velune_trace.private_baseline.contract as contract_module
from velune_trace.private_baseline import (
    BASELINE_ID_KIND,
    BASELINE_REVISION_ID_KIND,
    DIMENSION_KEY_MAX_LENGTH,
    EVALUATION_ID_KIND,
    IDENTIFIER_COLLISION_RETRY_LIMIT,
    ID_PREFIX_BY_KIND,
    MAX_DIMENSION_KEYS,
    MULTILINE_NOTE_MAX_LENGTH,
    PRIVATE_BASELINE_JUDGMENT_BOUNDARY,
    PRIVATE_BASELINE_SCHEMA_VERSION,
    PRIVATE_BASELINE_VISIBILITY,
    PrivateBaselineContractError,
    REFERENCE_MEMBERSHIP_LIMIT,
    REVIEW_RECORD_ID_KIND,
    build_private_baseline_judgment_boundary,
    generate_baseline_id_candidate,
    generate_baseline_revision_id_candidate,
    generate_evaluation_id_candidate,
    generate_review_record_id_candidate,
    normalize_dimensions,
    normalize_multiline_note,
    normalize_single_line_text,
    validate_opaque_identifier,
)


class PrivateBaselineIdentifierTests(
    unittest.TestCase
):
    def test_contract_constants_match_frozen_v1(self):
        self.assertEqual(
            PRIVATE_BASELINE_SCHEMA_VERSION,
            "0.1.0",
        )
        self.assertEqual(
            PRIVATE_BASELINE_VISIBILITY,
            "private_local_only",
        )
        self.assertEqual(
            REFERENCE_MEMBERSHIP_LIMIT,
            32,
        )

    def test_generates_each_prefixed_candidate(self):
        cases = (
            (
                generate_baseline_id_candidate,
                "vpb_",
            ),
            (
                generate_baseline_revision_id_candidate,
                "vpbr_",
            ),
            (
                generate_evaluation_id_candidate,
                "vpbe_",
            ),
            (
                generate_review_record_id_candidate,
                "vpbrr_",
            ),
        )

        for generator, prefix in cases:
            with self.subTest(prefix=prefix):
                with patch(
                    "velune_trace.private_baseline."
                    "contract.secrets.token_hex",
                    return_value="a" * 32,
                ) as token_hex:
                    candidate = generator()

                token_hex.assert_called_once_with(16)
                self.assertEqual(
                    candidate,
                    f"{prefix}{'a' * 32}",
                )

    def test_validates_each_identifier_kind(self):
        cases = (
            (
                BASELINE_ID_KIND,
                "vpb_",
            ),
            (
                BASELINE_REVISION_ID_KIND,
                "vpbr_",
            ),
            (
                EVALUATION_ID_KIND,
                "vpbe_",
            ),
            (
                REVIEW_RECORD_ID_KIND,
                "vpbrr_",
            ),
        )

        for kind, prefix in cases:
            identifier = f"{prefix}{'0' * 32}"

            with self.subTest(kind=kind):
                self.assertEqual(
                    validate_opaque_identifier(
                        identifier,
                        kind,
                    ),
                    identifier,
                )

    def test_rejects_unknown_identifier_kind(self):
        with self.assertRaises(
            PrivateBaselineContractError
        ) as caught:
            validate_opaque_identifier(
                f"vpb_{'0' * 32}",
                "unknown",
            )

        self.assertEqual(
            caught.exception.code,
            (
                "VELUNE_PRIVATE_BASELINE_"
                "IDENTIFIER_KIND_INVALID"
            ),
        )
        self.assertEqual(
            caught.exception.stage,
            "private_baseline_contract",
        )

    def test_rejects_invalid_identifier_formats(self):
        invalid_values = (
            None,
            "",
            f"vpb_{'0' * 31}",
            f"vpb_{'0' * 33}",
            f"vpb_{'A' * 32}",
            f"vpbr_{'0' * 32}",
            f"vpb_{'g' * 32}",
            f"vpb_{'0' * 31} ",
        )

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(
                    PrivateBaselineContractError
                ):
                    validate_opaque_identifier(
                        value,
                        BASELINE_ID_KIND,
                    )

    def test_candidate_iterator_is_bounded_to_32(self):
        calls = 0

        def token_hex(_byte_count):
            nonlocal calls
            token = f"{calls:032x}"
            calls += 1
            return token

        with patch(
            "velune_trace.private_baseline."
            "contract.secrets.token_hex",
            side_effect=token_hex,
        ):
            candidates = list(
                contract_module._iter_opaque_identifier_candidates(
                    BASELINE_ID_KIND,
                )
            )

        self.assertEqual(
            len(candidates),
            IDENTIFIER_COLLISION_RETRY_LIMIT,
        )
        self.assertEqual(
            calls,
            IDENTIFIER_COLLISION_RETRY_LIMIT,
        )
        self.assertEqual(
            candidates[0],
            f"vpb_{0:032x}",
        )
        self.assertEqual(
            candidates[-1],
            f"vpb_{31:032x}",
        )

    def test_public_candidate_generator_uses_secure_source(self):
        with patch(
            "velune_trace.private_baseline."
            "contract.secrets.token_hex",
            return_value="f" * 32,
        ) as token_hex:
            candidate = generate_baseline_id_candidate()

        token_hex.assert_called_once_with(16)
        self.assertEqual(
            candidate,
            f"vpb_{'f' * 32}",
        )

    def test_rejects_invalid_generator_output(self):
        invalid_tokens = (
            None,
            "",
            "a" * 31,
            "a" * 33,
            "A" * 32,
            "g" * 32,
        )

        for token in invalid_tokens:
            with self.subTest(token=token):
                with self.assertRaises(
                    PrivateBaselineContractError
                ):
                    with patch(
                        "velune_trace.private_baseline."
                        "contract.secrets.token_hex",
                        return_value=token,
                    ):
                        generate_baseline_id_candidate()

    def test_generator_exception_is_wrapped(self):
        def broken_generator(_count):
            raise RuntimeError("generator failure")

        with patch(
            "velune_trace.private_baseline."
            "contract.secrets.token_hex",
            side_effect=broken_generator,
        ):
            with self.assertRaises(
                PrivateBaselineContractError
            ) as caught:
                generate_baseline_id_candidate()

        self.assertEqual(
            caught.exception.code,
            (
                "VELUNE_PRIVATE_BASELINE_"
                "IDENTIFIER_GENERATION_FAILED"
            ),
        )

    def test_identifier_prefix_mapping_is_immutable(self):
        with self.assertRaises(TypeError):
            ID_PREFIX_BY_KIND[
                BASELINE_ID_KIND
            ] = "changed_"


class PrivateBaselineTextTests(
    unittest.TestCase
):
    def normalize_single(
        self,
        value,
        *,
        max_length=256,
    ):
        return normalize_single_line_text(
            value,
            field_name="field",
            max_length=max_length,
        )

    def test_single_line_normalizes_unicode_nfc(self):
        composed = self.normalize_single(
            "caf\u00e9"
        )
        decomposed = self.normalize_single(
            "cafe\u0301"
        )

        self.assertEqual(
            composed,
            decomposed,
        )
        self.assertEqual(
            composed,
            "caf\u00e9",
        )

    def test_single_line_rejects_empty_and_whitespace(self):
        invalid_values = (
            "",
            " value",
            "value ",
            "\tvalue",
            "value\n",
        )

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(
                    PrivateBaselineContractError
                ):
                    self.normalize_single(value)

    def test_single_line_rejects_instead_of_sanitizing(self):
        with self.assertRaises(
            PrivateBaselineContractError
        ):
            self.normalize_single(
                "first\nsecond"
            )

    def test_single_line_rejects_controls_and_separators(self):
        invalid_values = (
            "a\rb",
            "a\nb",
            "a\tb",
            "a\x00b",
            "a\x7fb",
            "a\x85b",
            "a\u2028b",
            "a\u2029b",
        )

        for value in invalid_values:
            with self.subTest(value=repr(value)):
                with self.assertRaises(
                    PrivateBaselineContractError
                ):
                    self.normalize_single(value)

    def test_single_line_rejects_unpaired_surrogate(self):
        with self.assertRaises(
            PrivateBaselineContractError
        ):
            self.normalize_single(
                "value\ud800"
            )

    def test_single_line_enforces_normalized_limit(self):
        self.assertEqual(
            self.normalize_single(
                "a" * 4,
                max_length=4,
            ),
            "a" * 4,
        )

        with self.assertRaises(
            PrivateBaselineContractError
        ):
            self.normalize_single(
                "a" * 5,
                max_length=4,
            )

    def test_single_line_raw_cap_precedes_normalization(self):
        oversized = (
            "a"
            * (contract_module._MAX_SINGLE_LINE_RAW_CODEPOINTS + 1)
        )

        with patch(
            "velune_trace.private_baseline.contract."
            "unicodedata.normalize"
        ) as normalize:
            with self.assertRaises(
                PrivateBaselineContractError
            ) as caught:
                self.normalize_single(oversized)

        normalize.assert_not_called()
        self.assertEqual(
            caught.exception.code,
            (
                "VELUNE_PRIVATE_BASELINE_"
                "TEXT_RAW_INPUT_TOO_LARGE"
            ),
        )

    def test_single_line_rejects_invalid_limit(self):
        invalid_limits = (
            True,
            0,
            -1,
            contract_module._MAX_SINGLE_LINE_RAW_CODEPOINTS + 1,
        )

        for limit in invalid_limits:
            with self.subTest(limit=limit):
                with self.assertRaises(
                    PrivateBaselineContractError
                ):
                    self.normalize_single(
                        "value",
                        max_length=limit,
                    )

    def test_multiline_normalizes_line_endings_and_nfc(self):
        normalized = normalize_multiline_note(
            "cafe\u0301\r\nline\rnext\tvalue",
            field_name="note",
        )

        self.assertEqual(
            normalized,
            "caf\u00e9\nline\nnext\tvalue",
        )

    def test_multiline_allows_empty_lf_and_tab(self):
        self.assertEqual(
            normalize_multiline_note(
                "",
                field_name="note",
            ),
            "",
        )
        self.assertEqual(
            normalize_multiline_note(
                "a\nb\tc",
                field_name="note",
            ),
            "a\nb\tc",
        )

    def test_multiline_rejects_invalid_controls(self):
        invalid_values = (
            "a\x00b",
            "a\x7fb",
            "a\x85b",
            "a\u2028b",
            "a\u2029b",
            "a\ud800b",
        )

        for value in invalid_values:
            with self.subTest(value=repr(value)):
                with self.assertRaises(
                    PrivateBaselineContractError
                ):
                    normalize_multiline_note(
                        value,
                        field_name="note",
                    )

    def test_multiline_enforces_normalized_limit(self):
        accepted = "a" * MULTILINE_NOTE_MAX_LENGTH

        self.assertEqual(
            normalize_multiline_note(
                accepted,
                field_name="note",
            ),
            accepted,
        )

        with self.assertRaises(
            PrivateBaselineContractError
        ):
            normalize_multiline_note(
                accepted + "a",
                field_name="note",
            )

    def test_multiline_raw_cap_precedes_normalization(self):
        oversized = (
            "a"
            * (contract_module._MAX_MULTILINE_RAW_CODEPOINTS + 1)
        )

        with patch(
            "velune_trace.private_baseline.contract."
            "unicodedata.normalize"
        ) as normalize:
            with self.assertRaises(
                PrivateBaselineContractError
            ) as caught:
                normalize_multiline_note(
                    oversized,
                    field_name="note",
                )

        normalize.assert_not_called()
        self.assertEqual(
            caught.exception.code,
            (
                "VELUNE_PRIVATE_BASELINE_"
                "NOTE_RAW_INPUT_TOO_LARGE"
            ),
        )


class PrivateBaselineDimensionAndBoundaryTests(
    unittest.TestCase
):
    def test_dimensions_are_detached_normalized_and_sorted(self):
        dimensions = {
            "z_key": "value_z",
            "cafe\u0301": "value_cafe\u0301",
            "a_key": "value_a",
        }
        original = copy.deepcopy(dimensions)

        normalized = normalize_dimensions(dimensions)

        self.assertEqual(
            list(normalized),
            [
                "a_key",
                "caf\u00e9",
                "z_key",
            ],
        )
        self.assertEqual(
            normalized["caf\u00e9"],
            "value_caf\u00e9",
        )
        self.assertEqual(
            dimensions,
            original,
        )

    def test_dimensions_reject_normalized_key_collision(self):
        dimensions = {
            "caf\u00e9": "first",
            "cafe\u0301": "second",
        }

        with self.assertRaises(
            PrivateBaselineContractError
        ) as caught:
            normalize_dimensions(dimensions)

        self.assertEqual(
            caught.exception.code,
            (
                "VELUNE_PRIVATE_BASELINE_"
                "DIMENSION_KEY_DUPLICATE"
            ),
        )

    def test_dimensions_reject_too_many_keys(self):
        dimensions = {
            f"key_{index:03d}": "value"
            for index in range(
                MAX_DIMENSION_KEYS + 1
            )
        }

        with self.assertRaises(
            PrivateBaselineContractError
        ):
            normalize_dimensions(dimensions)

    def test_dimensions_reject_invalid_inputs(self):
        with self.assertRaises(
            PrivateBaselineContractError
        ):
            normalize_dimensions([])

        with self.assertRaises(
            PrivateBaselineContractError
        ):
            normalize_dimensions({
                "key": 1,
            })

        with self.assertRaises(
            PrivateBaselineContractError
        ):
            normalize_dimensions({
                "a" * (
                    DIMENSION_KEY_MAX_LENGTH + 1
                ): "value",
            })

    def test_empty_dimensions_are_valid(self):
        self.assertEqual(
            normalize_dimensions({}),
            {},
        )

    def test_judgment_boundary_is_complete_and_disabled(self):
        expected_fields = {
            "root_cause_conclusion",
            "cause_inference",
            "fault_assignment",
            "liability_calculation",
            "safety_certification",
            "safety_classification",
            "severity_judgment",
            "normality_judgment",
            "superiority_judgment",
            "regression_judgment",
            "automatic_regression_judgment",
            "automatic_improvement_judgment",
            "automatic_reference_selection",
        }

        self.assertEqual(
            set(PRIVATE_BASELINE_JUDGMENT_BOUNDARY),
            expected_fields,
        )
        self.assertTrue(
            all(
                value is False
                for value in (
                    PRIVATE_BASELINE_JUDGMENT_BOUNDARY.values()
                )
            )
        )

    def test_judgment_boundary_builder_is_detached(self):
        first = (
            build_private_baseline_judgment_boundary()
        )
        second = (
            build_private_baseline_judgment_boundary()
        )

        self.assertEqual(first, second)
        self.assertIsNot(first, second)

        first["root_cause_conclusion"] = True

        self.assertFalse(
            second["root_cause_conclusion"]
        )
        self.assertFalse(
            PRIVATE_BASELINE_JUDGMENT_BOUNDARY[
                "root_cause_conclusion"
            ]
        )

    def test_judgment_boundary_constant_is_immutable(self):
        with self.assertRaises(TypeError):
            PRIVATE_BASELINE_JUDGMENT_BOUNDARY[
                "root_cause_conclusion"
            ] = True


if __name__ == "__main__":
    unittest.main()
