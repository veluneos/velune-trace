"""Verified initial Private Baseline creation service."""

from collections.abc import Mapping
import copy
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any

from velune_trace.comparison import (
    LoadedComparisonBundle,
    evaluate_bundle_compatibility,
    load_comparison_bundle,
)
from velune_trace.comparison.loader import (
    MANIFEST_FILENAME,
)
from velune_trace.private_baseline.contract import (
    DISPLAY_NAME_MAX_LENGTH,
    REFERENCE_MEMBERSHIP_LIMIT,
    normalize_single_line_text,
)
from velune_trace.private_baseline.errors import (
    PrivateBaselineContractError,
)
from velune_trace.private_baseline.registry import (
    LoadedPrivateBaselineRegistry,
)
from velune_trace.private_baseline.revision import (
    REPORT_BUNDLE_ID_PREFIX,
    SHA256_HEX_LENGTH,
    build_baseline_revision,
)
from velune_trace.private_baseline.storage import (
    _install_initial_private_baseline,
)


_READ_CHUNK_SIZE = 1024 * 1024

_REFERENCE_INPUT_FIELDS = frozenset({
    "bundle_dir",
    "dimensions",
    "selection",
})

_VALIDATION_BASELINE_ID = f"vpb_{'0' * 32}"
_VALIDATION_REVISION_ID = f"vpbr_{'0' * 32}"


class PrivateBaselineServiceError(
    PrivateBaselineContractError
):
    """Raised when verified Baseline creation cannot proceed."""

    default_code = (
        "VELUNE_PRIVATE_BASELINE_SERVICE_FAILED"
    )

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        hint: str | None = None,
        incompatibilities: tuple[
            dict[str, Any],
            ...,
        ] = (),
    ) -> None:
        super().__init__(
            message,
            code=code,
            hint=hint,
            stage="private_baseline_service",
        )

        self.incompatibilities = tuple(
            copy.deepcopy(item)
            for item in incompatibilities
        )


@dataclass(frozen=True)
class CreatedPrivateBaseline:
    """Result of verified initial Baseline creation."""

    loaded_registry: LoadedPrivateBaselineRegistry
    compatibility_warnings: tuple[
        dict[str, Any],
        ...,
    ]

    @property
    def root_dir(self) -> Path:
        return self.loaded_registry.root_dir

    @property
    def baseline_id(self) -> str:
        return str(
            self.loaded_registry.registry[
                "baseline_id"
            ]
        )

    @property
    def baseline_revision_id(self) -> str:
        return str(
            self.loaded_registry.registry[
                "current_revision_id"
            ]
        )


@dataclass(frozen=True)
class _VerifiedReference:
    """One verified Reference Bundle and private metadata."""

    loaded_bundle: LoadedComparisonBundle
    report_bundle_id: str
    report_manifest_sha256: str
    dimensions: dict[str, Any]
    selection: dict[str, Any]


def _raise_service_error(
    message: str,
    *,
    code: str,
    hint: str,
    incompatibilities: tuple[
        dict[str, Any],
        ...,
    ] = (),
) -> None:
    raise PrivateBaselineServiceError(
        message,
        code=code,
        hint=hint,
        incompatibilities=incompatibilities,
    )


