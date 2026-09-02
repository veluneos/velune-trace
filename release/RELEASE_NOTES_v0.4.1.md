# Velune Trace v0.4.1

Sparse Missing-Interval Evidence.

## Included

- Local MCAP inspection
- Versioned Core Report Bundles
- Bounded Top-K evidence-window extraction
- Sparse missing intervals derived from adjacent observed timestamps
- Explicit evidence provenance fields

## Sparse missing-interval evidence

A topic range containing no observed messages can now be represented as
a bounded sparse evidence candidate when it lies between two adjacent
observed timestamps.

The record includes:

- `evidence_kind=sparse_missing_interval`
- `derivation=adjacent_observed_timestamps`
- `missing_window_count`
- `previous_observed_ns`
- `next_observed_ns`

Velune Trace does not densely create every empty window. The candidate
uses the existing bounded Top-K evidence path.

## Release validation

- Sparse missing-interval evidence validated against a controlled fixture
  with removed messages

## Privacy and execution boundary

- Local processing
- No telemetry
- No automatic raw-log upload
- No Velune server call required

## Product boundary

Velune Trace does not automatically determine:

- root cause
- fault or liability
- safety or severity
- normality or superiority
- regression or improvement

Velune Trace finds and structures evidence.
Engineers make the conclusion.
