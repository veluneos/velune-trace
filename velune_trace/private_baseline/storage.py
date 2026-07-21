"""Atomic initial Private Baseline storage primitives."""

from collections.abc import Mapping
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

from velune_trace.private_baseline.contract import (
    BASELINE_ID_KIND,
    BASELINE_REVISION_ID_KIND,
    DISPLAY_NAME_MAX_LENGTH,
    PRIVATE_BASELINE_SCHEMA_VERSION,
    PRIVATE_BASELINE_VISIBILITY,
    _iter_opaque_identifier_candidates,
    normalize_single_line_text,
)
from velune_trace.private_baseline.errors import (
    PrivateBaselineContractError,
)
from velune_trace.private_baseline.registry import (
    BASELINE_REGISTRY_FILENAME,
    BASELINE_REGISTRY_SCHEMA_NAME,
    BASELINE_REGISTRY_SEMANTICS,
    LoadedPrivateBaselineRegistry,
    _normalize_bundle_locations,
    load_private_baseline_registry,
)
from velune_trace.private_baseline.revision import (
    build_baseline_revision,
)


_BASELINE_DIRECTORY_MODE = 0o700
_PRIVATE_FILE_MODE = 0o600

_REVISIONS_DIRECTORY_NAME = "revisions"
_EVALUATIONS_DIRECTORY_NAME = "evaluations"
_REVIEWS_DIRECTORY_NAME = "reviews"

_BASELINE_REVISION_FILENAME = (
    "baseline_revision.json"
)

_READ_WRITE_CHUNK_SIZE = 1024 * 1024

_VALIDATION_BASELINE_ID = f"vpb_{'0' * 32}"
_VALIDATION_REVISION_ID = f"vpbr_{'0' * 32}"


class PrivateBaselineStorageError(
    PrivateBaselineContractError
):
    """Raised when Private Baseline installation fails."""

    default_code = (
        "VELUNE_PRIVATE_BASELINE_STORAGE_FAILED"
    )


def _raise_storage_error(
    message: str,
    *,
    code: str,
    hint: str,
) -> None:
    raise PrivateBaselineStorageError(
        message,
        code=code,
        hint=hint,
        stage="private_baseline_storage",
    )


def _resolve_parent_directory(
    parent_dir: str | Path,
) -> Path:
    try:
        raw_parent = Path(parent_dir)
    except TypeError as exc:
        raise PrivateBaselineStorageError(
            "Private Baseline parent must be a filesystem "
            "path.",
            code=(
                "VELUNE_PRIVATE_BASELINE_STORAGE_"
                "PARENT_PATH_TYPE_INVALID"
            ),
            hint=(
                "Provide an existing local directory in "
                "which a new Private Baseline may be "
                "created."
            ),
            stage="private_baseline_storage",
        ) from exc

    if raw_parent.is_symlink():
        _raise_storage_error(
            "Private Baseline parent must not be a "
            "symbolic link.",
            code=(
                "VELUNE_PRIVATE_BASELINE_STORAGE_"
                "PARENT_SYMLINK_FORBIDDEN"
            ),
            hint=(
                "Use the real local parent directory."
            ),
        )

    try:
        resolved_parent = raw_parent.resolve(
            strict=True
        )
    except OSError as exc:
        raise PrivateBaselineStorageError(
            "Unable to resolve Private Baseline parent: "
            f"{exc}",
            code=(
                "VELUNE_PRIVATE_BASELINE_STORAGE_"
                "PARENT_UNAVAILABLE"
            ),
            hint=(
                "Create or restore the parent directory "
                "before creating a Private Baseline."
            ),
            stage="private_baseline_storage",
        ) from exc

    if not resolved_parent.is_dir():
        _raise_storage_error(
            "Private Baseline parent is not a directory.",
            code=(
                "VELUNE_PRIVATE_BASELINE_STORAGE_"
                "PARENT_TYPE_INVALID"
            ),
            hint=(
                "Provide an existing local directory."
            ),
        )

    return resolved_parent


