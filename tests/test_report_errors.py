import unittest

from velune_trace.reporting.errors import (
    ArtifactDefinitionError,
    BundleAssemblyError,
    BundleWriteError,
    EvidenceBundleError,
)


class EvidenceBundleErrorTests(unittest.TestCase):
    def test_uses_default_error_code(self):
        error = EvidenceBundleError("Bundle operation failed")

        self.assertEqual(
            error.code,
            "VELUNE_BUNDLE_ERROR",
        )
        self.assertIsNone(error.hint)
        self.assertEqual(
            error.cli_lines(),
            [
                "[ERROR] Bundle operation failed",
                "[ERROR_CODE] VELUNE_BUNDLE_ERROR",
            ],
        )

    def test_renders_custom_code_and_hint(self):
        error = EvidenceBundleError(
            "Invalid Bundle metadata",
            code="VELUNE_BUNDLE_METADATA_INVALID",
            hint="Check the Bundle metadata fields.",
        )

        self.assertEqual(
            error.cli_lines(),
            [
                "[ERROR] Invalid Bundle metadata",
                (
                    "[ERROR_CODE] "
                    "VELUNE_BUNDLE_METADATA_INVALID"
                ),
                (
                    "[HINT] "
                    "Check the Bundle metadata fields."
                ),
            ],
        )

    def test_artifact_error_uses_domain_default_code(self):
        error = ArtifactDefinitionError(
            "Artifact definition is invalid"
        )

        self.assertEqual(
            error.code,
            "VELUNE_BUNDLE_ARTIFACT_INVALID",
        )

    def test_assembly_error_uses_domain_default_code(self):
        error = BundleAssemblyError(
            "Bundle assembly failed"
        )

        self.assertEqual(
            error.code,
            "VELUNE_BUNDLE_ASSEMBLY_FAILED",
        )

    def test_write_error_uses_domain_default_code(self):
        error = BundleWriteError(
            "Bundle write failed"
        )

        self.assertEqual(
            error.code,
            "VELUNE_BUNDLE_WRITE_FAILED",
        )


if __name__ == "__main__":
    unittest.main()
