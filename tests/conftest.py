"""Shared pytest bootstrap for the Velune Trace test suite.

Historically this generated a shared sample MCAP at a fixed repository
path (examples/sample.mcap) once per session, because one test module
referenced that fixed path directly. That module now generates its own
deterministic sample inside a temporary directory (see
test_cli_dispatch.py's setUpModule/tearDownModule) alongside every other
test that needs a sample MCAP, so no test in this suite writes into the
source tree anymore, and a read-only source checkout can run the full
suite without any pre-test bootstrap step.

This file is kept (rather than removed) only because its presence in
tests/ is part of how pytest resolves this repository's rootdir/sys.path
for the `from velune_trace...` / `from tools...` imports used throughout
the suite, absent a pyproject.toml/pytest.ini in this project. It
performs no filesystem writes.
"""
