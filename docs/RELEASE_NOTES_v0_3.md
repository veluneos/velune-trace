# Velune Trace v0.3 Release Notes

## Release Focus

Velune Trace v0.3 is the first external validation-partner-ready release line.

It focuses on one primary workflow:

    Run Velune locally on an MCAP file.
    Generate ranked evidence windows.
    Keep raw logs inside the user's environment.
    Optionally submit one anonymous validation report.

## Primary Workflow

The primary evaluation path is:

    ./bin/velune validation-report /path/to/your_log.mcap \
      --export-dir velune_report \
      --window-sec 1 \
      --top 5 \
      --allowed-lateness-sec 2

This creates:

    velune_report/
    ├── summary.md
    ├── shareable_anonymous_report.json
    ├── topic_profile.json
    ├── evidence_windows.json
    └── SCHEMA.md

## Engine Proof

Velune Trace has been validated on a large robotics log benchmark:

- Input size: 10.7 GB
- Indexed events: 9,237,885
- Rows scanned for evidence extraction: 161
- Related events returned: 17
- Evidence-chain retrieval after indexing: approximately 0.002 seconds
- Initial index build: approximately 276 seconds
- Incremental append validation: 10,000 events in approximately 0.57 seconds

Important boundary:

    The 0.002 second retrieval result is measured after indexing.
    Velune does not claim raw 10GB parsing in 0.002 seconds.

## Validation Partner Workflow

Velune Trace can generate an anonymous report for the Validation Partner Program.

Participants may submit only:

    velune_report/shareable_anonymous_report.json

Raw MCAP files are not required.

Do not send:

- raw MCAP files
- camera images or video
- LiDAR point clouds
- sensor payloads
- maps or location data
- credentials, tokens, or keys
- private operational data
- customer-identifying information

## Added Documentation

This release line includes:

- docs/PARTNER_PROGRAM.md
- docs/EXAMPLE_FEEDBACK_REPORT.md
- docs/REFERENCE_COHORT_REGISTRY.md
- docs/RELEASE_NOTES_v0_3_1.md
- docs/RELEASE_NOTES_v0_3.md

## Reference Cohort Policy

Velune must not describe a result as a global average, industry percentile, or company-to-company comparison unless a validated matched cohort exists.

Current public comparison capability:

    Local evidence feedback: available
    Public reference comparison: limited
    Matched anonymous cohort comparison: not yet available
    Global percentile dashboard: not yet available

## Quick Start Placeholder Clarification

Quick Start examples now use `/path/to/your_log.mcap` instead of `your_log.mcap` to make it clear that users should replace the placeholder with their own MCAP file path.

## Advanced CLI Commands

The following commands remain available for advanced users:

- inspect
- profile
- windowed-verify
- evidence-window

The CLI help now also presents validation-report as the first example.

For first-time evaluation, use validation-report first.

## Boundary

Velune Trace reports observable timing evidence.

Velune Trace identifies evidence windows worth reviewing first.

Velune Trace does not infer root cause.

Velune Trace does not assign fault.

Velune Trace does not assign liability.

Velune Trace does not make safety-risk determinations.

Engineers determine cause.

## Public Release Name

    Velune Trace v0.3

## Git Tag

    v0.3.4
