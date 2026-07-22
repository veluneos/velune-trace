"""Deterministic structural digests for private MCAP provenance.

A structural digest is not a cryptographic hash of the complete source
file. It does not prove source authenticity, payload correctness, CRC
validity, or logical message integrity.
"""

import hashlib
import json
import unicodedata
from typing import Any

from velune_trace.adapters.mcap_reader import (
    McapInspectResult,
    McapTerminalMetadata,
)


SCHEMA_NAME = "velune.mcap_structural_digest"
SCHEMA_VERSION = "0.1.0"

DIGEST_ALGORITHM = "sha256"
DIGEST_PREFIX = "mcap_struct_sha256_"

CANONICALIZATION_POLICY = (
    "closed_schema_ascii_json_sorted_keys_nfc_no_floats_v1"
)


def _require_string(
    value: Any,
    field_name: str,
    *,
    optional: bool = False,
) -> str | None:
    if value is None and optional:
        return None

    if type(value) is not str:
        raise TypeError(
            f"{field_name} must be a string"
        )

    return unicodedata.normalize("NFC", value)


def _require_bool(
    value: Any,
    field_name: str,
) -> bool:
    if type(value) is not bool:
        raise TypeError(
            f"{field_name} must be a bool"
        )

    return value


def _require_int(
    value: Any,
    field_name: str,
    *,
    optional: bool = False,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int | None:
    if value is None and optional:
        return None

    # bool is deliberately rejected even though bool subclasses int.
    if type(value) is not int:
        raise TypeError(
            f"{field_name} must be an int"
        )

    if minimum is not None and value < minimum:
        raise ValueError(
            f"{field_name} must be >= {minimum}"
        )

    if maximum is not None and value > maximum:
        raise ValueError(
            f"{field_name} must be <= {maximum}"
        )

    return value


def _validate_closed_json(
    value: Any,
    path: str = "$",
) -> None:
    """Validate the closed canonical value tree.

    Boolean values are valid only because all fields entering this tree
    are constructed explicitly through declared field validators. No
    arbitrary source or extension mappings are passed through.
    """

    if value is None:
        return

    if type(value) in (bool, int, str):
        return

    if type(value) is float:
        raise TypeError(
            f"{path} must not contain float values"
        )

    if type(value) is list:
        for index, item in enumerate(value):
            _validate_closed_json(
                item,
                f"{path}[{index}]",
            )
        return

    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError(
                    f"{path} contains a non-string key"
                )

            _validate_closed_json(
                item,
                f"{path}.{key}",
            )
        return

    raise TypeError(
        f"{path} contains unsupported type "
        f"{type(value).__name__}"
    )


def _canonical_json(value: Any) -> str:
    _validate_closed_json(value)

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _normalize_topic(
    value: Any,
    index: int,
) -> dict[str, Any]:
    field_name = f"topics[{index}]"

    if type(value) is not dict:
        raise TypeError(
            f"{field_name} must be a mapping"
        )

    return {
        "channel_id": _require_int(
            value.get("channel_id"),
            f"{field_name}.channel_id",
            minimum=0,
        ),
        "topic": _require_string(
            value.get("topic"),
            f"{field_name}.topic",
        ),
        "message_encoding": _require_string(
            value.get("message_encoding"),
            f"{field_name}.message_encoding",
        ),
        "schema_id": _require_int(
            value.get("schema_id"),
            f"{field_name}.schema_id",
            minimum=0,
        ),
        "schema_name": _require_string(
            value.get("schema_name"),
            f"{field_name}.schema_name",
            optional=True,
        ),
        "schema_encoding": _require_string(
            value.get("schema_encoding"),
            f"{field_name}.schema_encoding",
            optional=True,
        ),
    }


def _build_topics(
    inspect_result: McapInspectResult,
) -> list[dict[str, Any]]:
    topics = [
        _normalize_topic(value, index)
        for index, value in enumerate(
            inspect_result.topics
        )
    ]

    # Full canonical records are used as the sort key. This remains
    # deterministic even when individual identifying fields collide.
    return sorted(
        topics,
        key=_canonical_json,
    )


def _normalize_chunk(
    value: Any,
    index: int,
) -> dict[str, Any]:
    field_name = f"chunks[{index}]"

    if type(value) is not dict:
        raise TypeError(
            f"{field_name} must be a mapping"
        )

    return {
        "chunk_id": _require_int(
            value.get("chunk_id"),
            f"{field_name}.chunk_id",
            minimum=0,
        ),
        "message_start_time_ns": _require_int(
            value.get("message_start_time_ns"),
            f"{field_name}.message_start_time_ns",
            optional=True,
            minimum=0,
        ),
        "message_end_time_ns": _require_int(
            value.get("message_end_time_ns"),
            f"{field_name}.message_end_time_ns",
            optional=True,
            minimum=0,
        ),
        "chunk_start_offset": _require_int(
            value.get("chunk_start_offset"),
            f"{field_name}.chunk_start_offset",
            optional=True,
            minimum=0,
        ),
        "chunk_length": _require_int(
            value.get("chunk_length"),
            f"{field_name}.chunk_length",
            optional=True,
            minimum=0,
        ),
        "message_index_offsets_count": _require_int(
            value.get("message_index_offsets_count"),
            f"{field_name}.message_index_offsets_count",
            minimum=0,
        ),
        "compression": _require_string(
            value.get("compression"),
            f"{field_name}.compression",
            optional=True,
        ),
        "compressed_size": _require_int(
            value.get("compressed_size"),
            f"{field_name}.compressed_size",
            optional=True,
            minimum=0,
        ),
        "uncompressed_size": _require_int(
            value.get("uncompressed_size"),
            f"{field_name}.uncompressed_size",
            optional=True,
            minimum=0,
        ),
    }


def _build_chunks(
    inspect_result: McapInspectResult,
) -> list[dict[str, Any]]:
    chunks = [
        _normalize_chunk(value, index)
        for index, value in enumerate(
            inspect_result.chunks
        )
    ]

    return sorted(
        chunks,
        key=_canonical_json,
    )


def _build_consistency_checks(
    *,
    file_size_bytes: int,
    has_summary: bool,
    summary_start: int,
    summary_offset_start: int,
    start_time_ns: int | None,
    end_time_ns: int | None,
    channel_count: int | None,
    chunk_count: int | None,
    topics: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
) -> tuple[dict[str, bool], list[str]]:
    checks: dict[str, bool] = {}
    warnings: list[str] = []

    def record(
        name: str,
        passed: bool,
        warning: str,
    ) -> None:
        checks[name] = passed

        if not passed:
            warnings.append(warning)

    record(
        "source_size_nonzero",
        file_size_bytes > 0,
        "MCAP_SOURCE_SIZE_ZERO",
    )

    record(
        "summary_start_within_file",
        (
            summary_start == 0
            or summary_start < file_size_bytes
        ),
        "MCAP_SUMMARY_START_OUT_OF_FILE_BOUNDS",
    )

    record(
        "summary_offset_start_within_file",
        (
            summary_offset_start == 0
            or summary_offset_start < file_size_bytes
        ),
        "MCAP_SUMMARY_OFFSET_OUT_OF_FILE_BOUNDS",
    )

    record(
        "summary_presence_matches_terminal_offset",
        has_summary == (summary_start != 0),
        "MCAP_SUMMARY_PRESENCE_OFFSET_MISMATCH",
    )

    summary_offset_layout_valid = (
        (
            summary_start == 0
            and summary_offset_start == 0
        )
        or (
            summary_start > 0
            and (
                summary_offset_start == 0
                or summary_offset_start >= summary_start
            )
        )
    )

    record(
        "summary_offset_layout_valid",
        summary_offset_layout_valid,
        "MCAP_SUMMARY_OFFSET_LAYOUT_INCONSISTENT",
    )

    time_range_valid = (
        start_time_ns is None
        or end_time_ns is None
        or end_time_ns >= start_time_ns
    )

    record(
        "message_time_range_valid",
        time_range_valid,
        "MCAP_MESSAGE_TIME_RANGE_INCONSISTENT",
    )

    channel_count_valid = (
        channel_count is None
        or channel_count == len(topics)
    )

    record(
        "channel_count_matches_topic_records",
        channel_count_valid,
        "MCAP_CHANNEL_COUNT_TOPIC_RECORD_MISMATCH",
    )

    chunk_count_valid = (
        chunk_count is None
        or chunk_count == len(chunks)
    )

    record(
        "chunk_count_matches_chunk_records",
        chunk_count_valid,
        "MCAP_CHUNK_COUNT_RECORD_MISMATCH",
    )

    checks["all_passed"] = all(checks.values())

    return checks, warnings


def build_mcap_structural_digest(
    *,
    inspect_result: McapInspectResult,
    terminal_metadata: McapTerminalMetadata,
) -> dict[str, Any]:
    """Build a deterministic digest from bounded MCAP observations.

    Invalid field types are rejected because they cannot be represented
    under the canonical contract. Structural inconsistencies are retained
    as degraded observations rather than aborting digest generation.
    """

    file_size_bytes = _require_int(
        inspect_result.file_size_bytes,
        "file_size_bytes",
        minimum=0,
    )
    has_summary = _require_bool(
        inspect_result.has_summary,
        "has_summary",
    )

    message_count = _require_int(
        inspect_result.message_count,
        "message_count",
        optional=True,
        minimum=0,
    )
    schema_count = _require_int(
        inspect_result.schema_count,
        "schema_count",
        optional=True,
        minimum=0,
    )
    channel_count = _require_int(
        inspect_result.channel_count,
        "channel_count",
        optional=True,
        minimum=0,
    )
    chunk_count = _require_int(
        inspect_result.chunk_count,
        "chunk_count",
        optional=True,
        minimum=0,
    )
    start_time_ns = _require_int(
        inspect_result.start_time_ns,
        "start_time_ns",
        optional=True,
        minimum=0,
    )
    end_time_ns = _require_int(
        inspect_result.end_time_ns,
        "end_time_ns",
        optional=True,
        minimum=0,
    )

    summary_start = _require_int(
        terminal_metadata.summary_start,
        "summary_start",
        minimum=0,
    )
    summary_offset_start = _require_int(
        terminal_metadata.summary_offset_start,
        "summary_offset_start",
        minimum=0,
    )
    summary_crc = _require_int(
        terminal_metadata.summary_crc,
        "summary_crc",
        minimum=0,
        maximum=0xFFFFFFFF,
    )
    data_section_crc = _require_int(
        terminal_metadata.data_section_crc,
        "data_section_crc",
        minimum=0,
        maximum=0xFFFFFFFF,
    )

    topics = _build_topics(inspect_result)
    chunks = _build_chunks(inspect_result)

    consistency, warnings = (
        _build_consistency_checks(
            file_size_bytes=file_size_bytes,
            has_summary=has_summary,
            summary_start=summary_start,
            summary_offset_start=(
                summary_offset_start
            ),
            start_time_ns=start_time_ns,
            end_time_ns=end_time_ns,
            channel_count=channel_count,
            chunk_count=chunk_count,
            topics=topics,
            chunks=chunks,
        )
    )

    compression = sorted({
        chunk["compression"]
        for chunk in chunks
        if chunk["compression"] is not None
    })

    components = {
        "format": "mcap",
        "format_generation": "MCAP0",
        "file_size_bytes": file_size_bytes,
        "summary": {
            "reported_present": has_summary,
            "summary_start": summary_start,
            "summary_offset_start": (
                summary_offset_start
            ),
        },
        "terminal_crc_fields_as_recorded": {
            "summary_crc": summary_crc,
            "data_section_crc": data_section_crc,
        },
        "statistics": {
            "message_count": message_count,
            "schema_count": schema_count,
            "channel_count": channel_count,
            "chunk_count": chunk_count,
            "start_time_ns": start_time_ns,
            "end_time_ns": end_time_ns,
        },
        "compression": compression,
        "topics": topics,
        "chunks": chunks,
    }

    canonical_text = _canonical_json(components)
    digest = hashlib.sha256(
        canonical_text.encode("ascii")
    ).hexdigest()

    status = (
        "ok"
        if consistency["all_passed"]
        else "degraded"
    )

    return {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "kind": "mcap_structural_metadata_digest",
        "status": status,
        "warnings": warnings,
        "digest_algorithm": DIGEST_ALGORITHM,
        "canonicalization": (
            CANONICALIZATION_POLICY
        ),
        "value": f"{DIGEST_PREFIX}{digest}",
        "coverage": {
            "full_source_bytes_hashed": False,
            "summary_metadata_included": True,
            "terminal_record_values_included": True,
            "topic_structure_included": True,
            "chunk_index_structure_included": True,
        },
        "integrity_semantics": {
            "summary_crc_field_nonzero": (
                summary_crc != 0
            ),
            "data_section_crc_field_nonzero": (
                data_section_crc != 0
            ),
            "crc_validation_performed": False,
            "payload_validation_performed": False,
            "logical_integrity_validation_performed": (
                False
            ),
            "source_authenticity_validation_performed": (
                False
            ),
        },
        "structural_consistency": consistency,
        "components": components,
        "limitations": [
            (
                "This value is not a cryptographic hash "
                "of the complete MCAP source bytes."
            ),
            (
                "CRC field values are included exactly as "
                "recorded but are not validated here."
            ),
            (
                "A degraded digest records structural "
                "inconsistencies without treating them as valid."
            ),
            (
                "This value does not prove source authenticity, "
                "payload correctness, or logical integrity."
            ),
        ],
    }
