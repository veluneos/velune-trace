#!/usr/bin/env python3

"""
Velune Trace Inspect CLI

Development usage:
  python -m velune_trace.cli.inspect <file.mcap>

Important:
  Run this command from the project root:
    ~/veluneos

Future target:
  velune inspect <file.mcap>

TODO:
  Replace direct print output with structured logging when CLI modes
  and debug verbosity levels are introduced.
"""

import sys

from velune_trace.utils.formatter import ns_to_sec
from velune_trace.adapters.mcap_reader import (
    VeluneMcapReader,
    VeluneError,
    McapInspectResult,
)


class InspectReporter:
    @staticmethod
    def print(result: McapInspectResult) -> None:
        print()
        print("=== VELUNE INSPECT ===")
        print()
        print(f"File                  : {result.path}")
        print(f"File Size             : {result.file_size_bytes:,} bytes")
        print(f"Metadata Load Time    : {result.metadata_load_time_sec:.6f} sec")
        print(f"Has Summary           : {result.has_summary}")

        if not result.has_summary:
            print()
            print("[WARN] MCAP summary section not found.")
            print("[WARN] Fast metadata inspection is limited.")
            return

        print()
        print("=== SUMMARY ===")
        print()
        print(f"Messages              : {result.message_count}")
        print(f"Schemas               : {result.schema_count}")
        print(f"Channels              : {result.channel_count}")
        print(f"Chunks                : {result.chunk_count}")
        print(f"Start Time (ns)       : {result.start_time_ns}")
        print(f"End Time (ns)         : {result.end_time_ns}")
        print(f"Start Time (sec)      : {ns_to_sec(result.start_time_ns)}")
        print(f"End Time (sec)        : {ns_to_sec(result.end_time_ns)}")

        print()
        print("=== TOPICS ===")
        print()

        for topic in result.topics:
            print(
                f"[channel_id={topic['channel_id']}] "
                f"{topic['topic']} | "
                f"encoding={topic['message_encoding']} | "
                f"schema={topic['schema_name']} | "
                f"schema_encoding={topic['schema_encoding']}"
            )

        print()
        print("=== CHUNKS ===")
        print()

        if not result.chunks:
            print("[WARN] No chunk indexes found.")
            return

        for chunk in result.chunks[:20]:
            print(
                f"[chunk_id={chunk['chunk_id']}] "
                f"start_ns={chunk['message_start_time_ns']} "
                f"end_ns={chunk['message_end_time_ns']} "
                f"offset={chunk['chunk_start_offset']} "
                f"length={chunk['chunk_length']} "
                f"indexes={chunk['message_index_offsets_count']} "
                f"compression={chunk['compression']} "
                f"compressed={chunk['compressed_size']} "
                f"uncompressed={chunk['uncompressed_size']}"
            )

        if len(result.chunks) > 20:
            print()
            print(f"... {len(result.chunks) - 20} more chunks omitted")


def main() -> int:
    if len(sys.argv) < 2:
        print("[ERROR] Usage: python -m velune_trace.cli.inspect <file.mcap>")
        print("[HINT] Run from project root: cd ~/veluneos")
        return 2

    filename = sys.argv[1]

    try:
        reader = VeluneMcapReader(filename, validate_crcs=False)
        result = reader.inspect()
        InspectReporter.print(result)
        return 0

    except ModuleNotFoundError as e:
        print()
        print("=== VELUNE ENVIRONMENT ERROR ===")
        print()
        print(f"[ERROR] Python module not found: {e}")
        print("[HINT] Make sure you are in the project root:")
        print("       cd ~/veluneos")
        print("[HINT] Make sure the virtual environment is active:")
        print("       source .venv/bin/activate")
        return 3

    except VeluneError as e:
        print()
        print("=== VELUNE INSPECT ERROR ===")
        print()
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
