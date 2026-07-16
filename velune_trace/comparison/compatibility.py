"""Compatibility gate for Core Bundle comparison."""

from collections.abc import Mapping
from dataclasses import dataclass
import math
from typing import Any


from velune_trace.comparison.loader import (
    LoadedComparisonBundle,
)


COMPATIBLE_STATUS = "compatible"
INCOMPATIBLE_STATUS = "incompatible"


@dataclass(frozen=True)
class _BlockingFieldSpec:
    """One blocking compatibility-field contract."""

    path: str
    segments: tuple[str, ...]
    value_kind: str


@dataclass(frozen=True)
class _WarningFieldSpec:
    """One non-blocking provenance warning contract."""

    path: str
    segments: tuple[str, ...]
    difference_code: str
    difference_message: str


_BLOCKING_FIELD_SPECS = (
    _BlockingFieldSpec(
        path="schema_name",
        segments=("schema_name",),
        value_kind="non_empty_string",
    ),
    _BlockingFieldSpec(
        path="schema_version",
        segments=("schema_version",),
        value_kind="non_empty_string",
    ),
    _BlockingFieldSpec(
        path="bundle_schema.name",
        segments=("bundle_schema", "name"),
        value_kind="non_empty_string",
    ),
    _BlockingFieldSpec(
        path="bundle_schema.version",
        segments=("bundle_schema", "version"),
        value_kind="non_empty_string",
    ),
    _BlockingFieldSpec(
        path="engine.name",
        segments=("engine", "name"),
        value_kind="non_empty_string",
    ),
    _BlockingFieldSpec(
        path="extraction.semantics",
        segments=("extraction", "semantics"),
        value_kind="non_empty_string",
    ),
    _BlockingFieldSpec(
        path="extraction.mode",
        segments=("extraction", "mode"),
        value_kind="non_empty_string",
    ),
    _BlockingFieldSpec(
        path="extraction.timestamp_unit",
        segments=("extraction", "timestamp_unit"),
        value_kind="non_empty_string",
    ),
    _BlockingFieldSpec(
        path="extraction.window_sec",
        segments=("extraction", "window_sec"),
        value_kind="positive_number",
    ),
    _BlockingFieldSpec(
        path="extraction.allowed_lateness_sec",
        segments=(
            "extraction",
            "allowed_lateness_sec",
        ),
        value_kind="non_negative_number",
    ),
    _BlockingFieldSpec(
        path="extraction.top",
        segments=("extraction", "top"),
        value_kind="positive_integer",
    ),
)

BLOCKING_FIELD_PATHS = tuple(
    spec.path
    for spec in _BLOCKING_FIELD_SPECS
)

_WARNING_FIELD_SPECS = (
    _WarningFieldSpec(
        path="engine.version",
        segments=("engine", "version"),
        difference_code=(
            "VELUNE_COMPARISON_"
            "ENGINE_VERSION_DIFFERENCE"
        ),
        difference_message=(
            "Reference and Target Bundles were generated "
            "by different Velune Trace versions."
        ),
    ),
    _WarningFieldSpec(
        path="source.format",
        segments=("source", "format"),
        difference_code=(
            "VELUNE_COMPARISON_"
            "SOURCE_FORMAT_DIFFERENCE"
        ),
        difference_message=(
            "Reference and Target Bundles declare "
            "different source formats."
        ),
    ),
)

WARNING_FIELD_PATHS = tuple(
    spec.path
    for spec in _WARNING_FIELD_SPECS
)


@dataclass(frozen=True)
class BundleCompatibilityResult:
    """Deterministic compatibility result for two verified Bundles."""

    status: str
    required_field_checks: tuple[dict[str, Any], ...]
    warnings: tuple[dict[str, Any], ...]
    blocking_reasons: tuple[dict[str, Any], ...]

    @property
    def is_compatible(self) -> bool:
        return self.status == COMPATIBLE_STATUS

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "required_field_checks": [
                dict(check)
                for check in self.required_field_checks
            ],
            "warnings": [
                dict(warning)
                for warning in self.warnings
            ],
            "blocking_reasons": [
                dict(reason)
                for reason in self.blocking_reasons
            ],
        }


def _read_nested_field(
    document: Mapping[str, Any],
    segments: tuple[str, ...],
) -> tuple[bool, Any]:
    current: Any = document

    for segment in segments:
        if (
            not isinstance(current, Mapping)
            or segment not in current
        ):
            return False, None

        current = current[segment]

    return True, current


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False

    if not isinstance(value, (int, float)):
        return False

    if isinstance(value, float):
        return math.isfinite(value)

    return True


def _is_valid_contract_value(
    value: Any,
    *,
    value_kind: str,
) -> bool:
    if value_kind == "non_empty_string":
        return (
            isinstance(value, str)
            and bool(value)
            and value == value.strip()
        )

    if value_kind == "positive_number":
        return (
            _is_finite_number(value)
            and value > 0
        )

    if value_kind == "non_negative_number":
        return (
            _is_finite_number(value)
            and value >= 0
        )

    if value_kind == "positive_integer":
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            and value > 0
        )

    raise ValueError(
        f"Unsupported compatibility value kind: "
        f"{value_kind}"
    )


def _contract_values_equal(
    reference_value: Any,
    target_value: Any,
) -> bool:
    """Compare validated contract values without fuzzy tolerance.

    Integer and float representations of the same finite numeric
    value are compatible. Booleans are never treated as numbers.
    """

    reference_numeric = _is_finite_number(
        reference_value
    )
    target_numeric = _is_finite_number(
        target_value
    )

    if reference_numeric and target_numeric:
        return reference_value == target_value

    return (
        type(reference_value) is type(target_value)
        and reference_value == target_value
    )


