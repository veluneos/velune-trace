#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import zipfile
from datetime import date
from pathlib import Path


VERSION_PATTERN = re.compile(
    r'^__version__\s*=\s*["\']([^"\']+)["\']\s*$',
    re.MULTILINE,
)

OID_PATTERN = re.compile(
    r"^[0-9a-f]{40}([0-9a-f]{24})?$"
)

ROOT_FILES = (
    "LICENSE",
    "README.md",
    "CHANGELOG.md",
    "requirements.txt",
    "requirements-lock.txt",
)

RUNTIME_DIRECTORIES = (
    "bin",
    "velune_trace",
)

PUBLIC_FILES = (
    "benchmarks/core_bundle_comparison_v1_validation_record.md",
    "docs/BUNDLE_COMPARISON_V1.md",
    "docs/EXAMPLE_FEEDBACK_REPORT.md",
    "docs/GETTING_STARTED.md",
    "docs/PARTNER_PROGRAM.md",
    "docs/PRIVATE_BASELINE_V1.md",
    "docs/REFERENCE_COHORT_REGISTRY.md",
    "docs/TRUST_AND_PRIVACY.md",
    "docs/validation/MASTER_NUSCENES_EXTERNAL_SWEEP_SUMMARY.md",
    "demo/private_baseline_phase2_mvp/README.md",
    "demo/private_baseline_phase2_mvp/baseline_evaluation_report_excerpt.json",
    "demo/private_baseline_phase2_mvp/baseline_evaluation_summary_demo.md",
    "demo/private_baseline_phase2_mvp/demo_manifest.json",
    "demo/private_baseline_phase2_mvp/private_validation_offer.md",
    "demo/private_baseline_phase2_mvp/product_claims.md",
)

EXCLUDED_COMPONENTS = {
    ".git",
    ".github",
    ".venv",
    "__pycache__",
    "site",
    "tests",
}

EXCLUDED_SUFFIXES = {
    ".mcap",
    ".pyc",
    ".pyo",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_version(source_root: Path) -> str:
    version_file = (
        source_root
        / "velune_trace"
        / "__init__.py"
    )

    text = version_file.read_text(
        encoding="utf-8"
    )

    matches = VERSION_PATTERN.findall(text)

    if len(matches) != 1:
        raise RuntimeError(
            "VERSION_ASSIGNMENT_COUNT="
            f"{len(matches)}"
        )

    return matches[0]


def is_excluded(path: Path) -> bool:
    if any(
        component in EXCLUDED_COMPONENTS
        for component in path.parts
    ):
        return True

    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True

    return False


def require_regular_file(path: Path) -> None:
    if path.is_symlink():
        raise RuntimeError(
            f"SYMLINK_NOT_ALLOWED={path}"
        )

    if not path.is_file():
        raise RuntimeError(
            f"REQUIRED_FILE_MISSING={path}"
        )


def collect_directory(
    source_root: Path,
    relative_directory: str,
) -> list[Path]:
    directory = source_root / relative_directory

    if not directory.is_dir():
        raise RuntimeError(
            f"REQUIRED_DIRECTORY_MISSING={relative_directory}"
        )

    collected: list[Path] = []

    for path in sorted(directory.rglob("*")):
        if path.is_dir():
            continue

        relative_path = path.relative_to(
            source_root
        )

        if is_excluded(relative_path):
            continue

        require_regular_file(path)
        collected.append(relative_path)

    return collected


MARKDOWN_LINK_PATTERN = re.compile(
    r"\[[^\]]+\]\(([^)]+)\)"
)


def validate_selected_markdown_links(
    source_root: Path,
    selected_paths: list[Path],
) -> None:
    selected_names = {
        path.as_posix()
        for path in selected_paths
    }

    failures: list[str] = []

    for markdown_path in sorted(
        path
        for path in selected_paths
        if path.suffix.lower() == ".md"
    ):
        markdown_text = (
            source_root
            / markdown_path
        ).read_text(
            encoding="utf-8"
        )

        for raw_target in MARKDOWN_LINK_PATTERN.findall(
            markdown_text
        ):
            target = raw_target.strip()

            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1].strip()

            if not target or target.startswith((
                "#",
                "http://",
                "https://",
                "mailto:",
            )):
                continue

            target = target.split("#", 1)[0]

            if not target:
                continue

            resolved_path = (
                source_root
                / markdown_path.parent
                / target
            ).resolve()

            try:
                relative_target = resolved_path.relative_to(
                    source_root
                )
            except ValueError:
                failures.append(
                    "LINK_OUTSIDE_SOURCE_ROOT:"
                    f"{markdown_path.as_posix()}->{target}"
                )
                continue

            relative_name = relative_target.as_posix()

            if not resolved_path.is_file():
                failures.append(
                    "LINK_TARGET_NOT_FOUND:"
                    f"{markdown_path.as_posix()}->{relative_name}"
                )
                continue

            if relative_name not in selected_names:
                failures.append(
                    "LINK_TARGET_NOT_PACKAGED:"
                    f"{markdown_path.as_posix()}->{relative_name}"
                )

    if failures:
        raise RuntimeError(
            "MARKDOWN_LINK_VALIDATION_FAILED\n"
            + "\n".join(sorted(set(failures)))
        )


