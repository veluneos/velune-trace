"""Pure Private Baseline Target Evaluation construction."""

from __future__ import annotations

from collections.abc import Mapping
import copy
from datetime import datetime
import re
import unicodedata
from typing import Any

from velune_trace.private_baseline.contract import (
    DIMENSION_KEY_MAX_LENGTH,
    DIMENSION_VALUE_MAX_LENGTH,
    PRIVATE_BASELINE_SCHEMA_VERSION,
    PRIVATE_BASELINE_VISIBILITY,
    normalize_single_line_text,
)
from velune_trace.private_baseline.errors import (
    PrivateBaselineContractError,
)


EVALUATION_SCHEMA_NAME = (
    "velune.private_baseline_evaluation"
)
EVALUATION_SEMANTICS = (
    "observed_against_user_selected_reference_set"
)

EVALUATION_REPORT_FILENAME = (
    "baseline_evaluation_report.json"
)
EVALUATION_SUMMARY_FILENAME = (
    "baseline_evaluation_summary.md"
)

EVALUATION_ID_PREFIX = "vpbe_"
REPORT_BUNDLE_ID_PREFIX = "vrb_sha256_"

_ALLOWED_COMPARISON_AXES = frozenset({
    "before_after",
    "robot_to_robot",
    "site_to_site",
    "version_to_version",
    "incident_deviation",
    "custom",
})

_EVALUATION_CONTEXT_FIELDS = frozenset({
    "comparison_axis",
    "axis_keys",
    "dimensions",
    "note",
})

_IDENTIFIER_PATTERN = re.compile(
    r"^vpbe_[0-9a-f]{32}$"
)
_BASELINE_ID_PATTERN = re.compile(
    r"^vpb_[0-9a-f]{32}$"
)
_REVISION_ID_PATTERN = re.compile(
    r"^vpbr_[0-9a-f]{32}$"
)
_REPORT_BUNDLE_ID_PATTERN = re.compile(
    r"^vrb_sha256_[0-9a-f]{64}$"
)
_SHA256_PATTERN = re.compile(
    r"^[0-9a-f]{64}$"
)

JUDGMENT_BOUNDARY = {
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
}

HUMAN_JUDGMENT_BOUNDARY_STATEMENT = (
    "Velune reports observed differences against a "
    "user-selected private Reference set. Engineers "
    "determine their meaning, cause, and review outcome."
)


class PrivateBaselineEvaluationError(
    PrivateBaselineContractError
):
    """Raised when an Evaluation document cannot be trusted."""

    default_code = (
        "VELUNE_PRIVATE_BASELINE_EVALUATION_INVALID"
    )


def _raise_evaluation_error(
    message: str,
    *,
    code: str,
    hint: str,
) -> None:
    raise PrivateBaselineEvaluationError(
        message,
        code=code,
        hint=hint,
        stage="private_baseline_evaluation",
    )


def _require_mapping(
    value: Any,
    *,
    field_name: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _raise_evaluation_error(
            f"{field_name} must be an object.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "OBJECT_REQUIRED"
            ),
            hint=(
                "Provide the frozen Private Baseline v1 "
                "object structure."
            ),
        )

    return value


def _require_exact_fields(
    value: Mapping[str, Any],
    *,
    required_fields: frozenset[str],
    field_name: str,
) -> None:
    observed = set(value)

    missing = sorted(
        required_fields - observed
    )
    unexpected = sorted(
        observed - required_fields
    )

    if missing:
        _raise_evaluation_error(
            f"{field_name} is missing fields: "
            f"{', '.join(missing)}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "FIELD_MISSING"
            ),
            hint=(
                "Provide every required Private Baseline "
                "v1 field explicitly."
            ),
        )

    if unexpected:
        _raise_evaluation_error(
            f"{field_name} contains unexpected fields: "
            f"{', '.join(unexpected)}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "FIELD_UNEXPECTED"
            ),
            hint=(
                "Remove fields outside the frozen Private "
                "Baseline v1 contract."
            ),
        )


