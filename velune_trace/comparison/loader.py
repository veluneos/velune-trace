"""Load and verify Core Bundles for private local comparison."""

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from velune_trace.reporting.errors import EvidenceBundleError


MANIFEST_FILENAME = "report_manifest.json"
TOPIC_PROFILE_FILENAME = "topic_profile.json"
EVIDENCE_WINDOWS_FILENAME = "evidence_windows.json"

REQUIRED_INPUT_FILENAMES = (
    MANIFEST_FILENAME,
    TOPIC_PROFILE_FILENAME,
    EVIDENCE_WINDOWS_FILENAME,
)

REQUIRED_DECLARED_ARTIFACTS = (
    TOPIC_PROFILE_FILENAME,
    EVIDENCE_WINDOWS_FILENAME,
)

SUPPORTED_HASH_ALGORITHMS = frozenset({
    "sha256",
})

READ_CHUNK_SIZE = 1024 * 1024


class BundleComparisonLoadError(EvidenceBundleError):
    """Raised when a Core Bundle cannot be trusted as comparison input."""

    default_code = "VELUNE_COMPARISON_BUNDLE_LOAD_FAILED"


@dataclass(frozen=True)
class LoadedComparisonBundle:
    """Verified machine-readable input for Bundle comparison."""

    bundle_dir: Path
    manifest: dict[str, Any]
    topic_profile: dict[str, Any]
    evidence_windows: dict[str, Any]
    artifacts_by_path: dict[str, dict[str, Any]]


def _raise_load_error(
    message: str,
    *,
    code: str,
    hint: str,
) -> None:
    raise BundleComparisonLoadError(
        message,
        code=code,
        hint=hint,
        stage="comparison_bundle_load",
    )


def _resolve_bundle_directory(
    bundle_dir: str | Path,
) -> Path:
    try:
        raw_bundle_dir = Path(bundle_dir)
    except TypeError as exc:
        raise BundleComparisonLoadError(
            "Bundle path must be a filesystem path",
            code=(
                "VELUNE_COMPARISON_"
                "BUNDLE_PATH_TYPE_INVALID"
            ),
            hint=(
                "Provide an existing Core Report Bundle "
                "directory."
            ),
            stage="comparison_bundle_load",
        ) from exc

    if raw_bundle_dir.is_symlink():
        _raise_load_error(
            "Bundle directory must not be a symbolic link",
            code=(
                "VELUNE_COMPARISON_"
                "BUNDLE_DIRECTORY_SYMLINK_FORBIDDEN"
            ),
            hint=(
                "Use the real Core Report Bundle directory "
                "rather than a symbolic link."
            ),
        )

    try:
        resolved_bundle_dir = raw_bundle_dir.resolve(
            strict=True
        )
    except OSError as exc:
        raise BundleComparisonLoadError(
            f"Unable to resolve Bundle directory: {exc}",
            code=(
                "VELUNE_COMPARISON_"
                "BUNDLE_DIRECTORY_UNAVAILABLE"
            ),
            hint=(
                "Confirm that the Core Report Bundle "
                "directory exists and is accessible."
            ),
            stage="comparison_bundle_load",
        ) from exc

    if not resolved_bundle_dir.is_dir():
        _raise_load_error(
            "Bundle path is not a directory",
            code=(
                "VELUNE_COMPARISON_"
                "BUNDLE_DIRECTORY_INVALID"
            ),
            hint="Provide a Core Report Bundle directory.",
        )

    return resolved_bundle_dir