def collect_payload_files(
    source_root: Path,
    version: str,
) -> list[Path]:
    collected: list[Path] = []

    for relative_name in ROOT_FILES:
        path = source_root / relative_name
        require_regular_file(path)
        collected.append(Path(relative_name))

    for directory in RUNTIME_DIRECTORIES:
        collected.extend(
            collect_directory(
                source_root,
                directory,
            )
        )

    for relative_name in PUBLIC_FILES:
        path = source_root / relative_name
        require_regular_file(path)
        collected.append(Path(relative_name))

    for relative_name in (
        "tools/create_sample_mcap.py",
        "release/INSTALL.md",
        "release/QUICKSTART.md",
        f"release/RELEASE_NOTES_v{version}.md",
    ):
        path = source_root / relative_name
        require_regular_file(path)
        collected.append(Path(relative_name))

    unique = sorted(
        set(collected),
        key=lambda path: path.as_posix(),
    )

    for relative_path in unique:
        if is_excluded(relative_path):
            raise RuntimeError(
                "EXCLUDED_FILE_SELECTED="
                f"{relative_path.as_posix()}"
            )

    validate_selected_markdown_links(
        source_root,
        unique,
    )

    return unique


def normalized_mode(path: Path) -> int:
    source_mode = stat.S_IMODE(
        path.stat().st_mode
    )

    if source_mode & stat.S_IXUSR:
        return 0o755

    return 0o644


def zip_timestamp(
    release_date: date,
) -> tuple[int, int, int, int, int, int]:
    return (
        release_date.year,
        release_date.month,
        release_date.day,
        0,
        0,
        0,
    )


