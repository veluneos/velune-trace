"""Pure in-memory engine for Core Bundle comparison."""

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import math
from typing import Any

from velune_trace.comparison.compatibility import (
    evaluate_bundle_compatibility,
)
from velune_trace.comparison.loader import (
    LoadedComparisonBundle,
)
from velune_trace.reporting.errors import EvidenceBundleError


COMPARISON_SCHEMA_NAME = (
    "velune.bundle_comparison_report"
)
COMPARISON_SCHEMA_VERSION = "0.1.0"
COMPARISON_VISIBILITY = "private_local_only"
COMPARISON_SEMANTICS = "observed_comparison_only"
EVIDENCE_SCORE_SEMANTICS = (
    "ranking_heuristic_only_no_root_cause_inference"
)


@dataclass(frozen=True)
class _MetricSpec:
    """One numeric comparison metric contract."""

    name: str
    value_kind: str


PROFILE_METRIC_SPECS = (
    _MetricSpec("count", "non_negative_integer"),
    _MetricSpec("duration_ns", "non_negative_integer"),
    _MetricSpec("avg_gap_ns", "non_negative_number"),
    _MetricSpec("max_gap_ns", "non_negative_integer"),
    _MetricSpec("jitter_ns", "non_negative_number"),
    _MetricSpec(
        "expected_count_per_window",
        "non_negative_number",
    ),
    _MetricSpec(
        "finalized_window_count",
        "non_negative_integer",
    ),
    _MetricSpec(
        "out_of_order_count",
        "non_negative_integer",
    ),
    _MetricSpec(
        "late_dropped_count",
        "non_negative_integer",
    ),
)

PROFILE_METRIC_FIELDS = tuple(
    spec.name
    for spec in PROFILE_METRIC_SPECS
)

PROFILE_CONTEXT_FIELDS = (
    "sensor_category",
    "expected_count_source",
    "expected_hz",
)

PROFILE_TIMESTAMP_FIELDS = (
    "first_ns",
    "last_ns",
)

EVIDENCE_SUMMARY_FIELDS = (
    "selected_window_count",
    "max_observed_irregularity_score",
    "mean_observed_irregularity_score",
    "min_count_ratio",
    "max_max_gap_ns",
    "max_jitter_ns",
)

EXCLUDED_FROM_CHANGE_EVALUATION = (
    "artifact_hashes",
    "bundle_local_paths",
    "generated_at",
    "output_file_modification_times",
    "report_bundle_id",
)


class BundleComparisonEngineError(EvidenceBundleError):
    """Raised when verified Bundles cannot be compared safely."""

    default_code = "VELUNE_COMPARISON_ENGINE_FAILED"


def _raise_engine_error(
    message: str,
    *,
    code: str,
    hint: str,
) -> None:
    raise BundleComparisonEngineError(
        message,
        code=code,
        hint=hint,
        stage="comparison_engine",
    )


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False

    if not isinstance(value, (int, float)):
        return False

    if isinstance(value, float):
        return math.isfinite(value)

    return True


def _validate_numeric_value(
    value: Any,
    *,
    value_kind: str,
    field_path: str,
) -> int | float:
    if value_kind == "non_negative_integer":
        valid = (
            isinstance(value, int)
            and not isinstance(value, bool)
            and value >= 0
        )
    elif value_kind == "non_negative_number":
        valid = (
            _is_finite_number(value)
            and value >= 0
        )
    else:
        raise ValueError(
            f"Unsupported metric value kind: {value_kind}"
        )

    if not valid:
        _raise_engine_error(
            f"Comparison metric '{field_path}' contains "
            f"an invalid {value_kind} value.",
            code=(
                "VELUNE_COMPARISON_"
                "METRIC_VALUE_INVALID"
            ),
            hint=(
                "Regenerate both Core Report Bundles with "
                "valid finite timing metrics."
            ),
        )

    return value


