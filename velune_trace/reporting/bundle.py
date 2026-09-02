"""Private Evidence Report Bundle manifest assembly."""

from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from velune_trace import __version__
from velune_trace.reporting.artifacts import (
    build_artifact_record,
)
from velune_trace.reporting.errors import (
    ArtifactDefinitionError,
    BundleAssemblyError,
)
from velune_trace.reporting.identity import (
    IDENTITY_ALGORITHM,
    build_report_bundle_id,
)
from velune_trace.reporting.manifest import (
    BUNDLE_SCHEMA_NAME,
    BUNDLE_SCHEMA_VERSION,
    build_private_report_manifest,
)


ENGINE_NAME = "velune_trace"

ARTIFACT_DEFINITION_FIELDS = frozenset({
    "path",
    "role",
    "media_type",
    "source_of_truth",
})

RESERVED_MANIFEST_PATH = "report_manifest.json"

RAW_RUNTIME_LOG_SUFFIXES = frozenset({
    ".bag",
    ".db3",
    ".mcap",
    ".sqlite3",
})


def _require_non_empty_string(
    value: Any,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise ArtifactDefinitionError(
            f"{field_name} must be a string",
            code="VELUNE_BUNDLE_ARTIFACT_FIELD_TYPE",
            hint=(
                "Check the artifact definition and provide "
                "a non-empty string."
            ),
        )

    if not value or value != value.strip():
        raise ArtifactDefinitionError(
            f"{field_name} must be a non-empty string "
            "without surrounding whitespace",
            code="VELUNE_BUNDLE_ARTIFACT_FIELD_VALUE",
            hint=(
                "Use a canonical Bundle-relative path, role, "
                "or media type."
            ),
        )

    return value


def _require_artifact_definition(
    value: Mapping[str, Any],
    index: int,
) -> dict[str, Any]:
    field_name = f"artifact_definitions[{index}]"

    if not isinstance(value, Mapping):
        raise ArtifactDefinitionError(
            f"{field_name} must be a mapping",
            code="VELUNE_BUNDLE_ARTIFACT_DEFINITION_TYPE",
            hint=(
                "Provide path, role, media_type, and "
                "source_of_truth fields."
            ),
        )

    definition = dict(value)

    missing_fields = sorted(
        ARTIFACT_DEFINITION_FIELDS.difference(definition)
    )
    if missing_fields:
        raise ArtifactDefinitionError(
            f"{field_name} is missing required fields: "
            f"{', '.join(missing_fields)}",
            code="VELUNE_BUNDLE_ARTIFACT_FIELDS_MISSING",
            hint=(
                "Every artifact definition requires path, role, "
                "media_type, and source_of_truth."
            ),
        )

    unknown_fields = sorted(
        set(definition).difference(
            ARTIFACT_DEFINITION_FIELDS
        )
    )
    if unknown_fields:
        raise ArtifactDefinitionError(
            f"{field_name} contains unsupported fields: "
            f"{', '.join(unknown_fields)}",
            code="VELUNE_BUNDLE_ARTIFACT_FIELDS_UNSUPPORTED",
            hint=(
                "Remove unsupported fields from the artifact "
                "definition."
            ),
        )

    definition["path"] = _require_non_empty_string(
        definition["path"],
        f"{field_name}.path",
    )
    definition["role"] = _require_non_empty_string(
        definition["role"],
        f"{field_name}.role",
    )
    definition["media_type"] = _require_non_empty_string(
        definition["media_type"],
        f"{field_name}.media_type",
    )

    if not isinstance(
        definition["source_of_truth"],
        bool,
    ):
        raise ArtifactDefinitionError(
            f"{field_name}.source_of_truth must be a bool",
            code="VELUNE_BUNDLE_SOURCE_OF_TRUTH_TYPE",
            hint="Use true or false for source_of_truth.",
        )

    return definition


def _enforce_bundle_artifact_policy(
    definition: Mapping[str, Any],
    index: int,
) -> None:
    field_name = f"artifact_definitions[{index}]"
    artifact_path = definition["path"]

    if artifact_path == RESERVED_MANIFEST_PATH:
        raise ArtifactDefinitionError(
            (
                "report_manifest.json must not be included "
                "as a Bundle artifact"
            ),
            code="VELUNE_BUNDLE_MANIFEST_SELF_REFERENCE",
            hint=(
                "Generate report_manifest.json only after all "
                "other Bundle artifacts have been finalized."
            ),
        )

    suffix = PurePosixPath(artifact_path).suffix.lower()

    if suffix in RAW_RUNTIME_LOG_SUFFIXES:
        raise ArtifactDefinitionError(
            (
                f"{field_name}.path references a raw runtime "
                f"log that cannot be included in the Bundle: "
                f"{artifact_path}"
            ),
            code="VELUNE_BUNDLE_RAW_LOG_ARTIFACT_FORBIDDEN",
            hint=(
                "Keep MCAP, rosbag2, and other raw runtime logs "
                "local. Include only derived Evidence Report "
                "Bundle artifacts."
            ),
        )


def assemble_private_report_manifest(
    *,
    bundle_dir: str | Path,
    generated_at: str,
    source: Mapping[str, Any],
    extraction: Mapping[str, Any],
    identity_extraction: Mapping[str, Any],
    artifact_definitions: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Assemble a private manifest from existing Bundle artifacts.

    ``extraction`` is human-readable manifest metadata and may contain finite
    floating-point values.

    ``identity_extraction`` is canonical Bundle identity metadata. It must use
    deterministic integer base units or decimal strings rather than floats.

    Artifact files are hashed sequentially in bounded-memory streaming mode.
    Raw MCAP, rosbag2, camera streams, PointCloud payloads, and other large
    runtime logs are not Evidence Report Bundle artifacts.

    This function returns an in-memory manifest. It does not write files,
    perform telemetry, or upload data.
    """

    if not isinstance(artifact_definitions, list):
        raise ArtifactDefinitionError(
            "artifact_definitions must be a list",
            code="VELUNE_BUNDLE_ARTIFACT_LIST_TYPE",
            hint="Provide a list of artifact definition objects.",
        )

    if not artifact_definitions:
        raise ArtifactDefinitionError(
            "artifact_definitions must contain at least "
            "one artifact",
            code="VELUNE_BUNDLE_ARTIFACT_LIST_EMPTY",
            hint=(
                "Generate the Bundle artifacts before assembling "
                "the manifest."
            ),
        )

    raw_bundle_dir = Path(bundle_dir)
    artifact_records: list[dict[str, object]] = []
    seen_paths: set[str] = set()

    for index, raw_definition in enumerate(
        artifact_definitions
    ):
        definition = _require_artifact_definition(
            raw_definition,
            index,
        )
        _enforce_bundle_artifact_policy(
            definition,
            index,
        )

        try:
            artifact_record = build_artifact_record(
                bundle_dir=raw_bundle_dir,
                artifact_path=(
                    raw_bundle_dir / definition["path"]
                ),
                role=definition["role"],
                media_type=definition["media_type"],
                source_of_truth=definition[
                    "source_of_truth"
                ],
            )
        except (OSError, TypeError, ValueError) as exc:
            raise ArtifactDefinitionError(
                f"Unable to inspect artifact "
                f"{definition['path']}: {exc}",
                code="VELUNE_BUNDLE_ARTIFACT_INSPECTION_FAILED",
                hint=(
                    "Confirm that the file exists inside the "
                    "Bundle directory and is not a symbolic link."
                ),
            ) from exc

        artifact_path = str(artifact_record["path"])

        if artifact_path in seen_paths:
            raise ArtifactDefinitionError(
                f"Duplicate artifact path: {artifact_path}",
                code="VELUNE_BUNDLE_ARTIFACT_PATH_DUPLICATE",
                hint=(
                    "Each Bundle artifact path must be unique."
                ),
            )

        seen_paths.add(artifact_path)
        artifact_records.append(artifact_record)

    artifact_records.sort(
        key=lambda artifact: str(artifact["path"])
    )

    try:
        report_bundle_id = build_report_bundle_id(
            bundle_schema_name=BUNDLE_SCHEMA_NAME,
            bundle_schema_version=BUNDLE_SCHEMA_VERSION,
            engine_name=ENGINE_NAME,
            engine_version=__version__,
            extraction=identity_extraction,
            artifacts=artifact_records,
        )
    except (TypeError, ValueError) as exc:
        raise BundleAssemblyError(
            f"Unable to derive the Bundle identity: {exc}",
            code="VELUNE_BUNDLE_IDENTITY_INVALID",
            hint=(
                "Use canonical identity metadata with integer "
                "base units such as window_ns. Do not use floats "
                "inside identity_extraction."
            ),
        ) from exc

    try:
        manifest = build_private_report_manifest(
            report_bundle_id=report_bundle_id,
            generated_at=generated_at,
            source=source,
            extraction=extraction,
            artifacts=artifact_records,
        )
    except (TypeError, ValueError) as exc:
        raise BundleAssemblyError(
            f"Unable to build the private manifest: {exc}",
            code="VELUNE_BUNDLE_MANIFEST_INVALID",
            hint=(
                "Check generated_at, source metadata, and "
                "extraction metadata."
            ),
        ) from exc

    total_artifact_size_bytes = sum(
        int(artifact["size_bytes"])
        for artifact in artifact_records
    )

    manifest["bundle_identity"] = {
        "algorithm": IDENTITY_ALGORITHM,
        "content_derived": True,
        "artifact_order_independent": True,
        "report_manifest_included": False,
        "generated_at_directly_included": False,
        "local_source_provenance_directly_included": False,
        "identity_extraction_requires_integer_base_units": True,
    }

    manifest["bundle_summary"] = {
        "artifact_count": len(artifact_records),
        "total_artifact_size_bytes": (
            total_artifact_size_bytes
        ),
        "artifact_hashing_mode": (
            "sequential_bounded_memory_streaming"
        ),
        "raw_runtime_logs_included": False,
    }

    return manifest
