"""Pure Private Baseline v1 contract primitives."""

from collections.abc import Iterator, Mapping
from types import MappingProxyType
import re
import secrets
import unicodedata
from typing import Any

from velune_trace.private_baseline.errors import (
    PrivateBaselineContractError,
)


PRIVATE_BASELINE_SCHEMA_VERSION = "0.1.0"
PRIVATE_BASELINE_VISIBILITY = "private_local_only"

PRIVATE_BASELINE_PRESENTATION_POLICY_VERSION = "0.1.0"

MARKDOWN_REFERENCE_PREVIEW_LIMIT = 10
MARKDOWN_TOPIC_PREVIEW_LIMIT = 5
MARKDOWN_TOPIC_DETAIL_LIMIT = 20
MARKDOWN_FIELD_DETAIL_LIMIT_PER_TOPIC = 50

IDENTIFIER_RANDOM_BYTE_COUNT = 16
IDENTIFIER_HEX_LENGTH = 32
IDENTIFIER_COLLISION_RETRY_LIMIT = 32

REFERENCE_MEMBERSHIP_LIMIT = 32
MAX_DIMENSION_KEYS = 64

DIMENSION_KEY_MAX_LENGTH = 64
DIMENSION_VALUE_MAX_LENGTH = 256
DISPLAY_NAME_MAX_LENGTH = 256
HUMAN_LABEL_MAX_LENGTH = 128
REVIEWER_IDENTITY_MAX_LENGTH = 256
ACTOR_IDENTITY_MAX_LENGTH = 256
CUSTOM_AXIS_VALUE_MAX_LENGTH = 64
MULTILINE_NOTE_MAX_LENGTH = 4096

# Resource-safety limits applied before Unicode normalization.
# These are deliberately larger than every normalized v1 field limit.
_MAX_SINGLE_LINE_RAW_CODEPOINTS = 8192
_MAX_MULTILINE_RAW_CODEPOINTS = 65536

BASELINE_ID_KIND = "baseline"
BASELINE_REVISION_ID_KIND = "baseline_revision"
EVALUATION_ID_KIND = "evaluation"
REVIEW_RECORD_ID_KIND = "review_record"

ID_PREFIX_BY_KIND = MappingProxyType({
    BASELINE_ID_KIND: "vpb_",
    BASELINE_REVISION_ID_KIND: "vpbr_",
    EVALUATION_ID_KIND: "vpbe_",
    REVIEW_RECORD_ID_KIND: "vpbrr_",
})

PRIVATE_BASELINE_JUDGMENT_BOUNDARY = MappingProxyType({
    "root_cause_conclusion": False,
    "cause_inference": False,
    "fault_assignment": False,
    "liability_calculation": False,
    "safety_certification": False,
    "safety_classification": False,
    "severity_judgment": False,
    "normality_judgment": False,
    "superiority_judgment": False,
    "regression_judgment": False,
    "automatic_regression_judgment": False,
    "automatic_improvement_judgment": False,
    "automatic_reference_selection": False,
})

# All Unicode Cc control ranges plus line and paragraph separators.
_SINGLE_LINE_FORBIDDEN_PATTERN = re.compile(
    r"[\x00-\x1f\x7f-\x9f\u2028\u2029]"
)

# LF and tab are intentionally excluded because multiline notes
# permit them. CR is converted to LF before this pattern is applied.
_MULTILINE_FORBIDDEN_PATTERN = re.compile(
    r"[\x00-\x08\x0b\x0c\x0d-\x1f"
    r"\x7f-\x9f\u2028\u2029]"
)


def _raise_contract_error(
    message: str,
    *,
    code: str,
    hint: str,
) -> None:
    raise PrivateBaselineContractError(
        message,
        code=code,
        hint=hint,
        stage="private_baseline_contract",
    )


def _require_field_name(
    field_name: Any,
) -> str:
    if (
        not isinstance(field_name, str)
        or not field_name
        or field_name != field_name.strip()
    ):
        _raise_contract_error(
            "field_name must be a non-empty string "
            "without surrounding whitespace.",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "FIELD_NAME_INVALID"
            ),
            hint=(
                "Use the canonical Private Baseline "
                "contract field path."
            ),
        )

    return field_name


