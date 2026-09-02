"""Content-derived identity for Velune Evidence Report Bundles."""

import hashlib
import json
import unicodedata
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Any

from velune_trace.reporting.artifacts import (
    SUPPORTED_HASH_ALGORITHMS,
)


BUNDLE_ID_PREFIX = "vrb_sha256_"
IDENTITY_ALGORITHM = "sha256_velune_ascii_json_v1"


def _normalize_required_string(
    value: str,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    normalized = unicodedata.normalize("NFC", value)

    if not normalized:
        raise ValueError(
            f"{field_name} must be a non-empty string"
        )

    if normalized != normalized.strip():
        raise ValueError(
            f"{field_name} must not contain leading or "
            "trailing whitespace"
        )

    return normalized


def _normalize_json_value(
    value: Any,
    field_name: str,
) -> Any:
    """Return a detached, normalized JSON-compatible value."""

    if value is None or isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        raise ValueError(
            f"{field_name} must not contain floating-point values; "
            "use integer base units or decimal strings"
        )

    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)

    if isinstance(value, list):
        return [
            _normalize_json_value(
                item,
                f"{field_name}[{index}]",
            )
            for index, item in enumerate(value)
        ]

    if isinstance(value, Mapping):
        normalized_mapping: dict[str, Any] = {}

        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    f"{field_name} keys must be strings"
                )

            normalized_key = unicodedata.normalize("NFC", key)

            if normalized_key in normalized_mapping:
                raise ValueError(
                    f"{field_name} contains duplicate keys "
                    "after Unicode normalization"
                )

            normalized_mapping[normalized_key] = (
                _normalize_json_value(
                    item,
                    f"{field_name}.{normalized_key}",
                )
            )

        return normalized_mapping

    raise ValueError(
        f"{field_name} contains a non-JSON-compatible value: "
        f"{type(value).__name__}"
    )


def _normalize_json_mapping(
    value: Mapping[str, Any],
    field_name: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")

    normalized = _normalize_json_value(value, field_name)

    if not isinstance(normalized, dict):
        raise TypeError(f"{field_name} must normalize to an object")

    return normalized


def _require_artifact_path(
    artifact: Mapping[str, Any],
    index: int,
) -> str:
    field_name = f"artifacts[{index}].path"

    if "path" not in artifact:
        raise ValueError(f"{field_name} is required")

    raw_path = artifact["path"]

    if not isinstance(raw_path, str):
        raise TypeError(f"{field_name} must be a string")

    normalized_path = unicodedata.normalize("NFC", raw_path)

    if not normalized_path:
        raise ValueError(
            f"{field_name} must be a non-empty string"
        )

    if normalized_path != normalized_path.strip():
        raise ValueError(
            f"{field_name} must not contain leading or "
            "trailing whitespace"
        )

    if "\\" in normalized_path:
        raise ValueError(
            f"{field_name} must use POSIX path separators"
        )

    if any(
        ord(character) < 32 or ord(character) == 127
        for character in normalized_path
    ):
        raise ValueError(
            f"{field_name} must not contain control characters"
        )

    parsed_path = PurePosixPath(normalized_path)

    if parsed_path.is_absolute():
        raise ValueError(
            f"{field_name} must be relative to the bundle"
        )

    if any(part in {".", ".."} for part in parsed_path.parts):
        raise ValueError(
            f"{field_name} must not contain '.' or '..'"
        )

    canonical_path = parsed_path.as_posix()

    if canonical_path == ".":
        raise ValueError(
            f"{field_name} must identify a file"
        )

    if canonical_path != normalized_path:
        raise ValueError(
            f"{field_name} must be a canonical relative "
            "POSIX path"
        )

    return canonical_path


def _validate_artifact_record(
    artifact: dict[str, Any],
    index: int,
) -> str:
    field_name = f"artifacts[{index}]"

    required_fields = {
        "path",
        "role",
        "media_type",
        "size_bytes",
        "hash",
        "source_of_truth",
    }
    missing_fields = sorted(
        required_fields.difference(artifact)
    )

    if missing_fields:
        raise ValueError(
            f"{field_name} is missing required fields: "
            f"{', '.join(missing_fields)}"
        )

    artifact_path = _require_artifact_path(
        artifact,
        index,
    )
    role = _normalize_required_string(
        artifact["role"],
        f"{field_name}.role",
    )
    media_type = _normalize_required_string(
        artifact["media_type"],
        f"{field_name}.media_type",
    )

    size_bytes = artifact["size_bytes"]
    if (
        isinstance(size_bytes, bool)
        or not isinstance(size_bytes, int)
        or size_bytes < 0
    ):
        raise ValueError(
            f"{field_name}.size_bytes must be a "
            "non-negative integer"
        )

    source_of_truth = artifact["source_of_truth"]
    if not isinstance(source_of_truth, bool):
        raise TypeError(
            f"{field_name}.source_of_truth must be a bool"
        )

    hash_record = artifact["hash"]
    if not isinstance(hash_record, Mapping):
        raise TypeError(
            f"{field_name}.hash must be a mapping"
        )

    if "algorithm" not in hash_record:
        raise ValueError(
            f"{field_name}.hash.algorithm is required"
        )

    if "value" not in hash_record:
        raise ValueError(
            f"{field_name}.hash.value is required"
        )

    hash_algorithm = _normalize_required_string(
        hash_record["algorithm"],
        f"{field_name}.hash.algorithm",
    ).lower()

    if hash_algorithm not in SUPPORTED_HASH_ALGORITHMS:
        supported = ", ".join(
            sorted(SUPPORTED_HASH_ALGORITHMS)
        )
        raise ValueError(
            f"{field_name}.hash.algorithm is unsupported: "
            f"{hash_algorithm}; supported algorithms: "
            f"{supported}"
        )

    hash_value = _normalize_required_string(
        hash_record["value"],
        f"{field_name}.hash.value",
    ).lower()

    expected_hex_length = (
        hashlib.new(hash_algorithm).digest_size * 2
    )

    if (
        len(hash_value) != expected_hex_length
        or any(
            character not in "0123456789abcdef"
            for character in hash_value
        )
    ):
        raise ValueError(
            f"{field_name}.hash.value must be a valid "
            f"{hash_algorithm} hexadecimal digest"
        )

    normalized_hash = dict(hash_record)
    normalized_hash["algorithm"] = hash_algorithm
    normalized_hash["value"] = hash_value

    artifact["path"] = artifact_path
    artifact["role"] = role
    artifact["media_type"] = media_type
    artifact["size_bytes"] = size_bytes
    artifact["hash"] = normalized_hash
    artifact["source_of_truth"] = source_of_truth

    return artifact_path


def _canonical_json_bytes(
    value: Mapping[str, Any],
) -> bytes:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "bundle identity payload must be canonical "
            "JSON-compatible"
        ) from exc

    # ensure_ascii=True guarantees ASCII-only output.
    return encoded.encode("ascii")


