#!/usr/bin/env python3

import sys

from velune_trace.cli.inspect import main as inspect_main
from velune_trace.cli.chunks import main as chunks_main
from velune_trace.cli.read import main as read_main
from velune_trace.cli.profile import main as profile_main
from velune_trace.cli.compare import main as compare_main
from velune_trace.cli.dataset_report import main as dataset_report_main
from velune_trace.cli.verify_dataset import main as verify_dataset_main
from velune_trace.cli.windowed_verify import main as windowed_verify_main
from velune_trace.cli.evidence_window import main as evidence_window_main
from velune_trace.cli.compare_all import main as compare_all_main


def print_help() -> None:
    print("[ERROR] Usage: velune <command> [args]")
    print()
    print("Commands:")
    print("  inspect      Inspect MCAP metadata")
    print("  chunks       List MCAP chunk index information")
    print("  read         Read selected MCAP chunk/time window")
    print("  profile      Profile topic frequency and timing stability")
    print("  compare      Compare one topic between two windows")
    print("  compare-all  Compare all common topics between two windows")
    print("  windowed-verify Rank timing-irregular windows for one topic")


def main() -> int:
    if len(sys.argv) < 2:
        print_help()
        return 2

    command = sys.argv[1]
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    if command == "inspect":
        return inspect_main()
    if command == "chunks":
        return chunks_main()
    if command == "read":
        return read_main()
    if command == "profile":
        return profile_main()
    if command == "compare":
        return compare_main()
    if command == "dataset-report":
        return dataset_report_main()
    if command == "verify-dataset":
        return verify_dataset_main()
    if command == "windowed-verify":
        return windowed_verify_main()
    if command == "evidence-window":
        return evidence_window_main()
    if command == "compare-all":
        return compare_all_main()

    print(f"[ERROR] Unknown command: {command}")
    print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
