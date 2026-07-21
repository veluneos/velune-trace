"""Private Baseline Evaluation JSON and Markdown outputs."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
from typing import Any

from velune_trace.private_baseline.evaluation import (
    EVALUATION_REPORT_FILENAME,
    EVALUATION_SCHEMA_NAME,
    EVALUATION_SUMMARY_FILENAME,
    HUMAN_JUDGMENT_BOUNDARY_STATEMENT,
    PrivateBaselineEvaluationError,
)
from velune_trace.private_baseline.storage import (
    _fsync_directory,
    _write_new_file_atomically,
)


PRIVATE_BASELINE_PRESENTATION_POLICY_VERSION = (
    "0.1.0"
)
MARKDOWN_REFERENCE_PREVIEW_LIMIT = 10
MARKDOWN_TOPIC_PREVIEW_LIMIT = 5
MARKDOWN_TOPIC_DETAIL_LIMIT = 20
MARKDOWN_FIELD_DETAIL_LIMIT_PER_TOPIC = 50


@dataclass(frozen=True)
class WrittenPrivateBaselineEvaluation:
    """Paths for one completed two-file Evaluation output."""

    output_dir: Path
    report_path: Path
    summary_path: Path


def _markdown_code(value: Any) -> str:
    text = str(value)

    text = (
        text.replace("\r\n", "\\n")
        .replace("\r", "\\n")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )

    safe = []

    for character in text:
        codepoint = ord(character)

        if (
            codepoint < 32
            or 0x7F <= codepoint <= 0x9F
            or 0xD800 <= codepoint <= 0xDFFF
        ):
            safe.append("�")
        else:
            safe.append(character)

    normalized = "".join(safe)

    longest_run = 0
    current_run = 0

    for character in normalized:
        if character == "`":
            current_run += 1
            longest_run = max(
                longest_run,
                current_run,
            )
        else:
            current_run = 0

    delimiter = "`" * max(
        1,
        longest_run + 1,
    )

    return (
        f"{delimiter}{normalized}{delimiter}"
    )


def render_private_baseline_evaluation_summary(
    report: Mapping[str, Any],
) -> str:
    """Render the bounded human-readable Evaluation view."""

    if not isinstance(report, Mapping):
        raise PrivateBaselineEvaluationError(
            "Evaluation report must be an object.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "SUMMARY_INPUT_INVALID"
            ),
            hint=(
                "Render the final validated Evaluation "
                "JSON document."
            ),
            stage="private_baseline_evaluation_writer",
        )

    if report.get("schema_name") != (
        EVALUATION_SCHEMA_NAME
    ):
        raise PrivateBaselineEvaluationError(
            "Evaluation report schema is invalid.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "SUMMARY_SCHEMA_INVALID"
            ),
            hint=(
                "Render a validated Private Baseline "
                "Evaluation document."
            ),
            stage="private_baseline_evaluation_writer",
        )

    aggregate = report[
        "aggregate_observations"
    ]
    aggregate_summary = aggregate["summary"]
    context = report["evaluation_context"]

    lines = [
        "# Private Baseline Target Evaluation",
        "",
        "## Evaluation",
        "",
        (
            "- Evaluation ID: "
            f"{_markdown_code(report['evaluation_id'])}"
        ),
        (
            "- Baseline ID: "
            f"{_markdown_code(report['baseline_id'])}"
        ),
        (
            "- Baseline Revision ID: "
            f"{_markdown_code(report['baseline_revision_id'])}"
        ),
        (
            "- Generated at: "
            f"{_markdown_code(report['generated_at'])}"
        ),
        (
            "- Comparison axis: "
            f"{_markdown_code(context['comparison_axis'])}"
        ),
        (
            "- Axis keys: "
            + ", ".join(
                _markdown_code(key)
                for key in context["axis_keys"]
            )
        ),
        (
            "- Target Bundle: "
            f"{_markdown_code(report['target']['report_bundle_id'])}"
        ),
        "",
        "## Descriptive Occurrence Summary",
        "",
        (
            "- Reference count: "
            f"{aggregate['reference_count']}"
        ),
        (
            "- Observed topic count: "
            f"{aggregate_summary['observed_topic_count']}"
        ),
        (
            "- Topics with changed fields: "
            f"{aggregate_summary['changed_topic_count']}"
        ),
        (
            "- Changed field records: "
            f"{aggregate_summary['changed_field_record_count']}"
        ),
        (
            "- Fields changed against every eligible Reference: "
            f"{aggregate_summary['all_references_field_count']}"
        ),
        (
            "- Fields changed against some eligible References: "
            f"{aggregate_summary['some_references_field_count']}"
        ),
        "",
        (
            "Counts describe where observed differences appeared. "
            "They are not severity, probability, regression, "
            "improvement, or normality scores."
        ),
        "",
    ]

    field_by_topic: dict[
        str,
        list[Mapping[str, Any]],
    ] = defaultdict(list)

    for observation in aggregate[
        "field_observations"
    ]:
        field_by_topic[
            observation["topic"]
        ].append(observation)

    changed_topics = sorted(field_by_topic)

    lines.extend([
        "## Changed Topic Preview",
        "",
    ])

    if not changed_topics:
        lines.append(
            "No changed field record was emitted."
        )
    else:
        for topic in changed_topics[
            :MARKDOWN_TOPIC_PREVIEW_LIMIT
        ]:
            lines.append(
                "- "
                f"{_markdown_code(topic)}: "
                f"{len(field_by_topic[topic])} "
                "changed field record(s)"
            )

        omitted_preview = (
            len(changed_topics)
            - MARKDOWN_TOPIC_PREVIEW_LIMIT
        )

        if omitted_preview > 0:
            lines.append(
                f"- {omitted_preview} additional changed "
                "topic(s) are available in the JSON "
                "source of truth."
            )

    lines.extend([
        "",
        "## Changed Field Details",
        "",
    ])

    for topic in changed_topics[
        :MARKDOWN_TOPIC_DETAIL_LIMIT
    ]:
        lines.extend([
            f"### {_markdown_code(topic)}",
            "",
        ])

        observations = sorted(
            field_by_topic[topic],
            key=lambda item: item["field"],
        )

        for observation in observations[
            :MARKDOWN_FIELD_DETAIL_LIMIT_PER_TOPIC
        ]:
            lines.append(
                "- "
                f"{_markdown_code(observation['field'])}: "
                "changed against "
                f"{observation['changed_against_reference_count']} "
                "of "
                f"{observation['eligible_reference_count']} "
                "eligible Reference(s); "
                "scope="
                f"{_markdown_code(observation['observation_scope'])}"
            )

        omitted_fields = (
            len(observations)
            - MARKDOWN_FIELD_DETAIL_LIMIT_PER_TOPIC
        )

        if omitted_fields > 0:
            lines.append(
                f"- {omitted_fields} additional field "
                "record(s) are available in "
                "`baseline_evaluation_report.json`."
            )

        lines.append("")

    omitted_topics = (
        len(changed_topics)
        - MARKDOWN_TOPIC_DETAIL_LIMIT
    )

    if omitted_topics > 0:
        lines.extend([
            (
                f"{omitted_topics} additional changed topic(s) "
                "are omitted from detailed Markdown."
            ),
            "",
        ])

    topic_set_differences = [
        item
        for item in aggregate[
            "topic_set_observations"
        ]
        if (
            item[
                "target_only_against_reference_count"
            ]
            or item[
                "reference_only_against_target_count"
            ]
        )
    ]

    lines.extend([
        "## Topic-Set Occurrence",
        "",
    ])

    if not topic_set_differences:
        lines.append(
            "No Reference-only or Target-only topic "
            "occurrence was observed."
        )
    else:
        for item in topic_set_differences[
            :MARKDOWN_TOPIC_DETAIL_LIMIT
        ]:
            lines.append(
                "- "
                f"{_markdown_code(item['topic'])}: "
                "common="
                f"{item['common_with_target_count']}, "
                "target_only="
                f"{item['target_only_against_reference_count']}, "
                "reference_only="
                f"{item['reference_only_against_target_count']}, "
                "absent_from_both="
                f"{item['absent_from_both_count']}"
            )

        omitted_topic_sets = (
            len(topic_set_differences)
            - MARKDOWN_TOPIC_DETAIL_LIMIT
        )

        if omitted_topic_sets > 0:
            lines.append(
                f"- {omitted_topic_sets} additional "
                "topic-set record(s) are available in "
                "`baseline_evaluation_report.json`."
            )

    reference_comparisons = report[
        "reference_comparisons"
    ]

    lines.extend([
        "",
        "## Reference Comparisons",
        "",
    ])

    for item in reference_comparisons[
        :MARKDOWN_REFERENCE_PREVIEW_LIMIT
    ]:
        comparison_summary = item[
            "comparison_report"
        ].get("summary", {})

        lines.append(
            "- "
            f"{_markdown_code(item['reference_report_bundle_id'])}: "
            "changed_profile_topics="
            f"{comparison_summary.get('changed_profile_topic_count', 'n/a')}, "
            "changed_evidence_summary_topics="
            f"{comparison_summary.get('changed_evidence_summary_topic_count', 'n/a')}"
        )

    omitted_references = (
        len(reference_comparisons)
        - MARKDOWN_REFERENCE_PREVIEW_LIMIT
    )

    if omitted_references > 0:
        lines.append(
            f"- {omitted_references} additional Reference "
            "comparison(s) are available in the JSON "
            "source of truth."
        )

    lines.extend([
        "",
        "## Presentation Policy",
        "",
        (
            "- Policy version: "
            f"{_markdown_code(PRIVATE_BASELINE_PRESENTATION_POLICY_VERSION)}"
        ),
        (
            "- Ordering is lexicographic and does not "
            "represent importance, severity, similarity, "
            "or priority."
        ),
        (
            "- Complete pairwise Comparison v1 reports and "
            "all aggregate records remain in "
            "`baseline_evaluation_report.json`."
        ),
        "",
        "## Human Judgment Boundary",
        "",
        f"> {HUMAN_JUDGMENT_BOUNDARY_STATEMENT}",
        "",
    ])

    return "\n".join(lines)


def _serialize_report(
    report: Mapping[str, Any],
) -> bytes:
    try:
        rendered = json.dumps(
            report,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
        )
    except (
        TypeError,
        ValueError,
        UnicodeEncodeError,
        RecursionError,
    ) as exc:
        raise PrivateBaselineEvaluationError(
            "Evaluation report cannot be serialized as "
            "strict deterministic JSON.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "JSON_SERIALIZATION_FAILED"
            ),
            hint=(
                "Use the validated Evaluation document."
            ),
            stage="private_baseline_evaluation_writer",
        ) from exc

    return f"{rendered}\n".encode(
        "utf-8",
        errors="strict",
    )


def write_private_baseline_evaluation_outputs(
    *,
    export_dir: str | Path,
    report: Mapping[str, Any],
) -> WrittenPrivateBaselineEvaluation:
    """Install exactly one JSON source and one derived Markdown file."""

    raw_export_dir = Path(export_dir)

    if raw_export_dir.is_symlink():
        raise PrivateBaselineEvaluationError(
            "Evaluation export directory must not be a "
            "symbolic link.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "EXPORT_SYMLINK_FORBIDDEN"
            ),
            hint=(
                "Use a new real local directory."
            ),
            stage="private_baseline_evaluation_writer",
        )

    if raw_export_dir.exists():
        raise PrivateBaselineEvaluationError(
            "Evaluation export directory already exists.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "EXPORT_ALREADY_EXISTS"
            ),
            hint=(
                "Use a new output directory. Existing "
                "Evaluation outputs are not overwritten."
            ),
            stage="private_baseline_evaluation_writer",
        )

    try:
        parent_dir = raw_export_dir.parent.resolve(
            strict=True
        )
    except OSError as exc:
        raise PrivateBaselineEvaluationError(
            "Evaluation export parent is unavailable.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "EXPORT_PARENT_UNAVAILABLE"
            ),
            hint=(
                "Create the local parent directory first."
            ),
            stage="private_baseline_evaluation_writer",
        ) from exc

    if not parent_dir.is_dir():
        raise PrivateBaselineEvaluationError(
            "Evaluation export parent is not a directory.",
            code=(
                "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                "EXPORT_PARENT_INVALID"
            ),
            hint=(
                "Use an existing local parent directory."
            ),
            stage="private_baseline_evaluation_writer",
        )

    output_dir = (
        parent_dir / raw_export_dir.name
    )

    report_payload = _serialize_report(
        report
    )
    summary_payload = (
        render_private_baseline_evaluation_summary(
            report
        )
        + "\n"
    ).encode(
        "utf-8",
        errors="strict",
    )

    claimed = False

    try:
        output_dir.mkdir(
            mode=0o700,
            exist_ok=False,
        )
        claimed = True

        report_path = (
            output_dir
            / EVALUATION_REPORT_FILENAME
        )
        summary_path = (
            output_dir
            / EVALUATION_SUMMARY_FILENAME
        )

        _write_new_file_atomically(
            report_path,
            report_payload,
        )
        _write_new_file_atomically(
            summary_path,
            summary_payload,
        )

        _fsync_directory(output_dir)
        _fsync_directory(parent_dir)

        observed_names = {
            path.name
            for path in output_dir.iterdir()
        }

        expected_names = {
            EVALUATION_REPORT_FILENAME,
            EVALUATION_SUMMARY_FILENAME,
        }

        if observed_names != expected_names:
            raise PrivateBaselineEvaluationError(
                "Evaluation output set is incomplete.",
                code=(
                    "VELUNE_PRIVATE_BASELINE_EVALUATION_"
                    "OUTPUT_SET_INVALID"
                ),
                hint=(
                    "Retain exactly the JSON source of truth "
                    "and derived Markdown summary."
                ),
                stage=(
                    "private_baseline_evaluation_writer"
                ),
            )

        return WrittenPrivateBaselineEvaluation(
            output_dir=output_dir,
            report_path=report_path,
            summary_path=summary_path,
        )

    except BaseException:
        if claimed:
            try:
                shutil.rmtree(output_dir)
                _fsync_directory(parent_dir)
            except OSError:
                pass

        raise