def _resolve_required_file(
    bundle_dir: Path,
    file_name: str,
) -> Path:
    path = bundle_dir / file_name

    if path.is_symlink():
        _raise_load_error(
            f"Required comparison input must not be a "
            f"symbolic link: {file_name}",
            code=(
                "VELUNE_COMPARISON_"
                "REQUIRED_FILE_SYMLINK_FORBIDDEN"
            ),
            hint=(
                "Replace the symbolic link with the actual "
                "Bundle artifact."
            ),
        )

    if not path.exists():
        _raise_load_error(
            f"Required comparison input is missing: "
            f"{file_name}",
            code=(
                "VELUNE_COMPARISON_"
                "REQUIRED_FILE_MISSING"
            ),
            hint=(
                "Generate or restore the complete Core "
                "Report Bundle before comparison."
            ),
        )

    if not path.is_file():
        _raise_load_error(
            f"Required comparison input is not a regular "
            f"file: {file_name}",
            code=(
                "VELUNE_COMPARISON_"
                "REQUIRED_FILE_INVALID"
            ),
            hint=(
                "Remove the conflicting filesystem entry "
                "and restore the Bundle artifact."
            ),
        )

    return path


def _reject_json_constant(value: str) -> None:
    raise ValueError(
        f"non-finite JSON number is not allowed: {value}"
    )


def _validate_json_value(
    value: Any,
    *,
    path: str,
) -> None:
    if (
        value is None
        or isinstance(value, (bool, int, str))
    ):
        return

    if isinstance(value, float):
        if not math.isfinite(value):
            _raise_load_error(
                f"{path} contains a non-finite number",
                code=(
                    "VELUNE_COMPARISON_"
                    "JSON_NON_FINITE"
                ),
                hint=(
                    "Replace NaN or Infinity with a finite "
                    "number or null."
                ),
            )
        return

    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                _raise_load_error(
                    f"{path} contains a non-string object key",
                    code=(
                        "VELUNE_COMPARISON_"
                        "JSON_STRUCTURE_INVALID"
                    ),
                    hint=(
                        "Use string keys in all JSON objects."
                    ),
                )

            _validate_json_value(
                item,
                path=f"{path}.{key}",
            )
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(
                item,
                path=f"{path}[{index}]",
            )
        return

    _raise_load_error(
        f"{path} contains unsupported JSON value type: "
        f"{type(value).__name__}",
        code=(
            "VELUNE_COMPARISON_"
            "JSON_STRUCTURE_INVALID"
        ),
        hint=(
            "Use only JSON objects, arrays, strings, finite "
            "numbers, booleans, and null."
        ),
    )


def _load_json_mapping(
    path: Path,
    *,
    document_name: str,
) -> dict[str, Any]:
    try:
        rendered = path.read_text(
            encoding="utf-8"
        )
    except (OSError, UnicodeError) as exc:
        raise BundleComparisonLoadError(
            f"Unable to read {document_name}: {exc}",
            code=(
                "VELUNE_COMPARISON_"
                "JSON_READ_FAILED"
            ),
            hint=(
                "Confirm that the Bundle artifact is valid "
                "UTF-8 and readable."
            ),
            stage="comparison_bundle_load",
        ) from exc

    try:
        value = json.loads(
            rendered,
            parse_constant=_reject_json_constant,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise BundleComparisonLoadError(
            f"Invalid JSON in {document_name}: {exc}",
            code=(
                "VELUNE_COMPARISON_"
                "JSON_INVALID"
            ),
            hint=(
                "Regenerate the Core Report Bundle from a "
                "trusted Velune Trace version."
            ),
            stage="comparison_bundle_load",
        ) from exc

    _validate_json_value(
        value,
        path=document_name,
    )

    if not isinstance(value, Mapping):
        _raise_load_error(
            f"{document_name} must contain a top-level "
            "JSON object",
            code=(
                "VELUNE_COMPARISON_"
                "JSON_TOP_LEVEL_INVALID"
            ),
            hint=(
                "Regenerate the Core Report Bundle with the "
                "expected machine-readable contract."
            ),
        )

    return dict(value)


def _require_non_empty_string(
    value: Any,
    *,
    field_name: str,
) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
    ):
        _raise_load_error(
            f"{field_name} must be a non-empty string "
            "without surrounding whitespace",
            code=(
                "VELUNE_COMPARISON_"
                "MANIFEST_ARTIFACT_INVALID"
            ),
            hint=(
                "Regenerate report_manifest.json from the "
                "Core Bundle finalizer."
            ),
        )

    return value