def build_report_bundle_id(
    *,
    bundle_schema_name: str,
    bundle_schema_version: str,
    engine_name: str,
    engine_version: str,
    extraction: Mapping[str, Any],
    artifacts: list[Mapping[str, Any]],
) -> str:
    """Build a content-derived identifier for one report bundle.

    A top-level generation timestamp and local source path are not direct
    identity inputs. The identifier still reflects the supplied artifact
    hashes. If an artifact embeds a timestamp, changing that timestamp changes
    the artifact hash and therefore changes the bundle identifier.
    """

    if not isinstance(artifacts, list):
        raise TypeError("artifacts must be a list")

    if not artifacts:
        raise ValueError(
            "artifacts must contain at least one artifact"
        )

    artifact_records: list[dict[str, Any]] = []
    artifact_paths: set[str] = set()

    for index, artifact in enumerate(artifacts):
        artifact_record = _normalize_json_mapping(
            artifact,
            f"artifacts[{index}]",
        )
        artifact_path = _validate_artifact_record(
            artifact_record,
            index,
        )

        if artifact_path in artifact_paths:
            raise ValueError(
                f"duplicate artifact path: {artifact_path}"
            )

        artifact_paths.add(artifact_path)
        artifact_record["path"] = artifact_path
        artifact_records.append(artifact_record)

    artifact_records.sort(
        key=lambda artifact: artifact["path"]
    )

    identity_payload = {
        "identity_algorithm": IDENTITY_ALGORITHM,
        "bundle_schema": {
            "name": _normalize_required_string(
                bundle_schema_name,
                "bundle_schema_name",
            ),
            "version": _normalize_required_string(
                bundle_schema_version,
                "bundle_schema_version",
            ),
        },
        "engine": {
            "name": _normalize_required_string(
                engine_name,
                "engine_name",
            ),
            "version": _normalize_required_string(
                engine_version,
                "engine_version",
            ),
        },
        "extraction": _normalize_json_mapping(
            extraction,
            "extraction",
        ),
        "artifacts": artifact_records,
    }

    digest = hashlib.sha256(
        _canonical_json_bytes(identity_payload)
    ).hexdigest()

    return f"{BUNDLE_ID_PREFIX}{digest}"
