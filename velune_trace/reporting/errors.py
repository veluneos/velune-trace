"""Domain errors for Velune Evidence Report Bundle operations."""


class EvidenceBundleError(Exception):
    """Base error that can be rendered cleanly by the Velune CLI."""

    default_code = "VELUNE_BUNDLE_ERROR"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        hint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code or self.default_code
        self.hint = hint

    def cli_lines(self) -> list[str]:
        """Return user-facing CLI lines without a traceback."""

        lines = [
            f"[ERROR] {self}",
            f"[ERROR_CODE] {self.code}",
        ]

        if self.hint:
            lines.append(f"[HINT] {self.hint}")

        return lines


class ArtifactDefinitionError(EvidenceBundleError):
    """Raised when an artifact definition or artifact file is invalid."""

    default_code = "VELUNE_BUNDLE_ARTIFACT_INVALID"


class BundleAssemblyError(EvidenceBundleError):
    """Raised when Bundle identity or manifest assembly fails."""

    default_code = "VELUNE_BUNDLE_ASSEMBLY_FAILED"


class BundleWriteError(EvidenceBundleError):
    """Raised when a Bundle manifest cannot be written safely."""

    default_code = "VELUNE_BUNDLE_WRITE_FAILED"