def _normalize_identifier(
    value: Any,
    *,
    field_name: str,
    pattern: re.Pattern[str],
) -> str:
    if not isinstance(value, str):
        _raise_evaluation_error(
            f"{field_name} must be a string.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "IDENTIFIER_INVALID"
            ),
            hint=(
                "Use the required opaque identifier format."
            ),
        )

    if pattern.fullmatch(value) is None:
        _raise_evaluation_error(
            f"{field_name} has an invalid identifier format.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "IDENTIFIER_INVALID"
            ),
            hint=(
                "Use the required prefix followed by "
                "lowercase hexadecimal characters."
            ),
        )

    return value


def _normalize_timestamp(
    value: Any,
    *,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        _raise_evaluation_error(
            f"{field_name} must be an ISO-8601 string.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "TIMESTAMP_INVALID"
            ),
            hint=(
                "Provide an ISO-8601 timestamp with a "
                "timezone offset."
            ),
        )

    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise PrivateBaselineEvaluationError(
            f"{field_name} is not valid ISO-8601.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "TIMESTAMP_INVALID"
            ),
            hint=(
                "Provide an ISO-8601 timestamp with a "
                "timezone offset."
            ),
            stage="private_baseline_evaluation",
        ) from exc

    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
    ):
        _raise_evaluation_error(
            f"{field_name} must include a timezone offset.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "TIMESTAMP_TIMEZONE_REQUIRED"
            ),
            hint=(
                "Use a timestamp such as "
                "2026-07-21T12:00:00+09:00."
            ),
        )

    return parsed.isoformat()


def _normalize_note(value: Any) -> str:
    if value is None:
        value = ""

    if not isinstance(value, str):
        _raise_evaluation_error(
            "evaluation_context.note must be a string.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "NOTE_INVALID"
            ),
            hint=(
                "Provide an optional human-authored note."
            ),
        )

    normalized = unicodedata.normalize(
        "NFC",
        value.replace("\r\n", "\n").replace(
            "\r",
            "\n",
        ),
    )

    if len(normalized) > 4096:
        _raise_evaluation_error(
            "evaluation_context.note exceeds 4096 "
            "Unicode code points.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "NOTE_TOO_LONG"
            ),
            hint=(
                "Shorten the human-authored Evaluation note."
            ),
        )

    for character in normalized:
        codepoint = ord(character)

        if 0xD800 <= codepoint <= 0xDFFF:
            _raise_evaluation_error(
                "evaluation_context.note contains an "
                "unpaired surrogate.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "NOTE_CONTROL_INVALID"
                ),
                hint=(
                    "Use valid Unicode scalar values."
                ),
            )

        if character in {"\n", "\t"}:
            continue

        if character in {"\u2028", "\u2029"}:
            _raise_evaluation_error(
                "evaluation_context.note contains a "
                "forbidden line separator.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "NOTE_CONTROL_INVALID"
                ),
                hint=(
                    "Use LF for line breaks."
                ),
            )

        if unicodedata.category(
            character
        ).startswith("C"):
            _raise_evaluation_error(
                "evaluation_context.note contains a "
                "forbidden control character.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "NOTE_CONTROL_INVALID"
                ),
                hint=(
                    "Use printable text, LF, and tab only."
                ),
            )

    return normalized


