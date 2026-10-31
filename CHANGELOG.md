# Changelog

All notable changes to Velune Trace are recorded here.

## [0.5.4] - 2026-10-31

### Changed

- `validation-report` no longer replaces an existing report. If any of
  the six report files is already in `--export-dir`, the command stops
  with exit status 2 before reading the MCAP and changes nothing. Add the
  new `--overwrite` option to replace the report on purpose. Scripts that
  write repeatedly into the same `--export-dir` need `--overwrite`.
  Other files in the directory are never touched; an empty or unrelated
  directory is accepted as before. An `--export-dir` that is a file is
  rejected.
- The README, `release/QUICKSTART.md` and the website now write the
  sample and your own log into different export directories.

### Fixed

- The documentation and CLI help described `shareable_anonymous_report.json`
  as an anonymized report suitable for sharing outside your environment.
  It contains original topic names and absolute recording times. The
  file name and schema are unchanged for compatibility; the README and
  `docs/TRUST_AND_PRIVACY.md` now list what each report file contains,
  and state that the data owner must review and approve any report file
  before it is shared.
- The Velune Adapter Beta Kit links point to Beta Kit 0.1.1b6.

### Added

- `tests/test_validation_report_overwrite.py`.

### Boundaries

Window construction, scoring, ranking and every report file's content
and schema are unchanged from v0.5.3. Only the export-directory check,
the `--overwrite` option and help text differ.

## [0.5.3] - 2026-10-30

### Fixed

- `windowed-verify` scored a window that was MORE regular than the
  baseline (smaller maximum gap or smaller jitter) as irregular, because
  the gap and jitter terms used the absolute log ratio. Such windows could
  outrank windows containing real long gaps. Only gaps and jitter above
  the baseline now raise a window's score, the same direction already
  used by `validation-report`. Windows where two or more messages share
  one timestamp (zero gap) keep the same +10 contribution as before.
- `windowed-verify` could not see a gap whose interval crosses a window
  boundary, because `max_gap` is measured only between messages inside
  one window. The gap term now uses the largest interval that ends in the
  window, including the interval from the previous observed message.
- Four README links pointed to files that are not part of the release
  package, so the release-package link validation failed. The Velune
  Adapter Beta Kit links now point to the same download on veluneos.ai,
  and the two benchmark-record links point to the same files on GitHub,
  pinned to commit ba50e23.

### Changed

- Ranking order and scores of `windowed-verify` can differ from v0.5.2.
  Every per-window score is computed from the same windows and the same
  observed timestamps; window construction, counts, `max_gap`, `jitter`,
  `evidence_command`, and the full-window ranking eligibility rule are
  unchanged.
- Windows with fewer than three messages no longer receive the +10
  "no jitter measurable" contribution, and single-message windows no
  longer receive the +10 "zero gap" contribution. They are still scored
  by the count term and by any real gap that ends in them.
- Human-readable output adds a `median_gap_in` baseline line and a
  `gap_in` table column.

### Added

- `--export-json`: per-window `stats.entry_gap` (seconds from the
  previous observed message to the window's first message; `null` for
  the first non-empty window and for empty windows) and
  `stats.max_gap_incl_entry` (`0.0` for empty windows); baseline
  `median_max_gap_incl_entry`; two explanatory `notes` lines. No existing
  field was removed, renamed, or changed in meaning.
- Ranking regression tests (`tests/test_windowed_verify_scoring.py`).

### Boundaries

This patch changes `windowed-verify` scoring and four README links only. `validation-report`,
`evidence-window`, `compare`, `compare-all`, the indexer, the extractor,
and the viewer are unchanged. Ranking remains observed timing
irregularity only; it does not infer root cause, fault, liability, or
safety.

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
