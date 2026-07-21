"""Public orchestration for Private Baseline Target Evaluation."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import secrets
from typing import Any

from velune_trace.comparison import (
    build_bundle_comparison,
    evaluate_bundle_compatibility,
)
from velune_trace.private_baseline.errors import (
    PrivateBaselineContractError,
)
from velune_trace.private_baseline.evaluation import (
    build_private_baseline_evaluation_report,
    normalize_evaluation_context,
)
from velune_trace.private_baseline.evaluation_writer import (
    WrittenPrivateBaselineEvaluation,
    write_private_baseline_evaluation_outputs,
)
from velune_trace.private_baseline.registry import (
    LoadedPrivateBaselineRegistry,
    load_private_baseline_registry,
)
from velune_trace.private_baseline.service import (
    _load_verified_references,
)


@dataclass(frozen=True)
class EvaluatedPrivateBaseline:
    """One completed standalone Target Evaluation."""

    loaded_registry: LoadedPrivateBaselineRegistry
    evaluation_report: dict[str, Any]
    written_evaluation: WrittenPrivateBaselineEvaluation
    compatibility_warnings: tuple[
        dict[str, Any],
        ...,
    ]


class PrivateBaselineEvaluationServiceError(
    PrivateBaselineContractError
):
    """Raised when Target Evaluation orchestration fails."""

    default_code = (
        "VELUNE_PRIVATE_BASELINE_EVALUATION_SERVICE_FAILED"
    )

    def __init__(
        self,
        message: str,
        *,
        code: str,
        hint: str,
        incompatibilities: Any = (),
    ) -> None:
        super().__init__(
            message,
            code=code,
            hint=hint,
            stage=(
                "private_baseline_evaluation_service"
            ),
        )

        self.incompatibilities = tuple(
            copy.deepcopy(
                list(incompatibilities)
            )
        )


def _raise_evaluation_service_error(
    message: str,
    *,
    code: str,
    hint: str,
    incompatibilities: Any = (),
) -> None:
    raise PrivateBaselineEvaluationServiceError(
        message,
        code=code,
        hint=hint,
        incompatibilities=incompatibilities,
    )


def _normalize_generated_at(
    value: Any,
) -> str:
    """Validate the single timestamp reused by every comparison."""

    if not isinstance(value, str):
        _raise_evaluation_service_error(
            "generated_at must be an ISO-8601 string.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "SERVICE_GENERATED_AT_INVALID"
            ),
            hint=(
                "Provide one ISO-8601 timestamp with a "
                "timezone offset."
            ),
        )

    try:
        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )
    except ValueError as exc:
        raise PrivateBaselineEvaluationServiceError(
            "generated_at is not valid ISO-8601.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "SERVICE_GENERATED_AT_INVALID"
            ),
            hint=(
                "Provide one ISO-8601 timestamp with a "
                "timezone offset."
            ),
            stage=(
                "private_baseline_evaluation_service"
            ),
        ) from exc

    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
    ):
        _raise_evaluation_service_error(
            "generated_at must include a timezone offset.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "SERVICE_GENERATED_AT_TIMEZONE_REQUIRED"
            ),
            hint=(
                "Use a timestamp such as "
                "2026-07-21T17:00:00+09:00."
            ),
        )

    return parsed.isoformat()


def _build_reference_inputs(
    loaded_registry: LoadedPrivateBaselineRegistry,
) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    """Resolve explicit Reference inputs without inferring paths."""

    revision_document = (
        loaded_registry.current_revision.document
    )

    reference_memberships = revision_document[
        "reference_memberships"
    ]

    bundle_locations = (
        loaded_registry.registry[
            "bundle_locations"
        ]
    )

    reference_inputs: list[
        dict[str, Any]
    ] = []

    memberships_by_bundle_id: dict[
        str,
        dict[str, Any],
    ] = {}

    for membership in reference_memberships:
        report_bundle_id = membership[
            "report_bundle_id"
        ]

        bundle_dir = bundle_locations.get(
            report_bundle_id
        )

        if bundle_dir is None:
            _raise_evaluation_service_error(
                "A registered Reference Bundle location "
                "is missing: "
                f"{report_bundle_id}.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "SERVICE_REFERENCE_LOCATION_MISSING"
                ),
                hint=(
                    "Restore the explicit local Bundle "
                    "locator without inferring a path."
                ),
            )

        if report_bundle_id in (
            memberships_by_bundle_id
        ):
            _raise_evaluation_service_error(
                "The immutable Revision contains a "
                "duplicate Reference Bundle identity.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "SERVICE_REFERENCE_DUPLICATE"
                ),
                hint=(
                    "Restore the verified immutable "
                    "Revision membership set."
                ),
            )

        reference_inputs.append({
            "bundle_dir": bundle_dir,
            "dimensions": copy.deepcopy(
                membership["dimensions"]
            ),
            "selection": copy.deepcopy(
                membership["selection"]
            ),
        })

        memberships_by_bundle_id[
            report_bundle_id
        ] = copy.deepcopy(
            membership
        )

    if not reference_inputs:
        _raise_evaluation_service_error(
            "The selected Revision contains no References.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "SERVICE_REFERENCE_REQUIRED"
            ),
            hint=(
                "Use a verified Revision with at least "
                "one explicit Reference membership."
            ),
        )

    return (
        reference_inputs,
        memberships_by_bundle_id,
    )


def evaluate_private_baseline(
    baseline_root: str | Path,
    target_bundle_dir: str | Path,
    export_dir: str | Path,
    *,
    generated_at: Any,
    evaluation_context: Any,
) -> EvaluatedPrivateBaseline:
    """Evaluate one Target against every current Reference.

    Processing order:

    1. Validate request metadata.
    2. Load the Baseline Registry fail-closed.
    3. Load and reverify each pinned Reference exactly once.
    4. Load and verify the explicit Target exactly once.
    5. Complete every compatibility preflight.
    6. Build one Comparison v1 report per Reference.
    7. Build and write the standalone Evaluation outputs.

    This operation does not mutate the Baseline Registry.
    """

    canonical_generated_at = (
        _normalize_generated_at(
            generated_at
        )
    )

    loaded_registry = (
        load_private_baseline_registry(
            baseline_root
        )
    )

    revision_document = (
        loaded_registry.current_revision.document
    )

    canonical_context = (
        normalize_evaluation_context(
            evaluation_context,
            dimension_policy=(
                revision_document[
                    "dimension_policy"
                ]
            ),
        )
    )

    (
        reference_inputs,
        memberships_by_bundle_id,
    ) = _build_reference_inputs(
        loaded_registry
    )

    verified_references = (
        _load_verified_references(
            reference_inputs
        )
    )

    if (
        len(verified_references)
        != len(reference_inputs)
    ):
        _raise_evaluation_service_error(
            "Verified Reference count differs from the "
            "immutable Revision membership count.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "SERVICE_REFERENCE_COUNT_MISMATCH"
            ),
            hint=(
                "Restore every Bundle pinned by the "
                "selected immutable Revision."
            ),
        )

    verified_reference_ids = {
        reference.report_bundle_id
        for reference in verified_references
    }

    expected_reference_ids = set(
        memberships_by_bundle_id
    )

    if (
        verified_reference_ids
        != expected_reference_ids
    ):
        _raise_evaluation_service_error(
            "Loaded Reference identities differ from the "
            "immutable Revision membership set.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "SERVICE_REFERENCE_SET_MISMATCH"
            ),
            hint=(
                "Restore the exact Reference Bundles "
                "selected for this Revision."
            ),
        )

    for reference in verified_references:
        membership = (
            memberships_by_bundle_id[
                reference.report_bundle_id
            ]
        )

        if (
            reference.report_manifest_sha256
            != membership[
                "report_manifest_sha256"
            ]
        ):
            _raise_evaluation_service_error(
                "Reference manifest SHA-256 no longer "
                "matches its immutable membership pin: "
                f"{reference.report_bundle_id}.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "SERVICE_REFERENCE_MANIFEST_MISMATCH"
                ),
                hint=(
                    "Restore the exact Reference Bundle "
                    "selected for this Revision."
                ),
            )

    target_inputs = [{
        "bundle_dir": target_bundle_dir,
        "dimensions": copy.deepcopy(
            canonical_context["dimensions"]
        ),
        "selection": {
            "selected_by": (
                "private_baseline_evaluation_service"
            ),
            "selected_at": (
                canonical_generated_at
            ),
        },
    }]

    verified_targets = (
        _load_verified_references(
            target_inputs
        )
    )

    if len(verified_targets) != 1:
        _raise_evaluation_service_error(
            "Exactly one verified Target Bundle is required.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "SERVICE_TARGET_COUNT_INVALID"
            ),
            hint=(
                "Provide one completed Core Report Bundle "
                "as the Evaluation Target."
            ),
        )

    target = verified_targets[0]

    if (
        target.report_bundle_id
        in expected_reference_ids
    ):
        _raise_evaluation_service_error(
            "Target Bundle must not also be a Reference "
            "membership in the selected Revision.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "SERVICE_TARGET_IS_REFERENCE"
            ),
            hint=(
                "Select a distinct completed Bundle as "
                "the Target."
            ),
        )

    compatibility_warnings: list[
        dict[str, Any]
    ] = []

    incompatibilities: list[
        dict[str, Any]
    ] = []

    for reference in verified_references:
        compatibility = (
            evaluate_bundle_compatibility(
                reference.loaded_bundle,
                target.loaded_bundle,
            )
        )

        for warning in compatibility.warnings:
            compatibility_warnings.append({
                "reference_report_bundle_id": (
                    reference.report_bundle_id
                ),
                "target_report_bundle_id": (
                    target.report_bundle_id
                ),
                "warning": copy.deepcopy(
                    warning
                ),
            })

        if not compatibility.is_compatible:
            incompatibilities.append({
                "reference_report_bundle_id": (
                    reference.report_bundle_id
                ),
                "target_report_bundle_id": (
                    target.report_bundle_id
                ),
                "blocking_reasons": copy.deepcopy(
                    list(
                        compatibility.blocking_reasons
                    )
                ),
            })

    if incompatibilities:
        _raise_evaluation_service_error(
            "Target Bundle is incompatible with one or "
            "more immutable References.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "SERVICE_PAIR_INCOMPATIBLE"
            ),
            hint=(
                "Use a Target whose Core schema and "
                "extraction contract match every Reference."
            ),
            incompatibilities=incompatibilities,
        )

    reference_comparisons = []

    for reference in verified_references:
        comparison_report = (
            build_bundle_comparison(
                reference.loaded_bundle,
                target.loaded_bundle,
                generated_at=(
                    canonical_generated_at
                ),
            )
        )

        reference_comparisons.append({
            "reference_report_bundle_id": (
                reference.report_bundle_id
            ),
            "comparison_report": (
                comparison_report
            ),
        })

    evaluation_id = (
        "vpbe_" + secrets.token_hex(16)
    )

    evaluation_report = (
        build_private_baseline_evaluation_report(
            evaluation_id=evaluation_id,
            generated_at=canonical_generated_at,
            baseline_id=(
                loaded_registry.registry[
                    "baseline_id"
                ]
            ),
            baseline_revision_id=(
                loaded_registry.registry[
                    "current_revision_id"
                ]
            ),
            dimension_policy=(
                revision_document[
                    "dimension_policy"
                ]
            ),
            evaluation_context=(
                canonical_context
            ),
            target_report_bundle_id=(
                target.report_bundle_id
            ),
            target_report_manifest_sha256=(
                target.report_manifest_sha256
            ),
            reference_comparisons=(
                reference_comparisons
            ),
        )
    )

    written_evaluation = (
        write_private_baseline_evaluation_outputs(
            export_dir=export_dir,
            report=evaluation_report,
        )
    )

    return EvaluatedPrivateBaseline(
        loaded_registry=loaded_registry,
        evaluation_report=(
            evaluation_report
        ),
        written_evaluation=(
            written_evaluation
        ),
        compatibility_warnings=tuple(
            compatibility_warnings
        ),
    )