def compare_numeric_values(
    reference: int | float,
    target: int | float,
) -> dict[str, Any]:
    """Return deterministic delta and ratio semantics."""

    if not _is_finite_number(reference):
        raise TypeError(
            "reference must be a finite non-boolean number"
        )

    if not _is_finite_number(target):
        raise TypeError(
            "target must be a finite non-boolean number"
        )

    delta = target - reference

    if reference == 0:
        if target == 0:
            ratio = 1.0
            ratio_state = "both_zero"
        else:
            ratio = None
            ratio_state = "reference_zero"
    else:
        ratio = target / reference
        ratio_state = "finite"

        if not math.isfinite(ratio):
            raise ValueError(
                "numeric comparison produced a non-finite "
                "ratio"
            )

    return {
        "reference": reference,
        "target": target,
        "delta": delta,
        "ratio": ratio,
        "ratio_state": ratio_state,
    }


def _validate_generated_at(
    generated_at: str,
) -> str:
    if (
        not isinstance(generated_at, str)
        or not generated_at
        or generated_at != generated_at.strip()
    ):
        _raise_engine_error(
            "generated_at must be a non-empty ISO-8601 "
            "timestamp string.",
            code=(
                "VELUNE_COMPARISON_"
                "GENERATED_AT_INVALID"
            ),
            hint=(
                "Provide a timezone-aware ISO-8601 "
                "timestamp."
            ),
        )

    candidate = generated_at

    if candidate.endswith("Z"):
        candidate = (
            f"{candidate[:-1]}+00:00"
        )

    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise BundleComparisonEngineError(
            f"generated_at is not valid ISO-8601: {exc}",
            code=(
                "VELUNE_COMPARISON_"
                "GENERATED_AT_INVALID"
            ),
            hint=(
                "Provide a timezone-aware ISO-8601 "
                "timestamp."
            ),
            stage="comparison_engine",
        ) from exc

    if parsed.tzinfo is None:
        _raise_engine_error(
            "generated_at must include a timezone offset.",
            code=(
                "VELUNE_COMPARISON_"
                "GENERATED_AT_INVALID"
            ),
            hint=(
                "Use a value such as "
                "2026-07-16T00:00:00+00:00."
            ),
        )

    return generated_at


def _require_mapping(
    value: Any,
    *,
    field_path: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _raise_engine_error(
            f"'{field_path}' must be a JSON object.",
            code=(
                "VELUNE_COMPARISON_"
                "STRUCTURE_INVALID"
            ),
            hint=(
                "Regenerate the Core Report Bundle using "
                "the stable Core schema."
            ),
        )

    return value


def _require_field(
    document: Mapping[str, Any],
    field_name: str,
    *,
    field_path: str,
) -> Any:
    if field_name not in document:
        _raise_engine_error(
            f"Required comparison field "
            f"'{field_path}' is missing.",
            code=(
                "VELUNE_COMPARISON_"
                "FIELD_MISSING"
            ),
            hint=(
                "Regenerate the complete Core Report Bundle "
                "before comparison."
            ),
        )

    return document[field_name]


def _validate_topic_contract(
    bundle: LoadedComparisonBundle,
    *,
    role: str,
) -> tuple[str, ...]:
    profile_topics = set(bundle.topic_profile)
    evidence_topics = set(bundle.evidence_windows)

    if profile_topics != evidence_topics:
        profile_only = sorted(
            profile_topics.difference(evidence_topics)
        )
        evidence_only = sorted(
            evidence_topics.difference(profile_topics)
        )

        _raise_engine_error(
            f"{role} Bundle topic_profile.json and "
            f"evidence_windows.json declare different "
            f"topic sets.",
            code=(
                "VELUNE_COMPARISON_"
                "BUNDLE_TOPIC_SET_INCONSISTENT"
            ),
            hint=(
                f"profile_only={profile_only}; "
                f"evidence_only={evidence_only}. "
                f"Regenerate the {role} Bundle."
            ),
        )

    return tuple(sorted(profile_topics))


def _validate_context_value(
    value: Any,
    *,
    field_name: str,
    topic: str,
) -> Any:
    field_path = (
        f"topic_profile[{topic!r}].{field_name}"
    )

    if field_name in {
        "sensor_category",
        "expected_count_source",
    }:
        if (
            not isinstance(value, str)
            or not value
            or value != value.strip()
        ):
            _raise_engine_error(
                f"Context field '{field_path}' must be a "
                f"non-empty string.",
                code=(
                    "VELUNE_COMPARISON_"
                    "CONTEXT_VALUE_INVALID"
                ),
                hint=(
                    "Regenerate the Core Report Bundle with "
                    "valid topic context."
                ),
            )

        return value

    if field_name == "expected_hz":
        if value is None:
            return None

        if (
            not _is_finite_number(value)
            or value < 0
        ):
            _raise_engine_error(
                f"Context field '{field_path}' must be null "
                f"or a non-negative finite number.",
                code=(
                    "VELUNE_COMPARISON_"
                    "CONTEXT_VALUE_INVALID"
                ),
                hint=(
                    "Regenerate the Core Report Bundle with "
                    "valid expected frequency metadata."
                ),
            )

        return value

    raise ValueError(
        f"Unsupported context field: {field_name}"
    )


def _validate_timestamp_value(
    value: Any,
    *,
    field_name: str,
    topic: str,
) -> int | None:
    if value is None:
        return None

    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
    ):
        _raise_engine_error(
            f"Timestamp provenance field "
            f"'topic_profile[{topic!r}].{field_name}' "
            f"must be null or a non-negative integer.",
            code=(
                "VELUNE_COMPARISON_"
                "TIMESTAMP_PROVENANCE_INVALID"
            ),
            hint=(
                "Regenerate the Core Report Bundle with "
                "integer nanosecond timestamps."
            ),
        )

    return value


