"""Evidence Report Bundle finalization orchestration."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from velune_trace.reporting.bundle import (
    assemble_private_report_manifest,
)
from velune_trace.reporting.errors import (
    EvidenceBundleError,
)
from velune_trace.reporting.writer import (
    write_private_report_manifest,
)


FINALIZATION_STAGE_ASSEMBLY = "manifest_assembly"
FINALIZATION_STAGE_WRITE = "manifest_write"


@dataclass(frozen=True)
class FinalizedPrivateReportBundle:
    """Result of successfully finalizing a private Bundle."""

    manifest: dict[str, Any]
    manifest_path: Path

    @property
    def report_bundle_id(self) -> str:
        """Return the content-derived Bundle identifier."""

        return str(self.manifest["report_bundle_id"])


def finalize_private_report_bundle(
    *,
    bundle_dir: str | Path,
    generated_at: str,
    source: Mapping[str, Any],
    extraction: Mapping[str, Any],
    identity_extraction: Mapping[str, Any],
    artifact_definitions: list[Mapping[str, Any]],
    overwrite_manifest: bool = False,
) -> FinalizedPrivateReportBundle:
    """Assemble and atomically finalize a private Evidence Bundle.

    All declared artifacts must already exist. Artifact integrity metadata and
    the content-derived Bundle ID are calculated before report_manifest.json
    is installed as the final Bundle file.

    Raw runtime logs remain local and are not accepted as Bundle artifacts.
    This function performs no telemetry, network access, or upload.

    Callers may catch ``EvidenceBundleError`` once for every expected Bundle
    failure. The original specific subclass, error code, hint, cause, and
    traceback are preserved. The error's ``stage`` identifies whether failure
    occurred during manifest assembly or atomic manifest writing.

    Raises:
        EvidenceBundleError:
            An expected artifact validation, Bundle assembly, identity,
            manifest validation, or atomic manifest write failure.

    Unexpected programming defects are intentionally not converted into
    domain errors, so their original traceback remains visible.
    """

    try:
        manifest = assemble_private_report_manifest(
            bundle_dir=bundle_dir,
            generated_at=generated_at,
            source=source,
            extraction=extraction,
            identity_extraction=identity_extraction,
            artifact_definitions=artifact_definitions,
        )
    except EvidenceBundleError as exc:
        exc.attach_stage(
            FINALIZATION_STAGE_ASSEMBLY
        )
        raise

    try:
        manifest_path = write_private_report_manifest(
            bundle_dir=bundle_dir,
            manifest=manifest,
            overwrite=overwrite_manifest,
        )
    except EvidenceBundleError as exc:
        exc.attach_stage(
            FINALIZATION_STAGE_WRITE
        )
        raise

    return FinalizedPrivateReportBundle(
        manifest=manifest,
        manifest_path=manifest_path,
    )
