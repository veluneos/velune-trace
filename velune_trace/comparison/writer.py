"""Atomic private writer for Core Bundle comparison outputs."""

from collections.abc import Mapping
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

from velune_trace.comparison.engine import (
    COMPARISON_SCHEMA_NAME,
    COMPARISON_SCHEMA_VERSION,
    COMPARISON_SEMANTICS,
    COMPARISON_VISIBILITY,
)
from velune_trace.reporting.errors import EvidenceBundleError


COMPARISON_REPORT_FILENAME = "comparison_report.json"
COMPARISON_SUMMARY_FILENAME = "comparison_summary.md"

COMPARISON_DIRECTORY_MODE = 0o700
COMPARISON_FILE_MODE = 0o600

HUMAN_JUDGMENT_BOUNDARY_STATEMENT = (
    "Velune reports observable differences between the Reference Bundle "
    "and Target Bundle. Engineers determine their meaning and cause."
)

REQUIRED_TOP_LEVEL_FIELDS = frozenset({
    "schema_name",
    "schema_version",
    "visibility",
    "semantics",
    "generated_at",
    "reference",
    "target",
    "compatibility",
    "topic_set",
    "topic_comparisons",
    "summary",
    "excluded_from_change_evaluation",
    "judgment_boundary",
})

REQUIRED_JUDGMENT_BOUNDARY_FIELDS = (
    "root_cause_conclusion",
    "fault_assignment",
    "liability_calculation",
    "safety_certification",
    "automatic_regression_judgment",
)

TOPIC_SET_FIELDS = (
    "common_topics",
    "reference_only_topics",
    "target_only_topics",
)


class BundleComparisonWriteError(EvidenceBundleError):
    """Raised when comparison outputs cannot be installed safely."""

    default_code = "VELUNE_COMPARISON_WRITE_FAILED"


@dataclass(frozen=True)
class WrittenBundleComparison:
    """Paths created by a successful comparison write."""

    output_dir: Path
    report_path: Path
    summary_path: Path


def _raise_write_error(
    message: str,
    *,
    code: str,
    hint: str,
) -> None:
    raise BundleComparisonWriteError(
        message,
        code=code,
        hint=hint,
        stage="comparison_write",
    )


def _validate_json_value(
    value: Any,
    *,
    path: str,
    active_container_ids: set[int],
) -> None:
    if value is None or isinstance(
        value,
        (bool, int, str),
    ):
        return

    if isinstance(value, float):
        if not math.isfinite(value):
            _raise_write_error(
                f"{path} must contain only finite numbers.",
                code=(
                    "VELUNE_COMPARISON_"
                    "JSON_VALUE_INVALID"
                ),
                hint=(
                    "Replace NaN or Infinity with a finite "
                    "number or null."
                ),
            )
        return

    if isinstance(value, Mapping):
        container_id = id(value)

        if container_id in active_container_ids:
            _raise_write_error(
                f"{path} contains a circular reference.",
                code=(
                    "VELUNE_COMPARISON_"
                    "JSON_VALUE_INVALID"
                ),
                hint=(
                    "Use an acyclic JSON-compatible report."
                ),
            )

        active_container_ids.add(container_id)

        try:
            for key, item in value.items():
                if not isinstance(key, str):
                    _raise_write_error(
                        f"{path} contains a non-string key.",
                        code=(
                            "VELUNE_COMPARISON_"
                            "JSON_VALUE_INVALID"
                        ),
                        hint=(
                            "All JSON object keys must be "
                            "strings."
                        ),
                    )

                _validate_json_value(
                    item,
                    path=f"{path}.{key}",
                    active_container_ids=(
                        active_container_ids
                    ),
                )
        finally:
            active_container_ids.remove(container_id)

        return

    if isinstance(value, list):
        container_id = id(value)

        if container_id in active_container_ids:
            _raise_write_error(
                f"{path} contains a circular reference.",
                code=(
                    "VELUNE_COMPARISON_"
                    "JSON_VALUE_INVALID"
                ),
                hint=(
                    "Use an acyclic JSON-compatible report."
                ),
            )

        active_container_ids.add(container_id)

        try:
            for index, item in enumerate(value):
                _validate_json_value(
                    item,
                    path=f"{path}[{index}]",
                    active_container_ids=(
                        active_container_ids
                    ),
                )
        finally:
            active_container_ids.remove(container_id)

        return

    _raise_write_error(
        f"{path} contains unsupported value type "
        f"{type(value).__name__}.",
        code="VELUNE_COMPARISON_JSON_VALUE_INVALID",
        hint=(
            "Use only JSON-compatible mappings, lists, "
            "strings, finite numbers, booleans, and null."
        ),
    )