def _extract_profile(
    bundle: LoadedComparisonBundle,
    topic: str,
) -> dict[str, Any]:
    raw_profile = _require_mapping(
        bundle.topic_profile[topic],
        field_path=f"topic_profile[{topic!r}]",
    )

    metrics = {}

    for spec in PROFILE_METRIC_SPECS:
        value = _require_field(
            raw_profile,
            spec.name,
            field_path=(
                f"topic_profile[{topic!r}].{spec.name}"
            ),
        )
        metrics[spec.name] = _validate_numeric_value(
            value,
            value_kind=spec.value_kind,
            field_path=(
                f"topic_profile[{topic!r}].{spec.name}"
            ),
        )

    context = {}

    for field_name in PROFILE_CONTEXT_FIELDS:
        value = _require_field(
            raw_profile,
            field_name,
            field_path=(
                f"topic_profile[{topic!r}]."
                f"{field_name}"
            ),
        )
        context[field_name] = _validate_context_value(
            value,
            field_name=field_name,
            topic=topic,
        )

    timestamps = {}

    for field_name in PROFILE_TIMESTAMP_FIELDS:
        value = _require_field(
            raw_profile,
            field_name,
            field_path=(
                f"topic_profile[{topic!r}]."
                f"{field_name}"
            ),
        )
        timestamps[field_name] = (
            _validate_timestamp_value(
                value,
                field_name=field_name,
                topic=topic,
            )
        )

    return {
        "metrics": metrics,
        "context": context,
        "timestamps": timestamps,
    }


def _validate_window_metric(
    window: Mapping[str, Any],
    *,
    field_name: str,
    topic: str,
    index: int,
) -> int | float:
    value = _require_field(
        window,
        field_name,
        field_path=(
            f"evidence_windows[{topic!r}]"
            f"[{index}].{field_name}"
        ),
    )

    return _validate_numeric_value(
        value,
        value_kind="non_negative_number",
        field_path=(
            f"evidence_windows[{topic!r}]"
            f"[{index}].{field_name}"
        ),
    )


