"""Atomic private Evidence Report Bundle manifest writer."""

from collections.abc import Mapping
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any

from velune_trace.reporting.errors import BundleWriteError


MANIFEST_FILENAME = "report_manifest.json"
MANIFEST_FILE_MODE = 0o600


def _validate_json_value(
    value: Any,
    *,
    path: str,
    active_container_ids: set[int],
) -> None:
    if value is None or isinstance(value, (bool, int, str)):
        return

    if isinstance(value, float):
        if not math.isfinite(value):
            raise BundleWriteError(
                f"{path} must contain only finite numbers",
                code="VELUNE_BUNDLE_MANIFEST_JSON_INVALID",
                hint=(
                    "Replace NaN or Infinity with a finite number, "
                    "null, or a documented string value."
                ),
            )
        return

    if isinstance(value, Mapping):
        container_id = id(value)

        if container_id in active_container_ids:
            raise BundleWriteError(
                f"{path} contains a circular reference",
                code="VELUNE_BUNDLE_MANIFEST_JSON_INVALID",
                hint=(
                    "Use an acyclic JSON-compatible manifest "
                    "structure."
                ),
            )

        active_container_ids.add(container_id)

        try:
            for key, item in value.items():
                if not isinstance(key, str):
                    raise BundleWriteError(
                        (
                            f"{path} contains a non-string "
                            "mapping key"
                        ),
                        code=(
                            "VELUNE_BUNDLE_MANIFEST_JSON_INVALID"
                        ),
                        hint=(
                            "All JSON object keys must be strings."
                        ),
                    )

                _validate_json_value(
                    item,
                    path=f"{path}.{key}",
                    active_container_ids=active_container_ids,
                )
        finally:
            active_container_ids.remove(container_id)

        return

    if isinstance(value, list):
        container_id = id(value)

        if container_id in active_container_ids:
            raise BundleWriteError(
                f"{path} contains a circular reference",
                code="VELUNE_BUNDLE_MANIFEST_JSON_INVALID",
                hint=(
                    "Use an acyclic JSON-compatible manifest "
                    "structure."
                ),
            )

        active_container_ids.add(container_id)

        try:
            for index, item in enumerate(value):
                _validate_json_value(
                    item,
                    path=f"{path}[{index}]",
                    active_container_ids=active_container_ids,
                )
        finally:
            active_container_ids.remove(container_id)

        return

    raise BundleWriteError(
        (
            f"{path} contains unsupported JSON value type: "
            f"{type(value).__name__}"
        ),
        code="VELUNE_BUNDLE_MANIFEST_JSON_INVALID",
        hint=(
            "Use only JSON-compatible objects, arrays, strings, "
            "finite numbers, booleans, and null."
        ),
    )


def _serialize_manifest(
    manifest: Mapping[str, Any],
) -> bytes:
    if not isinstance(manifest, Mapping):
        raise BundleWriteError(
            "manifest must be a mapping",
            code="VELUNE_BUNDLE_MANIFEST_TYPE_INVALID",
            hint=(
                "Pass the object returned by "
                "assemble_private_report_manifest."
            ),
        )

    _validate_json_value(
        manifest,
        path="manifest",
        active_container_ids=set(),
    )

    try:
        rendered = json.dumps(
            manifest,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
        )
        return f"{rendered}\n".encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise BundleWriteError(
            f"Unable to serialize report manifest: {exc}",
            code="VELUNE_BUNDLE_MANIFEST_SERIALIZATION_FAILED",
            hint=(
                "Confirm that the manifest contains valid UTF-8 "
                "JSON-compatible values."
            ),
        ) from exc


def _resolve_bundle_directory(
    bundle_dir: str | Path,
) -> Path:
    try:
        raw_bundle_dir = Path(bundle_dir)
    except TypeError as exc:
        raise BundleWriteError(
            "bundle_dir must be a filesystem path",
            code="VELUNE_BUNDLE_DIRECTORY_TYPE_INVALID",
            hint="Provide an existing Bundle directory path.",
        ) from exc

    if raw_bundle_dir.is_symlink():
        raise BundleWriteError(
            "Bundle directory must not be a symbolic link",
            code="VELUNE_BUNDLE_DIRECTORY_SYMLINK_FORBIDDEN",
            hint=(
                "Use the real Bundle directory rather than a "
                "symbolic link."
            ),
        )

    try:
        resolved_bundle_dir = raw_bundle_dir.resolve(
            strict=True
        )
    except OSError as exc:
        raise BundleWriteError(
            f"Unable to resolve Bundle directory: {exc}",
            code="VELUNE_BUNDLE_DIRECTORY_UNAVAILABLE",
            hint=(
                "Create the Bundle directory before writing the "
                "manifest."
            ),
        ) from exc

    if not resolved_bundle_dir.is_dir():
        raise BundleWriteError(
            "Bundle path is not a directory",
            code="VELUNE_BUNDLE_DIRECTORY_INVALID",
            hint="Provide an existing Bundle directory.",
        )

    return resolved_bundle_dir


