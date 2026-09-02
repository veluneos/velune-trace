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
import io
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from mcap.reader import make_reader
from mcap.exceptions import McapError
from mcap.records import DataEnd, Footer
from mcap.stream_reader import StreamReader


# Velune Trace currently supports the MCAP0 terminal layout.
# These constants describe the versioned binary record layout,
# not private size constants from the Python library.
_MCAP0_MAGIC = b"\x89MCAP0\r\n"
_MCAP_RECORD_HEADER_SIZE = 1 + 8
_MCAP_FOOTER_PAYLOAD_SIZE = 8 + 8 + 4
_MCAP_FOOTER_RECORD_SIZE = (
    _MCAP_RECORD_HEADER_SIZE
    + _MCAP_FOOTER_PAYLOAD_SIZE
)
_MCAP_DATA_END_PAYLOAD_SIZE = 4
_MCAP_DATA_END_RECORD_SIZE = (
    _MCAP_RECORD_HEADER_SIZE
    + _MCAP_DATA_END_PAYLOAD_SIZE
)


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


@dataclass(frozen=True)
class McapTerminalMetadata:
    """Values recorded in terminal MCAP records.

    Recorded CRC values do not prove source authenticity,
    payload correctness, or logical message integrity.
    """

    summary_start: int
    summary_offset_start: int
    summary_crc: int
    data_section_crc: int

    @property
    def summary_crc_recorded(self) -> bool:
        return self.summary_crc != 0

    @property
    def data_section_crc_recorded(self) -> bool:
        return self.data_section_crc != 0


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


    def inspect_terminal_metadata(
        self,
    ) -> McapTerminalMetadata:
        """Read recorded Footer and DataEnd values with bounded seeks.

        This requires a seekable file interface and is optimized for
        local files. NFS, SMB, and other network-mounted files may work,
        but their latency and failure behavior are not yet benchmarked.

        This method reads CRC fields recorded by the MCAP writer. It
        does not validate those CRCs, inspect payload correctness,
        establish source authenticity, or prove logical integrity.
        """

        if not self.path.exists():
            raise VeluneFileNotFoundError(
                f"File not found: {self.path}"
            )

        if not self.path.is_file():
            raise VeluneInvalidMcapError(
                f"Path is not a file: {self.path}"
            )

        try:
            with self.path.open("rb") as stream:
                if not stream.seekable():
                    raise McapError(
                        "terminal metadata inspection requires "
                        "a seekable file"
                    )

                stream.seek(0, io.SEEK_END)
                file_size = stream.tell()

                minimum_size = (
                    len(_MCAP0_MAGIC)
                    + _MCAP_DATA_END_RECORD_SIZE
                    + _MCAP_FOOTER_RECORD_SIZE
                    + len(_MCAP0_MAGIC)
                )

                if file_size < minimum_size:
                    raise McapError(
                        "file is too small to contain terminal "
                        "MCAP0 records"
                    )

                stream.seek(
                    -len(_MCAP0_MAGIC),
                    io.SEEK_END,
                )
                trailing_magic = stream.read(
                    len(_MCAP0_MAGIC)
                )

                if trailing_magic != _MCAP0_MAGIC:
                    raise McapError(
                        "invalid or unsupported trailing "
                        "MCAP0 magic"
                    )

                footer_offset = (
                    file_size
                    - len(_MCAP0_MAGIC)
                    - _MCAP_FOOTER_RECORD_SIZE
                )
                stream.seek(footer_offset, io.SEEK_SET)

                footer = next(
                    StreamReader(
                        stream,
                        skip_magic=True,
                    ).records
                )

                if not isinstance(footer, Footer):
                    raise McapError(
                        "expected Footer at the end of the "
                        f"MCAP file, found "
                        f"{type(footer).__name__}"
                    )

                if footer.summary_start > 0:
                    data_end_offset = (
                        footer.summary_start
                        - _MCAP_DATA_END_RECORD_SIZE
                    )
                else:
                    data_end_offset = (
                        footer_offset
                        - _MCAP_DATA_END_RECORD_SIZE
                    )

                maximum_data_end_offset = (
                    footer_offset
                    - _MCAP_DATA_END_RECORD_SIZE
                )

                if not (
                    len(_MCAP0_MAGIC)
                    <= data_end_offset
                    <= maximum_data_end_offset
                ):
                    raise McapError(
                        "invalid DataEnd offset derived from "
                        "terminal MCAP0 records"
                    )

                stream.seek(data_end_offset, io.SEEK_SET)

                data_end = next(
                    StreamReader(
                        stream,
                        skip_magic=True,
                    ).records
                )

                if not isinstance(data_end, DataEnd):
                    raise McapError(
                        "expected DataEnd before the MCAP "
                        f"summary, found "
                        f"{type(data_end).__name__}"
                    )

        except McapError as exc:
            raise VeluneInvalidMcapError(
                f"MCAP terminal record parse error: {exc}"
            ) from exc
        except StopIteration as exc:
            raise VeluneInvalidMcapError(
                "MCAP terminal record is missing or incomplete"
            ) from exc
        except (OSError, ValueError) as exc:
            raise VeluneInvalidMcapError(
                f"File seek/read error: {exc}"
            ) from exc

        return McapTerminalMetadata(
            summary_start=int(footer.summary_start),
            summary_offset_start=int(
                footer.summary_offset_start
            ),
            summary_crc=int(footer.summary_crc),
            data_section_crc=int(
                data_end.data_section_crc
            ),
        )
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

def read_messages(path):
    """
    Streaming MCAP message reader used by validation-report.

    Yields:
      {
        "topic": str,
        "log_time": int,
        "publish_time": int,
        "channel_id": int,
        "schema_id": int | None,
      }

    Payload bytes are intentionally not returned.
    """
    from pathlib import Path
    from mcap.reader import make_reader

    p = Path(path)

    with p.open("rb") as f:
        reader = make_reader(f)

        for schema, channel, message in reader.iter_messages():
            yield {
                "topic": channel.topic,
                "log_time": int(message.log_time),
                "publish_time": int(message.publish_time),
                "channel_id": int(message.channel_id),
                "schema_id": int(channel.schema_id) if channel.schema_id is not None else None,
            }