def _summarize_evidence_windows(
    bundle: LoadedComparisonBundle,
    topic: str,
) -> dict[str, int | float | None]:
    raw_windows = bundle.evidence_windows[topic]

    if not isinstance(raw_windows, list):
        _raise_engine_error(
            f"evidence_windows[{topic!r}] must be a list.",
            code=(
                "VELUNE_COMPARISON_"
                "EVIDENCE_WINDOWS_INVALID"
            ),
            hint=(
                "Regenerate the Core Report Bundle."
            ),
        )

    if not raw_windows:
        return {
            "selected_window_count": 0,
            "max_observed_irregularity_score": None,
            "mean_observed_irregularity_score": None,
            "min_count_ratio": None,
            "max_max_gap_ns": None,
            "max_jitter_ns": None,
        }

    scores = []
    count_ratios = []
    max_gaps = []
    jitters = []

    for index, raw_window in enumerate(raw_windows):
        window = _require_mapping(
            raw_window,
            field_path=(
                f"evidence_windows[{topic!r}]"
                f"[{index}]"
            ),
        )

        score_semantics = _require_field(
            window,
            "score_semantics",
            field_path=(
                f"evidence_windows[{topic!r}]"
                f"[{index}].score_semantics"
            ),
        )

        if score_semantics != EVIDENCE_SCORE_SEMANTICS:
            _raise_engine_error(
                f"Evidence window score semantics differ "
                f"from the v1 comparison contract for "
                f"topic '{topic}'.",
                code=(
                    "VELUNE_COMPARISON_"
                    "SCORE_SEMANTICS_INVALID"
                ),
                hint=(
                    "Use evidence windows generated with "
                    f"'{EVIDENCE_SCORE_SEMANTICS}'."
                ),
            )

        scores.append(
            _validate_window_metric(
                window,
                field_name=(
                    "observed_irregularity_score"
                ),
                topic=topic,
                index=index,
            )
        )
        count_ratios.append(
            _validate_window_metric(
                window,
                field_name="count_ratio",
                topic=topic,
                index=index,
            )
        )
        max_gaps.append(
            _validate_window_metric(
                window,
                field_name="max_gap_ns",
                topic=topic,
                index=index,
            )
        )
        jitters.append(
            _validate_window_metric(
                window,
                field_name="jitter_ns",
                topic=topic,
                index=index,
            )
        )

    mean_score = math.fsum(scores) / len(scores)

    if not math.isfinite(mean_score):
        _raise_engine_error(
            f"Evidence-window mean score is non-finite "
            f"for topic '{topic}'.",
            code=(
                "VELUNE_COMPARISON_"
                "EVIDENCE_SUMMARY_NON_FINITE"
            ),
            hint=(
                "Regenerate the Bundle using finite "
                "evidence-window metrics."
            ),
        )

    return {
        "selected_window_count": len(raw_windows),
        "max_observed_irregularity_score": max(scores),
        "mean_observed_irregularity_score": (
            mean_score
        ),
        "min_count_ratio": min(count_ratios),
        "max_max_gap_ns": max(max_gaps),
        "max_jitter_ns": max(jitters),
    }


