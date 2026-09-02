#!/usr/bin/env python3
import json
import time
import sqlite3
import argparse
import hashlib
import os
from pathlib import Path
from collections import Counter

SCHEMA_VERSION = "VELUNE_TRACE_INDEX_SQLITE_v0.1"

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def emit(lines, report_log=None):
    text = "\n".join(lines)
    print(text)
    if report_log:
        Path(report_log).parent.mkdir(parents=True, exist_ok=True)
        Path(report_log).write_text(text + "\n", encoding="utf-8")

def main():
    ap = argparse.ArgumentParser(description="Velune Trace SQLite Indexer v0.1")
    ap.add_argument("input_jsonl")
    ap.add_argument("--out", default=None)
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--report-log", default=None)
    ap.add_argument("--commit-every-records", type=int, default=50000)
    ap.add_argument("--commit-every-bytes", type=int, default=100 * 1024 * 1024)
    ap.add_argument("--busy-timeout-ms", type=int, default=30000)
    args = ap.parse_args()

    src = Path(args.input_jsonl)
    dst = Path(args.out) if args.out else src.with_suffix(src.suffix + ".index.sqlite")
    tmp = Path(str(dst) + ".tmp")
    lock = Path(str(dst) + ".lock")

    if dst.exists() and not args.replace:
        raise SystemExit(f"INDEX_EXISTS: {dst} already exists. Use --replace to rebuild.")

    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
    except FileExistsError:
        raise SystemExit(f"INDEX_LOCKED: {lock} exists. Another indexer may be running.")

    try:
        if tmp.exists():
            tmp.unlink()

        started = time.time()
        source_sha256 = sha256_file(src)

        con = sqlite3.connect(str(tmp), timeout=args.busy_timeout_ms / 1000)
        cur = con.cursor()

        cur.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        PRAGMA temp_store=FILE;

        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE events (
            event_id TEXT,
            sequence_index INTEGER,
            byte_offset INTEGER NOT NULL,
            trace_id TEXT,
            ros_time REAL,
            wall_time_utc TEXT,
            clock_domain TEXT,
            time_source TEXT,
            event_type TEXT,
            source_topic TEXT,
            source_node TEXT,
            event_hash TEXT,
            prev_event_hash TEXT,
            artifact_fingerprint TEXT
        );

        CREATE INDEX idx_event_id ON events(event_id);
        CREATE INDEX idx_sequence_index ON events(sequence_index);
        CREATE INDEX idx_ros_time ON events(ros_time);
        CREATE INDEX idx_event_type ON events(event_type);
        CREATE INDEX idx_topic ON events(source_topic);

        CREATE TABLE sequence_gaps (
            prev_sequence INTEGER,
            next_sequence INTEGER,
            gap_size INTEGER
        );

        CREATE TABLE summary_counts (
            category TEXT,
            name TEXT,
            count INTEGER,
            PRIMARY KEY(category, name)
        );
        """)

        total = 0
        bad_json = 0
        prev_seq = None
        sequence_gap_count = 0
        last_commit_record = 0
        last_commit_offset = 0

        event_types = Counter()
        topics = Counter()
        nodes = Counter()
        clock_domains = Counter()
        time_sources = Counter()

        min_ros_time = None
        max_ros_time = None

        with src.open("rb") as f:
            while True:
                byte_offset = f.tell()
                raw = f.readline()
                if not raw:
                    break
                if not raw.strip():
                    continue

                try:
                    e = json.loads(raw.decode("utf-8"))
                except Exception:
                    bad_json += 1
                    continue

                total += 1

                seq = e.get("sequence_index")
                ros_time = e.get("ros_time")
                event_type = e.get("event_type", "UNKNOWN")
                topic = e.get("source_topic", "UNKNOWN")
                node = e.get("source_node", "UNKNOWN")
                clock_domain = e.get("clock_domain", "MISSING")
                time_source = e.get("time_source", "MISSING")

                if isinstance(seq, int):
                    if prev_seq is not None and seq != prev_seq + 1:
                        gap = seq - prev_seq - 1
                        if gap > 0:
                            sequence_gap_count += 1
                            cur.execute("INSERT INTO sequence_gaps VALUES (?, ?, ?)", (prev_seq, seq, gap))
                    prev_seq = seq

                if isinstance(ros_time, (int, float)):
                    min_ros_time = ros_time if min_ros_time is None else min(min_ros_time, ros_time)
                    max_ros_time = ros_time if max_ros_time is None else max(max_ros_time, ros_time)

                cur.execute("""
                    INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    e.get("event_id"),
                    seq,
                    byte_offset,
                    e.get("trace_id"),
                    ros_time,
                    e.get("wall_time_utc"),
                    clock_domain,
                    time_source,
                    event_type,
                    topic,
                    node,
                    e.get("event_hash"),
                    e.get("prev_event_hash"),
                    e.get("artifact_fingerprint"),
                ))

                event_types[event_type] += 1
                topics[topic] += 1
                nodes[node] += 1
                clock_domains[clock_domain] += 1
                time_sources[time_source] += 1

                if (
                    total - last_commit_record >= args.commit_every_records
                    or byte_offset - last_commit_offset >= args.commit_every_bytes
                ):
                    con.commit()
                    last_commit_record = total
                    last_commit_offset = byte_offset

        for category, counter in [
            ("event_type", event_types),
            ("topic", topics),
            ("node", nodes),
            ("clock_domain", clock_domains),
            ("time_source", time_sources),
        ]:
            for name, count in counter.items():
                cur.execute("INSERT INTO summary_counts VALUES (?, ?, ?)", (category, name, count))

        elapsed = time.time() - started

        metadata = {
            "schema_version": SCHEMA_VERSION,
            "source_file": str(src),
            "source_size_bytes": str(src.stat().st_size),
            "source_sha256": source_sha256,
            "created_at_unix": str(time.time()),
            "build_time_seconds": str(round(elapsed, 6)),
            "total_events": str(total),
            "bad_json_records": str(bad_json),
            "sequence_gap_count": str(sequence_gap_count),
            "ros_time_min": str(min_ros_time),
            "ros_time_max": str(max_ros_time),
            "storage": "sqlite",
            "source_log_mutated": "FALSE",
            "index_disposable": "TRUE",
            "atomic_build": "TRUE",
            "replace_requested": str(args.replace).upper(),
            "incremental_indexing": "NOT_SUPPORTED_IN_V0_1",
            "partitioning": "NOT_SUPPORTED_IN_V0_1",
            "v0_2_roadmap": "incremental_append_indexing, partitioned_index_by_chunk, chunk_manifest",
            "ranking_used": "FALSE",
            "risk_scoring_used": "FALSE",
            "root_cause_used": "FALSE",
            "liability_used": "FALSE",
            "non_judgment_statement": "This index maps immutable trace events to byte offsets for retrieval only. It does not assign fault, liability, risk score, blame, or root cause.",
        }

        for k, v in metadata.items():
            cur.execute("INSERT INTO metadata VALUES (?, ?)", (k, v))

        con.commit()
        indexed_total = cur.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        con.close()

        if indexed_total != total:
            raise SystemExit(f"INTEGRITY_FAIL: indexed_total={indexed_total} total={total}")

        if dst.exists() and args.replace:
            dst.unlink()

        os.replace(tmp, dst)

        lines = [
            "TRACE_INDEXER_V0_1_SQLITE_REPORT",
            f"INPUT={src}",
            f"OUTPUT={dst}",
            f"SOURCE_SIZE_BYTES={src.stat().st_size}",
            f"SOURCE_SHA256={source_sha256}",
            f"INDEX_SIZE_BYTES={dst.stat().st_size}",
            f"EVENTS_INDEXED={total}",
            f"BAD_JSON_RECORDS={bad_json}",
            f"SEQUENCE_GAP_COUNT={sequence_gap_count}",
            f"EVENT_TYPES_INDEXED={len(event_types)}",
            f"TOPICS_INDEXED={len(topics)}",
            f"NODES_INDEXED={len(nodes)}",
            f"BUILD_TIME_SECONDS={round(elapsed, 6)}",
            "STORAGE=sqlite",
            "ATOMIC_BUILD=TRUE",
            "SOURCE_LOG_MUTATED=FALSE",
            "INDEX_DISPOSABLE=TRUE",
            "INCREMENTAL_INDEXING=NOT_SUPPORTED_IN_V0_1",
            "PARTITIONING=NOT_SUPPORTED_IN_V0_1",
            "V0_2_ROADMAP=incremental_append_indexing,partitioned_index_by_chunk,chunk_manifest",
            "RANKING_USED=FALSE",
            "RISK_SCORING_USED=FALSE",
            "ROOT_CAUSE_USED=FALSE",
            "LIABILITY_USED=FALSE",
            "RESULT=PASS" if total > 0 and bad_json == 0 else "RESULT=FAIL",
        ]
        emit(lines, args.report_log)

    finally:
        if lock.exists():
            lock.unlink()
        if tmp.exists():
            tmp.unlink()

if __name__ == "__main__":
    main()