def _require_non_negative_integer(
    value: Any,
    *,
    field_name: str,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
    ):
        _raise_load_error(
            f"{field_name} must be a non-negative integer",
            code=(
                "VELUNE_COMPARISON_"
                "MANIFEST_ARTIFACT_INVALID"
            ),
            hint=(
                "Regenerate report_manifest.json from the "
                "Core Bundle finalizer."
            ),
        )

    return value


def _validate_hash_record(
    value: Any,
    *,
    artifact_path: str,
) -> tuple[str, str]:
    if not isinstance(value, Mapping):
        _raise_load_error(
            f"Artifact hash must be an object: "
            f"{artifact_path}",
            code=(
                "VELUNE_COMPARISON_"
                "ARTIFACT_HASH_CONTRACT_INVALID"
            ),
            hint=(
                "Regenerate the Bundle manifest with a "
                "supported SHA-256 artifact record."
            ),
        )

    unknown_fields = sorted(
        set(value).difference({
            "algorithm",
            "value",
        })
    )
    missing_fields = sorted(
        {
            "algorithm",
            "value",
        }.difference(value)
    )

    if missing_fields or unknown_fields:
        _raise_load_error(
            f"Invalid artifact hash contract for "
            f"{artifact_path}",
            code=(
                "VELUNE_COMPARISON_"
                "ARTIFACT_HASH_CONTRACT_INVALID"
            ),
            hint=(
                "The hash object must contain only algorithm "
                "and value."
            ),
        )

    algorithm = _require_non_empty_string(
        value["algorithm"],
        field_name=(
            f"artifact[{artifact_path}].hash.algorithm"
        ),
    ).lower()

    if algorithm not in SUPPORTED_HASH_ALGORITHMS:
        _raise_load_error(
            f"Unsupported artifact hash algorithm for "
            f"{artifact_path}: {algorithm}",
            code=(
                "VELUNE_COMPARISON_"
                "ARTIFACT_HASH_ALGORITHM_UNSUPPORTED"
            ),
            hint="Use a Core Bundle with SHA-256 hashes.",
        )

    hash_value = _require_non_empty_string(
        value["value"],
        field_name=(
            f"artifact[{artifact_path}].hash.value"
        ),
    )

    if (
        len(hash_value) != 64
        or hash_value.lower() != hash_value
        or any(
            character not in "0123456789abcdef"
            for character in hash_value
        )
    ):
        _raise_load_error(
            f"Invalid SHA-256 value for {artifact_path}",
            code=(
                "VELUNE_COMPARISON_"
                "ARTIFACT_HASH_VALUE_INVALID"
            ),
            hint=(
                "Regenerate report_manifest.json from the "
                "trusted Bundle artifacts."
            ),
        )

    return algorithm, hash_value


