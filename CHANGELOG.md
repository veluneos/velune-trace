# Changelog

All notable changes to Velune Trace are recorded here.

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
