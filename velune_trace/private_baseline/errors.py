"""Domain errors for Private Baseline contract operations."""

from velune_trace.reporting.errors import (
    EvidenceBundleError,
)


class PrivateBaselineContractError(EvidenceBundleError):
    """Raised when a Private Baseline contract value is invalid."""

    default_code = (
        "VELUNE_PRIVATE_BASELINE_CONTRACT_INVALID"
    )
