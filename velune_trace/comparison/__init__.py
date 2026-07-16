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

__all__ = [
    "BLOCKING_FIELD_PATHS",
    "COMPARISON_SCHEMA_NAME",
    "COMPARISON_SCHEMA_VERSION",
    "COMPARISON_SEMANTICS",
    "COMPARISON_VISIBILITY",
    "COMPATIBLE_STATUS",
    "EVIDENCE_SCORE_SEMANTICS",
    "INCOMPATIBLE_STATUS",
    "WARNING_FIELD_PATHS",
    "BundleComparisonEngineError",
    "BundleComparisonLoadError",
    "BundleCompatibilityResult",
    "LoadedComparisonBundle",
    "build_bundle_comparison",
    "compare_numeric_values",
    "evaluate_bundle_compatibility",
    "load_comparison_bundle",
]
