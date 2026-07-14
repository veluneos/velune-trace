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
        stage: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code or self.default_code
        self.hint = hint
        self.stage = stage

    def attach_stage(self, stage: str) -> None:
        """Attach orchestration-stage context without wrapping the error."""

        if not isinstance(stage, str):
            raise TypeError("stage must be a string")

        if not stage or stage != stage.strip():
            raise ValueError(
                "stage must be a non-empty string without "
                "surrounding whitespace"
            )

        if self.stage is None:
            self.stage = stage

    def cli_lines(self) -> list[str]:
        """Return user-facing CLI lines without a traceback."""

        lines = [
            f"[ERROR] {self}",
            f"[ERROR_CODE] {self.code}",
        ]

        if self.stage:
            lines.append(f"[STAGE] {self.stage}")

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