def build_archive(
    *,
    source_root: Path,
    output_directory: Path,
    source_tree_oid: str,
    release_date: date,
) -> tuple[Path, Path, Path]:
    version = read_version(source_root)

    if not OID_PATTERN.fullmatch(
        source_tree_oid
    ):
        raise RuntimeError(
            f"INVALID_SOURCE_TREE_OID={source_tree_oid}"
        )

    archive_root = (
        f"velune-trace-v{version}"
    )

    archive_name = (
        f"{archive_root}.zip"
    )

    archive_path = (
        output_directory
        / archive_name
    )

    checksum_path = (
        output_directory
        / "SHA256SUMS"
    )

    external_manifest_path = (
        output_directory
        / f"{archive_root}.release-manifest.json"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    if any(output_directory.iterdir()):
        raise RuntimeError(
            "OUTPUT_DIRECTORY_NOT_EMPTY="
            f"{output_directory}"
        )

    payload_paths = collect_payload_files(
        source_root,
        version,
    )

    payload_records: list[dict[str, object]] = []
    payload_data: dict[str, tuple[bytes, int]] = {}

    for relative_path in payload_paths:
        source_path = source_root / relative_path
        data = source_path.read_bytes()
        mode = normalized_mode(source_path)
        relative_name = relative_path.as_posix()

        payload_data[relative_name] = (
            data,
            mode,
        )

        payload_records.append({
            "path": relative_name,
            "size_bytes": len(data),
            "sha256": sha256_bytes(data),
            "mode": format(mode, "04o"),
        })

    manifest = {
        "schema_name": "velune.release_manifest",
        "schema_version": "0.1.0",
        "product": "Velune Trace",
        "version": version,
        "archive_name": archive_name,
        "archive_root": archive_root,
        "source_tree_oid": source_tree_oid,
        "release_date": release_date.isoformat(),
        "integrity_scope": (
            "Payload files listed in this manifest. "
            "The manifest does not list itself."
        ),
        "file_count": len(payload_records),
        "files": payload_records,
    }

    manifest_bytes = (
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )

    timestamp = zip_timestamp(
        release_date
    )

    archive_entries = dict(payload_data)
    archive_entries[
        "RELEASE_MANIFEST.json"
    ] = (
        manifest_bytes,
        0o644,
    )

    with zipfile.ZipFile(
        archive_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for relative_name in sorted(
            archive_entries
        ):
            data, mode = archive_entries[
                relative_name
            ]

            archive_name_in_zip = (
                f"{archive_root}/"
                f"{relative_name}"
            )

            info = zipfile.ZipInfo(
                archive_name_in_zip,
                date_time=timestamp,
            )

            info.create_system = 3
            info.compress_type = (
                zipfile.ZIP_DEFLATED
            )
            info.external_attr = (
                mode & 0xFFFF
            ) << 16

            archive.writestr(
                info,
                data,
                compress_type=(
                    zipfile.ZIP_DEFLATED
                ),
                compresslevel=9,
            )

    archive_digest = sha256_bytes(
        archive_path.read_bytes()
    )

    checksum_path.write_text(
        f"{archive_digest}  {archive_name}\n",
        encoding="utf-8",
        newline="\n",
    )

    external_manifest_path.write_bytes(
        manifest_bytes
    )

    with zipfile.ZipFile(
        archive_path,
        mode="r",
    ) as archive:
        names = archive.namelist()

        if len(names) != len(set(names)):
            raise RuntimeError(
                "DUPLICATE_ZIP_ENTRY"
            )

        expected_names = {
            f"{archive_root}/{name}"
            for name in archive_entries
        }

        if set(names) != expected_names:
            raise RuntimeError(
                "ZIP_CONTENT_MISMATCH"
            )

        archived_manifest = archive.read(
            f"{archive_root}/"
            "RELEASE_MANIFEST.json"
        )

        if archived_manifest != manifest_bytes:
            raise RuntimeError(
                "ARCHIVED_MANIFEST_MISMATCH"
            )

        for record in payload_records:
            relative_name = str(
                record["path"]
            )

            archived_data = archive.read(
                f"{archive_root}/"
                f"{relative_name}"
            )

            if len(archived_data) != record[
                "size_bytes"
            ]:
                raise RuntimeError(
                    "ARCHIVED_SIZE_MISMATCH="
                    f"{relative_name}"
                )

            if sha256_bytes(
                archived_data
            ) != record["sha256"]:
                raise RuntimeError(
                    "ARCHIVED_HASH_MISMATCH="
                    f"{relative_name}"
                )

    print(f"VERSION={version}")
    print(
        f"SOURCE_TREE_OID={source_tree_oid}"
    )
    print(
        f"PAYLOAD_FILE_COUNT={len(payload_records)}"
    )
    print(
        f"ARCHIVE={archive_path}"
    )
    print(
        f"ARCHIVE_SHA256={archive_digest}"
    )
    print(
        f"CHECKSUM_FILE={checksum_path}"
    )
    print(
        "INTERNAL_ARCHIVE_VERIFICATION=PASS"
    )

    return (
        archive_path,
        checksum_path,
        external_manifest_path,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic Velune Trace "
            "release archive."
        )
    )

    parser.add_argument(
        "--source-root",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--source-tree-oid",
        required=True,
    )

    parser.add_argument(
        "--release-date",
        required=True,
    )

    arguments = parser.parse_args()

    source_root = (
        arguments.source_root
        .expanduser()
        .resolve()
    )

    output_directory = (
        arguments.output_dir
        .expanduser()
        .resolve()
    )

    parsed_release_date = date.fromisoformat(
        arguments.release_date
    )

    build_archive(
        source_root=source_root,
        output_directory=output_directory,
        source_tree_oid=(
            arguments.source_tree_oid
        ),
        release_date=parsed_release_date,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
