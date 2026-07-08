# Velune Trace v0.3.1 Release Notes

## Release Focus

v0.3.1 focuses on making Velune Trace easier for external robotics engineers to run, evaluate, and use as a local evidence-window extraction engine.

This release highlights the large-log evidence extraction proof and adds the Validation Partner workflow.

## Main Additions

### 1. Validation Report Workflow

Added the validation-report command as the primary external evaluation path.

Users can run Velune locally on an MCAP file and generate:

- summary.md
- evidence_windows.json
- topic_profile.json
- shareable_anonymous_report.json
- SCHEMA.md

Raw MCAP files are not required for partner submission.

### 2. Anonymous Report Submission

Added a shareable anonymous report path for the Velune Validation Partner Program.

For direct validation engagements, participants may share only:

    velune_report/shareable_anonymous_report.json

The report is designed to avoid raw sensor payloads.

### 3. Partner Onboarding Documentation

Added:

- docs/PARTNER_PROGRAM.md
- docs/EXAMPLE_FEEDBACK_REPORT.md
- docs/REFERENCE_COHORT_REGISTRY.md

These documents explain what participants run, what they may share, what they must not share, and what kind of feedback they may receive.

### 4. Reference Cohort Policy

Added the Reference Cohort Registry policy to prevent overclaiming.

The policy separates:

- synthetic samples
- public reference datasets
- internal benchmark corpora
- controlled fixtures
- future partner anonymous reports

Velune must not claim global averages, industry percentiles, or company-to-company comparisons unless a validated matched cohort exists.

### 5. Large-Log Engine Proof in README

Updated the README to emphasize Velune Trace as an evidence-window extraction engine for large robotics logs.

Highlighted validation evidence:

- 10.7 GB benchmark corpus
- 9,237,885 indexed events
- 161 rows scanned for evidence extraction
- 17 related events returned
- approximately 0.002 second evidence-chain retrieval after indexing
- approximately 276 second initial index build
- 10,000 event incremental append validation in approximately 0.57 seconds

## Boundary

Velune Trace reports observable timing evidence.

Velune Trace identifies evidence windows worth reviewing first.

Velune Trace does not infer root cause.

Velune Trace does not assign fault.

Velune Trace does not assign liability.

Velune Trace does not make safety-risk determinations.

Engineers determine cause.

## Recommended Tag

    v0.3.1
