"""Private local Core Bundle comparison support."""

from velune_trace.comparison.compatibility import (
    BLOCKING_FIELD_PATHS,
    COMPATIBLE_STATUS,
    INCOMPATIBLE_STATUS,
    WARNING_FIELD_PATHS,
    BundleCompatibilityResult,
    evaluate_bundle_compatibility,
)
from velune_trace.comparison.loader import (
    BundleComparisonLoadError,
    LoadedComparisonBundle,
    load_comparison_bundle,
)

__all__ = [
    "BLOCKING_FIELD_PATHS",
    "COMPATIBLE_STATUS",
    "INCOMPATIBLE_STATUS",
    "WARNING_FIELD_PATHS",
    "BundleComparisonLoadError",
    "BundleCompatibilityResult",
    "LoadedComparisonBundle",
    "evaluate_bundle_compatibility",
    "load_comparison_bundle",
]
