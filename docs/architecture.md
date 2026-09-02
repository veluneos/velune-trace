# Velune Trace Architecture

## MCAP Evidence Pipeline

Velune Trace's primary path reads MCAP files directly and produces a
local evidence report:

```text
MCAP file
    ↓
MCAP metadata / chunk / message adapter
    ↓
Topic timing profile (frequency, gaps, jitter)
    ↓
Windowed timing analysis (per-topic, per-window ranking)
    ↓
Ranked evidence windows
    ↓
Local report bundle (report_manifest.json, summary.md,
shareable_anonymous_report.json, topic_profile.json,
evidence_windows.json, SCHEMA.md)
```

`velune_trace/adapters/mcap_reader.py` reads MCAP metadata, chunks, and
messages. The CLI commands in `velune_trace/cli/` (`inspect`, `chunks`,
`read`, `profile`, `compare`, `compare-all`, `windowed-verify`,
`evidence-window`, `validation-report`) build on that adapter.

`validation-report` is the primary evaluation path. It profiles topic
timing, ranks candidate evidence windows, and writes the report bundle
through `velune_trace/reporting/` (bundle assembly, artifact records,
manifest, deterministic identity/hashing, and a bounded Markdown
summary writer).

## Legacy JSONL / SQLite Indexing Pipeline

An earlier, still-supported indexing path works on structured JSONL
trace events rather than raw MCAP files:

```text
Raw ROS2 runtime data
    ↓
Structured JSONL trace events
    ↓
SQLite index (indexer/)
    ↓
Seed event lookup
    ↓
Event-chain reconstruction (extractor/)
```

This path supports append-only incremental indexing so a large index
does not need to be rebuilt from scratch when new events are appended.
See [Incremental Indexing](incremental_indexing.md) for validated
checks and non-claims.

## Boundary

Velune Trace produces observable timing evidence and reproducible
evidence windows. It does not infer root cause, assign fault, assign
liability, or make safety-risk determinations. Engineers determine
cause.
