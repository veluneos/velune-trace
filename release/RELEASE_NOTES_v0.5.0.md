# Velune Trace v0.5.0

## Release Focus

v0.5.0 focuses on fresh-clone reproducibility and documentation
accuracy rather than new evidence-extraction features.

## Included

- Local MCAP inspection, chunk/read access, and topic timing profiling
- Windowed timing-irregularity ranking and evidence-window extraction
- Raw-window `compare` / `compare-all` diagnostics between two MCAP
  windows
- Versioned Core Report Bundle generation via `validation-report`
- Deterministic sample MCAP generation for local evaluation

## Fixed

- `pytest` no longer depends on an undocumented pre-existing
  `examples/sample.mcap`. A test-session bootstrap
  (`tests/conftest.py`) now generates the deterministic sample MCAP
  automatically on a fresh clone, before any test that needs it runs.
- `docs/architecture.md` contained malformed, stale content that did
  not match the current implementation. Replaced with an accurate
  description of the current MCAP evidence pipeline and the legacy
  JSONL/SQLite indexing pipeline.

## Removed

- Two unused, undocumented CLI modules (`verify_dataset.py`,
  `dataset_report.py`) that were never wired into the `velune`
  command dispatcher, had no tests, and had no documentation. Their
  sole dependency, PyYAML, was also removed from
  `requirements.txt` / `requirements-lock.txt`. The public command
  set is unchanged.

## Release validation

- Full automated test suite passes on a genuinely fresh clone (no
  pre-existing sample MCAP, no pre-existing virtual environment)
- Sample MCAP creation passes
- Local Validation Report generation passes
- All six required Core Report artifacts are present

## Product boundary

Velune Trace does not automatically determine:

- root cause
- fault or liability
- safety or severity
- normality or superiority
- regression or improvement

Find the events. Engineers find the cause.
