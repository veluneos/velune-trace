#!/usr/bin/env python3

"""
Velune Trace MCAP Reader

Purpose:
  Data Access Layer for reading MCAP metadata.

This module does NOT:
  - infer causality
  - assign liability
  - calculate fault score
  - reconstruct incident timelines

It only reads observable MCAP metadata.
"""

import time
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from mcap.reader import make_reader
from mcap.exceptions import McapError


class VeluneError(Exception):
    """Base Velune error."""


class VeluneFileNotFoundError(VeluneError):
    """Input file does not exist."""


class VeluneInvalidMcapError(VeluneError):
    """Input file cannot be inspected as MCAP."""


@dataclass
class McapInspectResult:
    path: str
    file_size_bytes: int
    metadata_load_time_sec: float
    message_count: int | None
    schema_count: int | None
    channel_count: int | None
    chunk_count: int | None
    start_time_ns: int | None
    end_time_ns: int | None
    topics: list[dict[str, Any]]
    chunks: list[dict[str, Any]]
    has_summary: bool


class VeluneMcapReader:
    """
    MCAP metadata reader.

    This is intentionally separated from CLI/reporting code so that
    Timeline Builder and future FORENSIC Engine can reuse the same
    data access layer.
    """

    def __init__(self, path: str, validate_crcs: bool = False):
        self.path = Path(path)
        self.validate_crcs = validate_crcs

    def inspect(self) -> McapInspectResult:
        if not self.path.exists():
            raise VeluneFileNotFoundError(f"File not found: {self.path}")

        if not self.path.is_file():
            raise VeluneInvalidMcapError(f"Path is not a file: {self.path}")

        file_size = self.path.stat().st_size

        try:
            start = time.perf_counter()

            with self.path.open("rb") as f:
                reader = make_reader(f, validate_crcs=self.validate_crcs)
                summary = reader.get_summary()

            elapsed = time.perf_counter() - start

        except McapError as e:
            raise VeluneInvalidMcapError(f"MCAP parse error: {e}") from e
        except OSError as e:
            raise VeluneInvalidMcapError(f"File read error: {e}") from e
        except Exception as e:
            raise VeluneInvalidMcapError(
                f"Unexpected MCAP inspection error: {type(e).__name__}: {e}"
            ) from e

        if summary is None:
            return McapInspectResult(
                path=str(self.path),
                file_size_bytes=file_size,
                metadata_load_time_sec=elapsed,
                message_count=None,
                schema_count=None,
                channel_count=None,
                chunk_count=None,
                start_time_ns=None,
                end_time_ns=None,
                topics=[],
                chunks=[],
                has_summary=False,
            )

        stats = summary.statistics

        topics = []
        for channel_id, channel in sorted(summary.channels.items()):
            schema = summary.schemas.get(channel.schema_id)

            topics.append(
                {
                    "channel_id": channel_id,
                    "topic": channel.topic,
                    "message_encoding": channel.message_encoding,
                    "schema_id": channel.schema_id,
                    "schema_name": schema.name if schema else None,
                    "schema_encoding": schema.encoding if schema else None,
                }
            )

        chunks = []
        for idx, chunk in enumerate(summary.chunk_indexes):
            chunks.append(
                {
                    "chunk_id": idx,
                    "message_start_time_ns": getattr(chunk, "message_start_time", None),
                    "message_end_time_ns": getattr(chunk, "message_end_time", None),
                    "chunk_start_offset": getattr(chunk, "chunk_start_offset", None),
                    "chunk_length": getattr(chunk, "chunk_length", None),
                    "message_index_offsets_count": len(
                        getattr(chunk, "message_index_offsets", {}) or {}
                    ),
                    "compression": getattr(chunk, "compression", None),
                    "compressed_size": getattr(chunk, "compressed_size", None),
                    "uncompressed_size": getattr(chunk, "uncompressed_size", None),
                }
            )

        return McapInspectResult(
            path=str(self.path),
            file_size_bytes=file_size,
            metadata_load_time_sec=elapsed,
            message_count=stats.message_count if stats else None,
            schema_count=stats.schema_count if stats else len(summary.schemas),
            channel_count=stats.channel_count if stats else len(summary.channels),
            chunk_count=stats.chunk_count if stats else len(summary.chunk_indexes),
            start_time_ns=stats.message_start_time if stats else None,
            end_time_ns=stats.message_end_time if stats else None,
            topics=topics,
            chunks=chunks,
            has_summary=True,
        )