def _require_sorted_unique_strings(
    value: Any,
    *,
    field_path: str,
) -> list[str]:
    if not isinstance(value, list):
        _raise_write_error(
            f"{field_path} must be a list.",
            code=(
                "VELUNE_COMPARISON_"
                "REPORT_CONTRACT_INVALID"
            ),
            hint=(
                "Build the report with the pure comparison "
                "engine before writing it."
            ),
        )

    if any(
        not isinstance(item, str)
        or not item
        or item != item.strip()
        for item in value
    ):
        _raise_write_error(
            f"{field_path} must contain non-empty strings.",
            code=(
                "VELUNE_COMPARISON_"
                "REPORT_CONTRACT_INVALID"
            ),
            hint=(
                "Use canonical topic and changed-field names."
            ),
        )

    if value != sorted(value):
        _raise_write_error(
            f"{field_path} must be sorted.",
            code=(
                "VELUNE_COMPARISON_"
                "REPORT_ORDER_INVALID"
            ),
            hint=(
                "Preserve deterministic engine ordering."
            ),
        )

    if len(value) != len(set(value)):
        _raise_write_error(
            f"{field_path} must not contain duplicates.",
            code=(
                "VELUNE_COMPARISON_"
                "REPORT_ORDER_INVALID"
            ),
            hint=(
                "Remove duplicate topic or field names."
            ),
        )

    return value