def _require_identifier_kind(
    kind: Any,
) -> str:
    if (
        not isinstance(kind, str)
        or kind not in ID_PREFIX_BY_KIND
    ):
        _raise_contract_error(
            f"Unsupported Private Baseline identifier "
            f"kind: {kind!r}",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "IDENTIFIER_KIND_INVALID"
            ),
            hint=(
                "Use baseline, baseline_revision, "
                "evaluation, or review_record."
            ),
        )

    return kind


def _require_max_length(
    max_length: Any,
) -> int:
    valid = (
        isinstance(max_length, int)
        and not isinstance(max_length, bool)
        and 0 < max_length
        <= _MAX_SINGLE_LINE_RAW_CODEPOINTS
    )

    if not valid:
        _raise_contract_error(
            "max_length must be a positive integer not "
            "greater than the single-line raw input cap.",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "TEXT_LIMIT_INVALID"
            ),
            hint=(
                "Use the frozen v1 field-specific length "
                "constant."
            ),
        )

    return max_length


def _require_unicode_scalar_string(
    value: str,
    *,
    field_name: str,
    error_code: str,
) -> None:
    # Strict UTF-8 encoding is implemented in native code and rejects
    # unpaired Python surrogate code points.
    try:
        value.encode(
            "utf-8",
            errors="strict",
        )
    except UnicodeEncodeError as exc:
        raise PrivateBaselineContractError(
            f"{field_name} must contain only valid Unicode "
            "scalar values.",
            code=error_code,
            hint=(
                "Remove unpaired surrogate code points."
            ),
            stage="private_baseline_contract",
        ) from exc


def _require_generator_output(
    token: Any,
) -> str:
    valid = (
        isinstance(token, str)
        and len(token) == IDENTIFIER_HEX_LENGTH
        and all(
            character in "0123456789abcdef"
            for character in token
        )
    )

    if not valid:
        _raise_contract_error(
            "Opaque identifier generator returned an "
            "invalid token.",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "IDENTIFIER_GENERATOR_OUTPUT_INVALID"
            ),
            hint=(
                "The generator must return exactly "
                "32 lowercase hexadecimal characters."
            ),
        )

    return token


def validate_opaque_identifier(
    value: Any,
    kind: str,
) -> str:
    """Validate one prefixed 128-bit Private Baseline identifier."""

    identifier_kind = _require_identifier_kind(kind)
    prefix = ID_PREFIX_BY_KIND[identifier_kind]

    if not isinstance(value, str):
        _raise_contract_error(
            f"{identifier_kind} identifier must be a string.",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "IDENTIFIER_TYPE_INVALID"
            ),
            hint=(
                f"Use {prefix} followed by "
                f"{IDENTIFIER_HEX_LENGTH} lowercase "
                "hexadecimal characters."
            ),
        )

    suffix = (
        value[len(prefix):]
        if value.startswith(prefix)
        else ""
    )

    valid = (
        value.startswith(prefix)
        and len(suffix) == IDENTIFIER_HEX_LENGTH
        and all(
            character in "0123456789abcdef"
            for character in suffix
        )
    )

    if not valid:
        _raise_contract_error(
            f"{identifier_kind} identifier has an invalid "
            "opaque identifier format.",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "IDENTIFIER_FORMAT_INVALID"
            ),
            hint=(
                f"Use {prefix} followed by exactly "
                f"{IDENTIFIER_HEX_LENGTH} lowercase "
                "hexadecimal characters."
            ),
        )

    return value


def _iter_opaque_identifier_candidates(
    kind: str,
) -> Iterator[str]:
    """Yield at most 32 candidates for atomic storage reservation.

    Candidate generation does not establish uniqueness.

    The storage installer must atomically claim one candidate and move
    to the next candidate when the storage layer reports a collision.

    Machine, process, thread, customer, path, and timestamp data are
    intentionally excluded from the external identifier.
    """

    identifier_kind = _require_identifier_kind(kind)
    prefix = ID_PREFIX_BY_KIND[identifier_kind]

    for _attempt in range(
        IDENTIFIER_COLLISION_RETRY_LIMIT
    ):
        try:
            token = secrets.token_hex(
                IDENTIFIER_RANDOM_BYTE_COUNT
            )
        except Exception as exc:
            raise PrivateBaselineContractError(
                "Opaque identifier generation failed.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_"
                    "IDENTIFIER_GENERATION_FAILED"
                ),
                hint=(
                    "Confirm that the operating system "
                    "secure random source is available."
                ),
                stage="private_baseline_contract",
            ) from exc

        candidate = (
            f"{prefix}"
            f"{_require_generator_output(token)}"
        )

        yield validate_opaque_identifier(
            candidate,
            identifier_kind,
        )


