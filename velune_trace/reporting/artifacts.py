"""Artifact metadata helpers for Velune Evidence Report Bundles."""

import hashlib
from pathlib import Path


DEFAULT_HASH_ALGORITHM = "sha256"
SUPPORTED_HASH_ALGORITHMS = frozenset({
    DEFAULT_HASH_ALGORITHM,
})
READ_CHUNK_SIZE = 1024 * 1024


def _require_non_empty_string(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")

    return value.strip()


def _require_hash_algorithm(value: str) -> str:
    algorithm = _require_non_empty_string(
        value,
        "hash_algorithm",
    ).lower()

    if algorithm not in SUPPORTED_HASH_ALGORITHMS:
        supported = ", ".join(sorted(SUPPORTED_HASH_ALGORITHMS))
        raise ValueError(
            f"unsupported hash_algorithm: {algorithm}; "
            f"supported algorithms: {supported}"
        )

    return algorithm


def _hash_file(
    path: Path,
    algorithm: str,
) -> tuple[str, int]:
    try:
        digest = hashlib.new(algorithm)
    except ValueError as exc:
        raise ValueError(
            f"hash algorithm is unavailable: {algorithm}"
        ) from exc

    size_bytes = 0

    with path.open("rb") as file_handle:
        while True:
            chunk = file_handle.read(READ_CHUNK_SIZE)
            if not chunk:
                break

            digest.update(chunk)
            size_bytes += len(chunk)

    return digest.hexdigest(), size_bytes


def build_artifact_record(
    *,
    bundle_dir: str | Path,
    artifact_path: str | Path,
    role: str,
    media_type: str,
    source_of_truth: bool,
    hash_algorithm: str = DEFAULT_HASH_ALGORITHM,
) -> dict[str, object]:
    """Build metadata for one regular file inside a report bundle.

    The artifact path stored in the manifest is relative to the bundle
    directory. Symbolic links and files outside the bundle are rejected.
    """

    role_value = _require_non_empty_string(role, "role")
    media_type_value = _require_non_empty_string(
        media_type,
        "media_type",
    )
    hash_algorithm_value = _require_hash_algorithm(
        hash_algorithm,
    )

    if not isinstance(source_of_truth, bool):
        raise TypeError("source_of_truth must be a bool")

    raw_bundle_dir = Path(bundle_dir)
    raw_artifact_path = Path(artifact_path)

    if raw_bundle_dir.is_symlink():
        raise ValueError(
            "bundle_dir must not be a symbolic link"
        )

    if raw_artifact_path.is_symlink():
        raise ValueError(
            "artifact_path must not be a symbolic link"
        )

    try:
        resolved_bundle_dir = raw_bundle_dir.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(
            f"bundle_dir does not exist: {raw_bundle_dir}"
        ) from exc

    if not resolved_bundle_dir.is_dir():
        raise ValueError(
            f"bundle_dir must be a directory: {raw_bundle_dir}"
        )

    try:
        resolved_artifact_path = raw_artifact_path.resolve(
            strict=True
        )
    except FileNotFoundError as exc:
        raise ValueError(
            f"artifact_path does not exist: {raw_artifact_path}"
        ) from exc

    if not resolved_artifact_path.is_file():
        raise ValueError(
            f"artifact_path must be a regular file: "
            f"{raw_artifact_path}"
        )

    try:
        relative_path = resolved_artifact_path.relative_to(
            resolved_bundle_dir
        )
    except ValueError as exc:
        raise ValueError(
            "artifact_path must be contained within bundle_dir"
        ) from exc

    hash_value, size_bytes = _hash_file(
        resolved_artifact_path,
        hash_algorithm_value,
    )

    return {
        "path": relative_path.as_posix(),
        "role": role_value,
        "media_type": media_type_value,
        "size_bytes": size_bytes,
        "hash": {
            "algorithm": hash_algorithm_value,
            "value": hash_value,
        },
        "source_of_truth": source_of_truth,
    }