def _normalize_dimensions(
    value: Any,
) -> dict[str, str]:
    mapping = _require_mapping(
        value,
        field_name=(
            "evaluation_context.dimensions"
        ),
    )

    if len(mapping) > 64:
        _raise_evaluation_error(
            "evaluation_context.dimensions exceeds "
            "64 entries.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "DIMENSION_LIMIT_EXCEEDED"
            ),
            hint=(
                "Use no more than 64 explicit private "
                "dimension keys."
            ),
        )

    normalized: dict[str, str] = {}

    for raw_key, raw_value in mapping.items():
        key = normalize_single_line_text(
            raw_key,
            field_name=(
                "evaluation_context.dimensions key"
            ),
            max_length=DIMENSION_KEY_MAX_LENGTH,
        )
        dimension_value = normalize_single_line_text(
            raw_value,
            field_name=(
                "evaluation_context.dimensions"
                f"[{key!r}]"
            ),
            max_length=DIMENSION_VALUE_MAX_LENGTH,
        )

        if key in normalized:
            _raise_evaluation_error(
                "Evaluation dimension keys collide after "
                f"normalization: {key}.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "DIMENSION_KEY_COLLISION"
                ),
                hint=(
                    "Use unique dimension keys after NFC "
                    "normalization."
                ),
            )

        normalized[key] = dimension_value

    return {
        key: normalized[key]
        for key in sorted(normalized)
    }


def normalize_evaluation_context(
    evaluation_context: Any,
    *,
    dimension_policy: Any,
) -> dict[str, Any]:
    """Validate explicit Evaluation context against one Revision."""

    context = _require_mapping(
        evaluation_context,
        field_name="evaluation_context",
    )
    _require_exact_fields(
        context,
        required_fields=(
            _EVALUATION_CONTEXT_FIELDS
        ),
        field_name="evaluation_context",
    )

    comparison_axis = (
        normalize_single_line_text(
            context["comparison_axis"],
            field_name=(
                "evaluation_context.comparison_axis"
            ),
            max_length=64,
        )
    )

    if comparison_axis not in (
        _ALLOWED_COMPARISON_AXES
    ):
        _raise_evaluation_error(
            "evaluation_context.comparison_axis is "
            "not supported by Private Baseline v1.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "COMPARISON_AXIS_INVALID"
            ),
            hint=(
                "Use before_after, robot_to_robot, "
                "site_to_site, version_to_version, "
                "incident_deviation, or custom."
            ),
        )

    raw_axis_keys = context["axis_keys"]

    if not isinstance(raw_axis_keys, list):
        _raise_evaluation_error(
            "evaluation_context.axis_keys must be a list.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "AXIS_KEYS_INVALID"
            ),
            hint=(
                "Provide at least one explicit varied "
                "dimension key."
            ),
        )

    if not raw_axis_keys:
        _raise_evaluation_error(
            "evaluation_context.axis_keys must not be empty.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "AXIS_KEYS_EMPTY"
            ),
            hint=(
                "Declare the dimension intentionally varied "
                "for this Evaluation."
            ),
        )

    axis_keys = [
        normalize_single_line_text(
            key,
            field_name=(
                "evaluation_context.axis_keys"
            ),
            max_length=DIMENSION_KEY_MAX_LENGTH,
        )
        for key in raw_axis_keys
    ]

    if len(set(axis_keys)) != len(axis_keys):
        _raise_evaluation_error(
            "evaluation_context.axis_keys contains "
            "duplicates.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "AXIS_KEY_DUPLICATE"
            ),
            hint=(
                "Declare each varied dimension key once."
            ),
        )

    if axis_keys != sorted(axis_keys):
        _raise_evaluation_error(
            "evaluation_context.axis_keys must be "
            "lexicographically sorted.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "AXIS_KEYS_UNSORTED"
            ),
            hint=(
                "Sort axis_keys lexicographically before "
                "Evaluation."
            ),
        )

    dimensions = _normalize_dimensions(
        context["dimensions"]
    )

    policy = _require_mapping(
        dimension_policy,
        field_name="dimension_policy",
    )

    match_values = _require_mapping(
        policy.get("match_values"),
        field_name=(
            "dimension_policy.match_values"
        ),
    )
    vary_keys = policy.get("vary_keys")
    required_keys = policy.get("required_keys")

    if not isinstance(vary_keys, list):
        _raise_evaluation_error(
            "dimension_policy.vary_keys must be a list.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "DIMENSION_POLICY_INVALID"
            ),
            hint=(
                "Use a verified immutable Baseline Revision."
            ),
        )

    if not isinstance(required_keys, list):
        _raise_evaluation_error(
            "dimension_policy.required_keys must be a list.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "DIMENSION_POLICY_INVALID"
            ),
            hint=(
                "Use a verified immutable Baseline Revision."
            ),
        )

    missing_required = sorted(
        set(required_keys) - set(dimensions)
    )

    if missing_required:
        _raise_evaluation_error(
            "Evaluation dimensions are missing required "
            f"keys: {', '.join(missing_required)}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "REQUIRED_DIMENSION_MISSING"
            ),
            hint=(
                "Provide every dimension required by the "
                "selected Baseline Revision."
            ),
        )

    for key, expected_value in (
        match_values.items()
    ):
        if dimensions.get(key) != expected_value:
            _raise_evaluation_error(
                "Evaluation dimension does not match the "
                f"Revision policy: {key}.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "MATCH_VALUE_MISMATCH"
                ),
                hint=(
                    "Use a Target with the required fixed "
                    "dimension value or select another "
                    "immutable Revision."
                ),
            )

    invalid_axis_keys = sorted(
        set(axis_keys) - set(vary_keys)
    )

    if invalid_axis_keys:
        _raise_evaluation_error(
            "Evaluation axis conflicts with the selected "
            "Revision vary_keys: "
            f"{', '.join(invalid_axis_keys)}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "AXIS_POLICY_CONFLICT"
            ),
            hint=(
                "Use only dimensions explicitly permitted "
                "to vary by the selected Revision."
            ),
        )

    conflicting_axis_keys = sorted(
        set(axis_keys) & set(match_values)
    )

    if conflicting_axis_keys:
        _raise_evaluation_error(
            "Evaluation axis conflicts with Revision "
            "match_values: "
            f"{', '.join(conflicting_axis_keys)}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "AXIS_MATCH_VALUE_CONFLICT"
            ),
            hint=(
                "A fixed match_values key cannot also be "
                "an Evaluation axis."
            ),
        )

    missing_axis_dimensions = sorted(
        set(axis_keys) - set(dimensions)
    )

    if missing_axis_dimensions:
        _raise_evaluation_error(
            "Evaluation dimensions are missing axis keys: "
            f"{', '.join(missing_axis_dimensions)}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "AXIS_DIMENSION_MISSING"
            ),
            hint=(
                "Provide a value for every declared "
                "Evaluation axis key."
            ),
        )

    return {
        "comparison_axis": comparison_axis,
        "axis_keys": list(axis_keys),
        "dimensions": dimensions,
        "note": _normalize_note(
            context["note"]
        ),
    }