def _generate_opaque_identifier_candidate(
    kind: str,
) -> str:
    """Generate one candidate without claiming storage uniqueness."""

    return next(
        _iter_opaque_identifier_candidates(
            kind,
        )
    )


def generate_baseline_id_candidate() -> str:
    return _generate_opaque_identifier_candidate(
        BASELINE_ID_KIND,
    )


def generate_baseline_revision_id_candidate() -> str:
    return _generate_opaque_identifier_candidate(
        BASELINE_REVISION_ID_KIND,
    )


def generate_evaluation_id_candidate() -> str:
    return _generate_opaque_identifier_candidate(
        EVALUATION_ID_KIND,
    )


def generate_review_record_id_candidate() -> str:
    return _generate_opaque_identifier_candidate(
        REVIEW_RECORD_ID_KIND,
    )


def normalize_single_line_text(
    value: Any,
    *,
    field_name: str,
    max_length: int,
) -> str:
    """Normalize and validate one required single-line field."""

    field_name = _require_field_name(field_name)
    max_length = _require_max_length(max_length)

    if not isinstance(value, str):
        _raise_contract_error(
            f"{field_name} must be a string.",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "TEXT_TYPE_INVALID"
            ),
            hint=(
                "Provide a Unicode string under the "
                "field-specific length limit."
            ),
        )

    # len(str) is O(1) in CPython. This blocks oversized input before
    # NFC normalization or complete control-character scanning.
    if len(value) > _MAX_SINGLE_LINE_RAW_CODEPOINTS:
        _raise_contract_error(
            f"{field_name} exceeds the raw single-line "
            "input safety cap.",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "TEXT_RAW_INPUT_TOO_LARGE"
            ),
            hint=(
                "Reject oversized text before Unicode "
                "normalization."
            ),
        )

    _require_unicode_scalar_string(
        value,
        field_name=field_name,
        error_code=(
            "VELUNE_PRIVATE_BASELINE_"
            "TEXT_SURROGATE_INVALID"
        ),
    )

    # The contract rejects forbidden characters. It does not silently
    # remove or replace them.
    if _SINGLE_LINE_FORBIDDEN_PATTERN.search(value):
        _raise_contract_error(
            f"{field_name} contains a forbidden "
            "single-line control character.",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "TEXT_CONTROL_CHARACTER_INVALID"
            ),
            hint=(
                "Single-line fields must not contain "
                "CR, LF, tab, line separators, or "
                "control characters."
            ),
        )

    normalized = unicodedata.normalize(
        "NFC",
        value,
    )

    if _SINGLE_LINE_FORBIDDEN_PATTERN.search(
        normalized
    ):
        _raise_contract_error(
            f"{field_name} contains a forbidden "
            "character after Unicode normalization.",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "TEXT_CONTROL_CHARACTER_INVALID"
            ),
            hint=(
                "Provide a valid single-line value."
            ),
        )

    if not normalized:
        _raise_contract_error(
            f"{field_name} must not be empty.",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "TEXT_EMPTY"
            ),
            hint="Provide a non-empty value.",
        )

    if normalized != normalized.strip():
        _raise_contract_error(
            f"{field_name} must not contain leading or "
            "trailing whitespace.",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "TEXT_SURROUNDING_WHITESPACE"
            ),
            hint=(
                "Remove surrounding whitespace."
            ),
        )

    if len(normalized) > max_length:
        _raise_contract_error(
            f"{field_name} exceeds the maximum length of "
            f"{max_length} Unicode code points.",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "TEXT_LENGTH_EXCEEDED"
            ),
            hint=(
                "Shorten the NFC-normalized value."
            ),
        )

    return normalized