def _require_reference_mapping(
    value: Any,
    *,
    index: int,
) -> Mapping[str, Any]:
    field_name = f"references[{index}]"

    if not isinstance(value, Mapping):
        _raise_service_error(
            f"{field_name} must be a mapping.",
            code=(
                "VELUNE_PRIVATE_BASELINE_SERVICE_"
                "REFERENCE_MAPPING_REQUIRED"
            ),
            hint=(
                "Provide bundle_dir, dimensions, and "
                "selection for every Reference."
            ),
        )

    actual_fields = set(value)

    missing_fields = sorted(
        _REFERENCE_INPUT_FIELDS.difference(
            actual_fields
        )
    )
    unexpected_fields = sorted(
        actual_fields.difference(
            _REFERENCE_INPUT_FIELDS
        )
    )

    if missing_fields:
        _raise_service_error(
            f"{field_name} is missing required fields: "
            f"{', '.join(missing_fields)}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_SERVICE_"
                "REFERENCE_FIELD_MISSING"
            ),
            hint=(
                "Provide bundle_dir, dimensions, and "
                "selection."
            ),
        )

    if unexpected_fields:
        _raise_service_error(
            f"{field_name} contains unexpected fields: "
            f"{', '.join(unexpected_fields)}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_SERVICE_"
                "REFERENCE_FIELD_UNEXPECTED"
            ),
            hint=(
                "Remove fields outside the explicit "
                "Reference input contract."
            ),
        )

    return value


def _normalize_reference_inputs(
    references: Any,
) -> list[dict[str, Any]]:
    if not isinstance(references, list):
        _raise_service_error(
            "references must be a list.",
            code=(
                "VELUNE_PRIVATE_BASELINE_SERVICE_"
                "REFERENCE_LIST_REQUIRED"
            ),
            hint=(
                "Provide one through 32 explicitly selected "
                "Reference Bundles."
            ),
        )

    if not references:
        _raise_service_error(
            "At least one Reference Bundle is required.",
            code=(
                "VELUNE_PRIVATE_BASELINE_SERVICE_"
                "REFERENCE_REQUIRED"
            ),
            hint=(
                "Select at least one verified Reference "
                "Bundle."
            ),
        )

    if len(references) > REFERENCE_MEMBERSHIP_LIMIT:
        _raise_service_error(
            "Reference count exceeds the Private Baseline "
            "v1 limit of 32.",
            code=(
                "VELUNE_PRIVATE_BASELINE_SERVICE_"
                "REFERENCE_LIMIT_EXCEEDED"
            ),
            hint=(
                "Create a Baseline with no more than 32 "
                "explicit References."
            ),
        )

    normalized: list[dict[str, Any]] = []

    for index, value in enumerate(references):
        reference = _require_reference_mapping(
            value,
            index=index,
        )

        normalized.append({
            "bundle_dir": copy.deepcopy(
                reference["bundle_dir"]
            ),
            "dimensions": copy.deepcopy(
                reference["dimensions"]
            ),
            "selection": copy.deepcopy(
                reference["selection"]
            ),
        })

    return normalized


def _prevalidate_private_request(
    *,
    display_name: Any,
    created_at: Any,
    created_by: Any,
    dimension_policy: Any,
    references: Any,
) -> dict[str, Any]:
    """Validate private metadata before Bundle I/O begins."""

    normalized_references = (
        _normalize_reference_inputs(
            references
        )
    )

    normalized_display_name = (
        normalize_single_line_text(
            display_name,
            field_name="display_name",
            max_length=DISPLAY_NAME_MAX_LENGTH,
        )
    )

    synthetic_memberships = []
    bundle_dir_by_synthetic_id = {}

    for index, reference in enumerate(
        normalized_references,
        start=1,
    ):
        synthetic_bundle_id = (
            f"{REPORT_BUNDLE_ID_PREFIX}"
            f"{index:064x}"
        )

        synthetic_memberships.append({
            "report_bundle_id": (
                synthetic_bundle_id
            ),
            "report_manifest_sha256": (
                f"{index + 1000:064x}"
            ),
            "dimensions": copy.deepcopy(
                reference["dimensions"]
            ),
            "selection": copy.deepcopy(
                reference["selection"]
            ),
        })

        bundle_dir_by_synthetic_id[
            synthetic_bundle_id
        ] = copy.deepcopy(
            reference["bundle_dir"]
        )

    prototype = build_baseline_revision(
        baseline_id=_VALIDATION_BASELINE_ID,
        baseline_revision_id=(
            _VALIDATION_REVISION_ID
        ),
        parent_revision_id=None,
        created_at=created_at,
        created_by=created_by,
        dimension_policy=dimension_policy,
        reference_memberships=(
            synthetic_memberships
        ),
    )

    canonical_references = []

    for membership in prototype[
        "reference_memberships"
    ]:
        synthetic_bundle_id = membership[
            "report_bundle_id"
        ]

        canonical_references.append({
            "bundle_dir": copy.deepcopy(
                bundle_dir_by_synthetic_id[
                    synthetic_bundle_id
                ]
            ),
            "dimensions": copy.deepcopy(
                membership["dimensions"]
            ),
            "selection": copy.deepcopy(
                membership["selection"]
            ),
        })

    return {
        "display_name": normalized_display_name,
        "created_at": prototype["created_at"],
        "created_by": prototype["created_by"],
        "dimension_policy": copy.deepcopy(
            prototype["dimension_policy"]
        ),
        "references": canonical_references,
    }


