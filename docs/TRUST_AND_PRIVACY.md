# Velune Trace Trust and Privacy Model

Velune Trace is local-first.

## Local Execution

Velune Trace runs on the user's machine.

It does not upload MCAP files.

It does not upload generated reports.

It does not perform background telemetry.

It does not call a Velune server.

It does not require a cloud account.

## Generated Artifacts

The validation-report command writes outputs to a local directory:

    velune_report/
    ├── summary.md
    ├── shareable_anonymous_report.json
    ├── topic_profile.json
    ├── evidence_windows.json
    └── SCHEMA.md

These files remain local unless the user manually decides to share them.

## Raw Data Boundary

Velune Trace does not require users to share:

- raw MCAP files
- camera images or video
- LiDAR point clouds
- sensor payloads
- maps or location data
- credentials, tokens, or keys
- customer-identifying information
- private operational data

## Optional Validation Engagements

The anonymous report is intended for direct validation engagements only.

Users should review the generated files internally before sharing anything.

If a validation engagement exists, share only the agreed anonymous artifact through the agreed private channel.

Do not submit private logs or confidential operational data through public GitHub Issues.

## Boundary

Velune Trace reports observable timing evidence.

Velune Trace identifies evidence windows worth reviewing first.

Velune Trace does not infer root cause.

Velune Trace does not assign fault.

Velune Trace does not assign liability.

Velune Trace does not make safety-risk determinations.

Engineers determine cause.