def _build_required_field_check(
    *,
    spec: _BlockingFieldSpec,
    reference_manifest: Mapping[str, Any],
    target_manifest: Mapping[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any] | None,
]:
    reference_present, reference_value = (
        _read_nested_field(
            reference_manifest,
            spec.segments,
        )
    )
    target_present, target_value = _read_nested_field(
        target_manifest,
        spec.segments,
    )

    reference_valid = (
        reference_present
        and _is_valid_contract_value(
            reference_value,
            value_kind=spec.value_kind,
        )
    )
    target_valid = (
        target_present
        and _is_valid_contract_value(
            target_value,
            value_kind=spec.value_kind,
        )
    )

    values_match = (
        reference_valid
        and target_valid
        and _contract_values_equal(
            reference_value,
            target_value,
        )
    )

    check = {
        "field": spec.path,
        "blocking": True,
        "value_kind": spec.value_kind,
        "reference_present": reference_present,
        "target_present": target_present,
        "reference_valid": reference_valid,
        "target_valid": target_valid,
        "reference": reference_value,
        "target": target_value,
        "match": values_match,
    }

    if values_match:
        return check, None

    if not reference_present or not target_present:
        reason = {
            "code": (
                "VELUNE_COMPARISON_"
                "REQUIRED_FIELD_MISSING"
            ),
            "field": spec.path,
            "message": (
                f"Required compatibility field "
                f"'{spec.path}' is missing from one or "
                f"both Bundle manifests."
            ),
            "reference_present": reference_present,
            "target_present": target_present,
        }
        return check, reason

    if not reference_valid or not target_valid:
        reason = {
            "code": (
                "VELUNE_COMPARISON_"
                "REQUIRED_FIELD_INVALID"
            ),
            "field": spec.path,
            "message": (
                f"Required compatibility field "
                f"'{spec.path}' contains an invalid "
                f"contract value."
            ),
            "expected_value_kind": spec.value_kind,
            "reference_valid": reference_valid,
            "target_valid": target_valid,
            "reference": reference_value,
            "target": target_value,
        }
        return check, reason

    reason = {
        "code": (
            "VELUNE_COMPARISON_"
            "REQUIRED_FIELD_MISMATCH"
        ),
        "field": spec.path,
        "message": (
            f"Required compatibility field "
            f"'{spec.path}' differs between the Reference "
            f"and Target Bundle manifests."
        ),
        "reference": reference_value,
        "target": target_value,
    }

    return check, reason


def _is_valid_warning_value(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
    )


def _build_warning(
    *,
    spec: _WarningFieldSpec,
    reference_manifest: Mapping[str, Any],
    target_manifest: Mapping[str, Any],
) -> dict[str, Any] | None:
    reference_present, reference_value = (
        _read_nested_field(
            reference_manifest,
            spec.segments,
        )
    )
    target_present, target_value = _read_nested_field(
        target_manifest,
        spec.segments,
    )

    reference_valid = (
        reference_present
        and _is_valid_warning_value(
            reference_value
        )
    )
    target_valid = (
        target_present
        and _is_valid_warning_value(
            target_value
        )
    )

    if (
        reference_valid
        and target_valid
        and reference_value == target_value
    ):
        return None

    if not reference_valid or not target_valid:
        return {
            "code": (
                "VELUNE_COMPARISON_"
                "WARNING_FIELD_UNAVAILABLE"
            ),
            "field": spec.path,
            "reason": "missing_or_invalid",
            "message": (
                f"Non-blocking provenance field "
                f"'{spec.path}' is missing or invalid in "
                f"one or both Bundle manifests."
            ),
            "reference_present": reference_present,
            "target_present": target_present,
            "reference_valid": reference_valid,
            "target_valid": target_valid,
            "reference": reference_value,
            "target": target_value,
        }

    return {
        "code": spec.difference_code,
        "field": spec.path,
        "reason": "value_difference",
        "message": (
            f"Non-blocking provenance field "
            f"'{spec.path}' differs. "
            f"{spec.difference_message}"
        ),
        "reference_present": reference_present,
        "target_present": target_present,
        "reference_valid": reference_valid,
        "target_valid": target_valid,
        "reference": reference_value,
        "target": target_value,
    }


def evaluate_bundle_compatibility(
    reference: LoadedComparisonBundle,
    target: LoadedComparisonBundle,
) -> BundleCompatibilityResult:
    """Evaluate whether two verified Core Bundles may be compared."""

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

    required_field_checks = []
    blocking_reasons = []

    for spec in _BLOCKING_FIELD_SPECS:
        check, reason = _build_required_field_check(
            spec=spec,
            reference_manifest=reference.manifest,
            target_manifest=target.manifest,
        )
        required_field_checks.append(check)

        if reason is not None:
            blocking_reasons.append(reason)

    warnings = []

    for spec in _WARNING_FIELD_SPECS:
        warning = _build_warning(
            spec=spec,
            reference_manifest=reference.manifest,
            target_manifest=target.manifest,
        )

        if warning is not None:
            warnings.append(warning)

    status = (
        COMPATIBLE_STATUS
        if not blocking_reasons
        else INCOMPATIBLE_STATUS
    )

    return BundleCompatibilityResult(
        status=status,
        required_field_checks=tuple(
            required_field_checks
        ),
        warnings=tuple(warnings),
        blocking_reasons=tuple(blocking_reasons),
    )