def _reject_duplicate_object_pairs(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise ValueError(
                f"Duplicate JSON object key: {key}"
            )

        result[key] = value

    return result


def _reject_non_finite_constant(
    value: str,
) -> None:
    raise ValueError(
        f"Non-finite JSON number is forbidden: {value}"
    )


def _read_verified_manifest_snapshot(
    bundle: LoadedComparisonBundle,
) -> str:
    """Hash the exact manifest matching the loader result."""

    manifest_path = (
        bundle.bundle_dir / MANIFEST_FILENAME
    )

    if manifest_path.is_symlink():
        _raise_service_error(
            "report_manifest.json became a symbolic "
            "link during verification.",
            code=(
                "VELUNE_PRIVATE_BASELINE_SERVICE_"
                "MANIFEST_CHANGED_DURING_VERIFICATION"
            ),
            hint=(
                "Restore the immutable Core Bundle and "
                "retry."
            ),
        )

    flags = os.O_RDONLY

    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    descriptor: int | None = None

    try:
        descriptor = os.open(
            manifest_path,
            flags,
        )

        before = os.fstat(descriptor)

        if not stat.S_ISREG(before.st_mode):
            _raise_service_error(
                "report_manifest.json is not a regular "
                "file.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_SERVICE_"
                    "MANIFEST_FILE_INVALID"
                ),
                hint=(
                    "Restore the finalized Core Bundle "
                    "manifest."
                ),
            )

        digest = hashlib.sha256()
        payload_parts: list[bytes] = []

        while True:
            chunk = os.read(
                descriptor,
                _READ_CHUNK_SIZE,
            )

            if not chunk:
                break

            digest.update(chunk)
            payload_parts.append(chunk)

        after = os.fstat(descriptor)

        stable_fields_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        stable_fields_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )

        if stable_fields_before != stable_fields_after:
            _raise_service_error(
                "report_manifest.json changed while it "
                "was being captured.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_SERVICE_"
                    "MANIFEST_CHANGED_DURING_VERIFICATION"
                ),
                hint=(
                    "Do not modify a Core Bundle while "
                    "creating a Baseline."
                ),
            )

        path_stat = os.stat(
            manifest_path,
            follow_symlinks=False,
        )

        if (
            not stat.S_ISREG(path_stat.st_mode)
            or path_stat.st_dev != after.st_dev
            or path_stat.st_ino != after.st_ino
        ):
            _raise_service_error(
                "report_manifest.json was replaced during "
                "verification.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_SERVICE_"
                    "MANIFEST_CHANGED_DURING_VERIFICATION"
                ),
                hint=(
                    "Use an unchanged finalized Core "
                    "Bundle."
                ),
            )

        payload = b"".join(payload_parts)

        try:
            decoded = payload.decode(
                "utf-8",
                errors="strict",
            )
            snapshot_document = json.loads(
                decoded,
                object_pairs_hook=(
                    _reject_duplicate_object_pairs
                ),
                parse_constant=(
                    _reject_non_finite_constant
                ),
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            ValueError,
        ) as exc:
            raise PrivateBaselineServiceError(
                "The physical manifest no longer matches "
                "the verified loader result.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_SERVICE_"
                    "MANIFEST_CHANGED_DURING_VERIFICATION"
                ),
                hint=(
                    "Restore the finalized Core Bundle "
                    "before retrying."
                ),
            ) from exc

        if (
            not isinstance(
                snapshot_document,
                dict,
            )
            or snapshot_document
            != bundle.manifest
        ):
            _raise_service_error(
                "The manifest snapshot differs from the "
                "document verified by the Bundle loader.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_SERVICE_"
                    "MANIFEST_CHANGED_DURING_VERIFICATION"
                ),
                hint=(
                    "Do not modify a Bundle during "
                    "Baseline creation."
                ),
            )

        return digest.hexdigest()

    except PrivateBaselineServiceError:
        raise
    except OSError as exc:
        raise PrivateBaselineServiceError(
            "Unable to capture the verified Core Bundle "
            f"manifest: {exc}",
            code=(
                "VELUNE_PRIVATE_BASELINE_SERVICE_"
                "MANIFEST_READ_FAILED"
            ),
            hint=(
                "Confirm that report_manifest.json remains "
                "readable and unchanged."
            ),
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _validate_report_bundle_id(
    value: Any,
    *,
    index: int,
) -> str:
    field_name = (
        f"references[{index}]."
        "manifest.report_bundle_id"
    )

    if not isinstance(value, str):
        _raise_service_error(
            f"{field_name} must be a string.",
            code=(
                "VELUNE_PRIVATE_BASELINE_SERVICE_"
                "REPORT_BUNDLE_ID_INVALID"
            ),
            hint=(
                "Regenerate the finalized Core Report "
                "Bundle."
            ),
        )

    suffix = (
        value[len(REPORT_BUNDLE_ID_PREFIX):]
        if value.startswith(
            REPORT_BUNDLE_ID_PREFIX
        )
        else ""
    )

    valid = (
        len(suffix) == SHA256_HEX_LENGTH
        and all(
            character in "0123456789abcdef"
            for character in suffix
        )
    )

    if not valid:
        _raise_service_error(
            f"{field_name} does not match the Core Bundle "
            "identifier format.",
            code=(
                "VELUNE_PRIVATE_BASELINE_SERVICE_"
                "REPORT_BUNDLE_ID_INVALID"
            ),
            hint=(
                "Use a finalized Bundle whose identifier "
                "uses vrb_sha256_ and 64 lowercase "
                "hexadecimal characters."
            ),
        )

    return value


def _load_verified_references(
    references: list[dict[str, Any]],
) -> list[_VerifiedReference]:
    verified: list[_VerifiedReference] = []
    observed_bundle_ids: set[str] = set()
    observed_bundle_dirs: set[Path] = set()

    for index, reference in enumerate(references):
        loaded = load_comparison_bundle(
            reference["bundle_dir"]
        )

        manifest_sha256 = (
            _read_verified_manifest_snapshot(
                loaded
            )
        )

        report_bundle_id = (
            _validate_report_bundle_id(
                loaded.manifest.get(
                    "report_bundle_id"
                ),
                index=index,
            )
        )

        if report_bundle_id in observed_bundle_ids:
            _raise_service_error(
                "Duplicate Reference report_bundle_id: "
                f"{report_bundle_id}.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_SERVICE_"
                    "REFERENCE_BUNDLE_DUPLICATE"
                ),
                hint=(
                    "Select each verified Core Bundle "
                    "identity only once."
                ),
            )

        if loaded.bundle_dir in observed_bundle_dirs:
            _raise_service_error(
                "The same resolved Bundle directory was "
                "selected more than once.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_SERVICE_"
                    "REFERENCE_PATH_DUPLICATE"
                ),
                hint=(
                    "Select each local Bundle directory "
                    "only once."
                ),
            )

        observed_bundle_ids.add(
            report_bundle_id
        )
        observed_bundle_dirs.add(
            loaded.bundle_dir
        )

        verified.append(
            _VerifiedReference(
                loaded_bundle=loaded,
                report_bundle_id=(
                    report_bundle_id
                ),
                report_manifest_sha256=(
                    manifest_sha256
                ),
                dimensions=copy.deepcopy(
                    reference["dimensions"]
                ),
                selection=copy.deepcopy(
                    reference["selection"]
                ),
            )
        )

    return verified