def _fsync_directory(
    directory: Path,
) -> None:
    flags = os.O_RDONLY

    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY

    descriptor: int | None = None

    try:
        descriptor = os.open(
            directory,
            flags,
        )
        os.fsync(descriptor)
    except OSError as exc:
        raise PrivateBaselineStorageError(
            f"Unable to synchronize directory "
            f"{directory}: {exc}",
            code=(
                "VELUNE_PRIVATE_BASELINE_STORAGE_"
                "DIRECTORY_SYNC_FAILED"
            ),
            hint=(
                "Check local storage availability and "
                "filesystem permissions."
            ),
            stage="private_baseline_storage",
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _claim_generated_directory(
    parent_dir: Path,
    *,
    identifier_kind: str,
) -> tuple[str, Path]:
    """Atomically claim one generated identifier directory."""

    for candidate in (
        _iter_opaque_identifier_candidates(
            identifier_kind
        )
    ):
        candidate_path = parent_dir / candidate

        try:
            os.mkdir(
                candidate_path,
                _BASELINE_DIRECTORY_MODE,
            )
        except FileExistsError:
            continue
        except OSError as exc:
            raise PrivateBaselineStorageError(
                f"Unable to claim identifier directory "
                f"{candidate}: {exc}",
                code=(
                    "VELUNE_PRIVATE_BASELINE_STORAGE_"
                    "IDENTIFIER_CLAIM_FAILED"
                ),
                hint=(
                    "Check parent-directory permissions "
                    "and local storage availability."
                ),
                stage="private_baseline_storage",
            ) from exc

        try:
            os.chmod(
                candidate_path,
                _BASELINE_DIRECTORY_MODE,
            )
            _fsync_directory(parent_dir)
        except BaseException:
            try:
                os.rmdir(candidate_path)
            except OSError:
                pass
            raise

        return candidate, candidate_path

    _raise_storage_error(
        "Unable to atomically claim an identifier after "
        "32 secure candidates.",
        code=(
            "VELUNE_PRIVATE_BASELINE_STORAGE_"
            "IDENTIFIER_CLAIM_EXHAUSTED"
        ),
        hint=(
            "Do not reuse or overwrite existing Private "
            "Baseline state."
        ),
    )


def _create_private_directory(
    directory: Path,
) -> None:
    try:
        os.mkdir(
            directory,
            _BASELINE_DIRECTORY_MODE,
        )
    except FileExistsError as exc:
        raise PrivateBaselineStorageError(
            f"Private Baseline path already exists: "
            f"{directory.name}.",
            code=(
                "VELUNE_PRIVATE_BASELINE_STORAGE_"
                "DIRECTORY_ALREADY_EXISTS"
            ),
            hint=(
                "Do not overwrite an existing Baseline "
                "directory."
            ),
            stage="private_baseline_storage",
        ) from exc
    except OSError as exc:
        raise PrivateBaselineStorageError(
            f"Unable to create Private Baseline directory "
            f"{directory}: {exc}",
            code=(
                "VELUNE_PRIVATE_BASELINE_STORAGE_"
                "DIRECTORY_CREATE_FAILED"
            ),
            hint=(
                "Check local storage availability and "
                "filesystem permissions."
            ),
            stage="private_baseline_storage",
        ) from exc

    try:
        os.chmod(
            directory,
            _BASELINE_DIRECTORY_MODE,
        )
        _fsync_directory(directory.parent)
    except BaseException:
        try:
            os.rmdir(directory)
        except OSError:
            pass
        raise


def _serialize_json_document(
    value: Mapping[str, Any],
    *,
    document_name: str,
) -> bytes:
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
        )
        return f"{text}\n".encode(
            "utf-8",
            errors="strict",
        )
    except (
        TypeError,
        ValueError,
        UnicodeEncodeError,
        RecursionError,
    ) as exc:
        raise PrivateBaselineStorageError(
            f"{document_name} cannot be serialized as "
            "deterministic strict JSON.",
            code=(
                "VELUNE_PRIVATE_BASELINE_STORAGE_"
                "JSON_SERIALIZATION_FAILED"
            ),
            hint=(
                "Use the validated Private Baseline v1 "
                "data contract."
            ),
            stage="private_baseline_storage",
        ) from exc


def _write_new_file_atomically(
    target_path: Path,
    payload: bytes,
) -> Path:
    """Publish one synchronized file without overwriting."""

    parent_dir = target_path.parent
    temporary_fd: int | None = None
    temporary_path: Path | None = None

    try:
        temporary_fd, temporary_name = tempfile.mkstemp(
            prefix=f".{target_path.name}.",
            suffix=".tmp",
            dir=parent_dir,
        )
        temporary_path = Path(temporary_name)

        os.fchmod(
            temporary_fd,
            _PRIVATE_FILE_MODE,
        )

        with os.fdopen(
            temporary_fd,
            mode="wb",
            closefd=True,
        ) as temporary_file:
            temporary_fd = None

            offset = 0

            while offset < len(payload):
                next_offset = min(
                    offset + _READ_WRITE_CHUNK_SIZE,
                    len(payload),
                )
                temporary_file.write(
                    payload[offset:next_offset]
                )
                offset = next_offset

            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        try:
            os.link(
                temporary_path,
                target_path,
                follow_symlinks=False,
            )
        except FileExistsError as exc:
            raise PrivateBaselineStorageError(
                f"Refusing to overwrite existing file: "
                f"{target_path}.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_STORAGE_"
                    "FILE_ALREADY_EXISTS"
                ),
                hint=(
                    "Use a newly claimed immutable record "
                    "identifier."
                ),
                stage="private_baseline_storage",
            ) from exc

        temporary_path.unlink()
        temporary_path = None

        _fsync_directory(parent_dir)

        return target_path

    except PrivateBaselineStorageError:
        raise
    except OSError as exc:
        raise PrivateBaselineStorageError(
            f"Unable to publish private file "
            f"{target_path.name}: {exc}",
            code=(
                "VELUNE_PRIVATE_BASELINE_STORAGE_"
                "FILE_WRITE_FAILED"
            ),
            hint=(
                "Check local storage availability and "
                "filesystem permissions."
            ),
            stage="private_baseline_storage",
        ) from exc
    finally:
        if temporary_fd is not None:
            os.close(temporary_fd)

        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass


