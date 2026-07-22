"""CLI orchestration for private local Core Bundle comparison."""

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sys

from velune_trace.comparison import (
    build_bundle_comparison,
    load_comparison_bundle,
    write_bundle_comparison_outputs,
)
from velune_trace.reporting.errors import EvidenceBundleError


COMMAND_NAME = "compare-bundles"
INTERNAL_ERROR_EXIT_CODE = 70
INTERNAL_ERROR_CODE = "VELUNE_INTERNAL_ERROR"


def build_parser() -> argparse.ArgumentParser:
    """Build the compare-bundles argument parser."""

    parser = argparse.ArgumentParser(
        prog="velune compare-bundles",
        description=(
            "Compare two verified local Core Report Bundles "
            "and write observed evidence differences."
        ),
    )
    parser.add_argument(
        "reference_bundle_dir",
        help="Reference Core Report Bundle directory",
    )
    parser.add_argument(
        "target_bundle_dir",
        help="Target Core Report Bundle directory",
    )
    parser.add_argument(
        "--export-dir",
        required=True,
        help=(
            "New local directory for comparison_report.json "
            "and comparison_summary.md"
        ),
    )

    return parser


def _utc_now_iso() -> str:
    """Return a timezone-aware UTC generation timestamp."""

    return datetime.now(
        timezone.utc
    ).isoformat(
        timespec="microseconds"
    )


def _debug_enabled() -> bool:
    """Return whether unexpected defects should show a traceback."""

    return os.environ.get("VELUNE_DEBUG") == "1"


def _print_domain_error(
    error: EvidenceBundleError,
) -> None:
    """Render an expected domain error without a traceback."""

    for line in error.cli_lines():
        print(line, file=sys.stderr)


def _print_internal_error(
    error: Exception,
) -> None:
    """Render an unexpected defect as an internal CLI failure."""

    print(
        "[FATAL] Unexpected internal error.",
        file=sys.stderr,
    )
    print(
        f"[ERROR_CODE] {INTERNAL_ERROR_CODE}",
        file=sys.stderr,
    )
    print(
        f"[ERROR_TYPE] {type(error).__name__}",
        file=sys.stderr,
    )
    print(
        f"[ERROR] {error}",
        file=sys.stderr,
    )
    print(
        "[HINT] Re-run with VELUNE_DEBUG=1 to display "
        "the full traceback.",
        file=sys.stderr,
    )


def main(argv=None) -> int:
    """Run the private local Bundle comparison workflow."""

    parser = build_parser()
    args = parser.parse_args(argv)

    reference_bundle_dir = Path(
        args.reference_bundle_dir
    )
    target_bundle_dir = Path(
        args.target_bundle_dir
    )
    export_dir = Path(args.export_dir)

    try:
        reference = load_comparison_bundle(
            reference_bundle_dir
        )
        target = load_comparison_bundle(
            target_bundle_dir
        )

        report = build_bundle_comparison(
            reference,
            target,
            generated_at=_utc_now_iso(),
        )

        written = write_bundle_comparison_outputs(
            export_dir=export_dir,
            report=report,
        )
    except EvidenceBundleError as error:
        _print_domain_error(error)
        return 1
    except Exception as error:
        if _debug_enabled():
            raise

        _print_internal_error(error)
        return INTERNAL_ERROR_EXIT_CODE

    summary = report["summary"]

    print("VELUNE CORE BUNDLE COMPARISON")
    print(
        f"REFERENCE_BUNDLE={reference_bundle_dir}"
    )
    print(
        f"TARGET_BUNDLE={target_bundle_dir}"
    )
    print(f"EXPORT_DIR={written.output_dir}")
    print(
        "COMPATIBILITY_STATUS="
        f"{report['compatibility']['status']}"
    )
    print(
        "COMMON_TOPIC_COUNT="
        f"{summary['common_topic_count']}"
    )
    print(
        "REFERENCE_ONLY_TOPIC_COUNT="
        f"{summary['reference_only_topic_count']}"
    )
    print(
        "TARGET_ONLY_TOPIC_COUNT="
        f"{summary['target_only_topic_count']}"
    )
    print(
        "CHANGED_PROFILE_TOPIC_COUNT="
        f"{summary['changed_profile_topic_count']}"
    )
    print(
        "CHANGED_EVIDENCE_SUMMARY_TOPIC_COUNT="
        f"{summary['changed_evidence_summary_topic_count']}"
    )
    print("OUTPUTS:")
    print(f"- {written.report_path}")
    print(f"- {written.summary_path}")
    print("")
    print(
        "LOCAL_ONLY_NOTICE="
        "No telemetry or automatic upload was performed."
    )
    print(
        "JUDGMENT_BOUNDARY_NOTICE="
        "Velune reports observable differences. "
        "Engineers determine their meaning and cause."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
