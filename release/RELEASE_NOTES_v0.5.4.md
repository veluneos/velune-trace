# Velune Trace v0.5.4

## Release Focus

v0.5.4 protects existing reports from being overwritten and corrects how
the documentation describes report sharing. Analysis results are
unchanged from v0.5.3.

## Changed — please read if you automate Velune Trace

- **Existing reports are not overwritten by default.** If any of the six
  report files is already in `--export-dir`, `validation-report` stops
  with exit status 2 before reading the MCAP, prints
  `[ERROR] Export directory already contains a report: …`, and changes
  nothing.
- Add `--overwrite` to replace a report on purpose. **Scripts that write
  repeatedly into the same `--export-dir` must add `--overwrite`** (or use
  a new directory per run).
- Other files in the export directory are never touched. An empty or
  unrelated existing directory is accepted as before. An `--export-dir`
  that is a regular file is rejected.

## Fixed

- **Report sharing guidance.** `shareable_anonymous_report.json` was
  described as an anonymized report suitable for sharing outside your
  environment. It is not anonymized: it contains your original topic
  names, absolute recording times and the source file name. Four of the
  six report files contain topic names and absolute times; three name the
  source file; none contains raw payloads, local paths, user or host names,
  or credentials. The file name and JSON schema are unchanged for
  compatibility. Review report files, and have the data owner approve,
  before sharing any of them. See `docs/TRUST_AND_PRIVACY.md` in the
  repository.
- CLI help no longer calls `validation-report` output anonymous.
- Quick Start examples use separate export directories for the sample and
  your own log.

## Unchanged

- Window construction, scoring, ranking, every report file's content and
  JSON schema, and stdout `KEY=VALUE` lines.
- `windowed-verify`, `evidence-window`, `compare`, `compare-all`,
  `profile`, `inspect`, `chunks` and `read`. Their `--export-json`
  options still replace an existing file.

## Release validation

- Full automated test suite passes: 152 tests and 64 subtests
  (2 skipped, as in v0.5.3).
- On the same recordings, `summary.md`, `topic_profile.json`,
  `evidence_windows.json` and `SCHEMA.md` are byte-identical to v0.5.3.

## Known limitations

- A failed run (for example an unreadable MCAP) can leave an empty export
  directory.
- An unwritable export directory is reported with a Python traceback.

## Product boundary

Velune Trace does not automatically determine:

- root cause
- fault or liability
- safety or severity
- normality or superiority
- regression or improvement

Find the events. Engineers find the cause.