def _prevalidate_creation_inputs(
    *,
    display_name: Any,
    created_at: Any,
    created_by: Any,
    dimension_policy: Any,
    reference_memberships: Any,
    bundle_locations: Any,
) -> dict[str, Any]:
    normalized_display_name = normalize_single_line_text(
        display_name,
        field_name="display_name",
        max_length=DISPLAY_NAME_MAX_LENGTH,
    )

    prototype_revision = build_baseline_revision(
        baseline_id=_VALIDATION_BASELINE_ID,
        baseline_revision_id=(
            _VALIDATION_REVISION_ID
        ),
        parent_revision_id=None,
        created_at=created_at,
        created_by=created_by,
        dimension_policy=dimension_policy,
        reference_memberships=reference_memberships,
    )

    normalized_locations = (
        _normalize_bundle_locations(
            {}
            if bundle_locations is None
            else bundle_locations
        )
    )

    canonical_memberships = []

    for membership in prototype_revision[
        "reference_memberships"
    ]:
        canonical_memberships.append({
            key: copy.deepcopy(value)
            for key, value in membership.items()
            if key != "membership_id"
        })

    return {
        "display_name": normalized_display_name,
        "created_at": prototype_revision[
            "created_at"
        ],
        "created_by": prototype_revision[
            "created_by"
        ],
        "dimension_policy": copy.deepcopy(
            prototype_revision[
                "dimension_policy"
            ]
        ),
        "reference_memberships": (
            canonical_memberships
        ),
        "bundle_locations": copy.deepcopy(
            normalized_locations
        ),
    }


def _remove_claimed_baseline_root(
    root_dir: Path,
    *,
    parent_dir: Path,
) -> None:
    try:
        if root_dir.exists():
            if root_dir.is_symlink():
                _raise_storage_error(
                    "Refusing to clean a symbolic-link "
                    "Baseline root.",
                    code=(
                        "VELUNE_PRIVATE_BASELINE_STORAGE_"
                        "CLEANUP_SYMLINK_FORBIDDEN"
                    ),
                    hint=(
                        "Inspect the claimed path manually "
                        "without following symbolic links."
                    ),
                )

            shutil.rmtree(root_dir)

        _fsync_directory(parent_dir)
    except PrivateBaselineStorageError:
        raise
    except OSError as exc:
        raise PrivateBaselineStorageError(
            "Unable to remove failed initial Private "
            f"Baseline installation: {exc}",
            code=(
                "VELUNE_PRIVATE_BASELINE_STORAGE_"
                "CLEANUP_FAILED"
            ),
            hint=(
                "Inspect the newly claimed Baseline path. "
                "Existing Baseline state was not "
                "intentionally modified."
            ),
            stage="private_baseline_storage",
        ) from exc


def _build_initial_registry(
    *,
    baseline_id: str,
    display_name: str,
    created_at: str,
    revision_id: str,
    revision_relative_path: str,
    revision_payload: bytes,
    bundle_locations: Mapping[str, str],
) -> dict[str, Any]:
    return {
        "schema_name": BASELINE_REGISTRY_SCHEMA_NAME,
        "schema_version": (
            PRIVATE_BASELINE_SCHEMA_VERSION
        ),
        "visibility": PRIVATE_BASELINE_VISIBILITY,
        "semantics": BASELINE_REGISTRY_SEMANTICS,
        "baseline_id": baseline_id,
        "display_name": display_name,
        "created_at": created_at,
        "current_revision_id": revision_id,
        "revisions": [
            {
                "record_id": revision_id,
                "relative_path": (
                    revision_relative_path
                ),
                "size_bytes": len(revision_payload),
                "sha256": hashlib.sha256(
                    revision_payload
                ).hexdigest(),
            },
        ],
        "evaluations": [],
        "reviews": [],
        "bundle_locations": dict(
            bundle_locations
        ),
    }


