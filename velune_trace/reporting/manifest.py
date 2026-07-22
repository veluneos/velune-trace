"""Private manifest contract for Velune Evidence Report Bundles."""

import json
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime
from typing import Any

from velune_trace import __version__


MANIFEST_SCHEMA_NAME = "velune.report_manifest"
MANIFEST_SCHEMA_VERSION = "0.1.0"

BUNDLE_SCHEMA_NAME = "velune.evidence_report_bundle"
BUNDLE_SCHEMA_VERSION = "0.1.0"

SCHEMA_STATUS = "draft"
MANIFEST_VISIBILITY = "private_local_only"
SOURCE_FINGERPRINT_POLICY = "private_only_if_present"


def _require_non_empty_string(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")

    return value.strip()


def _require_iso8601_timestamp(value: str, field_name: str) -> str:
    timestamp = _require_non_empty_string(value, field_name)

    normalized = (
        f"{timestamp[:-1]}+00:00"
        if timestamp.endswith("Z")
        else timestamp
    )

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be a valid ISO 8601 timestamp"
        ) from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(
            f"{field_name} must include a timezone offset"
        )

    return parsed.isoformat()


def _copy_json_mapping(
    value: Mapping[str, Any],
    field_name: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")

    copied = deepcopy(dict(value))

    try:
        json.dumps(copied, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} must contain only JSON-compatible finite values"
        ) from exc

    return copied


def build_private_report_manifest(
    *,
    report_bundle_id: str,
    generated_at: str,
    source: Mapping[str, Any],
    extraction: Mapping[str, Any],
    artifacts: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the private, local-only manifest for one report bundle.

    This manifest may contain local provenance such as the source file name,
    source size, or a future source fingerprint. It must not be used as the
    externally shareable report.
    """

    bundle_id = _require_non_empty_string(
        report_bundle_id,
        "report_bundle_id",
    )
    generation_timestamp = _require_iso8601_timestamp(
        generated_at,
        "generated_at",
    )

    source_record = _copy_json_mapping(source, "source")
    extraction_record = _copy_json_mapping(
        extraction,
        "extraction",
    )

    if not isinstance(artifacts, list):
        raise TypeError("artifacts must be a list")

    artifact_records = [
        _copy_json_mapping(
            artifact,
            f"artifacts[{index}]",
        )
        for index, artifact in enumerate(artifacts)
    ]

    return {
        "schema_name": MANIFEST_SCHEMA_NAME,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "schema_status": SCHEMA_STATUS,
        "bundle_schema": {
            "name": BUNDLE_SCHEMA_NAME,
            "version": BUNDLE_SCHEMA_VERSION,
        },
        "report_bundle_id": bundle_id,
        "generated_at": generation_timestamp,
        "visibility": MANIFEST_VISIBILITY,
        "engine": {
            "name": "velune_trace",
            "version": __version__,
        },
        "source_provenance_policy": {
            "visibility": MANIFEST_VISIBILITY,
            "fingerprint_policy": SOURCE_FINGERPRINT_POLICY,
        },
        "source": source_record,
        "extraction": extraction_record,
        "artifacts": artifact_records,
        "document_policy": {
            "machine_readable_json_source_of_truth": True,
            "markdown_is_derived_human_readable_view": True,
        },
        "judgment_boundary": {
            "root_cause_conclusion": False,
            "fault_assignment": False,
            "liability_calculation": False,
        },
    }
