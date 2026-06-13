# Velune Trace Architecture

## Pipeline

```text
Raw ROS2 runtime data
    ↓
Structured JSONL trace events
    ↓
SQLite index
    ↓
Seed event lookup
    ↓
Event-chain reconstruction


incremental 문서:

```bash
cat > github_release_v0_2/docs/incremental_indexing.md << 'EOF'
# Incremental Indexing

Velune Trace v0.2 supports append-only incremental indexing.

## Goal

Avoid rebuilding the full 10GB SQLite index when new trace events are appended.

## Validated Checks

- prefix mutation detection
- source truncation detection
- sequence continuity check
- last_event_hash continuity check
- transaction rollback safety
- no full source SHA256 recalculation in the incremental path

## Stress Validation

10,000 appended events were indexed in 0.569805 seconds.

## Non-Claims

Velune Trace v0.2 does not claim:

- full corpus tamper detection
- chunk manifest validation
- distributed indexing
- multi-writer safety
- crash recovery after power loss
