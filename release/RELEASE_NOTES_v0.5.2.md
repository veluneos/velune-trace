# Velune Trace v0.5.2

## Release Focus

v0.5.2 is a Windows-compatibility and test-infrastructure hardening
patch. It does not change engine behavior, benchmark results, or
validation measurements.

## Fixed

- Report-manifest writing failed on Windows during its
  directory-durability step. Windows does not support opening a
  directory for fsync at all, so this step is now skipped there (and
  on the narrow set of POSIX filesystems that also lack support).
  Directory fsync is unavailable through this implementation on
  Windows; file-content fsync and atomic rename/hardlink installation
  remain in effect on every platform. Unrelated I/O errors are
  unaffected and still surface.
- A test module depended on a fixed-path sample file that was only
  present after a separate bootstrap step under some invocation
  methods. Every test now generates its own deterministic sample MCAP
  into a private temporary directory. Running the test suite does not
  require, create, or modify a repository sample file; a developer's
  own local sample, if one already exists, is left untouched.

## Changed

- `windowed-verify`'s human-readable summary now distinguishes "total
  observed windows", "full windows ranked", and "top windows
  displayed" instead of one ambiguous "Total Windows" line. This is a
  change to human-readable stdout text only; the `--export-json` field
  set and values are unchanged from v0.5.1.

## Added

- A minimal Linux + Windows continuous-integration workflow (install,
  test suite, CLI smoke check), run on every push and pull request.

## Release validation

- Full automated test suite passes: 126 tests and 58 subtests.
- Verified on an actual GitHub Actions Ubuntu runner and an actual
  GitHub Actions Windows runner, both on Python 3.12.
- The machine-readable `--export-json` contract is unchanged from
  v0.5.1: no field was added, removed, or renamed.
- No ranking, scoring, evidence-level determination, or window
  construction changed.

## Product boundary

Velune Trace does not automatically determine:

- root cause
- fault or liability
- safety or severity
- normality or superiority
- regression or improvement

Find the events. Engineers find the cause.