def _fsync_directory(directory: Path) -> None:
    flags = os.O_RDONLY

    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY

    directory_fd = os.open(directory, flags)

    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def write_private_report_manifest(
    *,
    bundle_dir: str | Path,
    manifest: Mapping[str, Any],
    overwrite: bool = False,
) -> Path:
    """Write ``report_manifest.json`` atomically and securely.

    The complete UTF-8 JSON payload is written to a temporary file in the
    Bundle directory, flushed to disk, and installed only after writing
    succeeds.

    With ``overwrite=False``, installation uses an atomic hard-link operation
    so an existing manifest cannot be replaced by a check/write race.

    The manifest is created with owner-only permissions because private source
    provenance may be present.
    """

    if not isinstance(overwrite, bool):
        raise BundleWriteError(
            "overwrite must be a bool",
            code="VELUNE_BUNDLE_OVERWRITE_TYPE_INVALID",
            hint="Use true or false for overwrite.",
        )

    resolved_bundle_dir = _resolve_bundle_directory(
        bundle_dir
    )
    target_path = (
        resolved_bundle_dir / MANIFEST_FILENAME
    )

    if target_path.is_symlink():
        raise BundleWriteError(
            "Existing report manifest must not be a symbolic link",
            code="VELUNE_BUNDLE_MANIFEST_SYMLINK_FORBIDDEN",
            hint=(
                "Remove the symbolic link before generating the "
                "Bundle manifest."
            ),
        )

    if target_path.exists():
        if not target_path.is_file():
            raise BundleWriteError(
                "Existing report manifest path is not a file",
                code="VELUNE_BUNDLE_MANIFEST_PATH_INVALID",
                hint=(
                    "Remove the conflicting filesystem entry "
                    "before writing the manifest."
                ),
            )

        if not overwrite:
            raise BundleWriteError(
                "report_manifest.json already exists",
                code="VELUNE_BUNDLE_MANIFEST_ALREADY_EXISTS",
                hint=(
                    "Use a new Bundle directory or explicitly "
                    "enable overwrite."
                ),
            )

    payload = _serialize_manifest(manifest)

    temporary_path: Path | None = None
    temporary_fd: int | None = None

    try:
        temporary_fd, temporary_name = tempfile.mkstemp(
            prefix=".report_manifest.",
            suffix=".tmp",
            dir=resolved_bundle_dir,
        )
        temporary_path = Path(temporary_name)

        os.chmod(
            temporary_path,
            MANIFEST_FILE_MODE,
        )

        with os.fdopen(
            temporary_fd,
            mode="wb",
            closefd=True,
        ) as temporary_file:
            temporary_fd = None
            temporary_file.write(payload)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        if overwrite:
            os.replace(
                temporary_path,
                target_path,
            )
            temporary_path = None
        else:
            try:
                os.link(
                    temporary_path,
                    target_path,
                )
            except FileExistsError as exc:
                raise BundleWriteError(
                    "report_manifest.json already exists",
                    code=(
                        "VELUNE_BUNDLE_MANIFEST_ALREADY_EXISTS"
                    ),
                    hint=(
                        "Use a new Bundle directory or explicitly "
                        "enable overwrite."
                    ),
                ) from exc

            temporary_path.unlink()
            temporary_path = None

        _fsync_directory(resolved_bundle_dir)

        return target_path

    except BundleWriteError:
        raise
    except OSError as exc:
        raise BundleWriteError(
            f"Unable to write report manifest atomically: {exc}",
            code="VELUNE_BUNDLE_MANIFEST_WRITE_FAILED",
            hint=(
                "Check Bundle directory permissions and available "
                "disk space."
            ),
        ) from exc
    finally:
        if temporary_fd is not None:
            os.close(temporary_fd)

        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            try:
                temporary_path.unlink()
            except OSError:
                pass