def _normalize_string_list(
    value: Any,
    *,
    field_name: str,
) -> list[str]:
    if not isinstance(value, list):
        _raise_evaluation_error(
            f"{field_name} must be a list.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "COMPARISON_STRUCTURE_INVALID"
            ),
            hint=(
                "Use an unmodified Comparison v1 report."
            ),
        )

    normalized = []

    for item in value:
        if not isinstance(item, str):
            _raise_evaluation_error(
                f"{field_name} must contain strings.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "COMPARISON_STRUCTURE_INVALID"
                ),
                hint=(
                    "Use an unmodified Comparison v1 report."
                ),
            )

        normalized.append(item)

    if len(normalized) != len(
        set(normalized)
    ):
        _raise_evaluation_error(
            f"{field_name} contains duplicates.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "COMPARISON_STRUCTURE_INVALID"
            ),
            hint=(
                "Use deterministic Comparison v1 output."
            ),
        )

    if normalized != sorted(normalized):
        _raise_evaluation_error(
            f"{field_name} must be sorted.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "COMPARISON_STRUCTURE_INVALID"
            ),
            hint=(
                "Use deterministic Comparison v1 output."
            ),
        )

    return normalized


def _normalize_reference_comparisons(
    reference_comparisons: Any,
    *,
    generated_at: str,
    target_report_bundle_id: str,
) -> list[dict[str, Any]]:
    if not isinstance(
        reference_comparisons,
        list,
    ):
        _raise_evaluation_error(
            "reference_comparisons must be a list.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "REFERENCE_COMPARISONS_INVALID"
            ),
            hint=(
                "Provide one complete Comparison v1 report "
                "per Reference Bundle."
            ),
        )

    if not reference_comparisons:
        _raise_evaluation_error(
            "reference_comparisons must not be empty.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "REFERENCE_COMPARISONS_EMPTY"
            ),
            hint=(
                "Evaluate the Target against every Reference "
                "in the immutable Revision."
            ),
        )

    normalized = []
    observed_reference_ids: set[str] = set()

    for index, raw_record in enumerate(
        reference_comparisons
    ):
        record = _require_mapping(
            raw_record,
            field_name=(
                f"reference_comparisons[{index}]"
            ),
        )
        _require_exact_fields(
            record,
            required_fields=frozenset({
                "reference_report_bundle_id",
                "comparison_report",
            }),
            field_name=(
                f"reference_comparisons[{index}]"
            ),
        )

        reference_id = _normalize_identifier(
            record[
                "reference_report_bundle_id"
            ],
            field_name=(
                "reference_comparisons"
                f"[{index}].reference_report_bundle_id"
            ),
            pattern=_REPORT_BUNDLE_ID_PATTERN,
        )

        if reference_id in observed_reference_ids:
            _raise_evaluation_error(
                "reference_comparisons contains a "
                "duplicate Reference Bundle identity.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "REFERENCE_DUPLICATE"
                ),
                hint=(
                    "Include each immutable Reference "
                    "membership exactly once."
                ),
            )

        observed_reference_ids.add(reference_id)

        report = _require_mapping(
            record["comparison_report"],
            field_name=(
                "reference_comparisons"
                f"[{index}].comparison_report"
            ),
        )

        if (
            report.get("schema_name")
            != "velune.bundle_comparison_report"
        ):
            _raise_evaluation_error(
                "Embedded comparison_report does not use "
                "the Comparison v1 schema.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "COMPARISON_SCHEMA_INVALID"
                ),
                hint=(
                    "Embed the complete unmodified "
                    "Comparison v1 report."
                ),
            )

        if report.get("generated_at") != (
            generated_at
        ):
            _raise_evaluation_error(
                "Embedded comparison_report uses a "
                "different generated_at timestamp.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "PAIRWISE_TIMESTAMP_MISMATCH"
                ),
                hint=(
                    "Use the Evaluation's single captured "
                    "generated_at timestamp for every "
                    "pairwise Comparison."
                ),
            )

        compatibility = _require_mapping(
            report.get("compatibility"),
            field_name=(
                "comparison_report.compatibility"
            ),
        )

        if compatibility.get("status") != (
            "compatible"
        ):
            _raise_evaluation_error(
                "Embedded comparison_report is not "
                "compatible.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "PAIRWISE_INCOMPATIBLE"
                ),
                hint=(
                    "Block the entire Evaluation when any "
                    "Reference and Target pair is "
                    "incompatible."
                ),
            )

        reference_provenance = (
            _require_mapping(
                report.get("reference"),
                field_name=(
                    "comparison_report.reference"
                ),
            )
        )
        target_provenance = (
            _require_mapping(
                report.get("target"),
                field_name=(
                    "comparison_report.target"
                ),
            )
        )

        if (
            reference_provenance.get(
                "report_bundle_id"
            )
            != reference_id
        ):
            _raise_evaluation_error(
                "Embedded Reference Bundle identity does "
                "not match its wrapper record.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "REFERENCE_ID_MISMATCH"
                ),
                hint=(
                    "Preserve the Comparison v1 Reference "
                    "provenance unchanged."
                ),
            )

        if (
            target_provenance.get(
                "report_bundle_id"
            )
            != target_report_bundle_id
        ):
            _raise_evaluation_error(
                "Embedded Target Bundle identity differs "
                "across pairwise reports.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "TARGET_ID_MISMATCH"
                ),
                hint=(
                    "Use the same verified Target Bundle "
                    "for every pairwise Comparison."
                ),
            )

        normalized.append({
            "reference_report_bundle_id": (
                reference_id
            ),
            "comparison_report": copy.deepcopy(
                dict(report)
            ),
        })

    return sorted(
        normalized,
        key=lambda item: item[
            "reference_report_bundle_id"
        ],
    )


