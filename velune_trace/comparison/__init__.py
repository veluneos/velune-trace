"""Private local Core Bundle comparison support."""

from velune_trace.comparison.compatibility import (
    BLOCKING_FIELD_PATHS,
    COMPATIBLE_STATUS,
    INCOMPATIBLE_STATUS,
    WARNING_FIELD_PATHS,
    BundleCompatibilityResult,
    evaluate_bundle_compatibility,
)
from velune_trace.comparison.engine import (
    COMPARISON_SCHEMA_NAME,
    COMPARISON_SCHEMA_VERSION,
    COMPARISON_SEMANTICS,
    COMPARISON_VISIBILITY,
    EVIDENCE_SCORE_SEMANTICS,
    BundleComparisonEngineError,
    build_bundle_comparison,
    compare_numeric_values,
)
from velune_trace.comparison.loader import (
    BundleComparisonLoadError,
    LoadedComparisonBundle,
    load_comparison_bundle,
)
from velune_trace.comparison.writer import (
    COMPARISON_REPORT_FILENAME,
    COMPARISON_SUMMARY_FILENAME,
    HUMAN_JUDGMENT_BOUNDARY_STATEMENT,
    BundleComparisonWriteError,
    WrittenBundleComparison,
    render_comparison_summary,
    write_bundle_comparison_outputs,
)

__all__ = [
    "BLOCKING_FIELD_PATHS",
    "COMPARISON_REPORT_FILENAME",
    "COMPARISON_SCHEMA_NAME",
    "COMPARISON_SCHEMA_VERSION",
    "COMPARISON_SEMANTICS",
    "COMPARISON_SUMMARY_FILENAME",
    "COMPARISON_VISIBILITY",
    "COMPATIBLE_STATUS",
    "EVIDENCE_SCORE_SEMANTICS",
    "HUMAN_JUDGMENT_BOUNDARY_STATEMENT",
    "INCOMPATIBLE_STATUS",
    "WARNING_FIELD_PATHS",
    "BundleComparisonEngineError",
    "BundleComparisonLoadError",
    "BundleComparisonWriteError",
    "BundleCompatibilityResult",
    "LoadedComparisonBundle",
    "WrittenBundleComparison",
    "build_bundle_comparison",
    "compare_numeric_values",
    "evaluate_bundle_compatibility",
    "load_comparison_bundle",
    "render_comparison_summary",
    "write_bundle_comparison_outputs",
]
