# Velune Validation Partner Program

## Purpose

The Velune Validation Partner Program lets robotics engineers generate a local timing-evidence report from their own MCAP files and optionally share one anonymous report with Velune.

The purpose is to help engineers identify evidence windows worth reviewing first.

Velune Trace does not require raw MCAP upload.

## What You Run Locally

Run Velune Trace inside your own environment.

Command:

    ./bin/velune validation-report /path/to/your_log.mcap \
      --export-dir velune_report \
      --window-sec 1 \
      --top 5 \
      --allowed-lateness-sec 2

Replace `/path/to/your_log.mcap` with the path to your own MCAP file.

This creates:

    velune_report/
    ├── summary.md
    ├── shareable_anonymous_report.json
    ├── topic_profile.json
    ├── evidence_windows.json
    └── SCHEMA.md

## What You May Share

If you choose to participate, send only:

    velune_report/shareable_anonymous_report.json

Send it to:

    skagusdn1998@gmail.com

## What You Must Not Send

Do not send:

- raw MCAP files
- camera images or video
- LiDAR point clouds
- sensor payloads
- maps or location data
- credentials, tokens, or keys
- private operational data
- customer-identifying information

## What Participants May Receive

When a relevant reference cohort is available, participants may receive:

- timing evidence summary
- top evidence windows recommended for review
- investigation starting points
- anonymous reference comparison
- validation feedback

## Current Program Status

This is an early Validation Partner Program.

Velune does not yet provide an automatic global percentile dashboard.

A comparison may be limited to local evidence, public reference datasets, or a small anonymous reference cohort.

## Boundary

Velune reports observable timing evidence and reproducible evidence windows.

Velune does not infer root cause.

Velune does not assign fault.

Velune does not make safety, liability, or risk determinations.

Engineers determine cause.