def _compare_context(
    reference: Mapping[str, Any],
    target: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    comparison = {}
    changed_fields = []

    for field_name in PROFILE_CONTEXT_FIELDS:
        reference_value = reference[field_name]
        target_value = target[field_name]
        changed = reference_value != target_value

        comparison[field_name] = {
            "reference": reference_value,
            "target": target_value,
            "changed": changed,
        }

        if changed:
            changed_fields.append(field_name)

    return comparison, changed_fields


def _compare_timestamp_provenance(
    reference: Mapping[str, Any],
    target: Mapping[str, Any],
) -> dict[str, Any]:
    changed_fields = [
        field_name
        for field_name in PROFILE_TIMESTAMP_FIELDS
        if reference[field_name] != target[field_name]
    ]

    return {
        "reference": dict(reference),
        "target": dict(target),
        "changed_fields": sorted(changed_fields),
        "excluded_from_delta_and_ratio": True,
    }


def _compare_evidence_summaries(
    reference: Mapping[str, Any],
    target: Mapping[str, Any],
) -> tuple[
    dict[str, dict[str, Any]],
    list[str],
    list[str],
]:
    metric_comparisons = {}
    changed_fields = []
    non_comparable_fields = []

    for field_name in EVIDENCE_SUMMARY_FIELDS:
        reference_value = reference[field_name]
        target_value = target[field_name]

        if reference_value != target_value:
            changed_fields.append(field_name)

        if (
            reference_value is None
            or target_value is None
        ):
            if reference_value != target_value:
                non_comparable_fields.append(field_name)
            continue

        metric_comparisons[field_name] = (
            compare_numeric_values(
                reference_value,
                target_value,
            )
        )

    return (
        metric_comparisons,
        sorted(changed_fields),
        sorted(non_comparable_fields),
    )


def _build_topic_comparison(
    *,
    topic: str,
    reference: LoadedComparisonBundle,
    target: LoadedComparisonBundle,
) -> tuple[dict[str, Any], bool, bool]:
    reference_profile = _extract_profile(
        reference,
        topic,
    )
    target_profile = _extract_profile(
        target,
        topic,
    )

    profile_metric_comparisons = {}
    profile_metric_changes = []

    for field_name in PROFILE_METRIC_FIELDS:
        reference_value = (
            reference_profile["metrics"][field_name]
        )
        target_value = (
            target_profile["metrics"][field_name]
        )

        profile_metric_comparisons[field_name] = (
            compare_numeric_values(
                reference_value,
                target_value,
            )
        )

        if reference_value != target_value:
            profile_metric_changes.append(field_name)

    (
        profile_context_comparisons,
        profile_context_changes,
    ) = _compare_context(
        reference_profile["context"],
        target_profile["context"],
    )

    timestamp_provenance = (
        _compare_timestamp_provenance(
            reference_profile["timestamps"],
            target_profile["timestamps"],
        )
    )

    reference_evidence_summary = (
        _summarize_evidence_windows(
            reference,
            topic,
        )
    )
    target_evidence_summary = (
        _summarize_evidence_windows(
            target,
            topic,
        )
    )

    (
        evidence_summary_comparisons,
        evidence_summary_changes,
        evidence_non_comparable_fields,
    ) = _compare_evidence_summaries(
        reference_evidence_summary,
        target_evidence_summary,
    )

    changed_fields = sorted([
        *(
            f"profile.{field_name}"
            for field_name in profile_metric_changes
        ),
        *(
            f"context.{field_name}"
            for field_name in profile_context_changes
        ),
        *(
            f"evidence_summary.{field_name}"
            for field_name in evidence_summary_changes
        ),
    ])

    profile_changed = bool(
        profile_metric_changes
        or profile_context_changes
    )
    evidence_changed = bool(
        evidence_summary_changes
    )

    return (
        {
            "topic": topic,
            "reference_profile_context": dict(
                reference_profile["context"]
            ),
            "target_profile_context": dict(
                target_profile["context"]
            ),
            "profile_context_comparisons": (
                profile_context_comparisons
            ),
            "profile_metric_comparisons": (
                profile_metric_comparisons
            ),
            "timestamp_provenance": (
                timestamp_provenance
            ),
            "reference_evidence_summary": dict(
                reference_evidence_summary
            ),
            "target_evidence_summary": dict(
                target_evidence_summary
            ),
            "evidence_summary_comparisons": (
                evidence_summary_comparisons
            ),
            "evidence_summary_non_comparable_fields": (
                evidence_non_comparable_fields
            ),
            "changed_fields": changed_fields,
        },
        profile_changed,
        evidence_changed,
    )


def _read_nested_or_none(
    document: Mapping[str, Any],
    *segments: str,
) -> Any:
    current: Any = document

    for segment in segments:
        if (
            not isinstance(current, Mapping)
            or segment not in current
        ):
            return None

        current = current[segment]

    return deepcopy(current)


def _build_input_provenance(
    bundle: LoadedComparisonBundle,
) -> dict[str, Any]:
    manifest = bundle.manifest
    extraction = _read_nested_or_none(
        manifest,
        "extraction",
    )

    return {
        "report_bundle_id": _read_nested_or_none(
            manifest,
            "report_bundle_id",
        ),
        "generated_at": _read_nested_or_none(
            manifest,
            "generated_at",
        ),
        "bundle_schema": {
            "name": _read_nested_or_none(
                manifest,
                "bundle_schema",
                "name",
            ),
            "version": _read_nested_or_none(
                manifest,
                "bundle_schema",
                "version",
            ),
        },
        "engine": {
            "name": _read_nested_or_none(
                manifest,
                "engine",
                "name",
            ),
            "version": _read_nested_or_none(
                manifest,
                "engine",
                "version",
            ),
        },
        "source": {
            "format": _read_nested_or_none(
                manifest,
                "source",
                "format",
            ),
            "file_name": _read_nested_or_none(
                manifest,
                "source",
                "file_name",
            ),
            "file_size_bytes": _read_nested_or_none(
                manifest,
                "source",
                "file_size_bytes",
            ),
        },
        "extraction": extraction,
        "total_messages_observed": (
            _read_nested_or_none(
                manifest,
                "extraction",
                "total_messages_observed",
            )
        ),
        "topic_count": len(bundle.topic_profile),
    }


def build_bundle_comparison(
    reference: LoadedComparisonBundle,
    target: LoadedComparisonBundle,
    *,
    generated_at: str,
) -> dict[str, Any]:
    """Build a complete in-memory v1 comparison report."""

    if not isinstance(
        reference,
        LoadedComparisonBundle,
    ):
        raise TypeError(
            "reference must be a LoadedComparisonBundle"
        )

    if not isinstance(
        target,
        LoadedComparisonBundle,
    ):
        raise TypeError(
            "target must be a LoadedComparisonBundle"
        )

    generated_at_value = _validate_generated_at(
        generated_at
    )

    reference_topics = _validate_topic_contract(
        reference,
        role="Reference",
    )
    target_topics = _validate_topic_contract(
        target,
        role="Target",
    )

    compatibility = evaluate_bundle_compatibility(
        reference,
        target,
    )

    if not compatibility.is_compatible:
        fields = [
            reason["field"]
            for reason in compatibility.blocking_reasons
        ]

        _raise_engine_error(
            f"Reference and Target Bundles are "
            f"incompatible: blocking_fields={fields}",
            code=(
                "VELUNE_COMPARISON_"
                "BUNDLES_INCOMPATIBLE"
            ),
            hint=(
                "Use Bundles with matching Core schema and "
                "extraction contracts."
            ),
        )

    reference_topic_set = set(reference_topics)
    target_topic_set = set(target_topics)

    common_topics = sorted(
        reference_topic_set.intersection(
            target_topic_set
        )
    )
    reference_only_topics = sorted(
        reference_topic_set.difference(
            target_topic_set
        )
    )
    target_only_topics = sorted(
        target_topic_set.difference(
            reference_topic_set
        )
    )

    topic_comparisons = []

    identical_profile_topic_count = 0
    changed_profile_topic_count = 0
    identical_evidence_summary_topic_count = 0
    changed_evidence_summary_topic_count = 0

    for topic in common_topics:
        (
            topic_comparison,
            profile_changed,
            evidence_changed,
        ) = _build_topic_comparison(
            topic=topic,
            reference=reference,
            target=target,
        )

        topic_comparisons.append(
            topic_comparison
        )

        if profile_changed:
            changed_profile_topic_count += 1
        else:
            identical_profile_topic_count += 1

        if evidence_changed:
            changed_evidence_summary_topic_count += 1
        else:
            identical_evidence_summary_topic_count += 1

    return {
        "schema_name": COMPARISON_SCHEMA_NAME,
        "schema_version": (
            COMPARISON_SCHEMA_VERSION
        ),
        "visibility": COMPARISON_VISIBILITY,
        "semantics": COMPARISON_SEMANTICS,
        "generated_at": generated_at_value,
        "reference": _build_input_provenance(
            reference
        ),
        "target": _build_input_provenance(target),
        "compatibility": compatibility.as_dict(),
        "topic_set": {
            "common_topics": common_topics,
            "reference_only_topics": (
                reference_only_topics
            ),
            "target_only_topics": (
                target_only_topics
            ),
        },
        "topic_comparisons": topic_comparisons,
        "summary": {
            "reference_topic_count": len(
                reference_topics
            ),
            "target_topic_count": len(
                target_topics
            ),
            "common_topic_count": len(
                common_topics
            ),
            "reference_only_topic_count": len(
                reference_only_topics
            ),
            "target_only_topic_count": len(
                target_only_topics
            ),
            "identical_profile_topic_count": (
                identical_profile_topic_count
            ),
            "changed_profile_topic_count": (
                changed_profile_topic_count
            ),
            (
                "identical_evidence_summary_"
                "topic_count"
            ): (
                identical_evidence_summary_topic_count
            ),
            (
                "changed_evidence_summary_"
                "topic_count"
            ): (
                changed_evidence_summary_topic_count
            ),
        },
        "excluded_from_change_evaluation": list(
            EXCLUDED_FROM_CHANGE_EVALUATION
        ),
        "judgment_boundary": {
            "cause_inference": False,
            "severity_judgment": False,
            "normality_judgment": False,
            "superiority_judgment": False,
            "regression_judgment": False,
            "fault_assignment": False,
            "liability_calculation": False,
            "safety_classification": False,
            "automatic_improvement_label": False,
        },
    }