def _install_initial_private_baseline(
    parent_dir: str | Path,
    *,
    display_name: Any,
    created_at: Any,
    created_by: Any,
    dimension_policy: Any,
    reference_memberships: Any,
    bundle_locations: Any = None,
) -> LoadedPrivateBaselineRegistry:
    """Create one Baseline and its first immutable Revision.

    Reference membership metadata must already originate from verified
    Core Bundles. Bundle loading and mutual compatibility orchestration
    are intentionally outside this storage-only primitive.
    """

    resolved_parent = _resolve_parent_directory(
        parent_dir
    )

    canonical = _prevalidate_creation_inputs(
        display_name=display_name,
        created_at=created_at,
        created_by=created_by,
        dimension_policy=dimension_policy,
        reference_memberships=reference_memberships,
        bundle_locations=bundle_locations,
    )

    claimed_root: Path | None = None

    try:
        baseline_id, claimed_root = (
            _claim_generated_directory(
                resolved_parent,
                identifier_kind=BASELINE_ID_KIND,
            )
        )

        revisions_dir = (
            claimed_root
            / _REVISIONS_DIRECTORY_NAME
        )
        evaluations_dir = (
            claimed_root
            / _EVALUATIONS_DIRECTORY_NAME
        )
        reviews_dir = (
            claimed_root
            / _REVIEWS_DIRECTORY_NAME
        )

        _create_private_directory(revisions_dir)
        _create_private_directory(evaluations_dir)
        _create_private_directory(reviews_dir)

        revision_id, revision_dir = (
            _claim_generated_directory(
                revisions_dir,
                identifier_kind=(
                    BASELINE_REVISION_ID_KIND
                ),
            )
        )

        revision_document = build_baseline_revision(
            baseline_id=baseline_id,
            baseline_revision_id=revision_id,
            parent_revision_id=None,
            created_at=canonical["created_at"],
            created_by=canonical["created_by"],
            dimension_policy=(
                canonical["dimension_policy"]
            ),
            reference_memberships=(
                canonical["reference_memberships"]
            ),
        )

        revision_payload = _serialize_json_document(
            revision_document,
            document_name=(
                _BASELINE_REVISION_FILENAME
            ),
        )

        revision_path = (
            revision_dir
            / _BASELINE_REVISION_FILENAME
        )

        _write_new_file_atomically(
            revision_path,
            revision_payload,
        )

        revision_relative_path = (
            f"{_REVISIONS_DIRECTORY_NAME}/"
            f"{revision_id}/"
            f"{_BASELINE_REVISION_FILENAME}"
        )

        registry_document = _build_initial_registry(
            baseline_id=baseline_id,
            display_name=canonical["display_name"],
            created_at=canonical["created_at"],
            revision_id=revision_id,
            revision_relative_path=(
                revision_relative_path
            ),
            revision_payload=revision_payload,
            bundle_locations=(
                canonical["bundle_locations"]
            ),
        )

        registry_payload = _serialize_json_document(
            registry_document,
            document_name=(
                BASELINE_REGISTRY_FILENAME
            ),
        )

        for directory in (
            revision_dir,
            revisions_dir,
            evaluations_dir,
            reviews_dir,
            claimed_root,
        ):
            _fsync_directory(directory)

        _write_new_file_atomically(
            (
                claimed_root
                / BASELINE_REGISTRY_FILENAME
            ),
            registry_payload,
        )

        try:
            loaded = load_private_baseline_registry(
                claimed_root
            )
        except BaseException as exc:
            raise PrivateBaselineStorageError(
                "Installed Private Baseline failed final "
                "Registry verification.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_STORAGE_"
                    "POST_INSTALL_VALIDATION_FAILED"
                ),
                hint=(
                    "The newly created Baseline will be "
                    "removed rather than retained in an "
                    "untrusted state."
                ),
                stage="private_baseline_storage",
            ) from exc

        return loaded

    except BaseException as exc:
        if claimed_root is not None:
            try:
                _remove_claimed_baseline_root(
                    claimed_root,
                    parent_dir=resolved_parent,
                )
            except PrivateBaselineStorageError as cleanup_exc:
                raise cleanup_exc from exc

        if isinstance(
            exc,
            (
                PrivateBaselineContractError,
                KeyboardInterrupt,
                SystemExit,
            ),
        ):
            raise

        raise PrivateBaselineStorageError(
            f"Initial Private Baseline creation failed: "
            f"{exc}",
            code=(
                "VELUNE_PRIVATE_BASELINE_STORAGE_"
                "CREATE_FAILED"
            ),
            hint=(
                "No newly claimed Private Baseline state "
                "was retained."
            ),
            stage="private_baseline_storage",
        ) from exc
