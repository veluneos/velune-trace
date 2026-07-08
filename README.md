# Velune Trace

Evidence-window extraction engine for large robotics MCAP / ROS2 runtime logs.

Stop replaying the entire log.

Start from the evidence windows worth reviewing first.

Velune Trace helps engineers reduce large robotics logs into a small set of reproducible evidence windows.

It runs locally.

Raw MCAP files do not need to leave your environment.

Velune does not determine root cause, assign fault, assign liability, or make safety-risk judgments.

Engineers determine cause.

---

## Engine Proof: Large-Log Evidence Extraction

Velune Trace has been validated on a large robotics log benchmark.

- Input size: 10.7 GB
- Indexed events: 9,237,885
- Rows scanned for evidence extraction: 161
- Related events returned: 17
- Evidence-chain retrieval after indexing: approximately 0.002 seconds
- Initial index build: approximately 276 seconds
- Incremental append validation: 10,000 events in approximately 0.57 seconds

The point is not to replay everything.

The point is to reduce the investigation scope to the evidence windows worth reviewing first.

---

## 3-Minute Validation Partner Quick Start

### Step 1. Create the sample MCAP

    python3 tools/create_sample_mcap.py

### Step 2. Run Velune on the sample

    ./bin/velune validation-report examples/sample.mcap \
      --export-dir velune_report \
      --window-sec 1 \
      --top 5 \
      --allowed-lateness-sec 2

### Step 3. Run Velune on your own MCAP

    ./bin/velune validation-report /path/to/your_log.mcap \
      --export-dir velune_report \
      --window-sec 1 \
      --top 5 \
      --allowed-lateness-sec 2

Replace `/path/to/your_log.mcap` with the path to your own MCAP file.

### Step 4. Review the local report

Velune creates:

    velune_report/
    ├── summary.md
    ├── shareable_anonymous_report.json
    ├── topic_profile.json
    ├── evidence_windows.json
    └── SCHEMA.md

### Step 5. Optional Validation Partner submission

Send only:

    velune_report/shareable_anonymous_report.json

Do not send raw MCAP files, sensor payloads, maps, credentials, or private operational data.

Temporary submission address:

    skagusdn1998@gmail.com

Program details:

    docs/PARTNER_PROGRAM.md

Example feedback report:

    docs/EXAMPLE_FEEDBACK_REPORT.md

Reference cohort policy:

    docs/REFERENCE_COHORT_REGISTRY.md

---

## What You Get

Velune Trace produces local evidence artifacts:

- `summary.md` — human-readable timing evidence summary
- `evidence_windows.json` — ranked evidence windows
- `topic_profile.json` — topic-level timing profile
- `shareable_anonymous_report.json` — optional anonymous report for the Validation Partner Program
- `SCHEMA.md` — report schema description

The shareable report is designed to avoid raw sensor payloads.

---

## What Velune Does Not Do

Velune does not perform root-cause analysis.

Velune does not assign fault.

Velune does not assign liability.

Velune does not make safety-risk determinations.

Velune reports observable timing evidence.

Engineers determine cause.

---

## Start Here

- [Getting Started](docs/GETTING_STARTED.md)
- [Validation Partner Program](docs/PARTNER_PROGRAM.md)
- [Example Feedback Report](docs/EXAMPLE_FEEDBACK_REPORT.md)
- [Reference Cohort Registry](docs/REFERENCE_COHORT_REGISTRY.md)
- [External nuScenes Validation Summary](docs/validation/MASTER_NUSCENES_EXTERNAL_SWEEP_SUMMARY.md)

---



## Validated On

- 10.7 GB benchmark corpus
- 9,237,885 indexed events
- External nuScenes MCAP dataset
- Controlled dropout recovery fixture
- Incremental indexing validation

Velune has been validated on both internal robotics datasets and external autonomous-driving MCAP datasets.

---

## The Problem

Large robotics investigations often begin with one question:

> Where should I start looking?

Engineers may spend hours replaying logs, switching topics, checking timestamps, and manually narrowing the investigation scope.

Velune Trace is built to reduce that search space.

Instead of starting from an entire log corpus, engineers start from ranked evidence windows.

---

## Investigation Workflow

Without Velune

    400GB MCAP
    ↓
    Manual replay
    ↓
    Topic hopping
    ↓
    Timestamp hunting
    ↓
    Investigation

With Velune

    400GB MCAP
    ↓
    validation-report
    ↓
    Ranked evidence windows
    ↓
    Local evidence artifacts
    ↓
    Engineer investigation

The primary evaluation path is:

    ./bin/velune validation-report /path/to/your_log.mcap \
      --export-dir velune_report \
      --window-sec 1 \
      --top 5 \
      --allowed-lateness-sec 2

This produces:

    velune_report/
    ├── summary.md
    ├── shareable_anonymous_report.json
    ├── topic_profile.json
    ├── evidence_windows.json
    └── SCHEMA.md

---

## Advanced CLI Commands

The commands below are lower-level tools for engineers who want to inspect, profile, or extract specific evidence windows manually.

For first-time evaluation, start with `validation-report`.

### Inspect an MCAP file

    ./bin/velune inspect examples/sample.mcap

### Profile topic timing

    ./bin/velune profile incident.mcap \
      --start-sec 1535489296.047916889 \
      --end-sec 1535489315.948405981 \
      --sort max_gap

### Rank timing windows for a specific topic

    ./bin/velune windowed-verify \
      incident.mcap \
      --topic /lidar_top \
      --window-sec 1 \
      --top 5 \
      --export-json windowed_report.json

### Extract a reproducible evidence window

    ./bin/velune evidence-window \
      incident.mcap \
      --topic /lidar_top \
      --start-sec 1535489307.047916889 \
      --end-sec 1535489308.047916889 \
      --expected-count 20 \
      --export-json evidence_window.json

Typical advanced outputs include:

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
