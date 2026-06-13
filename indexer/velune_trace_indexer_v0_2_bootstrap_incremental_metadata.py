#!/usr/bin/env python3
import sqlite3
import hashlib
import os
import argparse
from datetime import datetime, timezone

PREFIX_PROBE_BYTES = 1024 * 1024

def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def sha256_prefix(path, nbytes):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(nbytes))
    return h.hexdigest()

def upsert_meta(cur, key, value):
    cur.execute(
        "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
        (key, str(value)),
    )

def get_line_end_offset(path, start_offset):
    with open(path, "rb") as f:
        f.seek(start_offset)
        line = f.readline()
        if not line:
            raise SystemExit("FAIL: No line found at last indexed byte_offset")
        return start_offset + len(line), len(line)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--index", required=True)
    args = ap.parse_args()

    source = args.source
    index = args.index

    source_size = os.path.getsize(source)

    con = sqlite3.connect(index)
    cur = con.cursor()

    cur.execute("""
        SELECT sequence_index, byte_offset, event_id, event_hash, prev_event_hash
        FROM events
        ORDER BY sequence_index DESC
        LIMIT 1
    """)
    last_by_seq = cur.fetchone()

    cur.execute("""
        SELECT sequence_index, byte_offset, event_id, event_hash, prev_event_hash
        FROM events
        ORDER BY byte_offset DESC
        LIMIT 1
    """)
    last_by_offset = cur.fetchone()

    if not last_by_seq:
        raise SystemExit("FAIL: events table is empty")

    if last_by_seq != last_by_offset:
        raise SystemExit("FAIL: Last event by sequence_index differs from last event by byte_offset")

    last_seq, last_start_offset, last_event_id, last_event_hash, last_prev_event_hash = last_by_seq

    if source_size <= last_start_offset:
        raise SystemExit("FAIL: Source file truncated. Last indexed offset is out of bounds.")

    last_end_offset, last_line_bytes = get_line_end_offset(source, last_start_offset)

    if last_end_offset > source_size:
        raise SystemExit("FAIL: Last indexed line exceeds current source size")

    prefix_bytes = min(PREFIX_PROBE_BYTES, source_size)
    prefix_sha = sha256_prefix(source, prefix_bytes)

    cur.execute("BEGIN IMMEDIATE")

    upsert_meta(cur, "schema_version", "VELUNE_TRACE_INDEX_SQLITE_v0.2_INCREMENTAL_BOOTSTRAPPED")
    upsert_meta(cur, "incremental_indexing", "SUPPORTED_IN_V0_2")
    upsert_meta(cur, "incremental_mode", "APPEND_ONLY")
    upsert_meta(cur, "full_source_sha256_recalculation", "NOT_USED_IN_INCREMENTAL_PATH")

    upsert_meta(cur, "last_indexed_seq", last_seq)
    upsert_meta(cur, "last_indexed_start_offset", last_start_offset)
    upsert_meta(cur, "last_indexed_end_offset", last_end_offset)
    upsert_meta(cur, "last_indexed_line_bytes", last_line_bytes)
    upsert_meta(cur, "last_event_id", last_event_id)
    upsert_meta(cur, "last_event_hash", last_event_hash)
    upsert_meta(cur, "last_prev_event_hash", last_prev_event_hash)

    upsert_meta(cur, "bootstrap_source_size_bytes", source_size)
    upsert_meta(cur, "prefix_probe_offset", prefix_bytes)
    upsert_meta(cur, "prefix_probe_sha256", prefix_sha)

    upsert_meta(cur, "updated_at_utc", utc_now())
    upsert_meta(cur, "v0_2_claim_scope", "append_only_incremental_indexing_with_prefix_probe_and_hash_continuity")
    upsert_meta(cur, "v0_2_non_claim", "does_not_claim_full_corpus_tamper_detection_or_root_cause_judgment")

    con.commit()
    con.close()

    print("VELUNE_TRACE_INDEXER_v0_2_INCREMENTAL_METADATA_BOOTSTRAP")
    print("RESULT=PASS")
    print(f"SOURCE={source}")
    print(f"INDEX={index}")
    print(f"BOOTSTRAP_SOURCE_SIZE_BYTES={source_size}")
    print(f"LAST_INDEXED_SEQ={last_seq}")
    print(f"LAST_INDEXED_START_OFFSET={last_start_offset}")
    print(f"LAST_INDEXED_END_OFFSET={last_end_offset}")
    print(f"LAST_INDEXED_LINE_BYTES={last_line_bytes}")
    print(f"LAST_EVENT_ID={last_event_id}")
    print(f"LAST_EVENT_HASH={last_event_hash}")
    print(f"PREFIX_PROBE_OFFSET={prefix_bytes}")
    print(f"PREFIX_PROBE_SHA256={prefix_sha}")
    print("FULL_SOURCE_SHA256_RECALCULATION=NOT_USED_IN_INCREMENTAL_PATH")

if __name__ == "__main__":
    main()
