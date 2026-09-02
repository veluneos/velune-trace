#!/usr/bin/env python3
"""Build a size-targeted MCAP benchmark corpus.

This tool cycles through real source MCAP scenes, preserves encoded
message payloads without decoding them, remaps schemas and channels,
and shifts each segment into a non-overlapping logical time range.

The resulting corpus is replicated real-payload benchmark data.
It must not be described as unique continuous driving data.
"""

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcap.reader import (
    NonSeekingReader,
    make_reader,
)
from mcap.writer import (
    CompressionType,
    IndexType,
    Writer,
)


UINT64_MAX = (1 << 64) - 1
TOOL_LIBRARY = (
    "velune-build-mcap-benchmark-corpus/0.1.0"
)
CORPUS_KIND = "replicated_real_payload"
DEFAULT_GAP_NS = 1_000_000_000


@dataclass(frozen=True)
class SourceDescriptor:
    path: Path
    profile: str
    source_library: str
    summary: Any
    start_time_ns: int
    end_time_ns: int
    message_count: int
    contract_digest: str
    metadata_records: tuple[
        tuple[str, dict[str, str]],
        ...,
    ]


def checked_timestamp(
    value: int,
    offset_ns: int,
    field_name: str,
) -> int:
    shifted = value + offset_ns

    if not 0 <= shifted <= UINT64_MAX:
        raise ValueError(
            f"{field_name} is outside uint64 range "
            f"after offset: {shifted}"
        )

    return shifted


def schema_key(schema: Any) -> tuple[str, str, bytes]:
    return (
        schema.name,
        schema.encoding,
        schema.data,
    )


def channel_key(
    channel: Any,
    schemas: dict[int, Any],
) -> tuple[Any, ...]:
    source_schema = (
        None
        if channel.schema_id == 0
        else schemas[channel.schema_id]
    )

    return (
        channel.topic,
        channel.message_encoding,
        (
            None
            if source_schema is None
            else schema_key(source_schema)
        ),
        tuple(sorted(channel.metadata.items())),
    )


