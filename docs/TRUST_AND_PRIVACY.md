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
    ├── report_manifest.json
    ├── summary.md
    ├── shareable_anonymous_report.json
    ├── topic_profile.json
    ├── evidence_windows.json
    └── SCHEMA.md

These files remain local unless the user manually decides to share them.

## What the Report Files Contain

Leaving out raw data does not by itself make a report anonymous or safe
to share. `shareable_anonymous_report.json` keeps its name for
compatibility, but it is not anonymized.

| File | Original topic names | Absolute timestamps (epoch) | Other identifying data |
|---|---|---|---|
| `summary.md` | yes | yes (window start/end) | source file name, file size |
| `topic_profile.json` | yes | yes (`first_ns`, `last_ns`) | per-topic counts and rates |
| `evidence_windows.json` | yes | yes (`start_ns`, `end_ns`, `start_sec`, `end_sec`) | per-topic counts and gaps |
| `shareable_anonymous_report.json` | yes (topic list, keys, each window) | yes | source file name, file size, report time |
| `report_manifest.json` | no | no (report time only) | source file name, file size |
| `SCHEMA.md` | no | no | none |

None of these files contains raw payloads, message contents, local paths,
user names, host names or credentials. Message counts and rates still
describe how your system is built.

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

Report files are shared only within a direct validation engagement, and
only after the user has reviewed them internally.

Agree in advance which files may be shared and through which private
channel, then share only those files. If topic names, recording times or
the source file name must not leave your environment, do not share these
report files.

Do not submit private logs or confidential operational data through public GitHub Issues.

## Boundary

Velune Trace reports observable timing evidence.

Velune Trace identifies evidence windows worth reviewing first.

Velune Trace does not infer root cause.

Velune Trace does not assign fault.

Velune Trace does not assign liability.

Velune Trace does not make safety-risk determinations.

Engineers determine cause.
