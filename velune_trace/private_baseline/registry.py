"""Fail-closed Private Baseline Registry v1 loading."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import stat
import unicodedata
from typing import Any

from velune_trace.private_baseline.contract import (
    BASELINE_ID_KIND,
    BASELINE_REVISION_ID_KIND,
    DISPLAY_NAME_MAX_LENGTH,
    EVALUATION_ID_KIND,
    PRIVATE_BASELINE_SCHEMA_VERSION,
    PRIVATE_BASELINE_VISIBILITY,
    REVIEW_RECORD_ID_KIND,
    normalize_single_line_text,
    validate_opaque_identifier,
)
from velune_trace.private_baseline.errors import (
    PrivateBaselineContractError,
)
from velune_trace.private_baseline.revision import (
    REPORT_BUNDLE_ID_PREFIX,
    SHA256_HEX_LENGTH,
    validate_baseline_revision,
)


BASELINE_REGISTRY_FILENAME = "baseline_registry.json"
BASELINE_REGISTRY_SCHEMA_NAME = (
    "velune.private_baseline_registry"
)
BASELINE_REGISTRY_SEMANTICS = (
    "local_atomic_baseline_index"
)

READ_CHUNK_SIZE = 1024 * 1024
ISO8601_TIMESTAMP_MAX_LENGTH = 64

_EVALUATION_SCHEMA_NAME = (
    "velune.private_baseline_evaluation"
)
_EVALUATION_SEMANTICS = (
    "observed_against_user_selected_reference_set"
)

_REVIEW_SCHEMA_NAME = (
    "velune.private_baseline_review"
)
_REVIEW_SEMANTICS = (
    "human_authored_review_record"
)

_REGISTRY_FIELDS = frozenset({
    "schema_name",
    "schema_version",
    "visibility",
    "semantics",
    "baseline_id",
    "display_name",
    "created_at",
    "current_revision_id",
    "revisions",
    "evaluations",
    "reviews",
    "bundle_locations",
})

_RECORD_ENTRY_FIELDS = frozenset({
    "record_id",
    "relative_path",
    "size_bytes",
    "sha256",
})

_EVALUATION_FIELDS = frozenset({
    "schema_name",
    "schema_version",
    "visibility",
    "semantics",
    "evaluation_id",
    "generated_at",
    "baseline_id",
    "baseline_revision_id",
    "evaluation_context",
    "target",
    "reference_comparisons",
    "aggregate_observations",
    "judgment_boundary",
})

_REVIEW_FIELDS = frozenset({
    "schema_name",
    "schema_version",
    "visibility",
    "semantics",
    "review_record_id",
    "created_at",
    "baseline_id",
    "baseline_revision_id",
    "evaluation_id",
    "review_scope",
    "subject",
    "label_source",
    "label",
    "reviewer",
    "notes",
    "supersedes_review_record_id",
})


class PrivateBaselineRegistryError(
    PrivateBaselineContractError
):
    """Raised when Registry state cannot be trusted."""

    default_code = (
        "VELUNE_PRIVATE_BASELINE_REGISTRY_INVALID"
    )


@dataclass(frozen=True)
class LoadedRegistryRecord:
    """One verified immutable file referenced by the Registry."""

    registry_array: str
    record_id: str
    relative_path: str
    path: Path
    size_bytes: int
    sha256: str
    document: dict[str, Any]

    def as_registry_entry(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "relative_path": self.relative_path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class LoadedPrivateBaselineRegistry:
    """Verified Registry and its referenced immutable records."""

    root_dir: Path
    registry_path: Path
    registry: dict[str, Any]
    revisions_by_id: dict[str, LoadedRegistryRecord]
    evaluations_by_id: dict[
        str,
        LoadedRegistryRecord,
    ]
    reviews_by_id: dict[str, LoadedRegistryRecord]

    @property
    def current_revision(self) -> LoadedRegistryRecord:
        return self.revisions_by_id[
            self.registry["current_revision_id"]
        ]


@dataclass(frozen=True)
class _RecordSpec:
    array_name: str
    id_kind: str
    id_field: str
    schema_name: str


_RECORD_SPECS = {
    "revisions": _RecordSpec(
        array_name="revisions",
        id_kind=BASELINE_REVISION_ID_KIND,
        id_field="baseline_revision_id",
        schema_name=(
            "velune.private_baseline_revision"
        ),
    ),
    "evaluations": _RecordSpec(
        array_name="evaluations",
        id_kind=EVALUATION_ID_KIND,
        id_field="evaluation_id",
        schema_name=_EVALUATION_SCHEMA_NAME,
    ),
    "reviews": _RecordSpec(
        array_name="reviews",
        id_kind=REVIEW_RECORD_ID_KIND,
        id_field="review_record_id",
        schema_name=_REVIEW_SCHEMA_NAME,
    ),
}


class _DuplicateJsonKeyError(ValueError):
    """Internal strict-JSON duplicate-key error."""


def _raise_registry_error(
    message: str,
    *,
    code: str,
    hint: str,
) -> None:
    raise PrivateBaselineRegistryError(
        message,
        code=code,
        hint=hint,
        stage="private_baseline_registry",
    )


def _require_mapping(
    value: Any,
    *,
    field_name: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _raise_registry_error(
            f"{field_name} must be a JSON object.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "MAPPING_REQUIRED"
            ),
            hint=(
                "Restore a complete Registry or immutable "
                "JSON record."
            ),
        )

    for key in value:
        if not isinstance(key, str):
            _raise_registry_error(
                f"{field_name} keys must be strings.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "KEY_TYPE_INVALID"
                ),
                hint="Use canonical JSON field names.",
            )

    return value


def _require_exact_fields(
    value: Mapping[str, Any],
    *,
    required_fields: frozenset[str],
    field_name: str,
) -> None:
    actual_fields = set(value)

    missing = sorted(
        required_fields.difference(actual_fields)
    )
    unexpected = sorted(
        actual_fields.difference(required_fields)
    )

    if missing:
        _raise_registry_error(
            f"{field_name} is missing required fields: "
            f"{', '.join(missing)}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "REQUIRED_FIELD_MISSING"
            ),
            hint=(
                "Restore the complete frozen v1 JSON "
                "record."
            ),
        )

    if unexpected:
        _raise_registry_error(
            f"{field_name} contains unexpected fields: "
            f"{', '.join(unexpected)}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "UNEXPECTED_FIELD"
            ),
            hint=(
                "Remove fields outside the frozen v1 "
                "schema."
            ),
        )


def _wrap_identifier(
    value: Any,
    *,
    kind: str,
    field_name: str,
) -> str:
    try:
        return validate_opaque_identifier(
            value,
            kind,
        )
    except PrivateBaselineContractError as exc:
        raise PrivateBaselineRegistryError(
            f"{field_name} contains an invalid identifier.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "IDENTIFIER_INVALID"
            ),
            hint=(
                "Restore the exact opaque identifier "
                "recorded at installation."
            ),
            stage="private_baseline_registry",
        ) from exc


def _wrap_single_line(
    value: Any,
    *,
    field_name: str,
    max_length: int,
) -> str:
    try:
        return normalize_single_line_text(
            value,
            field_name=field_name,
            max_length=max_length,
        )
    except PrivateBaselineContractError as exc:
        raise PrivateBaselineRegistryError(
            f"{field_name} violates the private text "
            "contract.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "TEXT_INVALID"
            ),
            hint=(
                "Restore the NFC-normalized private "
                "Registry value."
            ),
            stage="private_baseline_registry",
        ) from exc


def _normalize_timestamp(
    value: Any,
    *,
    field_name: str,
) -> str:
    normalized = _wrap_single_line(
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
        raise PrivateBaselineRegistryError(
            f"{field_name} must be a valid ISO-8601 "
            "timestamp.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "TIMESTAMP_INVALID"
            ),
            hint=(
                "Use a timezone-aware ISO-8601 "
                "timestamp."
            ),
            stage="private_baseline_registry",
        ) from exc

    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
    ):
        _raise_registry_error(
            f"{field_name} must include a timezone.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "TIMESTAMP_TIMEZONE_REQUIRED"
            ),
            hint="Use Z or an explicit UTC offset.",
        )

    return normalized


def _normalize_sha256(
    value: Any,
    *,
    field_name: str,
) -> str:
    normalized = _wrap_single_line(
        value,
        field_name=field_name,
        max_length=SHA256_HEX_LENGTH,
    )

    valid = (
        len(normalized) == SHA256_HEX_LENGTH
        and all(
            character in "0123456789abcdef"
            for character in normalized
        )
    )

    if not valid:
        _raise_registry_error(
            f"{field_name} must be a lowercase SHA-256 "
            "digest.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "SHA256_INVALID"
            ),
            hint=(
                "Restore the exact immutable-record "
                "SHA-256."
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

    normalized = _wrap_single_line(
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
        _raise_registry_error(
            f"{field_name} must be a verified Core Bundle "
            "identifier.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "REPORT_BUNDLE_ID_INVALID"
            ),
            hint=(
                "Use vrb_sha256_ followed by a complete "
                "lowercase SHA-256 digest."
            ),
        )

    return normalized


def _object_pairs_without_duplicates(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKeyError(
                f"Duplicate JSON object key: {key}"
            )

        result[key] = value

    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(
        f"Non-finite JSON number is forbidden: {value}"
    )


def _require_valid_unicode_scalar(
    value: str,
    *,
    field_name: str,
) -> None:
    try:
        value.encode(
            "utf-8",
            errors="strict",
        )
    except UnicodeEncodeError as exc:
        raise ValueError(
            f"{field_name} contains an unpaired "
            "surrogate"
        ) from exc


def _validate_json_value(
    value: Any,
    *,
    field_name: str,
) -> None:
    if value is None or isinstance(value, bool):
        return

    if isinstance(value, int):
        return

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(
                f"{field_name} contains a non-finite "
                "number"
            )
        return

    if isinstance(value, str):
        _require_valid_unicode_scalar(
            value,
            field_name=field_name,
        )
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(
                item,
                field_name=f"{field_name}[{index}]",
            )
        return

    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(
                    f"{field_name} contains a non-string "
                    "JSON object key"
                )

            _require_valid_unicode_scalar(
                key,
                field_name=f"{field_name}.key",
            )

            _validate_json_value(
                item,
                field_name=f"{field_name}.{key}",
            )
        return

    raise ValueError(
        f"{field_name} contains a non-JSON value: "
        f"{type(value).__name__}"
    )


def _load_json_mapping_bytes(
    payload: bytes,
    *,
    document_name: str,
) -> dict[str, Any]:
    try:
        decoded = payload.decode(
            "utf-8",
            errors="strict",
        )

        value = json.loads(
            decoded,
            parse_constant=_reject_json_constant,
            object_pairs_hook=(
                _object_pairs_without_duplicates
            ),
        )

        _validate_json_value(
            value,
            field_name=document_name,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        _DuplicateJsonKeyError,
        RecursionError,
        ValueError,
    ) as exc:
        raise PrivateBaselineRegistryError(
            f"{document_name} is not valid strict JSON.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "JSON_INVALID"
            ),
            hint=(
                "Restore the valid UTF-8 JSON file. "
                "NaN, Infinity, duplicate keys, and "
                "unpaired surrogates are forbidden."
            ),
            stage="private_baseline_registry",
        ) from exc

    if not isinstance(value, dict):
        _raise_registry_error(
            f"{document_name} must contain a JSON object.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "JSON_OBJECT_REQUIRED"
            ),
            hint=(
                "Restore the complete JSON object."
            ),
        )

    return value


def _open_regular_file(
    path: Path,
    *,
    document_name: str,
):
    flags = os.O_RDONLY

    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    try:
        descriptor = os.open(
            path,
            flags,
        )
    except OSError as exc:
        raise PrivateBaselineRegistryError(
            f"Unable to open {document_name}: {exc}",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "FILE_UNAVAILABLE"
            ),
            hint=(
                "Restore the required regular file and "
                "remove symbolic links."
            ),
            stage="private_baseline_registry",
        ) from exc

    try:
        file_stat = os.fstat(descriptor)

        if not stat.S_ISREG(file_stat.st_mode):
            _raise_registry_error(
                f"{document_name} is not a regular file.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "FILE_TYPE_INVALID"
                ),
                hint=(
                    "Restore the required immutable JSON "
                    "file."
                ),
            )

        return os.fdopen(
            descriptor,
            "rb",
        )
    except Exception:
        os.close(descriptor)
        raise


def _read_file_bytes(
    path: Path,
    *,
    document_name: str,
) -> bytes:
    try:
        with _open_regular_file(
            path,
            document_name=document_name,
        ) as handle:
            return handle.read()
    except PrivateBaselineRegistryError:
        raise
    except OSError as exc:
        raise PrivateBaselineRegistryError(
            f"Unable to read {document_name}: {exc}",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "FILE_READ_FAILED"
            ),
            hint=(
                "Confirm the private file is readable and "
                "complete."
            ),
            stage="private_baseline_registry",
        ) from exc


def _read_verified_record(
    path: Path,
    *,
    document_name: str,
    expected_size: int,
    expected_sha256: str,
) -> bytes:
    digest = hashlib.sha256()
    payload = bytearray()
    actual_size = 0

    try:
        with _open_regular_file(
            path,
            document_name=document_name,
        ) as handle:
            file_stat = os.fstat(handle.fileno())

            if file_stat.st_size != expected_size:
                _raise_registry_error(
                    f"{document_name} size does not match "
                    "the Registry.",
                    code=(
                        "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                        "RECORD_SIZE_MISMATCH"
                    ),
                    hint=(
                        "Do not load a modified or "
                        "incomplete immutable record."
                    ),
                )

            while True:
                chunk = handle.read(READ_CHUNK_SIZE)

                if not chunk:
                    break

                digest.update(chunk)
                payload.extend(chunk)
                actual_size += len(chunk)
    except PrivateBaselineRegistryError:
        raise
    except OSError as exc:
        raise PrivateBaselineRegistryError(
            f"Unable to read {document_name}: {exc}",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "FILE_READ_FAILED"
            ),
            hint=(
                "Confirm the immutable record is readable "
                "and complete."
            ),
            stage="private_baseline_registry",
        ) from exc

    if actual_size != expected_size:
        _raise_registry_error(
            f"{document_name} size changed while it was "
            "being read.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "RECORD_SIZE_MISMATCH"
            ),
            hint=(
                "Do not mutate immutable records while "
                "loading."
            ),
        )

    actual_sha256 = digest.hexdigest()

    if actual_sha256 != expected_sha256:
        _raise_registry_error(
            f"{document_name} SHA-256 does not match the "
            "Registry.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "RECORD_HASH_MISMATCH"
            ),
            hint=(
                "Do not load a modified or untrusted "
                "immutable record."
            ),
        )

    return bytes(payload)


def _resolve_registry_root(
    root_dir: str | Path,
) -> Path:
    try:
        raw_root = Path(root_dir)
    except TypeError as exc:
        raise PrivateBaselineRegistryError(
            "Private Baseline root must be a filesystem "
            "path.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "ROOT_PATH_TYPE_INVALID"
            ),
            hint=(
                "Provide the existing Private Baseline "
                "root directory."
            ),
            stage="private_baseline_registry",
        ) from exc

    if raw_root.is_symlink():
        _raise_registry_error(
            "Private Baseline root must not be a symbolic "
            "link.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "ROOT_SYMLINK_FORBIDDEN"
            ),
            hint=(
                "Use the real Private Baseline root "
                "directory."
            ),
        )

    try:
        resolved_root = raw_root.resolve(
            strict=True
        )
    except OSError as exc:
        raise PrivateBaselineRegistryError(
            f"Unable to resolve Private Baseline root: "
            f"{exc}",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "ROOT_UNAVAILABLE"
            ),
            hint=(
                "Restore the existing Private Baseline "
                "root directory."
            ),
            stage="private_baseline_registry",
        ) from exc

    if not resolved_root.is_dir():
        _raise_registry_error(
            "Private Baseline root is not a directory.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "ROOT_TYPE_INVALID"
            ),
            hint=(
                "Provide the Private Baseline root "
                "directory."
            ),
        )

    return resolved_root


def _resolve_registry_file(
    root_dir: Path,
) -> Path:
    path = root_dir / BASELINE_REGISTRY_FILENAME

    if path.is_symlink():
        _raise_registry_error(
            "baseline_registry.json must not be a "
            "symbolic link.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "REGISTRY_SYMLINK_FORBIDDEN"
            ),
            hint=(
                "Restore the actual Registry file."
            ),
        )

    if not path.exists():
        _raise_registry_error(
            "baseline_registry.json is missing.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "REGISTRY_MISSING"
            ),
            hint=(
                "Restore a valid retained Registry. "
                "Automatic recovery is prohibited."
            ),
        )

    if not path.is_file():
        _raise_registry_error(
            "baseline_registry.json is not a regular file.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "REGISTRY_TYPE_INVALID"
            ),
            hint=(
                "Restore the actual Registry JSON file."
            ),
        )

    return path


def _normalize_relative_path(
    value: Any,
    *,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        _raise_registry_error(
            f"{field_name} must be a string.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "RELATIVE_PATH_INVALID"
            ),
            hint=(
                "Use a canonical root-relative POSIX path."
            ),
        )

    try:
        value.encode(
            "utf-8",
            errors="strict",
        )
    except UnicodeEncodeError as exc:
        raise PrivateBaselineRegistryError(
            f"{field_name} contains invalid Unicode.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "RELATIVE_PATH_INVALID"
            ),
            hint=(
                "Use valid Unicode scalar values."
            ),
            stage="private_baseline_registry",
        ) from exc

    normalized = unicodedata.normalize(
        "NFC",
        value,
    )

    if (
        not normalized
        or normalized != normalized.strip()
        or "\\" in normalized
        or "\x00" in normalized
        or any(
            unicodedata.category(character) == "Cc"
            or character in {"\u2028", "\u2029"}
            for character in normalized
        )
    ):
        _raise_registry_error(
            f"{field_name} is not a valid canonical "
            "relative path.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "RELATIVE_PATH_INVALID"
            ),
            hint=(
                "Use a normalized root-relative POSIX "
                "path without controls or backslashes."
            ),
        )

    parsed = PurePosixPath(normalized)

    if parsed.is_absolute():
        _raise_registry_error(
            f"{field_name} must not be absolute.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "RELATIVE_PATH_ABSOLUTE"
            ),
            hint=(
                "Use a path relative to the Private "
                "Baseline root."
            ),
        )

    if (
        normalized == "."
        or any(
            part in {".", ".."}
            for part in parsed.parts
        )
        or parsed.as_posix() != normalized
    ):
        _raise_registry_error(
            f"{field_name} contains noncanonical path "
            "components.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "RELATIVE_PATH_NONCANONICAL"
            ),
            hint=(
                "Remove '.', '..', repeated separators, "
                "and trailing separators."
            ),
        )

    return normalized


def _resolve_record_path(
    root_dir: Path,
    relative_path: str,
) -> Path:
    parsed = PurePosixPath(relative_path)
    candidate = root_dir

    for part in parsed.parts:
        candidate = candidate / part

        if candidate.is_symlink():
            _raise_registry_error(
                "Registry record paths must not contain "
                "symbolic links.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RECORD_SYMLINK_FORBIDDEN"
                ),
                hint=(
                    "Restore the real immutable record "
                    "inside the Private Baseline root."
                ),
            )

    try:
        resolved = candidate.resolve(
            strict=True
        )
    except OSError as exc:
        raise PrivateBaselineRegistryError(
            f"Registry record is unavailable: "
            f"{relative_path}: {exc}",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "RECORD_PATH_UNAVAILABLE"
            ),
            hint=(
                "Restore the immutable record at the "
                "registered relative path."
            ),
            stage="private_baseline_registry",
        ) from exc

    try:
        resolved.relative_to(root_dir)
    except ValueError as exc:
        raise PrivateBaselineRegistryError(
            "Registry record resolves outside the Private "
            "Baseline root.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "RECORD_PATH_OUTSIDE_ROOT"
            ),
            hint=(
                "Use a root-relative immutable-record "
                "path."
            ),
            stage="private_baseline_registry",
        ) from exc

    if not resolved.is_file():
        _raise_registry_error(
            f"Registry record is not a regular file: "
            f"{relative_path}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "RECORD_FILE_TYPE_INVALID"
            ),
            hint=(
                "Restore the immutable JSON record."
            ),
        )

    return resolved


def _normalize_non_negative_integer(
    value: Any,
    *,
    field_name: str,
) -> int:
    valid = (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 0
    )

    if not valid:
        _raise_registry_error(
            f"{field_name} must be a non-negative integer.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "SIZE_INVALID"
            ),
            hint=(
                "Restore the physical immutable-record "
                "size."
            ),
        )

    return value


def _normalize_record_entry(
    value: Any,
    *,
    spec: _RecordSpec,
    index: int,
) -> dict[str, Any]:
    field_name = f"{spec.array_name}[{index}]"
    entry = _require_mapping(
        value,
        field_name=field_name,
    )

    _require_exact_fields(
        entry,
        required_fields=_RECORD_ENTRY_FIELDS,
        field_name=field_name,
    )

    return {
        "record_id": _wrap_identifier(
            entry["record_id"],
            kind=spec.id_kind,
            field_name=f"{field_name}.record_id",
        ),
        "relative_path": _normalize_relative_path(
            entry["relative_path"],
            field_name=f"{field_name}.relative_path",
        ),
        "size_bytes": _normalize_non_negative_integer(
            entry["size_bytes"],
            field_name=f"{field_name}.size_bytes",
        ),
        "sha256": _normalize_sha256(
            entry["sha256"],
            field_name=f"{field_name}.sha256",
        ),
    }


def _validate_contract_constants(
    document: Mapping[str, Any],
    *,
    field_name: str,
    schema_name: str,
    semantics: str,
) -> None:
    expected = {
        "schema_name": schema_name,
        "schema_version": (
            PRIVATE_BASELINE_SCHEMA_VERSION
        ),
        "visibility": PRIVATE_BASELINE_VISIBILITY,
        "semantics": semantics,
    }

    for key, expected_value in expected.items():
        if document.get(key) != expected_value:
            _raise_registry_error(
                f"{field_name}.{key} does not match the "
                "frozen v1 contract.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RECORD_SCHEMA_INVALID"
                ),
                hint=(
                    "Place the immutable record in its "
                    "correct Registry array."
                ),
            )


def _validate_revision_document(
    document: dict[str, Any],
    *,
    registry_baseline_id: str,
) -> dict[str, Any]:
    try:
        canonical = validate_baseline_revision(
            document
        )
    except PrivateBaselineContractError as exc:
        raise PrivateBaselineRegistryError(
            "Registered Baseline Revision is invalid.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "REVISION_RECORD_INVALID"
            ),
            hint=(
                "Restore the original immutable Revision "
                "record."
            ),
            stage="private_baseline_registry",
        ) from exc

    if canonical["baseline_id"] != registry_baseline_id:
        _raise_registry_error(
            "Registered Revision belongs to a different "
            "Private Baseline.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "RECORD_BASELINE_ID_MISMATCH"
            ),
            hint=(
                "Restore the Registry and Revision from "
                "the same Private Baseline."
            ),
        )

    return canonical


def _validate_evaluation_document(
    document: dict[str, Any],
    *,
    registry_baseline_id: str,
    revision_ids: set[str],
) -> dict[str, Any]:
    _require_exact_fields(
        document,
        required_fields=_EVALUATION_FIELDS,
        field_name="baseline_evaluation",
    )

    _validate_contract_constants(
        document,
        field_name="baseline_evaluation",
        schema_name=_EVALUATION_SCHEMA_NAME,
        semantics=_EVALUATION_SEMANTICS,
    )

    evaluation_id = _wrap_identifier(
        document["evaluation_id"],
        kind=EVALUATION_ID_KIND,
        field_name="baseline_evaluation.evaluation_id",
    )

    baseline_id = _wrap_identifier(
        document["baseline_id"],
        kind=BASELINE_ID_KIND,
        field_name="baseline_evaluation.baseline_id",
    )

    revision_id = _wrap_identifier(
        document["baseline_revision_id"],
        kind=BASELINE_REVISION_ID_KIND,
        field_name=(
            "baseline_evaluation.baseline_revision_id"
        ),
    )

    generated_at = _normalize_timestamp(
        document["generated_at"],
        field_name="baseline_evaluation.generated_at",
    )

    if baseline_id != registry_baseline_id:
        _raise_registry_error(
            "Registered Evaluation belongs to a different "
            "Private Baseline.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "RECORD_BASELINE_ID_MISMATCH"
            ),
            hint=(
                "Restore the Registry and Evaluation from "
                "the same Private Baseline."
            ),
        )

    if revision_id not in revision_ids:
        _raise_registry_error(
            "Registered Evaluation references an unknown "
            "Baseline Revision.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "RECORD_REFERENCE_MISSING"
            ),
            hint=(
                "Restore the complete Revision lineage "
                "before loading the Evaluation."
            ),
        )

    for field_name in (
        "evaluation_context",
        "target",
        "aggregate_observations",
        "judgment_boundary",
    ):
        _require_mapping(
            document[field_name],
            field_name=(
                f"baseline_evaluation.{field_name}"
            ),
        )

    if not isinstance(
        document["reference_comparisons"],
        list,
    ):
        _raise_registry_error(
            "baseline_evaluation.reference_comparisons "
            "must be a JSON array.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "RECORD_ENVELOPE_INVALID"
            ),
            hint=(
                "Restore the immutable Evaluation JSON."
            ),
        )

    canonical = dict(document)
    canonical["evaluation_id"] = evaluation_id
    canonical["baseline_id"] = baseline_id
    canonical["baseline_revision_id"] = revision_id
    canonical["generated_at"] = generated_at

    return canonical


def _validate_review_document(
    document: dict[str, Any],
    *,
    registry_baseline_id: str,
    revision_ids: set[str],
    evaluations_by_id: Mapping[
        str,
        LoadedRegistryRecord,
    ],
) -> dict[str, Any]:
    _require_exact_fields(
        document,
        required_fields=_REVIEW_FIELDS,
        field_name="baseline_review",
    )

    _validate_contract_constants(
        document,
        field_name="baseline_review",
        schema_name=_REVIEW_SCHEMA_NAME,
        semantics=_REVIEW_SEMANTICS,
    )

    review_id = _wrap_identifier(
        document["review_record_id"],
        kind=REVIEW_RECORD_ID_KIND,
        field_name="baseline_review.review_record_id",
    )

    baseline_id = _wrap_identifier(
        document["baseline_id"],
        kind=BASELINE_ID_KIND,
        field_name="baseline_review.baseline_id",
    )

    revision_id = _wrap_identifier(
        document["baseline_revision_id"],
        kind=BASELINE_REVISION_ID_KIND,
        field_name=(
            "baseline_review.baseline_revision_id"
        ),
    )

    evaluation_id = _wrap_identifier(
        document["evaluation_id"],
        kind=EVALUATION_ID_KIND,
        field_name="baseline_review.evaluation_id",
    )

    created_at = _normalize_timestamp(
        document["created_at"],
        field_name="baseline_review.created_at",
    )

    if baseline_id != registry_baseline_id:
        _raise_registry_error(
            "Registered Review belongs to a different "
            "Private Baseline.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "RECORD_BASELINE_ID_MISMATCH"
            ),
            hint=(
                "Restore the Registry and Review from the "
                "same Private Baseline."
            ),
        )

    if revision_id not in revision_ids:
        _raise_registry_error(
            "Registered Review references an unknown "
            "Baseline Revision.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "RECORD_REFERENCE_MISSING"
            ),
            hint=(
                "Restore the complete Revision lineage "
                "before loading the Review."
            ),
        )

    if evaluation_id not in evaluations_by_id:
        _raise_registry_error(
            "Registered Review references an unknown "
            "Evaluation.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "RECORD_REFERENCE_MISSING"
            ),
            hint=(
                "Restore the immutable Evaluation before "
                "loading its Review history."
            ),
        )

    evaluation_revision_id = (
        evaluations_by_id[
            evaluation_id
        ].document["baseline_revision_id"]
    )

    if revision_id != evaluation_revision_id:
        _raise_registry_error(
            "Registered Review baseline_revision_id does "
            "not match its referenced Evaluation.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "REVIEW_EVALUATION_REVISION_MISMATCH"
            ),
            hint=(
                "Restore the Review record associated "
                "with the same immutable Evaluation and "
                "Baseline Revision."
            ),
        )

    _require_mapping(
        document["subject"],
        field_name="baseline_review.subject",
    )

    canonical = dict(document)
    canonical["review_record_id"] = review_id
    canonical["baseline_id"] = baseline_id
    canonical["baseline_revision_id"] = revision_id
    canonical["evaluation_id"] = evaluation_id
    canonical["created_at"] = created_at

    return canonical


def _load_record_array(
    value: Any,
    *,
    spec: _RecordSpec,
    root_dir: Path,
    registry_baseline_id: str,
    revision_ids: set[str],
    evaluations_by_id: Mapping[
        str,
        LoadedRegistryRecord,
    ],
    observed_record_ids: set[str],
    observed_relative_paths: set[str],
) -> dict[str, LoadedRegistryRecord]:
    if not isinstance(value, list):
        _raise_registry_error(
            f"{spec.array_name} must be a JSON array.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "RECORD_ARRAY_INVALID"
            ),
            hint=(
                "Restore the Registry record arrays."
            ),
        )

    loaded: dict[str, LoadedRegistryRecord] = {}

    for index, raw_entry in enumerate(value):
        entry = _normalize_record_entry(
            raw_entry,
            spec=spec,
            index=index,
        )

        record_id = entry["record_id"]
        relative_path = entry["relative_path"]

        if record_id in observed_record_ids:
            _raise_registry_error(
                f"Duplicate Registry record_id: "
                f"{record_id}.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RECORD_ID_DUPLICATE"
                ),
                hint=(
                    "Each immutable record must appear "
                    "exactly once."
                ),
            )

        if relative_path in observed_relative_paths:
            _raise_registry_error(
                f"Duplicate Registry relative_path: "
                f"{relative_path}.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RECORD_PATH_DUPLICATE"
                ),
                hint=(
                    "One immutable file must not be "
                    "registered as multiple records."
                ),
            )

        observed_record_ids.add(record_id)
        observed_relative_paths.add(relative_path)

        record_path = _resolve_record_path(
            root_dir,
            relative_path,
        )

        payload = _read_verified_record(
            record_path,
            document_name=relative_path,
            expected_size=entry["size_bytes"],
            expected_sha256=entry["sha256"],
        )

        document = _load_json_mapping_bytes(
            payload,
            document_name=relative_path,
        )

        if spec.array_name == "revisions":
            canonical = _validate_revision_document(
                document,
                registry_baseline_id=(
                    registry_baseline_id
                ),
            )
        elif spec.array_name == "evaluations":
            canonical = _validate_evaluation_document(
                document,
                registry_baseline_id=(
                    registry_baseline_id
                ),
                revision_ids=revision_ids,
            )
        elif spec.array_name == "reviews":
            canonical = _validate_review_document(
                document,
                registry_baseline_id=(
                    registry_baseline_id
                ),
                revision_ids=revision_ids,
                evaluations_by_id=(
                    evaluations_by_id
                ),
            )
        else:
            raise AssertionError(
                f"Unsupported Registry array: "
                f"{spec.array_name}"
            )

        internal_record_id = canonical.get(
            spec.id_field
        )

        if internal_record_id != record_id:
            _raise_registry_error(
                f"{relative_path} internal "
                f"{spec.id_field} does not match Registry "
                f"record_id.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "RECORD_IDENTIFIER_MISMATCH"
                ),
                hint=(
                    "Restore the Registry entry and "
                    "immutable record from the same "
                    "installation."
                ),
            )

        loaded[record_id] = LoadedRegistryRecord(
            registry_array=spec.array_name,
            record_id=record_id,
            relative_path=relative_path,
            path=record_path,
            size_bytes=entry["size_bytes"],
            sha256=entry["sha256"],
            document=canonical,
        )

    return loaded


def _validate_revision_lineage(
    revisions_by_id: Mapping[
        str,
        LoadedRegistryRecord,
    ],
) -> None:
    """Validate one rooted, acyclic Revision lineage.

    Revision branching is permitted in v1. Unlike human-review
    supersession, the Revision contract does not require one linear
    chain.
    """

    parent_by_revision_id: dict[
        str,
        str | None,
    ] = {}

    root_revision_ids: list[str] = []

    for revision_id, record in (
        revisions_by_id.items()
    ):
        parent_revision_id = record.document[
            "parent_revision_id"
        ]

        if parent_revision_id is None:
            root_revision_ids.append(revision_id)
        elif parent_revision_id not in revisions_by_id:
            _raise_registry_error(
                "Registered Revision references an "
                "unknown parent Revision: "
                f"{revision_id} -> "
                f"{parent_revision_id}.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "REVISION_PARENT_MISSING"
                ),
                hint=(
                    "Restore the complete immutable "
                    "Revision lineage."
                ),
            )

        parent_by_revision_id[
            revision_id
        ] = parent_revision_id

    if len(root_revision_ids) != 1:
        _raise_registry_error(
            "A Private Baseline Revision lineage must "
            "contain exactly one root Revision with "
            "parent_revision_id=null.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "REVISION_ROOT_COUNT_INVALID"
            ),
            hint=(
                "Restore the single initial Revision and "
                "the parent link of every later Revision."
            ),
        )

    completed: set[str] = set()

    for start_revision_id in sorted(
        parent_by_revision_id
    ):
        if start_revision_id in completed:
            continue

        chain: list[str] = []
        position_by_revision_id: dict[
            str,
            int,
        ] = {}

        current_revision_id: str | None = (
            start_revision_id
        )

        while (
            current_revision_id is not None
            and current_revision_id not in completed
        ):
            if (
                current_revision_id
                in position_by_revision_id
            ):
                cycle_start = (
                    position_by_revision_id[
                        current_revision_id
                    ]
                )
                cycle = [
                    *chain[cycle_start:],
                    current_revision_id,
                ]

                _raise_registry_error(
                    "Revision parent lineage contains a "
                    "cycle: "
                    f"{' -> '.join(cycle)}.",
                    code=(
                        "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                        "REVISION_LINEAGE_CYCLE"
                    ),
                    hint=(
                        "Restore the immutable Revision "
                        "parent links without rewriting "
                        "existing records."
                    ),
                )

            position_by_revision_id[
                current_revision_id
            ] = len(chain)

            chain.append(current_revision_id)

            current_revision_id = (
                parent_by_revision_id[
                    current_revision_id
                ]
            )

        completed.update(chain)


def _normalize_bundle_locator(
    value: Any,
    *,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        _raise_registry_error(
            f"{field_name} must be a local path string.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "BUNDLE_LOCATION_INVALID"
            ),
            hint=(
                "Provide the current local Bundle "
                "directory as an operational locator."
            ),
        )

    try:
        value.encode(
            "utf-8",
            errors="strict",
        )
    except UnicodeEncodeError as exc:
        raise PrivateBaselineRegistryError(
            f"{field_name} contains invalid Unicode.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "BUNDLE_LOCATION_INVALID"
            ),
            hint=(
                "Use valid Unicode scalar values."
            ),
            stage="private_baseline_registry",
        ) from exc

    normalized = unicodedata.normalize(
        "NFC",
        value,
    )

    if not normalized or "\x00" in normalized:
        _raise_registry_error(
            f"{field_name} must be a non-empty local path "
            "without NUL characters.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "BUNDLE_LOCATION_INVALID"
            ),
            hint=(
                "Provide the current local Bundle "
                "directory."
            ),
        )

    return normalized


def _normalize_bundle_locations(
    value: Any,
) -> dict[str, str]:
    locations = _require_mapping(
        value,
        field_name="bundle_locations",
    )

    normalized: dict[str, str] = {}

    for raw_bundle_id, raw_path in locations.items():
        bundle_id = _normalize_report_bundle_id(
            raw_bundle_id,
            field_name="bundle_locations.key",
        )

        if bundle_id in normalized:
            _raise_registry_error(
                "bundle_locations contains a duplicate "
                "Bundle identifier.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "BUNDLE_LOCATION_DUPLICATE"
                ),
                hint=(
                    "Keep one mutable locator per verified "
                    "Bundle identifier."
                ),
            )

        normalized[bundle_id] = (
            _normalize_bundle_locator(
                raw_path,
                field_name=(
                    f"bundle_locations.{bundle_id}"
                ),
            )
        )

    return {
        bundle_id: normalized[bundle_id]
        for bundle_id in sorted(normalized)
    }


def load_private_baseline_registry(
    root_dir: str | Path,
) -> LoadedPrivateBaselineRegistry:
    """Load Registry state and verify every immutable record."""

    resolved_root = _resolve_registry_root(
        root_dir
    )
    registry_path = _resolve_registry_file(
        resolved_root
    )

    registry_payload = _read_file_bytes(
        registry_path,
        document_name=BASELINE_REGISTRY_FILENAME,
    )

    raw_registry = _load_json_mapping_bytes(
        registry_payload,
        document_name=BASELINE_REGISTRY_FILENAME,
    )

    registry = _require_mapping(
        raw_registry,
        field_name="baseline_registry",
    )

    _require_exact_fields(
        registry,
        required_fields=_REGISTRY_FIELDS,
        field_name="baseline_registry",
    )

    expected_constants = {
        "schema_name": BASELINE_REGISTRY_SCHEMA_NAME,
        "schema_version": (
            PRIVATE_BASELINE_SCHEMA_VERSION
        ),
        "visibility": PRIVATE_BASELINE_VISIBILITY,
        "semantics": BASELINE_REGISTRY_SEMANTICS,
    }

    for field_name, expected_value in (
        expected_constants.items()
    ):
        if registry[field_name] != expected_value:
            _raise_registry_error(
                f"baseline_registry.{field_name} does not "
                "match the frozen v1 contract.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                    "CONTRACT_CONSTANT_INVALID"
                ),
                hint=(
                    f"Use the required value: "
                    f"{expected_value}."
                ),
            )

    baseline_id = _wrap_identifier(
        registry["baseline_id"],
        kind=BASELINE_ID_KIND,
        field_name="baseline_registry.baseline_id",
    )

    display_name = _wrap_single_line(
        registry["display_name"],
        field_name="baseline_registry.display_name",
        max_length=DISPLAY_NAME_MAX_LENGTH,
    )

    created_at = _normalize_timestamp(
        registry["created_at"],
        field_name="baseline_registry.created_at",
    )

    current_revision_id = _wrap_identifier(
        registry["current_revision_id"],
        kind=BASELINE_REVISION_ID_KIND,
        field_name=(
            "baseline_registry.current_revision_id"
        ),
    )

    observed_record_ids: set[str] = set()
    observed_relative_paths: set[str] = set()

    revisions_by_id = _load_record_array(
        registry["revisions"],
        spec=_RECORD_SPECS["revisions"],
        root_dir=resolved_root,
        registry_baseline_id=baseline_id,
        revision_ids=set(),
        evaluations_by_id={},
        observed_record_ids=observed_record_ids,
        observed_relative_paths=(
            observed_relative_paths
        ),
    )

    if not revisions_by_id:
        _raise_registry_error(
            "A Private Baseline Registry must contain at "
            "least one immutable Revision.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "REVISION_REQUIRED"
            ),
            hint=(
                "Restore the initial Registry and first "
                "Revision together."
            ),
        )

    revision_ids = set(revisions_by_id)

    _validate_revision_lineage(
        revisions_by_id
    )

    if current_revision_id not in revision_ids:
        _raise_registry_error(
            "current_revision_id does not identify a "
            "registered Revision.",
            code=(
                "VELUNE_PRIVATE_BASELINE_REGISTRY_"
                "CURRENT_REVISION_MISSING"
            ),
            hint=(
                "Restore the Registry without inferring a "
                "replacement current Revision."
            ),
        )

    evaluations_by_id = _load_record_array(
        registry["evaluations"],
        spec=_RECORD_SPECS["evaluations"],
        root_dir=resolved_root,
        registry_baseline_id=baseline_id,
        revision_ids=revision_ids,
        evaluations_by_id={},
        observed_record_ids=observed_record_ids,
        observed_relative_paths=(
            observed_relative_paths
        ),
    )

    reviews_by_id = _load_record_array(
        registry["reviews"],
        spec=_RECORD_SPECS["reviews"],
        root_dir=resolved_root,
        registry_baseline_id=baseline_id,
        revision_ids=revision_ids,
        evaluations_by_id=evaluations_by_id,
        observed_record_ids=observed_record_ids,
        observed_relative_paths=(
            observed_relative_paths
        ),
    )

    bundle_locations = _normalize_bundle_locations(
        registry["bundle_locations"]
    )

    canonical_registry = {
        "schema_name": BASELINE_REGISTRY_SCHEMA_NAME,
        "schema_version": (
            PRIVATE_BASELINE_SCHEMA_VERSION
        ),
        "visibility": PRIVATE_BASELINE_VISIBILITY,
        "semantics": BASELINE_REGISTRY_SEMANTICS,
        "baseline_id": baseline_id,
        "display_name": display_name,
        "created_at": created_at,
        "current_revision_id": current_revision_id,
        "revisions": [
            record.as_registry_entry()
            for record in revisions_by_id.values()
        ],
        "evaluations": [
            record.as_registry_entry()
            for record in evaluations_by_id.values()
        ],
        "reviews": [
            record.as_registry_entry()
            for record in reviews_by_id.values()
        ],
        "bundle_locations": bundle_locations,
    }

    return LoadedPrivateBaselineRegistry(
        root_dir=resolved_root,
        registry_path=registry_path,
        registry=canonical_registry,
        revisions_by_id=revisions_by_id,
        evaluations_by_id=evaluations_by_id,
        reviews_by_id=reviews_by_id,
    )