def _evaluate_reference_compatibility(
    references: list[_VerifiedReference],
) -> tuple[
    tuple[dict[str, Any], ...],
    tuple[dict[str, Any], ...],
]:
    """Compare every candidate with one equality-contract anchor."""

    anchor = references[0]

    warnings: list[dict[str, Any]] = []
    incompatibilities: list[
        dict[str, Any]
    ] = []

    for candidate in references[1:]:
        result = evaluate_bundle_compatibility(
            anchor.loaded_bundle,
            candidate.loaded_bundle,
        )

        pair = {
            "anchor_report_bundle_id": (
                anchor.report_bundle_id
            ),
            "candidate_report_bundle_id": (
                candidate.report_bundle_id
            ),
        }

        for warning in result.warnings:
            warnings.append({
                **pair,
                "warning": copy.deepcopy(
                    warning
                ),
            })

        if not result.is_compatible:
            incompatibilities.append({
                **pair,
                "blocking_reasons": [
                    copy.deepcopy(reason)
                    for reason in (
                        result.blocking_reasons
                    )
                ],
            })

    return (
        tuple(warnings),
        tuple(incompatibilities),
    )


def create_private_baseline(
    parent_dir: str | Path,
    *,
    display_name: Any,
    created_at: Any,
    created_by: Any,
    dimension_policy: Any,
    references: Any,
) -> CreatedPrivateBaseline:
    """Create a Baseline from explicitly selected verified Bundles.

    Each Reference Bundle is loaded exactly once in this operation.
    No persistent cache, automatic schema conversion, soft correction,
    automatic Reference selection, or network access is performed.
    """

    request = _prevalidate_private_request(
        display_name=display_name,
        created_at=created_at,
        created_by=created_by,
        dimension_policy=dimension_policy,
        references=references,
    )

    verified_references = (
        _load_verified_references(
            request["references"]
        )
    )

    (
        compatibility_warnings,
        incompatibilities,
    ) = _evaluate_reference_compatibility(
        verified_references
    )

    if incompatibilities:
        _raise_service_error(
            "Selected Reference Bundles are mutually "
            "incompatible under Comparison v1. "
            f"Incompatible pairs: "
            f"{len(incompatibilities)}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_SERVICE_"
                "REFERENCES_INCOMPATIBLE"
            ),
            hint=(
                "Use References with matching Core schema "
                "and extraction contracts. Provenance-only "
                "differences may remain warnings."
            ),
            incompatibilities=(
                incompatibilities
            ),
        )

    memberships = [
        {
            "report_bundle_id": (
                reference.report_bundle_id
            ),
            "report_manifest_sha256": (
                reference.report_manifest_sha256
            ),
            "dimensions": copy.deepcopy(
                reference.dimensions
            ),
            "selection": copy.deepcopy(
                reference.selection
            ),
        }
        for reference in verified_references
    ]

    bundle_locations = {
        reference.report_bundle_id: str(
            reference.loaded_bundle.bundle_dir
        )
        for reference in verified_references
    }

    loaded_registry = (
        _install_initial_private_baseline(
            parent_dir,
            display_name=request[
                "display_name"
            ],
            created_at=request["created_at"],
            created_by=request["created_by"],
            dimension_policy=request[
                "dimension_policy"
            ],
            reference_memberships=memberships,
            bundle_locations=bundle_locations,
        )
    )

    return CreatedPrivateBaseline(
        loaded_registry=loaded_registry,
        compatibility_warnings=(
            compatibility_warnings
        ),
    )
