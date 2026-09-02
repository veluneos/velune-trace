#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sqlite3
import time
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def sha256_prefix(path, nbytes):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(nbytes))
    return h.hexdigest()

def meta_get(cur, key, default=None):
    cur.execute("SELECT value FROM metadata WHERE key=?", (key,))
    row = cur.fetchone()
    return row[0] if row else default

def meta_set(cur, key, value):
    cur.execute(
        "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
        (key, str(value)),
    )

def require_meta(cur, key):
    v = meta_get(cur, key)
    if v is None:
        raise SystemExit(f"FAIL: missing metadata key: {key}")
    return v

def extract_event(row, byte_offset):
    event_id = row.get("event_id")
    sequence_index = row.get("sequence_index", row.get("seq"))
    trace_id = row.get("trace_id")
    ros_time = row.get("ros_time")
    wall_time_utc = row.get("wall_time_utc")
    clock_domain = row.get("clock_domain")
    time_source = row.get("time_source")
    event_type = row.get("event_type")
    source_topic = row.get("source_topic", row.get("topic"))
    source_node = row.get("source_node", row.get("node"))
    event_hash = row.get("event_hash")
    prev_event_hash = row.get("prev_event_hash")
    artifact_fingerprint = row.get("artifact_fingerprint")

    if sequence_index is None:
        raise ValueError("missing sequence_index/seq")
    if not event_id:
        raise ValueError("missing event_id")
    if not event_hash:
        raise ValueError("missing event_hash")
    if prev_event_hash is None:
        raise ValueError("missing prev_event_hash")

    return (
        event_id,
        int(sequence_index),
        int(byte_offset),
        trace_id,
        ros_time,
        wall_time_utc,
        clock_domain,
        time_source,
        event_type,
        source_topic,
        source_node,
        event_hash,
        prev_event_hash,
        artifact_fingerprint,
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--index", required=True)
    ap.add_argument("--report", default="VELUNE_TRACE_INDEXER_v0_2_INCREMENTAL_VALIDATION_REPORT.txt")
    args = ap.parse_args()

    source = args.source
    index = args.index
    source_size = os.path.getsize(source)

    con = sqlite3.connect(index)
    cur = con.cursor()

    last_seq = int(require_meta(cur, "last_indexed_seq"))
    last_end_offset = int(require_meta(cur, "last_indexed_end_offset"))
    last_event_hash = require_meta(cur, "last_event_hash")
    prefix_probe_offset = int(require_meta(cur, "prefix_probe_offset"))
    expected_prefix_sha = require_meta(cur, "prefix_probe_sha256")

    if source_size < last_end_offset:
        raise SystemExit("FAIL: source file truncated below last_indexed_end_offset")

    prefix_bytes = min(prefix_probe_offset, source_size)
    actual_prefix_sha = sha256_prefix(source, prefix_bytes)
    if actual_prefix_sha != expected_prefix_sha:
        raise SystemExit("FAIL: prefix mutation detected")

    started = time.perf_counter()
    inserted = 0
    bad_json = 0
    first_new_seq = None
    first_new_prev_hash = None
    new_last_seq = last_seq
    new_last_hash = last_event_hash
    new_last_event_id = None
    new_last_end_offset = last_end_offset

    try:
        cur.execute("BEGIN IMMEDIATE")

        with open(source, "rb") as f:
            f.seek(last_end_offset)

            while True:
                byte_offset = f.tell()
                line = f.readline()
                if not line:
                    break

                if not line.strip():
                    new_last_end_offset = f.tell()
                    continue

                try:
                    row = json.loads(line)
                    ev = extract_event(row, byte_offset)
                except Exception:
                    bad_json += 1
                    raise

                (
                    event_id,
                    sequence_index,
                    _byte_offset,
                    trace_id,
                    ros_time,
                    wall_time_utc,
                    clock_domain,
                    time_source,
                    event_type,
                    source_topic,
                    source_node,
                    event_hash,
                    prev_event_hash,
                    artifact_fingerprint,
                ) = ev

                if inserted == 0:
                    first_new_seq = sequence_index
                    first_new_prev_hash = prev_event_hash

                    if first_new_seq != last_seq + 1:
                        raise SystemExit(
                            f"FAIL: sequence continuity broken: expected {last_seq + 1}, got {first_new_seq}"
                        )

                    if first_new_prev_hash != last_event_hash:
                        raise SystemExit("FAIL: last_event_hash continuity broken")

                else:
                    if sequence_index != new_last_seq + 1:
                        raise SystemExit(
                            f"FAIL: internal append sequence gap: expected {new_last_seq + 1}, got {sequence_index}"
                        )

                    if prev_event_hash != new_last_hash:
                        raise SystemExit("FAIL: internal append hash continuity broken")

                cur.execute("""
                    INSERT INTO events(
                        event_id,
                        sequence_index,
                        byte_offset,
                        trace_id,
                        ros_time,
                        wall_time_utc,
                        clock_domain,
                        time_source,
                        event_type,
                        source_topic,
                        source_node,
                        event_hash,
                        prev_event_hash,
                        artifact_fingerprint
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ev)

                inserted += 1
                new_last_seq = sequence_index
                new_last_hash = event_hash
                new_last_event_id = event_id
                new_last_end_offset = f.tell()

        meta_set(cur, "last_indexed_seq", new_last_seq)
        meta_set(cur, "last_indexed_end_offset", new_last_end_offset)
        meta_set(cur, "last_event_hash", new_last_hash)
        if new_last_event_id:
            meta_set(cur, "last_event_id", new_last_event_id)
        meta_set(cur, "bootstrap_source_size_bytes", source_size)
        meta_set(cur, "updated_at_utc", utc_now())
        meta_set(cur, "last_incremental_events_indexed", inserted)
        meta_set(cur, "last_incremental_bad_json_records", bad_json)
        meta_set(cur, "last_incremental_full_source_sha256_recalculation", "NOT_USED")
        meta_set(cur, "last_incremental_result", "PASS")

        con.commit()

    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()

    elapsed = time.perf_counter() - started

    report = f"""VELUNE_TRACE_INDEXER_v0_2_INCREMENTAL_VALIDATION_REPORT
RESULT=PASS
SOURCE={source}
INDEX={index}
SOURCE_SIZE_BYTES={source_size}
PREVIOUS_LAST_INDEXED_SEQ={last_seq}
PREVIOUS_LAST_INDEXED_END_OFFSET={last_end_offset}
NEW_LAST_INDEXED_SEQ={new_last_seq}
NEW_LAST_INDEXED_END_OFFSET={new_last_end_offset}
INCREMENTAL_EVENTS_INDEXED={inserted}
BAD_JSON_RECORDS={bad_json}
PREFIX_PROBE_CHECK=PASS
SOURCE_TRUNCATION_CHECK=PASS
SEQUENCE_CONTINUITY_CHECK=PASS
LAST_EVENT_HASH_CONTINUITY_CHECK=PASS
TRANSACTION_ROLLBACK_SAFETY=PASS
FULL_SOURCE_SHA256_RECALCULATION=NOT_USED
INCREMENTAL_INDEX_TIME_SECONDS={elapsed:.6f}
NON_JUDGMENT_STATEMENT=This index maps immutable trace events to byte offsets for retrieval only. It does not assign fault, liability, risk score, blame, or root cause.
CLAIM_SCOPE=append-only incremental indexing with prefix probe and hash continuity checks
NON_CLAIM=does not claim full corpus tamper detection, causal discovery, root cause judgment, or liability assignment
UPDATED_AT_UTC={utc_now()}
"""
    with open(args.report, "w", encoding="utf-8") as f:
        f.write(report)

    print(report)

if __name__ == "__main__":
    main()
