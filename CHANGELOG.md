# Changelog

All notable changes to Velune Trace are recorded here.

## [0.5.2] - 2026-09-08

### Fixed

- Report-manifest writing failed on Windows during its directory-durability
  step. Windows does not support opening a directory for fsync at all, so
  this step is now skipped there (and on the narrow set of POSIX
  filesystems that also lack support). Directory fsync is unavailable
  through this implementation on Windows; file-content fsync and atomic
  rename/hardlink installation remain in effect on every platform.
  Unrelated I/O errors are unaffected and still surface.
- A test module depended on a fixed-path sample file that is only present
  after a separate bootstrap step under some invocation methods. Every
  test now generates its own deterministic sample MCAP into a private
  temporary directory. Running the test suite does not require, create,
  or modify a repository sample file; a developer's own local sample, if
  one already exists, is left untouched.

### Changed

- `windowed-verify`'s human-readable summary now distinguishes "total
  observed windows", "full windows ranked", and "top windows displayed"
  instead of one ambiguous "Total Windows" line. This is a change to
  human-readable stdout text only; the `--export-json` field set and
  values are unchanged from v0.5.1.

### Added

- A minimal Linux + Windows continuous-integration workflow (install,
  test suite, CLI smoke check).

### Boundaries

This patch changes test infrastructure, filesystem-durability portability,
and human-readable CLI text only. The machine-readable `--export-json`
contract is unchanged from v0.5.1. No ranking, scoring, evidence-level
determination, or exported JSON field changed. It does not change engine
behavior, benchmark results, or validation measurements.

## [0.5.1] - 2026-09-02

### Changed

- Renamed the nuScenes validation terminology from `External Validation`
  to `Public Dataset Validation` to distinguish Velune-run validation on
  publicly available datasets from independent third-party evaluation.
- Replaced the illustrative `400GB MCAP` workflow label with the
  size-neutral `Large Robotics Log` because no public 400GB validation
  evidence is currently published.
- Renamed the nuScenes validation summary and updated release-package
  references and historical evaluation wording for consistent claim
  hygiene.

### Boundaries

This patch changes documentation and public claim terminology only.
It does not change engine behavior, benchmark results, or validation
measurements.

## [0.5.0] - 2026-09-02

### Fixed

- Fresh-clone test execution no longer silently depends on an
  undocumented pre-existing `examples/sample.mcap`. A pytest session
  bootstrap now generates the deterministic sample automatically if it
  is missing.
- `docs/architecture.md` contained malformed, stale content that did
  not match the current implementation. Rewritten with an accurate
  description of the current MCAP evidence pipeline and the legacy
  JSONL/SQLite indexing pipeline.

### Removed

- Two unused CLI modules (`verify_dataset.py`, `dataset_report.py`)
  that were not wired into the `velune` command dispatcher, untested,
  and undocumented. Their sole dependency, PyYAML, was removed from
  `requirements.txt` / `requirements-lock.txt`. The public command
  set is unchanged.

### Changed

- Release-process documentation and version references brought
  current for this release.

### Boundaries

Velune Trace reports observed evidence and differences. It does not
automatically determine root cause, fault, liability, safety, severity,
normality, superiority, regression, or improvement.

## [0.4.1] - 2026-07-23

### Added

- Sparse missing-interval evidence derived from adjacent observed timestamps
- Evidence provenance fields for ranked windows

### Changed

- Fully unobserved aligned ranges can enter the bounded Top-K evidence result
  without densely materializing every empty window.
- `SCHEMA.md` documents observed windows and sparse missing intervals
  separately.

### Boundaries

Velune Trace reports observed evidence and differences. It does not
automatically determine root cause, fault, liability, safety, severity,
normality, superiority, regression, or improvement.

## [0.4.0] - 2026-07-22

### Added

- Versioned Core Report Bundle generation
- Report Bundle identity and artifact-integrity metadata
- Core Bundle compatibility validation
- JSON source-of-truth evaluation reports
- Bounded Markdown review summaries
- Locked dependency record for the downloadable release

### Changed

- Sample MCAP generation is reusable from tests and command-line workflows.
- Sample-dependent tests now create isolated temporary fixtures.
- CLI wrapper tests explicitly control their Python interpreter.
- Test execution no longer depends on an existing local sample MCAP,
  project virtual environment, or ROS Python path.

### Validated

- 316 automated tests in a clean exported Git index
- Fresh Python virtual environment
- Four locked Python packages
- Explicit sample MCAP generation
- Local Validation Report generation
- Six required Core Report artifacts

### Boundaries

Velune Trace reports observed evidence and differences. It does not
automatically determine root cause, fault, liability, safety, severity,
normality, superiority, regression, or improvement.
