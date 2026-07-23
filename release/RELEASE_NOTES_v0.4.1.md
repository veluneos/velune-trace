# Velune Trace v0.4.1

Sparse Missing-Interval Evidence and Numeric Bundle Comparison.

## Included

- Local MCAP inspection
- Versioned Core Report Bundles
- Bounded Top-K evidence-window extraction
- Sparse missing intervals derived from adjacent observed timestamps
- Explicit evidence provenance fields
- Pairwise Core Bundle comparison
- Machine-readable comparison JSON
- Numeric human-readable comparison summaries

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

## Numeric Bundle comparison summary

For changed comparable fields, `comparison_summary.md` now presents:

- Reference
- Target
- Delta
- Ratio
- Ratio state

`comparison_report.json` remains the machine-readable source of truth.

## Release validation

- 318 automated tests passed
- Reference and Target contained 41 topics
- One changed common topic was observed: `/lidar_top`
- `/lidar_top` message count: 398 → 378
- Profile maximum gap: 100.089 ms → 1,050.060 ms
- Minimum Top-K count ratio: 0.904762 → 0.0
- Target sparse missing interval ranked first
- Maximum active windows: 119 → 119

The Target was an explicitly modified nuScenes scene-0553 validation
fixture with 20 `/lidar_top` messages removed.

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
