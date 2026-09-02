"""Shared pytest bootstrap for the Velune Trace test suite.

Some tests reference the repository's documented sample MCAP
(examples/sample.mcap) by its fixed path rather than generating a
private copy in a temp directory. examples/*.mcap is intentionally
gitignored (binary artifacts are not tracked), so a fresh clone will
not have it yet. Generate it deterministically here, once, before the
test session runs, so `pytest` is self-contained on a fresh clone
without requiring a manual bootstrap step first.
"""

from pathlib import Path

from tools.create_sample_mcap import create_sample_mcap

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_MCAP_PATH = REPO_ROOT / "examples" / "sample.mcap"


def pytest_configure(config):
    if not SAMPLE_MCAP_PATH.exists():
        create_sample_mcap(SAMPLE_MCAP_PATH)
