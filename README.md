# Velune Trace

Find the events that matter inside large ROS2 logs.

Velune Trace is a trace indexing and event-chain reconstruction prototype designed for large ROS2 runtime logs.

## Quick Start

Build an index:

```bash
python indexer/velune_trace_indexer_v0_1_sqlite.py \
  --source trace.jsonl \
  --index trace.index.sqlite
Run incremental indexing:

python indexer/velune_trace_indexer_v0_2_incremental.py \
  --source trace.jsonl \
  --index trace.index.sqlite

See each script's --help output for current options.

Validation Snapshot
Metric	Result
Corpus Size	10 GB
Events Indexed	9,237,885
Initial Index Build	276 sec
SQLite Index Size	~4.8 GB
Event Chain Retrieval	0.002 sec
Incremental Append	10,000 events in 0.57 sec
Incremental Idle Path Peak RAM	~19 MB
ROS2 Compatibility

Current validation uses structured JSONL trace events.

Planned adapters:

rosbag2 (.db3)
rosbag2 (.mcap)

Velune Trace is designed to index normalized runtime events extracted from ROS2 logging pipelines.

What Velune Trace Does
Indexes large structured trace corpora
Maps events to byte offsets
Reconstructs deterministic event chains
Supports append-only incremental indexing
Reduces log-search time after indexing
What Velune Trace Does Not Do
Root cause analysis
Fault attribution
Liability assignment
Risk scoring
Judgment engines
Current Validation Scope

Validated:

ROS2-style trace logs
Structured JSONL event format
SQLite indexing
Event-chain retrieval after indexing
Append-only incremental indexing
Invalid append rejection and rollback safety

Not yet validated:

100GB+ corpora
1TB-scale fleet data
Distributed indexing
Multi-user deployments
Unstructured legacy logs
Real-time monitoring workloads
Repository Layout

indexer/

SQLite index builder
Incremental indexer

extractor/

Event-chain extraction

viewer/

Streaming trace viewer

validation/

Failure-mode validation

benchmarks/

Benchmark reports

docs/

Architecture notes
Important Benchmark Note

The 0.002 second event-chain retrieval result is measured after the corpus has already been indexed.

Velune Trace does not claim raw 10GB parsing and chain extraction in 0.002 seconds.

Current workflow:

Index once.
Query fast.
Append incrementally.
How to Think About It

Velune Trace is not a root-cause engine.

It helps engineers get from a large trace corpus to a small, deterministic event chain faster.

Find the events.

Engineers find the cause.