def contract_digest(summary: Any) -> str:
    schema_descriptions = {
        schema_id: {
            "name": schema.name,
            "encoding": schema.encoding,
            "data_sha256": hashlib.sha256(
                schema.data
            ).hexdigest(),
        }
        for schema_id, schema
        in summary.schemas.items()
    }

    channels = []

    for channel in summary.channels.values():
        channels.append({
            "topic": channel.topic,
            "message_encoding": (
                channel.message_encoding
            ),
            "schema": (
                None
                if channel.schema_id == 0
                else schema_descriptions[
                    channel.schema_id
                ]
            ),
            "metadata": dict(
                sorted(channel.metadata.items())
            ),
        })

    channels.sort(
        key=lambda item: json.dumps(
            item,
            sort_keys=True,
            separators=(",", ":"),
        )
    )

    canonical = json.dumps(
        channels,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")

    return hashlib.sha256(canonical).hexdigest()


def inspect_source(path: Path) -> SourceDescriptor:
    if not path.is_file():
        raise FileNotFoundError(
            f"source MCAP not found: {path}"
        )

    with path.open("rb") as stream:
        reader = make_reader(stream)
        header = reader.get_header()
        summary = reader.get_summary()

        if summary is None:
            raise ValueError(
                f"source has no readable summary: {path}"
            )

        if summary.statistics is None:
            raise ValueError(
                f"source has no statistics: {path}"
            )

        if summary.attachment_indexes:
            raise ValueError(
                "attachment preservation is not supported: "
                f"{path}"
            )

        metadata_records = tuple(
            (
                record.name,
                dict(record.metadata),
            )
            for record in reader.iter_metadata()
        )

    statistics = summary.statistics

    return SourceDescriptor(
        path=path,
        profile=header.profile,
        source_library=header.library,
        summary=summary,
        start_time_ns=int(
            statistics.message_start_time
        ),
        end_time_ns=int(
            statistics.message_end_time
        ),
        message_count=int(
            statistics.message_count
        ),
        contract_digest=contract_digest(summary),
        metadata_records=metadata_records,
    )


def build_output_contract(
    *,
    writer: Writer,
    reference: SourceDescriptor,
) -> tuple[
    dict[tuple[str, str, bytes], int],
    dict[tuple[Any, ...], int],
]:
    output_schema_ids = {}

    for _, schema in sorted(
        reference.summary.schemas.items()
    ):
        key = schema_key(schema)

        if key not in output_schema_ids:
            output_schema_ids[key] = (
                writer.register_schema(
                    name=schema.name,
                    encoding=schema.encoding,
                    data=schema.data,
                )
            )

    output_channel_ids = {}

    for _, channel in sorted(
        reference.summary.channels.items()
    ):
        key = channel_key(
            channel,
            reference.summary.schemas,
        )

        source_schema = (
            None
            if channel.schema_id == 0
            else reference.summary.schemas[
                channel.schema_id
            ]
        )

        output_schema_id = (
            0
            if source_schema is None
            else output_schema_ids[
                schema_key(source_schema)
            ]
        )

        output_channel_ids[key] = (
            writer.register_channel(
                topic=channel.topic,
                message_encoding=(
                    channel.message_encoding
                ),
                schema_id=output_schema_id,
                metadata=dict(channel.metadata),
            )
        )

    return (
        output_schema_ids,
        output_channel_ids,
    )


def build_source_channel_map(
    *,
    source: SourceDescriptor,
    output_channel_ids: dict[
        tuple[Any, ...],
        int,
    ],
) -> dict[int, int]:
    mapping = {}

    for source_channel_id, channel in (
        source.summary.channels.items()
    ):
        key = channel_key(
            channel,
            source.summary.schemas,
        )

        if key not in output_channel_ids:
            raise ValueError(
                "source channel contract is not present "
                f"in the output contract: {source.path}"
            )

        mapping[source_channel_id] = (
            output_channel_ids[key]
        )

    return mapping


def build_corpus(
    *,
    source_paths: list[Path],
    output_path: Path,
    target_size_bytes: int,
    segment_gap_ns: int,
    overwrite: bool,
) -> dict[str, int]:
    if not source_paths:
        raise ValueError(
            "at least one source MCAP is required"
        )

    if target_size_bytes <= 0:
        raise ValueError(
            "target_size_bytes must be positive"
        )

    if segment_gap_ns < 0:
        raise ValueError(
            "segment_gap_ns must be non-negative"
        )

    sources = [
        inspect_source(path)
        for path in source_paths
    ]

    reference_digest = sources[0].contract_digest

    for source in sources[1:]:
        if source.contract_digest != reference_digest:
            raise ValueError(
                "source MCAP contracts are inconsistent: "
                f"{source.path}"
            )

    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"output already exists: {output_path}"
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    partial_path = output_path.with_name(
        output_path.name + ".partial"
    )
    partial_path.unlink(missing_ok=True)

    segment_count = 0
    total_messages = 0
    total_file_order_regressions = 0
    previous_segment_end_ns = None

    try:
        with partial_path.open("wb") as output_stream:
            writer = Writer(
                output_stream,
                chunk_size=1_048_576,
                compression=CompressionType.ZSTD,
                index_types=IndexType.ALL,
                repeat_channels=True,
                repeat_schemas=True,
                use_chunking=True,
                use_statistics=True,
                use_summary_offsets=True,
                enable_crcs=True,
                enable_data_crcs=False,
            )

            writer.start(
                profile=sources[0].profile,
                library=TOOL_LIBRARY,
            )

            _, output_channel_ids = (
                build_output_contract(
                    writer=writer,
                    reference=sources[0],
                )
            )

            writer.add_metadata(
                name="velune-benchmark-corpus",
                data={
                    "corpus_kind": CORPUS_KIND,
                    "target_size_bytes": str(
                        target_size_bytes
                    ),
                    "source_count": str(
                        len(sources)
                    ),
                    "source_files_json": json.dumps(
                        [
                            source.path.name
                            for source in sources
                        ],
                        separators=(",", ":"),
                    ),
                    "contract_sha256": (
                        reference_digest
                    ),
                    "segment_gap_ns": str(
                        segment_gap_ns
                    ),
                    "unique_continuous_drive": "false",
                },
            )

            while output_stream.tell() < target_size_bytes:
                source_index = (
                    segment_count % len(sources)
                )
                pass_index = (
                    segment_count // len(sources)
                )
                source = sources[source_index]

                if previous_segment_end_ns is None:
                    output_segment_start_ns = (
                        source.start_time_ns
                    )
                else:
                    output_segment_start_ns = (
                        previous_segment_end_ns
                        + segment_gap_ns
                    )

                offset_ns = (
                    output_segment_start_ns
                    - source.start_time_ns
                )
                output_segment_end_ns = (
                    source.end_time_ns
                    + offset_ns
                )

                checked_timestamp(
                    source.start_time_ns,
                    offset_ns,
                    "segment_start_time",
                )
                checked_timestamp(
                    source.end_time_ns,
                    offset_ns,
                    "segment_end_time",
                )

                channel_id_map = (
                    build_source_channel_map(
                        source=source,
                        output_channel_ids=(
                            output_channel_ids
                        ),
                    )
                )

                original_metadata_json = json.dumps(
                    [
                        {
                            "name": name,
                            "data": data,
                        }
                        for name, data
                        in source.metadata_records
                    ],
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                )

                writer.add_metadata(
                    name=(
                        "velune-corpus-segment-"
                        f"{segment_count:06d}"
                    ),
                    data={
                        "segment_index": str(
                            segment_count
                        ),
                        "pass_index": str(pass_index),
                        "source_index": str(
                            source_index
                        ),
                        "source_file": source.path.name,
                        "source_library": (
                            source.source_library
                        ),
                        "source_start_time_ns": str(
                            source.start_time_ns
                        ),
                        "source_end_time_ns": str(
                            source.end_time_ns
                        ),
                        "output_start_time_ns": str(
                            output_segment_start_ns
                        ),
                        "output_end_time_ns": str(
                            output_segment_end_ns
                        ),
                        "time_offset_ns": str(
                            offset_ns
                        ),
                        "source_message_count": str(
                            source.message_count
                        ),
                        "source_metadata_json": (
                            original_metadata_json
                        ),
                    },
                )

                segment_messages = 0
                source_last_log_time = None
                segment_file_order_regressions = 0

                with source.path.open(
                    "rb"
                ) as message_stream:
                    message_reader = NonSeekingReader(
                        message_stream
                    )

                    for _, channel, message in (
                        message_reader.iter_messages(
                            log_time_order=False
                        )
                    ):
                        if (
                            source_last_log_time
                            is not None
                            and message.log_time
                            < source_last_log_time
                        ):
                            segment_file_order_regressions += 1

                        writer.add_message(
                            channel_id=channel_id_map[
                                channel.id
                            ],
                            log_time=checked_timestamp(
                                message.log_time,
                                offset_ns,
                                "log_time",
                            ),
                            publish_time=(
                                checked_timestamp(
                                    message.publish_time,
                                    offset_ns,
                                    "publish_time",
                                )
                            ),
                            sequence=message.sequence,
                            data=message.data,
                        )

                        source_last_log_time = (
                            message.log_time
                        )
                        segment_messages += 1

                if (
                    segment_messages
                    != source.message_count
                ):
                    raise ValueError(
                        "source message count changed "
                        f"during streaming: {source.path}"
                    )

                segment_count += 1
                total_messages += segment_messages
                total_file_order_regressions += (
                    segment_file_order_regressions
                )
                previous_segment_end_ns = (
                    output_segment_end_ns
                )

                print(
                    "SEGMENT_WRITTEN "
                    f"index={segment_count - 1} "
                    f"source={source.path.name} "
                    f"messages={segment_messages} "
                    f"file_order_regressions="
                    f"{segment_file_order_regressions} "
                    f"bytes_flushed={output_stream.tell()}"
                )

            writer.add_metadata(
                name=(
                    "velune-benchmark-corpus-"
                    "build-summary"
                ),
                data={
                    "segment_count": str(
                        segment_count
                    ),
                    "total_messages": str(
                        total_messages
                    ),
                    "source_file_order_regressions": str(
                        total_file_order_regressions
                    ),
                    (
                        "logical_segment_ranges_"
                        "non_overlapping"
                    ): "true",
                    "physical_record_order_preserved": (
                        "true"
                    ),
                },
            )

            writer.finish()
            output_stream.flush()
            os.fsync(output_stream.fileno())

        os.replace(
            partial_path,
            output_path,
        )

    except Exception:
        partial_path.unlink(missing_ok=True)
        raise

    return {
        "segment_count": segment_count,
        "total_messages": total_messages,
        "source_file_order_regressions": (
            total_file_order_regressions
        ),
        "final_size_bytes": (
            output_path.stat().st_size
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "sources",
        nargs="+",
        type=Path,
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--target-size-bytes",
        required=True,
        type=int,
    )
    parser.add_argument(
        "--segment-gap-ns",
        type=int,
        default=DEFAULT_GAP_NS,
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
    )
    args = parser.parse_args()

    result = build_corpus(
        source_paths=[
            path.expanduser()
            for path in args.sources
        ],
        output_path=args.output.expanduser(),
        target_size_bytes=args.target_size_bytes,
        segment_gap_ns=args.segment_gap_ns,
        overwrite=args.overwrite,
    )

    print("MCAP_BENCHMARK_CORPUS_BUILD=PASS")
    print(f"CORPUS_KIND={CORPUS_KIND}")
    print(
        "UNIQUE_CONTINUOUS_DRIVE=false"
    )
    print(
        f"SEGMENT_COUNT="
        f"{result['segment_count']}"
    )
    print(
        f"TOTAL_MESSAGES="
        f"{result['total_messages']}"
    )
    print(
        "SOURCE_FILE_ORDER_REGRESSIONS="
        f"{result['source_file_order_regressions']}"
    )
    print(
        f"FINAL_SIZE_BYTES="
        f"{result['final_size_bytes']}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
