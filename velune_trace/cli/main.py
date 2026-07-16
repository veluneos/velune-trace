#!/usr/bin/env python3
"""Velune Trace CLI command dispatcher."""

import sys

from velune_trace.cli.chunks import main as chunks_main
from velune_trace.cli.compare import main as compare_main
from velune_trace.cli.compare_all import (
    main as compare_all_main,
)
from velune_trace.cli.compare_bundles import (
    main as compare_bundles_main,
)
from velune_trace.cli.evidence_window import (
    main as evidence_window_main,
)
from velune_trace.cli.inspect import main as inspect_main
from velune_trace.cli.profile import main as profile_main
from velune_trace.cli.read import main as read_main
from velune_trace.cli.validation_report import (
    main as validation_report_main,
)
from velune_trace.cli.windowed_verify import (
    main as windowed_verify_main,
)


COMMANDS = {
    "inspect": inspect_main,
    "chunks": chunks_main,
    "read": read_main,
    "profile": profile_main,
    "compare": compare_main,
    "compare-all": compare_all_main,
    "compare-bundles": compare_bundles_main,
    "windowed-verify": windowed_verify_main,
    "evidence-window": evidence_window_main,
    "validation-report": validation_report_main,
}


def print_usage() -> None:
    """Print top-level CLI usage."""

    print("Usage: velune <command> [args]")
    print("")
    print("Commands:")
    print(
        "  inspect            "
        "Inspect MCAP metadata"
    )
    print(
        "  chunks             "
        "List MCAP chunk index information"
    )
    print(
        "  read               "
        "Read selected MCAP chunk/time window"
    )
    print(
        "  profile            "
        "Profile topic frequency and timing stability"
    )
    print(
        "  compare            "
        "Compare one topic between two windows"
    )
    print(
        "  compare-all        "
        "Compare all common topics between two windows"
    )
    print(
        "  compare-bundles    "
        "Compare two verified Core Report Bundles"
    )
    print(
        "  windowed-verify    "
        "Rank timing-irregular windows for one topic"
    )
    print(
        "  evidence-window    "
        "Extract a reproducible evidence window"
    )
    print(
        "  validation-report  "
        "Generate anonymous validation report"
    )


def main(argv=None) -> int:
    """Dispatch one Velune CLI command."""

    argv = list(
        sys.argv[1:]
        if argv is None
        else argv
    )

    if (
        not argv
        or argv[0] in {
            "--help",
            "-h",
            "help",
        }
    ):
        print_usage()
        return 0

    command = argv[0]
    args = argv[1:]

    command_function = COMMANDS.get(command)

    if command_function is None:
        print(
            f"[ERROR] Unknown command: {command}",
            file=sys.stderr,
        )
        print_usage()
        return 2

    result = command_function(args)

    return 0 if result is None else result


if __name__ == "__main__":
    raise SystemExit(main())