def _validate_report_contract(
    report: Mapping[str, Any],
) -> None:
    if not isinstance(report, Mapping):
        _raise_write_error(
            "report must be a mapping.",
            code=(
                "VELUNE_COMPARISON_"
                "REPORT_TYPE_INVALID"
            ),
            hint=(
                "Pass the object returned by "
                "build_bundle_comparison."
            ),
        )

    missing_fields = sorted(
        REQUIRED_TOP_LEVEL_FIELDS.difference(report)
    )

    if missing_fields:
        _raise_write_error(
            "Comparison report is missing required fields: "
            + ", ".join(missing_fields),
            code=(
                "VELUNE_COMPARISON_"
                "REPORT_CONTRACT_INVALID"
            ),
            hint=(
                "Rebuild the report with the current "
                "comparison engine."
            ),
        )

    expected_constants = {
        "schema_name": COMPARISON_SCHEMA_NAME,
        "schema_version": COMPARISON_SCHEMA_VERSION,
        "visibility": COMPARISON_VISIBILITY,
        "semantics": COMPARISON_SEMANTICS,
    }

    for field_name, expected_value in (
        expected_constants.items()
    ):
        if report[field_name] != expected_value:
            _raise_write_error(
                f"{field_name} does not match the v1 "
                f"comparison contract.",
                code=(
                    "VELUNE_COMPARISON_"
                    "REPORT_CONTRACT_INVALID"
                ),
                hint=(
                    "Use a report generated by the current "
                    "comparison engine."
                ),
            )

    generated_at = report["generated_at"]

    if (
        not isinstance(generated_at, str)
        or not generated_at
        or generated_at != generated_at.strip()
    ):
        _raise_write_error(
            "generated_at must be a non-empty string.",
            code=(
                "VELUNE_COMPARISON_"
                "REPORT_CONTRACT_INVALID"
            ),
            hint=(
                "Use the timezone-aware generated_at value "
                "validated by the engine."
            ),
        )

    compatibility = report["compatibility"]

    if not isinstance(compatibility, Mapping):
        _raise_write_error(
            "compatibility must be a mapping.",
            code=(
                "VELUNE_COMPARISON_"
                "REPORT_CONTRACT_INVALID"
            ),
            hint=(
                "Use the compatibility result produced by "
                "the comparison engine."
            ),
        )

    if compatibility.get("status") != "compatible":
        _raise_write_error(
            "Only compatible Bundle comparisons may be "
            "written.",
            code=(
                "VELUNE_COMPARISON_"
                "REPORT_INCOMPATIBLE"
            ),
            hint=(
                "Resolve blocking compatibility differences "
                "before generating outputs."
            ),
        )

    topic_set = report["topic_set"]

    if not isinstance(topic_set, Mapping):
        _raise_write_error(
            "topic_set must be a mapping.",
            code=(
                "VELUNE_COMPARISON_"
                "REPORT_CONTRACT_INVALID"
            ),
            hint=(
                "Use the topic-set object produced by the "
                "comparison engine."
            ),
        )

    for field_name in TOPIC_SET_FIELDS:
        if field_name not in topic_set:
            _raise_write_error(
                f"topic_set.{field_name} is missing.",
                code=(
                    "VELUNE_COMPARISON_"
                    "REPORT_CONTRACT_INVALID"
                ),
                hint=(
                    "Rebuild the report with the current "
                    "comparison engine."
                ),
            )

        _require_sorted_unique_strings(
            topic_set[field_name],
            field_path=f"topic_set.{field_name}",
        )

    topic_comparisons = report["topic_comparisons"]

    if not isinstance(topic_comparisons, list):
        _raise_write_error(
            "topic_comparisons must be a list.",
            code=(
                "VELUNE_COMPARISON_"
                "REPORT_CONTRACT_INVALID"
            ),
            hint=(
                "Use the comparison records produced by the "
                "comparison engine."
            ),
        )

    topic_names = []

    for index, comparison in enumerate(
        topic_comparisons
    ):
        if not isinstance(comparison, Mapping):
            _raise_write_error(
                f"topic_comparisons[{index}] must be a "
                f"mapping.",
                code=(
                    "VELUNE_COMPARISON_"
                    "REPORT_CONTRACT_INVALID"
                ),
                hint=(
                    "Use the comparison records produced by "
                    "the comparison engine."
                ),
            )

        topic = comparison.get("topic")

        if (
            not isinstance(topic, str)
            or not topic
            or topic != topic.strip()
        ):
            _raise_write_error(
                f"topic_comparisons[{index}].topic is "
                f"invalid.",
                code=(
                    "VELUNE_COMPARISON_"
                    "REPORT_CONTRACT_INVALID"
                ),
                hint="Use a canonical non-empty topic name.",
            )

        topic_names.append(topic)

        if "changed_fields" not in comparison:
            _raise_write_error(
                f"topic_comparisons[{index}].changed_fields "
                f"is missing.",
                code=(
                    "VELUNE_COMPARISON_"
                    "REPORT_CONTRACT_INVALID"
                ),
                hint=(
                    "Rebuild the report with the current "
                    "comparison engine."
                ),
            )

        _require_sorted_unique_strings(
            comparison["changed_fields"],
            field_path=(
                f"topic_comparisons[{index}]."
                f"changed_fields"
            ),
        )

    if topic_names != sorted(topic_names):
        _raise_write_error(
            "topic_comparisons must be sorted by topic.",
            code=(
                "VELUNE_COMPARISON_"
                "REPORT_ORDER_INVALID"
            ),
            hint=(
                "Preserve deterministic engine ordering."
            ),
        )

    if len(topic_names) != len(set(topic_names)):
        _raise_write_error(
            "topic_comparisons contains duplicate topics.",
            code=(
                "VELUNE_COMPARISON_"
                "REPORT_ORDER_INVALID"
            ),
            hint="Remove duplicate topic records.",
        )

    summary = report["summary"]

    if not isinstance(summary, Mapping):
        _raise_write_error(
            "summary must be a mapping.",
            code=(
                "VELUNE_COMPARISON_"
                "REPORT_CONTRACT_INVALID"
            ),
            hint=(
                "Use the summary generated by the comparison "
                "engine."
            ),
        )

    for field_name, value in summary.items():
        if (
            not isinstance(field_name, str)
            or isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            _raise_write_error(
                "summary must contain only non-negative "
                "integer counts.",
                code=(
                    "VELUNE_COMPARISON_"
                    "REPORT_CONTRACT_INVALID"
                ),
                hint=(
                    "Do not add scores, labels, or judgments "
                    "to the summary."
                ),
            )

    excluded = report[
        "excluded_from_change_evaluation"
    ]

    _require_sorted_unique_strings(
        excluded,
        field_path=(
            "excluded_from_change_evaluation"
        ),
    )

    judgment_boundary = report["judgment_boundary"]

    if not isinstance(judgment_boundary, Mapping):
        _raise_write_error(
            "judgment_boundary must be a mapping.",
            code=(
                "VELUNE_COMPARISON_"
                "REPORT_CONTRACT_INVALID"
            ),
            hint=(
                "Use the judgment boundary generated by the "
                "comparison engine."
            ),
        )

    for field_name in (
        REQUIRED_JUDGMENT_BOUNDARY_FIELDS
    ):
        if judgment_boundary.get(field_name) is not False:
            _raise_write_error(
                f"judgment_boundary.{field_name} must be "
                f"false.",
                code=(
                    "VELUNE_COMPARISON_"
                    "JUDGMENT_BOUNDARY_INVALID"
                ),
                hint=(
                    "Comparison outputs must not emit causal, "
                    "fault, liability, safety, or regression "
                    "judgments."
                ),
            )

    for field_name, value in (
        judgment_boundary.items()
    ):
        if value is not False:
            _raise_write_error(
                f"judgment_boundary.{field_name} must be "
                f"false.",
                code=(
                    "VELUNE_COMPARISON_"
                    "JUDGMENT_BOUNDARY_INVALID"
                ),
                hint=(
                    "Every declared judgment capability must "
                    "remain disabled."
                ),
            )

    _validate_json_value(
        report,
        path="report",
        active_container_ids=set(),
    )


def _serialize_report(
    report: Mapping[str, Any],
) -> bytes:
    _validate_report_contract(report)

    try:
        rendered = json.dumps(
            report,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
        )
    except (TypeError, ValueError, UnicodeError) as exc:
        raise BundleComparisonWriteError(
            f"Unable to serialize comparison report: {exc}",
            code=(
                "VELUNE_COMPARISON_"
                "REPORT_SERIALIZATION_FAILED"
            ),
            hint=(
                "Confirm that the report contains valid "
                "UTF-8 JSON-compatible values."
            ),
            stage="comparison_write",
        ) from exc

    return f"{rendered}\n".encode("utf-8")


def _markdown_code(value: Any) -> str:
    text = str(value)
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")
    text = text.replace("`", "\\`")
    return f"`{text}`"


def _markdown_topic_list(
    topics: list[str],
) -> list[str]:
    if not topics:
        return ["- None"]

    return [
        f"- {_markdown_code(topic)}"
        for topic in topics
    ]


def render_comparison_summary(
    report: Mapping[str, Any],
) -> str:
    """Render deterministic Markdown from the final JSON object."""

    _validate_report_contract(report)

    reference = report["reference"]
    target = report["target"]
    compatibility = report["compatibility"]
    topic_set = report["topic_set"]
    summary = report["summary"]

    warnings = compatibility.get("warnings", [])

    if not isinstance(warnings, list):
        _raise_write_error(
            "compatibility.warnings must be a list.",
            code=(
                "VELUNE_COMPARISON_"
                "REPORT_CONTRACT_INVALID"
            ),
            hint=(
                "Use the compatibility record generated by "
                "the comparison engine."
            ),
        )

    lines = [
        "# Velune Core Bundle Comparison",
        "",
        HUMAN_JUDGMENT_BOUNDARY_STATEMENT,
        "",
        "## Report",
        "",
        (
            "- Generated at: "
            f"{_markdown_code(report['generated_at'])}"
        ),
        (
            "- Visibility: "
            f"{_markdown_code(report['visibility'])}"
        ),
        (
            "- Semantics: "
            f"{_markdown_code(report['semantics'])}"
        ),
        "",
        "## Input Bundles",
        "",
        (
            "- Reference Bundle ID: "
            f"{_markdown_code(reference.get('report_bundle_id'))}"
        ),
        (
            "- Reference source: "
            f"{_markdown_code(reference.get('source', {}).get('file_name'))}"
        ),
        (
            "- Target Bundle ID: "
            f"{_markdown_code(target.get('report_bundle_id'))}"
        ),
        (
            "- Target source: "
            f"{_markdown_code(target.get('source', {}).get('file_name'))}"
        ),
        "",
        "## Compatibility",
        "",
        (
            "- Status: "
            f"{_markdown_code(compatibility['status'])}"
        ),
        f"- Warning count: {len(warnings)}",
        "",
        "## Topic Set",
        "",
        (
            "- Reference topic count: "
            f"{summary['reference_topic_count']}"
        ),
        (
            "- Target topic count: "
            f"{summary['target_topic_count']}"
        ),
        (
            "- Common topic count: "
            f"{summary['common_topic_count']}"
        ),
        (
            "- Reference-only topic count: "
            f"{summary['reference_only_topic_count']}"
        ),
        (
            "- Target-only topic count: "
            f"{summary['target_only_topic_count']}"
        ),
        "",
        "### Reference-only Topics",
        "",
        *_markdown_topic_list(
            topic_set["reference_only_topics"]
        ),
        "",
        "### Target-only Topics",
        "",
        *_markdown_topic_list(
            topic_set["target_only_topics"]
        ),
        "",
        "## Observed Difference Counts",
        "",
        (
            "- Changed profile topic count: "
            f"{summary['changed_profile_topic_count']}"
        ),
        (
            "- Identical profile topic count: "
            f"{summary['identical_profile_topic_count']}"
        ),
        (
            "- Changed evidence-summary topic count: "
            f"{summary['changed_evidence_summary_topic_count']}"
        ),
        (
            "- Identical evidence-summary topic count: "
            f"{summary['identical_evidence_summary_topic_count']}"
        ),
        "",
        "## Common Topic Review Points",
        "",
    ]

    topic_comparisons = report[
        "topic_comparisons"
    ]

    if not topic_comparisons:
        lines.append("No common topics were available.")
        lines.append("")
    else:
        for comparison in topic_comparisons:
            lines.append(
                f"### {_markdown_code(comparison['topic'])}"
            )
            lines.append("")

            changed_fields = comparison[
                "changed_fields"
            ]

            if changed_fields:
                lines.append("- Changed fields:")
                lines.extend(
                    f"  - {_markdown_code(field_name)}"
                    for field_name in changed_fields
                )
            else:
                lines.append(
                    "- Changed fields: None observed"
                )

            lines.append("")

    lines.extend([
        "## Judgment Boundary",
        "",
        (
            "This report does not determine root cause, "
            "fault, liability, safety, severity, normality, "
            "superiority, regression, or improvement."
        ),
        "",
    ])

    return "\n".join(lines)


def _fsync_directory(directory: Path) -> None:
    flags = os.O_RDONLY

    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY

    directory_fd = os.open(directory, flags)

    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _write_atomic_private_file(
    *,
    directory: Path,
    filename: str,
    payload: bytes,
) -> Path:
    target_path = directory / filename
    temporary_fd: int | None = None
    temporary_path: Path | None = None

    try:
        temporary_fd, temporary_name = tempfile.mkstemp(
            prefix=f".{filename}.",
            suffix=".tmp",
            dir=directory,
        )
        temporary_path = Path(temporary_name)

        os.chmod(
            temporary_path,
            COMPARISON_FILE_MODE,
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

        os.replace(
            temporary_path,
            target_path,
        )
        temporary_path = None

        return target_path
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


def _resolve_output_paths(
    export_dir: str | Path,
) -> tuple[Path, Path]:
    try:
        raw_export_dir = Path(export_dir)
    except TypeError as exc:
        raise BundleComparisonWriteError(
            "export_dir must be a filesystem path.",
            code=(
                "VELUNE_COMPARISON_"
                "OUTPUT_DIRECTORY_TYPE_INVALID"
            ),
            hint=(
                "Provide a new local output directory path."
            ),
            stage="comparison_write",
        ) from exc

    if not raw_export_dir.name:
        _raise_write_error(
            "export_dir must name a new directory.",
            code=(
                "VELUNE_COMPARISON_"
                "OUTPUT_DIRECTORY_INVALID"
            ),
            hint=(
                "Use a path such as comparison_output."
            ),
        )

    if (
        raw_export_dir.is_symlink()
        or raw_export_dir.exists()
    ):
        _raise_write_error(
            "Comparison output directory already exists.",
            code=(
                "VELUNE_COMPARISON_"
                "OUTPUT_DIRECTORY_ALREADY_EXISTS"
            ),
            hint=(
                "Use a new output directory. Comparison v1 "
                "does not overwrite existing outputs."
            ),
        )

    try:
        parent = raw_export_dir.parent.resolve(
            strict=True
        )
    except OSError as exc:
        raise BundleComparisonWriteError(
            f"Unable to resolve output parent directory: "
            f"{exc}",
            code=(
                "VELUNE_COMPARISON_"
                "OUTPUT_PARENT_UNAVAILABLE"
            ),
            hint=(
                "Create the parent directory before writing "
                "comparison outputs."
            ),
            stage="comparison_write",
        ) from exc

    if not parent.is_dir():
        _raise_write_error(
            "Comparison output parent is not a directory.",
            code=(
                "VELUNE_COMPARISON_"
                "OUTPUT_PARENT_INVALID"
            ),
            hint=(
                "Provide a path inside an existing directory."
            ),
        )

    target = parent / raw_export_dir.name

    if target.is_symlink() or target.exists():
        _raise_write_error(
            "Comparison output directory already exists.",
            code=(
                "VELUNE_COMPARISON_"
                "OUTPUT_DIRECTORY_ALREADY_EXISTS"
            ),
            hint=(
                "Use a new output directory. Comparison v1 "
                "does not overwrite existing outputs."
            ),
        )

    return parent, target


def _remove_directory(
    directory: Path | None,
) -> None:
    if directory is None:
        return

    try:
        if directory.is_symlink():
            directory.unlink()
        elif directory.exists():
            shutil.rmtree(directory)
    except OSError:
        pass


def write_bundle_comparison_outputs(
    *,
    export_dir: str | Path,
    report: Mapping[str, Any],
) -> WrittenBundleComparison:
    """Write exactly two private comparison output files.

    The JSON report is the source of truth. Markdown is rendered from that
    final in-memory JSON object. Existing output directories are never
    overwritten. Any expected write failure removes the incomplete output
    directory.
    """

    report_payload = _serialize_report(report)
    summary_payload = render_comparison_summary(
        report
    ).encode("utf-8")

    parent, target = _resolve_output_paths(
        export_dir
    )

    staging: Path | None = None
    target_created = False
    success = False

    try:
        staging = Path(tempfile.mkdtemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=parent,
        ))
        os.chmod(
            staging,
            COMPARISON_DIRECTORY_MODE,
        )

        staged_report = _write_atomic_private_file(
            directory=staging,
            filename=COMPARISON_REPORT_FILENAME,
            payload=report_payload,
        )
        staged_summary = _write_atomic_private_file(
            directory=staging,
            filename=COMPARISON_SUMMARY_FILENAME,
            payload=summary_payload,
        )

        _fsync_directory(staging)

        try:
            os.mkdir(
                target,
                COMPARISON_DIRECTORY_MODE,
            )
        except FileExistsError as exc:
            raise BundleComparisonWriteError(
                "Comparison output directory already exists.",
                code=(
                    "VELUNE_COMPARISON_"
                    "OUTPUT_DIRECTORY_ALREADY_EXISTS"
                ),
                hint=(
                    "Use a new output directory. Comparison "
                    "v1 does not overwrite existing outputs."
                ),
                stage="comparison_write",
            ) from exc

        target_created = True

        report_path = (
            target / COMPARISON_REPORT_FILENAME
        )
        summary_path = (
            target / COMPARISON_SUMMARY_FILENAME
        )

        os.replace(
            staged_report,
            report_path,
        )
        os.replace(
            staged_summary,
            summary_path,
        )

        _fsync_directory(target)

        staging.rmdir()
        staging = None

        _fsync_directory(parent)

        installed_names = sorted(
            path.name
            for path in target.iterdir()
        )
        expected_names = sorted([
            COMPARISON_REPORT_FILENAME,
            COMPARISON_SUMMARY_FILENAME,
        ])

        if installed_names != expected_names:
            _raise_write_error(
                "Comparison output directory does not "
                "contain exactly the two v1 files.",
                code=(
                    "VELUNE_COMPARISON_"
                    "OUTPUT_SET_INVALID"
                ),
                hint=(
                    "Remove the output directory and retry."
                ),
            )

        success = True

        return WrittenBundleComparison(
            output_dir=target,
            report_path=report_path,
            summary_path=summary_path,
        )

    except BundleComparisonWriteError:
        raise
    except OSError as exc:
        raise BundleComparisonWriteError(
            f"Unable to write comparison outputs: {exc}",
            code=(
                "VELUNE_COMPARISON_"
                "OUTPUT_INSTALL_FAILED"
            ),
            hint=(
                "Check parent-directory permissions and "
                "available disk space."
            ),
            stage="comparison_write",
        ) from exc
    finally:
        _remove_directory(staging)

        if not success and target_created:
            _remove_directory(target)
