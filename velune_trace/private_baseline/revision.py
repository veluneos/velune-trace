"""Pure immutable Baseline Revision v1 assembly and validation."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from velune_trace.private_baseline.contract import (
    ACTOR_IDENTITY_MAX_LENGTH,
    BASELINE_ID_KIND,
    BASELINE_REVISION_ID_KIND,
    DIMENSION_KEY_MAX_LENGTH,
    MAX_DIMENSION_KEYS,
    PRIVATE_BASELINE_SCHEMA_VERSION,
    PRIVATE_BASELINE_VISIBILITY,
    REFERENCE_MEMBERSHIP_LIMIT,
    build_private_baseline_judgment_boundary,
    normalize_dimensions,
    normalize_multiline_note,
    normalize_single_line_text,
    validate_opaque_identifier,
)
from velune_trace.private_baseline.errors import (
    PrivateBaselineContractError,
)


BASELINE_REVISION_SCHEMA_NAME = (
    "velune.private_baseline_revision"
)
BASELINE_REVISION_SEMANTICS = (
    "user_selected_reference_set"
)

REPORT_BUNDLE_ID_PREFIX = "vrb_sha256_"
SHA256_HEX_LENGTH = 64

MEMBERSHIP_ID_PREFIX = "ref_"
MEMBERSHIP_ID_WIDTH = 4

ISO8601_TIMESTAMP_MAX_LENGTH = 64

_DIMENSION_POLICY_FIELDS = frozenset({
    "match_values",
    "vary_keys",
    "required_keys",
})

_REFERENCE_MEMBERSHIP_INPUT_FIELDS = frozenset({
    "report_bundle_id",
    "report_manifest_sha256",
    "dimensions",
    "selection",
})

_REFERENCE_MEMBERSHIP_FINAL_FIELDS = frozenset({
    "membership_id",
    *_REFERENCE_MEMBERSHIP_INPUT_FIELDS,
})

_SELECTION_REQUIRED_FIELDS = frozenset({
    "selected_by",
    "selected_at",
})

_SELECTION_OPTIONAL_FIELDS = frozenset({
    "selection_note",
})

_REVISION_FIELDS = frozenset({
    "schema_name",
    "schema_version",
    "visibility",
    "semantics",
    "baseline_id",
    "baseline_revision_id",
    "parent_revision_id",
    "created_at",
    "created_by",
    "dimension_policy",
    "reference_memberships",
    "judgment_boundary",
})


class PrivateBaselineRevisionError(
    PrivateBaselineContractError
):
    """Raised when a Baseline Revision violates the v1 contract."""

    default_code = (
        "VELUNE_PRIVATE_BASELINE_REVISION_INVALID"
    )


def _raise_revision_error(
    message: str,
    *,
    code: str,
    hint: str,
) -> None:
    raise PrivateBaselineRevisionError(
        message,
        code=code,
        hint=hint,
        stage="private_baseline_revision",
    )


def _require_mapping(
    value: Any,
    *,
    field_name: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _raise_revision_error(
            f"{field_name} must be a mapping.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "MAPPING_REQUIRED"
            ),
            hint=(
                "Provide the complete JSON object required "
                "by the frozen Private Baseline v1 contract."
            ),
        )

    for key in value:
        if not isinstance(key, str):
            _raise_revision_error(
                f"{field_name} keys must be strings.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_REVISION_"
                    "KEY_TYPE_INVALID"
                ),
                hint=(
                    "Use canonical string field names."
                ),
            )

    return value


def _require_exact_fields(
    value: Mapping[str, Any],
    *,
    required_fields: frozenset[str],
    optional_fields: frozenset[str] = frozenset(),
    field_name: str,
) -> None:
    actual_fields = set(value)
    missing = sorted(
        required_fields.difference(actual_fields)
    )
    unexpected = sorted(
        actual_fields.difference(
            required_fields.union(optional_fields)
        )
    )

    if missing:
        _raise_revision_error(
            f"{field_name} is missing required fields: "
            f"{', '.join(missing)}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "REQUIRED_FIELD_MISSING"
            ),
            hint=(
                "Provide every field required by the "
                "frozen v1 schema."
            ),
        )

    if unexpected:
        _raise_revision_error(
            f"{field_name} contains unexpected fields: "
            f"{', '.join(unexpected)}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "UNEXPECTED_FIELD"
            ),
            hint=(
                "Remove fields outside the frozen v1 "
                "schema."
            ),
        )


def _normalize_string_list(
    value: Any,
    *,
    field_name: str,
) -> list[str]:
    if not isinstance(value, list):
        _raise_revision_error(
            f"{field_name} must be a JSON array.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "STRING_ARRAY_REQUIRED"
            ),
            hint=(
                "Provide a list of explicit private "
                "dimension keys."
            ),
        )

    if len(value) > MAX_DIMENSION_KEYS:
        _raise_revision_error(
            f"{field_name} exceeds the maximum of "
            f"{MAX_DIMENSION_KEYS} dimension keys.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "DIMENSION_KEY_COUNT_EXCEEDED"
            ),
            hint=(
                "A Reference or Target dimensions object "
                "can contain at most 64 keys."
            ),
        )

    normalized_values: list[str] = []
    observed: set[str] = set()

    for index, raw_value in enumerate(value):
        normalized = normalize_single_line_text(
            raw_value,
            field_name=f"{field_name}[{index}]",
            max_length=DIMENSION_KEY_MAX_LENGTH,
        )

        if normalized in observed:
            _raise_revision_error(
                f"{field_name} contains duplicate values "
                "after Unicode NFC normalization.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_REVISION_"
                    "DIMENSION_KEY_DUPLICATE"
                ),
                hint=(
                    "Use unique dimension keys after NFC "
                    "normalization."
                ),
            )

        observed.add(normalized)
        normalized_values.append(normalized)

    return sorted(normalized_values)


def _normalize_timezone_aware_timestamp(
    value: Any,
    *,
    field_name: str,
) -> str:
    normalized = normalize_single_line_text(
        value,
        field_name=field_name,
        max_length=ISO8601_TIMESTAMP_MAX_LENGTH,
    )

    candidate = normalized

    if candidate.endswith("Z"):
        candidate = f"{candidate[:-1]}+00:00"

    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise PrivateBaselineRevisionError(
            f"{field_name} must be a valid ISO-8601 "
            "timestamp.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "TIMESTAMP_INVALID"
            ),
            hint=(
                "Provide a timezone-aware ISO-8601 "
                "timestamp."
            ),
            stage="private_baseline_revision",
        ) from exc

    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
    ):
        _raise_revision_error(
            f"{field_name} must include a timezone.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "TIMESTAMP_TIMEZONE_REQUIRED"
            ),
            hint=(
                "Use Z or an explicit UTC offset."
            ),
        )

    return normalized


def _normalize_lowercase_hex(
    value: Any,
    *,
    field_name: str,
    expected_length: int,
) -> str:
    normalized = normalize_single_line_text(
        value,
        field_name=field_name,
        max_length=expected_length,
    )

    valid = (
        len(normalized) == expected_length
        and all(
            character in "0123456789abcdef"
            for character in normalized
        )
    )

    if not valid:
        _raise_revision_error(
            f"{field_name} must contain exactly "
            f"{expected_length} lowercase hexadecimal "
            "characters.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "HEX_VALUE_INVALID"
            ),
            hint=(
                "Use the verified lowercase digest from "
                "the Core Bundle manifest."
            ),
        )

    return normalized


def _normalize_report_bundle_id(
    value: Any,
    *,
    field_name: str,
) -> str:
    expected_length = (
        len(REPORT_BUNDLE_ID_PREFIX)
        + SHA256_HEX_LENGTH
    )

    normalized = normalize_single_line_text(
        value,
        field_name=field_name,
        max_length=expected_length,
    )

    suffix = (
        normalized[len(REPORT_BUNDLE_ID_PREFIX):]
        if normalized.startswith(
            REPORT_BUNDLE_ID_PREFIX
        )
        else ""
    )

    valid = (
        normalized.startswith(
            REPORT_BUNDLE_ID_PREFIX
        )
        and len(suffix) == SHA256_HEX_LENGTH
        and all(
            character in "0123456789abcdef"
            for character in suffix
        )
    )

    if not valid:
        _raise_revision_error(
            f"{field_name} must be a verified Core Bundle "
            "identifier.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "REPORT_BUNDLE_ID_INVALID"
            ),
            hint=(
                "Use vrb_sha256_ followed by the complete "
                "lowercase SHA-256 digest."
            ),
        )

    return normalized


def _normalize_membership_id(
    value: Any,
    *,
    field_name: str,
) -> str:
    expected_length = (
        len(MEMBERSHIP_ID_PREFIX)
        + MEMBERSHIP_ID_WIDTH
    )

    normalized = normalize_single_line_text(
        value,
        field_name=field_name,
        max_length=expected_length,
    )

    suffix = (
        normalized[len(MEMBERSHIP_ID_PREFIX):]
        if normalized.startswith(
            MEMBERSHIP_ID_PREFIX
        )
        else ""
    )

    valid = (
        normalized.startswith(
            MEMBERSHIP_ID_PREFIX
        )
        and len(suffix) == MEMBERSHIP_ID_WIDTH
        and suffix.isascii()
        and suffix.isdigit()
        and 1 <= int(suffix)
        <= REFERENCE_MEMBERSHIP_LIMIT
    )

    if not valid:
        _raise_revision_error(
            f"{field_name} must use the deterministic "
            "ref_0001 through ref_0032 format.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "MEMBERSHIP_ID_INVALID"
            ),
            hint=(
                "Allow the Revision builder to assign "
                "membership identifiers after sorting."
            ),
        )

    return normalized


def normalize_dimension_policy(
    value: Any,
) -> dict[str, Any]:
    """Validate and canonicalize one explicit dimension policy."""

    policy = _require_mapping(
        value,
        field_name="dimension_policy",
    )

    _require_exact_fields(
        policy,
        required_fields=_DIMENSION_POLICY_FIELDS,
        field_name="dimension_policy",
    )

    match_values = normalize_dimensions(
        policy["match_values"],
        field_name="dimension_policy.match_values",
    )

    vary_keys = _normalize_string_list(
        policy["vary_keys"],
        field_name="dimension_policy.vary_keys",
    )

    required_keys = _normalize_string_list(
        policy["required_keys"],
        field_name="dimension_policy.required_keys",
    )

    match_key_set = set(match_values)
    vary_key_set = set(vary_keys)
    required_key_set = set(required_keys)

    overlap = sorted(
        match_key_set.intersection(vary_key_set)
    )

    if overlap:
        _raise_revision_error(
            "dimension_policy keys cannot be both fixed "
            "match_values and vary_keys: "
            f"{', '.join(overlap)}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "DIMENSION_POLICY_OVERLAP"
            ),
            hint=(
                "Classify each dimension as fixed or "
                "permitted to vary, never both."
            ),
        )

    uncovered = sorted(
        match_key_set.union(vary_key_set).difference(
            required_key_set
        )
    )

    if uncovered:
        _raise_revision_error(
            "Every match_values and vary_keys dimension "
            "must also appear in required_keys: "
            f"{', '.join(uncovered)}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "DIMENSION_POLICY_REQUIRED_KEY_MISSING"
            ),
            hint=(
                "Add all fixed and varying keys to "
                "required_keys."
            ),
        )

    return {
        "match_values": match_values,
        "vary_keys": vary_keys,
        "required_keys": required_keys,
    }


def _validate_membership_dimensions(
    dimensions: Mapping[str, str],
    *,
    dimension_policy: Mapping[str, Any],
    field_name: str,
) -> None:
    required_keys = set(
        dimension_policy["required_keys"]
    )

    missing_required = sorted(
        required_keys.difference(dimensions)
    )

    if missing_required:
        _raise_revision_error(
            f"{field_name} is missing required dimensions: "
            f"{', '.join(missing_required)}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "REQUIRED_DIMENSION_MISSING"
            ),
            hint=(
                "Explicitly provide every dimension "
                "required by the selected Revision policy."
            ),
        )

    mismatches = [
        key
        for key, expected_value in (
            dimension_policy["match_values"].items()
        )
        if dimensions.get(key) != expected_value
    ]

    if mismatches:
        _raise_revision_error(
            f"{field_name} violates fixed match_values: "
            f"{', '.join(sorted(mismatches))}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "MATCH_VALUE_MISMATCH"
            ),
            hint=(
                "Use Reference Bundles whose explicitly "
                "provided dimensions satisfy match_values."
            ),
        )


def _normalize_selection(
    value: Any,
    *,
    field_name: str,
) -> dict[str, str]:
    selection = _require_mapping(
        value,
        field_name=field_name,
    )

    _require_exact_fields(
        selection,
        required_fields=_SELECTION_REQUIRED_FIELDS,
        optional_fields=_SELECTION_OPTIONAL_FIELDS,
        field_name=field_name,
    )

    selected_by = normalize_single_line_text(
        selection["selected_by"],
        field_name=f"{field_name}.selected_by",
        max_length=ACTOR_IDENTITY_MAX_LENGTH,
    )

    selected_at = _normalize_timezone_aware_timestamp(
        selection["selected_at"],
        field_name=f"{field_name}.selected_at",
    )

    selection_note = normalize_multiline_note(
        selection.get("selection_note", ""),
        field_name=f"{field_name}.selection_note",
    )

    return {
        "selected_by": selected_by,
        "selected_at": selected_at,
        "selection_note": selection_note,
    }


def _normalize_reference_membership_input(
    value: Any,
    *,
    index: int,
    dimension_policy: Mapping[str, Any],
) -> dict[str, Any]:
    field_name = f"reference_memberships[{index}]"

    membership = _require_mapping(
        value,
        field_name=field_name,
    )

    _require_exact_fields(
        membership,
        required_fields=(
            _REFERENCE_MEMBERSHIP_INPUT_FIELDS
        ),
        field_name=field_name,
    )

    report_bundle_id = _normalize_report_bundle_id(
        membership["report_bundle_id"],
        field_name=f"{field_name}.report_bundle_id",
    )

    report_manifest_sha256 = _normalize_lowercase_hex(
        membership["report_manifest_sha256"],
        field_name=(
            f"{field_name}.report_manifest_sha256"
        ),
        expected_length=SHA256_HEX_LENGTH,
    )

    dimensions = normalize_dimensions(
        membership["dimensions"],
        field_name=f"{field_name}.dimensions",
    )

    _validate_membership_dimensions(
        dimensions,
        dimension_policy=dimension_policy,
        field_name=f"{field_name}.dimensions",
    )

    selection = _normalize_selection(
        membership["selection"],
        field_name=f"{field_name}.selection",
    )

    return {
        "report_bundle_id": report_bundle_id,
        "report_manifest_sha256": (
            report_manifest_sha256
        ),
        "dimensions": dimensions,
        "selection": selection,
    }


def _build_reference_memberships(
    value: Any,
    *,
    dimension_policy: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        _raise_revision_error(
            "reference_memberships must be a JSON array.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "MEMBERSHIP_ARRAY_REQUIRED"
            ),
            hint=(
                "Provide one through 32 explicitly selected "
                "Reference memberships."
            ),
        )

    membership_count = len(value)

    if not (
        1 <= membership_count
        <= REFERENCE_MEMBERSHIP_LIMIT
    ):
        _raise_revision_error(
            "reference_memberships must contain between "
            "1 and 32 References.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "MEMBERSHIP_COUNT_INVALID"
            ),
            hint=(
                "Create a Revision with at least one and "
                "no more than 32 verified References."
            ),
        )

    normalized_memberships = [
        _normalize_reference_membership_input(
            membership,
            index=index,
            dimension_policy=dimension_policy,
        )
        for index, membership in enumerate(value)
    ]

    observed_bundle_ids: set[str] = set()

    for membership in normalized_memberships:
        report_bundle_id = membership[
            "report_bundle_id"
        ]

        if report_bundle_id in observed_bundle_ids:
            _raise_revision_error(
                "Duplicate Reference report_bundle_id: "
                f"{report_bundle_id}.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_REVISION_"
                    "REFERENCE_BUNDLE_DUPLICATE"
                ),
                hint=(
                    "Each verified Core Bundle may appear "
                    "only once in one Revision."
                ),
            )

        observed_bundle_ids.add(report_bundle_id)

    normalized_memberships.sort(
        key=lambda membership: membership[
            "report_bundle_id"
        ]
    )

    return [
        {
            "membership_id": (
                f"{MEMBERSHIP_ID_PREFIX}"
                f"{position:0{MEMBERSHIP_ID_WIDTH}d}"
            ),
            **membership,
        }
        for position, membership in enumerate(
            normalized_memberships,
            start=1,
        )
    ]


def _normalize_parent_revision_id(
    value: Any,
    *,
    baseline_revision_id: str,
) -> str | None:
    if value is None:
        return None

    parent_revision_id = validate_opaque_identifier(
        value,
        BASELINE_REVISION_ID_KIND,
    )

    if parent_revision_id == baseline_revision_id:
        _raise_revision_error(
            "parent_revision_id must not reference the "
            "Revision itself.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "PARENT_SELF_REFERENCE"
            ),
            hint=(
                "Use null for the first Revision or the "
                "identifier of its immutable predecessor."
            ),
        )

    return parent_revision_id


def build_baseline_revision(
    *,
    baseline_id: Any,
    baseline_revision_id: Any,
    parent_revision_id: Any,
    created_at: Any,
    created_by: Any,
    dimension_policy: Any,
    reference_memberships: Any,
) -> dict[str, Any]:
    """Build one deterministic JSON-ready immutable Revision."""

    normalized_baseline_id = validate_opaque_identifier(
        baseline_id,
        BASELINE_ID_KIND,
    )

    normalized_revision_id = validate_opaque_identifier(
        baseline_revision_id,
        BASELINE_REVISION_ID_KIND,
    )

    normalized_parent_id = (
        _normalize_parent_revision_id(
            parent_revision_id,
            baseline_revision_id=(
                normalized_revision_id
            ),
        )
    )

    normalized_created_at = (
        _normalize_timezone_aware_timestamp(
            created_at,
            field_name="created_at",
        )
    )

    normalized_created_by = (
        normalize_single_line_text(
            created_by,
            field_name="created_by",
            max_length=ACTOR_IDENTITY_MAX_LENGTH,
        )
    )

    normalized_policy = normalize_dimension_policy(
        dimension_policy
    )

    normalized_memberships = (
        _build_reference_memberships(
            reference_memberships,
            dimension_policy=normalized_policy,
        )
    )

    return {
        "schema_name": BASELINE_REVISION_SCHEMA_NAME,
        "schema_version": (
            PRIVATE_BASELINE_SCHEMA_VERSION
        ),
        "visibility": PRIVATE_BASELINE_VISIBILITY,
        "semantics": BASELINE_REVISION_SEMANTICS,
        "baseline_id": normalized_baseline_id,
        "baseline_revision_id": (
            normalized_revision_id
        ),
        "parent_revision_id": normalized_parent_id,
        "created_at": normalized_created_at,
        "created_by": normalized_created_by,
        "dimension_policy": normalized_policy,
        "reference_memberships": (
            normalized_memberships
        ),
        "judgment_boundary": (
            build_private_baseline_judgment_boundary()
        ),
    }


def _validate_judgment_boundary(
    value: Any,
) -> None:
    boundary = _require_mapping(
        value,
        field_name="judgment_boundary",
    )

    expected = (
        build_private_baseline_judgment_boundary()
    )

    _require_exact_fields(
        boundary,
        required_fields=frozenset(expected),
        field_name="judgment_boundary",
    )

    invalid_fields = sorted(
        key
        for key, expected_value in expected.items()
        if (
            boundary.get(key) is not expected_value
            or expected_value is not False
        )
    )

    if invalid_fields:
        _raise_revision_error(
            "Every automated judgment capability must "
            "remain false: "
            f"{', '.join(invalid_fields)}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "JUDGMENT_BOUNDARY_INVALID"
            ),
            hint=(
                "Private Baseline v1 reports observed "
                "differences only."
            ),
        )


def validate_baseline_revision(
    value: Any,
) -> dict[str, Any]:
    """Validate a complete immutable Revision and return canonical data."""

    revision = _require_mapping(
        value,
        field_name="baseline_revision",
    )

    _require_exact_fields(
        revision,
        required_fields=_REVISION_FIELDS,
        field_name="baseline_revision",
    )

    constant_fields = {
        "schema_name": BASELINE_REVISION_SCHEMA_NAME,
        "schema_version": (
            PRIVATE_BASELINE_SCHEMA_VERSION
        ),
        "visibility": PRIVATE_BASELINE_VISIBILITY,
        "semantics": BASELINE_REVISION_SEMANTICS,
    }

    for field_name, expected_value in (
        constant_fields.items()
    ):
        if revision[field_name] != expected_value:
            _raise_revision_error(
                f"{field_name} does not match the frozen "
                "Revision v1 contract.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_REVISION_"
                    "CONTRACT_CONSTANT_INVALID"
                ),
                hint=(
                    f"Use the required value: "
                    f"{expected_value}."
                ),
            )

    supplied_memberships = revision[
        "reference_memberships"
    ]

    if not isinstance(supplied_memberships, list):
        _raise_revision_error(
            "reference_memberships must be a JSON array.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "MEMBERSHIP_ARRAY_REQUIRED"
            ),
            hint=(
                "Restore the complete immutable Revision "
                "record."
            ),
        )

    raw_memberships: list[dict[str, Any]] = []
    normalized_supplied: list[dict[str, Any]] = []

    normalized_policy = normalize_dimension_policy(
        revision["dimension_policy"]
    )

    for index, supplied in enumerate(
        supplied_memberships
    ):
        field_name = (
            f"reference_memberships[{index}]"
        )

        membership = _require_mapping(
            supplied,
            field_name=field_name,
        )

        _require_exact_fields(
            membership,
            required_fields=(
                _REFERENCE_MEMBERSHIP_FINAL_FIELDS
            ),
            field_name=field_name,
        )

        membership_id = _normalize_membership_id(
            membership["membership_id"],
            field_name=f"{field_name}.membership_id",
        )

        raw_membership = {
            key: membership[key]
            for key in (
                "report_bundle_id",
                "report_manifest_sha256",
                "dimensions",
                "selection",
            )
        }

        normalized_raw = (
            _normalize_reference_membership_input(
                raw_membership,
                index=index,
                dimension_policy=normalized_policy,
            )
        )

        raw_memberships.append(raw_membership)
        normalized_supplied.append({
            "membership_id": membership_id,
            **normalized_raw,
        })

    _validate_judgment_boundary(
        revision["judgment_boundary"]
    )

    expected = build_baseline_revision(
        baseline_id=revision["baseline_id"],
        baseline_revision_id=(
            revision["baseline_revision_id"]
        ),
        parent_revision_id=(
            revision["parent_revision_id"]
        ),
        created_at=revision["created_at"],
        created_by=revision["created_by"],
        dimension_policy=normalized_policy,
        reference_memberships=raw_memberships,
    )

    if (
        normalized_supplied
        != expected["reference_memberships"]
    ):
        _raise_revision_error(
            "Reference memberships are not in canonical "
            "report_bundle_id order or use incorrect "
            "deterministic membership identifiers.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REVISION_"
                "MEMBERSHIP_CANONICAL_ORDER_INVALID"
            ),
            hint=(
                "Sort by report_bundle_id and assign "
                "ref_0001 through ref_0032 in order."
            ),
        )

    return expected