def aggregate_reference_comparisons(
    reference_comparisons: Any,
) -> dict[str, Any]:
    """Count observed pairwise differences without scoring."""

    if not isinstance(
        reference_comparisons,
        list,
    ) or not reference_comparisons:
        _raise_evaluation_error(
            "reference_comparisons must contain at least "
            "one pairwise report.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "REFERENCE_COMPARISONS_EMPTY"
            ),
            hint=(
                "Provide one Comparison v1 report per "
                "Reference Bundle."
            ),
        )

    report_states = []
    all_topics: set[str] = set()
    changed_fields_by_topic: dict[
        str,
        set[str],
    ] = {}

    for index, wrapper in enumerate(
        reference_comparisons
    ):
        wrapper_mapping = _require_mapping(
            wrapper,
            field_name=(
                f"reference_comparisons[{index}]"
            ),
        )
        report = _require_mapping(
            wrapper_mapping.get(
                "comparison_report"
            ),
            field_name=(
                "reference_comparisons"
                f"[{index}].comparison_report"
            ),
        )
        topic_set = _require_mapping(
            report.get("topic_set"),
            field_name=(
                "comparison_report.topic_set"
            ),
        )

        common_topics = set(
            _normalize_string_list(
                topic_set.get("common_topics"),
                field_name=(
                    "comparison_report.topic_set."
                    "common_topics"
                ),
            )
        )
        reference_only_topics = set(
            _normalize_string_list(
                topic_set.get(
                    "reference_only_topics"
                ),
                field_name=(
                    "comparison_report.topic_set."
                    "reference_only_topics"
                ),
            )
        )
        target_only_topics = set(
            _normalize_string_list(
                topic_set.get(
                    "target_only_topics"
                ),
                field_name=(
                    "comparison_report.topic_set."
                    "target_only_topics"
                ),
            )
        )

        if (
            common_topics
            & reference_only_topics
            or common_topics
            & target_only_topics
            or reference_only_topics
            & target_only_topics
        ):
            _raise_evaluation_error(
                "Comparison topic-set states overlap.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "TOPIC_SET_STATE_INVALID"
                ),
                hint=(
                    "Use an unmodified Comparison v1 "
                    "topic_set record."
                ),
            )

        pair_changed: dict[
            str,
            set[str],
        ] = {}

        raw_topic_comparisons = report.get(
            "topic_comparisons"
        )

        if not isinstance(
            raw_topic_comparisons,
            list,
        ):
            _raise_evaluation_error(
                "comparison_report.topic_comparisons "
                "must be a list.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "COMPARISON_STRUCTURE_INVALID"
                ),
                hint=(
                    "Use an unmodified Comparison v1 report."
                ),
            )

        for topic_index, raw_topic in enumerate(
            raw_topic_comparisons
        ):
            topic_record = _require_mapping(
                raw_topic,
                field_name=(
                    "comparison_report.topic_comparisons"
                    f"[{topic_index}]"
                ),
            )

            topic = topic_record.get("topic")

            if not isinstance(topic, str):
                _raise_evaluation_error(
                    "Comparison topic name must be a string.",
                    code=(
                        "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                        "COMPARISON_STRUCTURE_INVALID"
                    ),
                    hint=(
                        "Use an unmodified Comparison v1 "
                        "report."
                    ),
                )

            if topic not in common_topics:
                _raise_evaluation_error(
                    "A topic_comparisons record is not "
                    "listed as a common topic.",
                    code=(
                        "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                        "COMPARISON_TOPIC_INCONSISTENT"
                    ),
                    hint=(
                        "Use an internally consistent "
                        "Comparison v1 report."
                    ),
                )

            changed_fields = set(
                _normalize_string_list(
                    topic_record.get(
                        "changed_fields"
                    ),
                    field_name=(
                        "comparison_report."
                        "topic_comparisons"
                        f"[{topic_index}].changed_fields"
                    ),
                )
            )

            pair_changed[topic] = (
                changed_fields
            )

            if changed_fields:
                changed_fields_by_topic.setdefault(
                    topic,
                    set(),
                ).update(changed_fields)

        all_topics.update(common_topics)
        all_topics.update(reference_only_topics)
        all_topics.update(target_only_topics)

        report_states.append({
            "common": common_topics,
            "reference_only": (
                reference_only_topics
            ),
            "target_only": target_only_topics,
            "changed": pair_changed,
        })

    reference_count = len(report_states)

    field_observations = []

    for topic in sorted(
        changed_fields_by_topic
    ):
        eligible_reference_count = sum(
            1
            for state in report_states
            if topic in state["common"]
        )

        for field in sorted(
            changed_fields_by_topic[topic]
        ):
            changed_count = sum(
                1
                for state in report_states
                if (
                    topic in state["common"]
                    and field
                    in state["changed"].get(
                        topic,
                        set(),
                    )
                )
            )

            if changed_count == 0:
                continue

            unchanged_count = (
                eligible_reference_count
                - changed_count
            )

            field_observations.append({
                "topic": topic,
                "field": field,
                "eligible_reference_count": (
                    eligible_reference_count
                ),
                "changed_against_reference_count": (
                    changed_count
                ),
                "unchanged_against_reference_count": (
                    unchanged_count
                ),
                "observation_scope": (
                    "all_references"
                    if changed_count
                    == eligible_reference_count
                    else "some_references"
                ),
            })

    topic_set_observations = []

    for topic in sorted(all_topics):
        common_count = 0
        target_only_count = 0
        reference_only_count = 0
        absent_from_both_count = 0

        for state in report_states:
            if topic in state["common"]:
                common_count += 1
            elif topic in state["target_only"]:
                target_only_count += 1
            elif topic in state["reference_only"]:
                reference_only_count += 1
            else:
                absent_from_both_count += 1

        if (
            common_count
            + target_only_count
            + reference_only_count
            + absent_from_both_count
            != reference_count
        ):
            _raise_evaluation_error(
                "Topic-set directional counts do not sum "
                "to the Reference count.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "TOPIC_SET_INVARIANT_FAILED"
                ),
                hint=(
                    "Preserve one directional topic state "
                    "per Reference comparison."
                ),
            )

        topic_set_observations.append({
            "topic": topic,
            "total_reference_count": (
                reference_count
            ),
            "common_with_target_count": (
                common_count
            ),
            "target_only_against_reference_count": (
                target_only_count
            ),
            "reference_only_against_target_count": (
                reference_only_count
            ),
            "absent_from_both_count": (
                absent_from_both_count
            ),
        })

    changed_topics = sorted({
        observation["topic"]
        for observation in field_observations
    })

    return {
        "reference_count": reference_count,
        "field_observations": (
            field_observations
        ),
        "topic_set_observations": (
            topic_set_observations
        ),
        "summary": {
            "observed_topic_count": len(
                topic_set_observations
            ),
            "changed_topic_count": len(
                changed_topics
            ),
            "changed_field_record_count": len(
                field_observations
            ),
            "all_references_field_count": sum(
                1
                for item in field_observations
                if item["observation_scope"]
                == "all_references"
            ),
            "some_references_field_count": sum(
                1
                for item in field_observations
                if item["observation_scope"]
                == "some_references"
            ),
        },
        "numeric_aggregation": {
            "means_of_ratios": False,
            "medians_of_deltas": False,
            "percentiles": False,
            "standard_deviations": False,
            "confidence_intervals": False,
            "anomaly_probabilities": False,
            "severity_scores": False,
            "weighted_scores": False,
        },
        "reference_weighting": {
            "enabled": False,
            "semantics": (
                "equal_descriptive_occurrence_counts_only"
            ),
        },
    }


