# Velune Trace

Find the events.  
Engineers find the cause.

Velune Trace is an evidence-window extraction engine for large robotics logs.

It helps engineers move from large ROS2 / MCAP runtime logs to a small set of reproducible evidence windows.

Velune Trace is the first operational component of the broader VeluneOS evidence architecture.

Velune does not perform root-cause analysis.  
Velune does not assign fault.  
Velune does not assign liability.

Velune helps engineers find where to look first.

---

## The Problem

Large robotics investigations often begin with one question:

> Where should I start looking?

Engineers may spend hours replaying logs, switching topics, checking timestamps, and manually narrowing the investigation scope.

Velune Trace is built to reduce that search space.

Instead of starting from an entire log corpus, engineers start from ranked evidence windows.

---

## 30-Second MCAP Example

Inspect an MCAP file:

~~~bash
./bin/velune inspect incident.mcap
~~~

Profile topic timing:

~~~bash
./bin/velune profile incident.mcap \
  --start-sec 1535489296.047916889 \
  --end-sec 1535489315.948405981 \
  --sort max_gap
~~~

Rank suspicious timing windows:

~~~bash
./bin/velune windowed-verify \
  incident.mcap \
  --topic /lidar_top \
  --window-sec 1 \
  --top 5 \
  --export-json windowed_report.json
~~~

Extract a reproducible evidence window:

~~~bash
./bin/velune evidence-window \
  incident.mcap \
  --topic /lidar_top \
  --start-sec 1535489307.047916889 \
  --end-sec 1535489308.047916889 \
  --expected-count 20 \
  --export-json evidence_window.json
~~~

Typical outputs include:

- ranked evidence windows
- observed count
- expected count
- count ratio
- max timing gap
- jitter statistics
- silent span
- reproducible JSON evidence

---

## How Velune Relates to Foxglove

Foxglove helps engineers visualize robotics data.

Velune helps engineers identify which time windows are worth inspecting before deeper investigation.

Typical workflow:

~~~text
MCAP / Runtime Logs
↓
Velune Trace
↓
Ranked Evidence Windows
↓
Foxglove / Investigation
↓
Engineer Analysis
~~~

Velune is not a replacement for Foxglove.

It is designed to work before or alongside visualization tools.

---

## Validation Highlights

| Validation | Result |
|---|---:|
| 10.7 GB benchmark corpus | PASS |
| Events indexed | 9,237,885 |
| Initial index build | 276 sec |
| SQLite index size | ~4.8 GB |
| Indexed evidence-chain retrieval | 0.002 sec |
| Incremental append validation | 10,000 events in 0.57 sec |
| External nuScenes MCAP validation | PASS |
| Controlled dropout recovery validation | PASS |

Important note:

The 0.002 sec retrieval result is measured after the corpus has already been indexed.

Velune does not claim raw 10GB parsing in 0.002 sec.

---

## External Validation

Velune Trace has been validated against external autonomous-driving MCAP datasets generated through the Foxglove `nuscenes2mcap` pipeline.

Dataset summary:

- Dataset: nuScenes mini
- Scenes: 10
- Topics: `/lidar_top`, `/imu`
- Generated windowed-verify reports: 20
- Controlled dropout fixture: PASS

Validation scope:

- MCAP metadata inspection
- topic profiling
- windowed timing irregularity ranking
- evidence command generation
- evidence window extraction
- JSON evidence export
- controlled dropout recovery validation

See:

- [MASTER_NUSCENES_EXTERNAL_SWEEP_SUMMARY](docs/validation/MASTER_NUSCENES_EXTERNAL_SWEEP_SUMMARY.md)

---

## What Velune Trace Does

Velune currently supports:

- MCAP metadata inspection
- topic timing profiling
- windowed timing irregularity ranking
- evidence window extraction
- deterministic evidence export
- large-scale trace indexing
- append-only incremental indexing

---

## What Velune Trace Does Not Do

Velune does not:

- perform root-cause analysis
- detect faults automatically
- replace Foxglove
- assign fault
- assign liability
- assign risk scores
- perform real-time fleet monitoring
- make autonomous incident judgments

---

## Ecosystem Roadmap

Completed:

- [x] Structured JSONL runtime trace input
- [x] SQLite trace indexing
- [x] Append-only incremental indexing
- [x] MCAP metadata inspection
- [x] MCAP topic profiling
- [x] MCAP windowed timing analysis
- [x] MCAP evidence-window extraction
- [x] External nuScenes validation

Roadmap:

- [ ] rosbag2 database adapter `.db3`
- [ ] custom message introspection
- [ ] larger-scale benchmark datasets
- [ ] additional external robotics datasets
- [ ] fleet-scale validation
- [ ] evidence classification layer

---

## Indexing Workflow

Build an index:

~~~bash
python indexer/velune_trace_indexer_v0_1_sqlite.py \
  --source trace.jsonl \
  --index trace.index.sqlite
~~~

Run incremental indexing:

~~~bash
python indexer/velune_trace_indexer_v0_2_incremental.py \
  --source trace.jsonl \
  --index trace.index.sqlite
~~~

Current indexing workflow:

~~~text
Index once.
Query fast.
Append incrementally.
~~~

---

## Repository Layout

**indexer/**

- SQLite index builder
- incremental indexer

**extractor/**

- event-chain extraction

**viewer/**

- streaming trace viewer

**validation/**

- failure-mode validation

**benchmarks/**

- benchmark reports

**docs/**

- architecture notes
- validation records

---

## Current Validation Scope

Validated:

- ROS2-style trace logs
- structured JSONL event format
- SQLite indexing
- event-chain retrieval after indexing
- append-only incremental indexing
- invalid append rejection and rollback safety
- external nuScenes MCAP timing analysis
- controlled dropout recovery fixture

Not yet validated:

- 100GB+ corpora
- 1TB-scale fleet data
- distributed indexing
- multi-user deployments
- real-time monitoring workloads
- full semantic interpretation of arbitrary custom ROS2 message fields

---

## How to Think About Velune

Velune Trace is not a root-cause engine.

It helps engineers get from a large robotics log corpus to a small, reproducible set of evidence windows faster.

Find the events.  
Engineers find the cause.
