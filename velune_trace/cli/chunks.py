#!/usr/bin/env python3

"""
Velune Trace Chunks CLI

Purpose:
  Show MCAP chunk index information.

Development:
  python -m velune_trace.cli.main chunks <file.mcap>

Local:
  ./bin/velune chunks <file.mcap>
"""

import sys

from velune_trace.adapters.mcap_reader import (
    VeluneMcapReader,
    VeluneError,
    McapInspectResult,
)
from velune_trace.utils.formatter import ns_to_sec


class ChunksReporter:
    @staticmethod
    def print(result: McapInspectResult) -> None:
        print()
        print("=== VELUNE CHUNKS ===")
        print()
        print(f"File               : {result.path}")
        print(f"Chunks             : {result.chunk_count}")
        print(f"Metadata Load Time : {result.metadata_load_time_sec:.6f} sec")

        if not result.has_summary:
            print()
            print("[WARN] MCAP summary section not found.")
            print("[WARN] Chunk index inspection is unavailable.")
            return

        if not result.chunks:
            print()
            print("[WARN] No chunk indexes found.")
            return

        print()
        print("chunk_id | start_sec          | end_sec            | offset    | length    | indexes")
        print("---------|--------------------|--------------------|-----------|-----------|--------")

        for chunk in result.chunks:
            chunk_id = chunk["chunk_id"]
            start_sec = ns_to_sec(chunk["message_start_time_ns"])
            end_sec = ns_to_sec(chunk["message_end_time_ns"])
            offset = chunk["chunk_start_offset"]
            length = chunk["chunk_length"]
            indexes = chunk["message_index_offsets_count"]

            print(
                f"{chunk_id:<8} | "
                f"{start_sec:<18} | "
                f"{end_sec:<18} | "
                f"{offset:<9} | "
                f"{length:<9} | "
                f"{indexes}"
            )


def main() -> int:
    if len(sys.argv) < 2:
        print("[ERROR] Usage: velune chunks <file.mcap>")
        return 2

    filename = sys.argv[1]

    try:
        reader = VeluneMcapReader(filename, validate_crcs=False)
        result = reader.inspect()
        ChunksReporter.print(result)
        return 0

    except VeluneError as e:
        print()
        print("=== VELUNE CHUNKS ERROR ===")
        print()
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