def normalize_multiline_note(
    value: Any,
    *,
    field_name: str,
) -> str:
    """Normalize and validate one optional multiline note."""

    field_name = _require_field_name(field_name)

    if not isinstance(value, str):
        _raise_contract_error(
            f"{field_name} must be a string.",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "NOTE_TYPE_INVALID"
            ),
            hint=(
                "Provide a Unicode note or an empty string."
            ),
        )

    if len(value) > _MAX_MULTILINE_RAW_CODEPOINTS:
        _raise_contract_error(
            f"{field_name} exceeds the raw multiline "
            "input safety cap.",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "NOTE_RAW_INPUT_TOO_LARGE"
            ),
            hint=(
                "Reject oversized text before Unicode "
                "normalization."
            ),
        )

    _require_unicode_scalar_string(
        value,
        field_name=field_name,
        error_code=(
            "VELUNE_PRIVATE_BASELINE_"
            "NOTE_SURROGATE_INVALID"
        ),
    )

    line_normalized = value.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    if _MULTILINE_FORBIDDEN_PATTERN.search(
        line_normalized
    ):
        _raise_contract_error(
            f"{field_name} contains a forbidden "
            "multiline control character.",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "NOTE_CONTROL_CHARACTER_INVALID"
            ),
            hint=(
                "Multiline notes may contain only LF and "
                "tab control characters."
            ),
        )

    normalized = unicodedata.normalize(
        "NFC",
        line_normalized,
    )

    if _MULTILINE_FORBIDDEN_PATTERN.search(
        normalized
    ):
        _raise_contract_error(
            f"{field_name} contains a forbidden character "
            "after Unicode normalization.",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "NOTE_CONTROL_CHARACTER_INVALID"
            ),
            hint=(
                "Use LF for line breaks and remove other "
                "control characters."
            ),
        )

    if len(normalized) > MULTILINE_NOTE_MAX_LENGTH:
        _raise_contract_error(
            f"{field_name} exceeds the maximum length of "
            f"{MULTILINE_NOTE_MAX_LENGTH} Unicode code "
            "points.",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "NOTE_LENGTH_EXCEEDED"
            ),
            hint=(
                "Shorten the note after line-ending and "
                "NFC normalization."
            ),
        )

    return normalized


def normalize_dimensions(
    value: Any,
    *,
    field_name: str = "dimensions",
) -> dict[str, str]:
    """Return a detached, sorted, NFC-normalized dimension map."""

    field_name = _require_field_name(field_name)

    if not isinstance(value, Mapping):
        _raise_contract_error(
            f"{field_name} must be a mapping.",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "DIMENSIONS_TYPE_INVALID"
            ),
            hint=(
                "Provide string dimension keys and values."
            ),
        )

    if len(value) > MAX_DIMENSION_KEYS:
        _raise_contract_error(
            f"{field_name} exceeds the maximum of "
            f"{MAX_DIMENSION_KEYS} keys.",
            code=(
                "VELUNE_PRIVATE_BASELINE_"
                "DIMENSIONS_COUNT_EXCEEDED"
            ),
            hint=(
                "Reduce the number of private dimensions."
            ),
        )

    normalized_dimensions: dict[str, str] = {}

    for raw_key, raw_value in value.items():
        normalized_key = normalize_single_line_text(
            raw_key,
            field_name=f"{field_name}.key",
            max_length=DIMENSION_KEY_MAX_LENGTH,
        )

        if normalized_key in normalized_dimensions:
            _raise_contract_error(
                f"{field_name} contains duplicate keys "
                "after Unicode NFC normalization.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_"
                    "DIMENSION_KEY_DUPLICATE"
                ),
                hint=(
                    "Use unique dimension keys after NFC "
                    "normalization."
                ),
            )

        normalized_value = normalize_single_line_text(
            raw_value,
            field_name=(
                f"{field_name}.{normalized_key}"
            ),
            max_length=DIMENSION_VALUE_MAX_LENGTH,
        )

        normalized_dimensions[
            normalized_key
        ] = normalized_value

    return {
        key: normalized_dimensions[key]
        for key in sorted(normalized_dimensions)
    }


def build_private_baseline_judgment_boundary(
) -> dict[str, bool]:
    """Return a detached JSON-ready disabled judgment boundary."""

    return dict(
        PRIVATE_BASELINE_JUDGMENT_BOUNDARY
    )
