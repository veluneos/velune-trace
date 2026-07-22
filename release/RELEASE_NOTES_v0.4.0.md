# Velune Trace v0.4.0

Local Evidence and Private Baseline Preview.

## Included

- Local MCAP inspection
- Timing profile generation
- Reproducible evidence-window extraction
- Versioned Core Report Bundles
- Core Bundle compatibility validation
- Pairwise Core Bundle comparison
- Private Baseline Python APIs
- Local evaluation reports
- JSON source-of-truth artifacts
- Bounded Markdown summaries

## Release validation

- 316 automated tests passed
- Test suite passed without a tracked sample MCAP
- Test suite passed in a fresh Python virtual environment
- ROS Python path was excluded from validation
- Four exact dependency versions were recorded
- Sample MCAP creation passed
- Local Validation Report generation passed
- Six required Core Report artifacts were verified

## Previously measured evidence

- 10.7GB large-log benchmark
- Approximately 9.2 million indexed events
- Initial index construction measured separately from retrieval
- Real-derived Core Bundle validation
- Private Baseline Service E2E validation

## Product boundary

Velune Trace does not automatically determine:

- root cause
- fault or liability
- safety or severity
- normality or superiority
- regression or improvement

Velune Trace finds and structures evidence.
Engineers make the conclusion.