def _build_artifact_index(
    manifest: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    artifacts = manifest.get("artifacts")

    if not isinstance(artifacts, list):
        _raise_load_error(
            "report_manifest.json artifacts must be a list",
            code=(
                "VELUNE_COMPARISON_"
                "MANIFEST_ARTIFACTS_INVALID"
            ),
            hint=(
                "Regenerate the complete Core Report Bundle."
            ),
        )

    artifacts_by_path: dict[str, dict[str, Any]] = {}

    for index, raw_artifact in enumerate(artifacts):
        if not isinstance(raw_artifact, Mapping):
            _raise_load_error(
                f"manifest.artifacts[{index}] must be an "
                "object",
                code=(
                    "VELUNE_COMPARISON_"
                    "MANIFEST_ARTIFACT_INVALID"
                ),
                hint=(
                    "Regenerate report_manifest.json from "
                    "the Core Bundle finalizer."
                ),
            )

        artifact = dict(raw_artifact)

        artifact_path = _require_non_empty_string(
            artifact.get("path"),
            field_name=(
                f"manifest.artifacts[{index}].path"
            ),
        )

        if artifact_path in artifacts_by_path:
            _raise_load_error(
                f"Duplicate manifest artifact path: "
                f"{artifact_path}",
                code=(
                    "VELUNE_COMPARISON_"
                    "MANIFEST_ARTIFACT_DUPLICATE"
                ),
                hint=(
                    "Regenerate the Bundle manifest with one "
                    "record per artifact."
                ),
            )

        _require_non_negative_integer(
            artifact.get("size_bytes"),
            field_name=(
                f"manifest.artifacts[{index}].size_bytes"
            ),
        )

        _validate_hash_record(
            artifact.get("hash"),
            artifact_path=artifact_path,
        )

        artifacts_by_path[artifact_path] = artifact

    for required_path in REQUIRED_DECLARED_ARTIFACTS:
        if required_path not in artifacts_by_path:
            _raise_load_error(
                f"Required comparison artifact is not "
                f"declared in the manifest: {required_path}",
                code=(
                    "VELUNE_COMPARISON_"
                    "ARTIFACT_UNDECLARED"
                ),
                hint=(
                    "Regenerate the complete Core Report "
                    "Bundle before comparison."
                ),
            )

    return artifacts_by_path


def _hash_file(
    path: Path,
    algorithm: str,
) -> tuple[str, int]:
    try:
        digest = hashlib.new(algorithm)
    except ValueError as exc:
        raise BundleComparisonLoadError(
            f"Hash algorithm is unavailable: {algorithm}",
            code=(
                "VELUNE_COMPARISON_"
                "ARTIFACT_HASH_UNAVAILABLE"
            ),
            hint=(
                "Use a Python runtime with SHA-256 support."
            ),
            stage="comparison_bundle_load",
        ) from exc

    size_bytes = 0

    try:
        with path.open("rb") as file_handle:
            while True:
                chunk = file_handle.read(
                    READ_CHUNK_SIZE
                )
                if not chunk:
                    break

                digest.update(chunk)
                size_bytes += len(chunk)
    except OSError as exc:
        raise BundleComparisonLoadError(
            f"Unable to hash Bundle artifact "
            f"{path.name}: {exc}",
            code=(
                "VELUNE_COMPARISON_"
                "ARTIFACT_HASH_READ_FAILED"
            ),
            hint=(
                "Confirm that the Bundle artifact is readable."
            ),
            stage="comparison_bundle_load",
        ) from exc

    return digest.hexdigest(), size_bytes


def _verify_declared_artifact(
    *,
    path: Path,
    artifact_record: Mapping[str, Any],
) -> None:
    algorithm, expected_hash = _validate_hash_record(
        artifact_record.get("hash"),
        artifact_path=path.name,
    )
    expected_size = _require_non_negative_integer(
        artifact_record.get("size_bytes"),
        field_name=(
            f"artifact[{path.name}].size_bytes"
        ),
    )

    actual_hash, actual_size = _hash_file(
        path,
        algorithm,
    )

    if actual_size != expected_size:
        _raise_load_error(
            f"Artifact size mismatch for {path.name}: "
            f"manifest={expected_size}, actual={actual_size}",
            code=(
                "VELUNE_COMPARISON_"
                "ARTIFACT_SIZE_MISMATCH"
            ),
            hint=(
                "Do not compare a modified or incomplete "
                "Core Report Bundle."
            ),
        )

    if actual_hash != expected_hash:
        _raise_load_error(
            f"Artifact hash mismatch for {path.name}",
            code=(
                "VELUNE_COMPARISON_"
                "ARTIFACT_HASH_MISMATCH"
            ),
            hint=(
                "Do not compare a modified or untrusted "
                "Core Report Bundle."
            ),
        )


def _validate_topic_profile(
    topic_profile: Mapping[str, Any],
) -> None:
    for topic, profile in topic_profile.items():
        if (
            not isinstance(topic, str)
            or not topic
            or topic != topic.strip()
        ):
            _raise_load_error(
                "topic_profile.json contains an invalid "
                "topic name",
                code=(
                    "VELUNE_COMPARISON_"
                    "TOPIC_PROFILE_STRUCTURE_INVALID"
                ),
                hint=(
                    "Regenerate the Core Report Bundle."
                ),
            )

        if not isinstance(profile, Mapping):
            _raise_load_error(
                f"Topic profile must be an object: {topic}",
                code=(
                    "VELUNE_COMPARISON_"
                    "TOPIC_PROFILE_STRUCTURE_INVALID"
                ),
                hint=(
                    "Regenerate the Core Report Bundle."
                ),
            )


def _validate_evidence_windows(
    evidence_windows: Mapping[str, Any],
) -> None:
    for topic, windows in evidence_windows.items():
        if (
            not isinstance(topic, str)
            or not topic
            or topic != topic.strip()
        ):
            _raise_load_error(
                "evidence_windows.json contains an invalid "
                "topic name",
                code=(
                    "VELUNE_COMPARISON_"
                    "EVIDENCE_WINDOWS_STRUCTURE_INVALID"
                ),
                hint=(
                    "Regenerate the Core Report Bundle."
                ),
            )

        if not isinstance(windows, list):
            _raise_load_error(
                f"Evidence windows must be a list: {topic}",
                code=(
                    "VELUNE_COMPARISON_"
                    "EVIDENCE_WINDOWS_STRUCTURE_INVALID"
                ),
                hint=(
                    "Regenerate the Core Report Bundle."
                ),
            )

        for index, window in enumerate(windows):
            if not isinstance(window, Mapping):
                _raise_load_error(
                    f"Evidence window must be an object: "
                    f"{topic}[{index}]",
                    code=(
                        "VELUNE_COMPARISON_"
                        "EVIDENCE_WINDOWS_STRUCTURE_INVALID"
                    ),
                    hint=(
                        "Regenerate the Core Report Bundle."
                    ),
                )


def load_comparison_bundle(
    bundle_dir: str | Path,
) -> LoadedComparisonBundle:
    """Load and verify one Core Bundle for local comparison."""

    resolved_bundle_dir = _resolve_bundle_directory(
        bundle_dir
    )

    required_paths = {
        file_name: _resolve_required_file(
            resolved_bundle_dir,
            file_name,
        )
        for file_name in REQUIRED_INPUT_FILENAMES
    }

    manifest = _load_json_mapping(
        required_paths[MANIFEST_FILENAME],
        document_name=MANIFEST_FILENAME,
    )

    artifacts_by_path = _build_artifact_index(
        manifest
    )

    for artifact_name in REQUIRED_DECLARED_ARTIFACTS:
        _verify_declared_artifact(
            path=required_paths[artifact_name],
            artifact_record=artifacts_by_path[
                artifact_name
            ],
        )

    topic_profile = _load_json_mapping(
        required_paths[TOPIC_PROFILE_FILENAME],
        document_name=TOPIC_PROFILE_FILENAME,
    )
    evidence_windows = _load_json_mapping(
        required_paths[EVIDENCE_WINDOWS_FILENAME],
        document_name=EVIDENCE_WINDOWS_FILENAME,
    )

    _validate_topic_profile(topic_profile)
    _validate_evidence_windows(evidence_windows)

    return LoadedComparisonBundle(
        bundle_dir=resolved_bundle_dir,
        manifest=manifest,
        topic_profile=topic_profile,
        evidence_windows=evidence_windows,
        artifacts_by_path=artifacts_by_path,
    )