def build_private_baseline_evaluation_report(
    *,
    evaluation_id: Any,
    generated_at: Any,
    baseline_id: Any,
    baseline_revision_id: Any,
    dimension_policy: Any,
    evaluation_context: Any,
    target_report_bundle_id: Any,
    target_report_manifest_sha256: Any,
    reference_comparisons: Any,
) -> dict[str, Any]:
    """Build one deterministic JSON-ready Evaluation document."""

    normalized_evaluation_id = (
        _normalize_identifier(
            evaluation_id,
            field_name="evaluation_id",
            pattern=_IDENTIFIER_PATTERN,
        )
    )
    normalized_generated_at = (
        _normalize_timestamp(
            generated_at,
            field_name="generated_at",
        )
    )
    normalized_baseline_id = (
        _normalize_identifier(
            baseline_id,
            field_name="baseline_id",
            pattern=_BASELINE_ID_PATTERN,
        )
    )
    normalized_revision_id = (
        _normalize_identifier(
            baseline_revision_id,
            field_name=(
                "baseline_revision_id"
            ),
            pattern=_REVISION_ID_PATTERN,
        )
    )
    normalized_target_id = (
        _normalize_identifier(
            target_report_bundle_id,
            field_name=(
                "target_report_bundle_id"
            ),
            pattern=_REPORT_BUNDLE_ID_PATTERN,
        )
    )
    normalized_target_manifest_sha256 = (
        _normalize_identifier(
            target_report_manifest_sha256,
            field_name=(
                "target_report_manifest_sha256"
            ),
            pattern=_SHA256_PATTERN,
        )
    )

    normalized_context = (
        normalize_evaluation_context(
            evaluation_context,
            dimension_policy=dimension_policy,
        )
    )

    normalized_comparisons = (
        _normalize_reference_comparisons(
            reference_comparisons,
            generated_at=(
                normalized_generated_at
            ),
            target_report_bundle_id=(
                normalized_target_id
            ),
        )
    )

    aggregate = (
        aggregate_reference_comparisons(
            normalized_comparisons
        )
    )

    return {
        "schema_name": EVALUATION_SCHEMA_NAME,
        "schema_version": (
            PRIVATE_BASELINE_SCHEMA_VERSION
        ),
        "visibility": (
            PRIVATE_BASELINE_VISIBILITY
        ),
        "semantics": EVALUATION_SEMANTICS,
        "evaluation_id": (
            normalized_evaluation_id
        ),
        "generated_at": (
            normalized_generated_at
        ),
        "baseline_id": (
            normalized_baseline_id
        ),
        "baseline_revision_id": (
            normalized_revision_id
        ),
        "evaluation_context": (
            normalized_context
        ),
        "target": {
            "report_bundle_id": (
                normalized_target_id
            ),
            "report_manifest_sha256": (
                normalized_target_manifest_sha256
            ),
            "dimensions": copy.deepcopy(
                normalized_context["dimensions"]
            ),
        },
        "reference_comparisons": (
            normalized_comparisons
        ),
        "aggregate_observations": (
            aggregate
        ),
        "judgment_boundary": copy.deepcopy(
            JUDGMENT_BOUNDARY
        ),
    }
