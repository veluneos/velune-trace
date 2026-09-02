#!/usr/bin/env python3
import json
import time
import sqlite3
import argparse
from pathlib import Path

SCHEMA_VERSION = "VELUNE_EXTRACTED_CHAIN_v0.2"

PRESETS = {
    "minimal_context": {
        "scan_radius": 20,
        "prev_motion": 2,
        "prev_perception": 1,
        "next_motion": 4,
        "next_perception": 1,
    },
    "command_motion_scan": {
        "scan_radius": 80,
        "prev_motion": 3,
        "prev_perception": 1,
        "next_motion": 10,
        "next_perception": 2,
    },
    "motion_perception_context": {
        "scan_radius": 120,
        "prev_motion": 8,
        "prev_perception": 3,
        "next_motion": 12,
        "next_perception": 3,
    },
    "wide_context": {
        "scan_radius": 250,
        "prev_motion": 20,
        "prev_perception": 5,
        "next_motion": 30,
        "next_perception": 5,
    },
}

def read_event_from_open_file(f, byte_offset):
    f.seek(byte_offset)
    raw = f.readline()
    return json.loads(raw.decode("utf-8"))

def apply_preset(args):
    if not args.preset:
        return

    preset = PRESETS[args.preset]

    args.scan_radius = preset["scan_radius"]
    args.prev_motion = preset["prev_motion"]
    args.prev_perception = preset["prev_perception"]
    args.next_motion = preset["next_motion"]
    args.next_perception = preset["next_perception"]

def main():
    ap = argparse.ArgumentParser(description="Velune Chain Extractor v0.2 - focused candidate chain exporter")
    ap.add_argument("--log", required=True)
    ap.add_argument("--index", required=True)
    ap.add_argument("--seed-event", required=True)
    ap.add_argument("--preset", choices=sorted(PRESETS.keys()), default=None)
    ap.add_argument("--scan-radius", type=int, default=80)
    ap.add_argument("--prev-motion", type=int, default=3)
    ap.add_argument("--prev-perception", type=int, default=1)
    ap.add_argument("--next-motion", type=int, default=10)
    ap.add_argument("--next-perception", type=int, default=2)
    ap.add_argument("--include-topics", default="/cmd_vel,/odom,/scan")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    apply_preset(args)

    started = time.time()

    log_path = Path(args.log)
    index_path = Path(args.index)
    out_path = Path(args.out)

    include_topics = set(x.strip() for x in args.include_topics.split(",") if x.strip())

    con = sqlite3.connect(str(index_path))
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    seed = cur.execute(
        "SELECT * FROM events WHERE event_id=? LIMIT 1",
        (args.seed_event,)
    ).fetchone()

    if seed is None:
        raise SystemExit("SEED_EVENT_NOT_FOUND")

    seed_seq = seed["sequence_index"]
    if seed_seq is None:
        raise SystemExit("SEED_EVENT_HAS_NO_SEQUENCE_INDEX")

    start_seq = max(0, seed_seq - args.scan_radius)
    end_seq = seed_seq + args.scan_radius

    rows = cur.execute(
        """
        SELECT * FROM events
        WHERE sequence_index BETWEEN ? AND ?
        ORDER BY sequence_index ASC
        """,
        (start_seq, end_seq)
    ).fetchall()

    before = []
    seed_event = None
    after = []
    skipped_by_topic = 0

    with open(log_path, "rb") as log_file:
        for r in rows:
            if r["source_topic"] not in include_topics:
                skipped_by_topic += 1
                continue

            e = read_event_from_open_file(log_file, r["byte_offset"])
            seq = e.get("sequence_index")

            if seq < seed_seq:
                before.append(e)
            elif seq == seed_seq:
                seed_event = e
            else:
                after.append(e)

    if seed_event is None:
        raise SystemExit("SEED_EVENT_NOT_RECONSTRUCTED_FROM_LOG")

    selected_before = []
    prev_motion_count = 0
    prev_perception_count = 0

    for e in reversed(before):
        et = e.get("event_type")
        if et == "MOTION_SUMMARY" and prev_motion_count < args.prev_motion:
            selected_before.append(e)
            prev_motion_count += 1
        elif et == "PERCEPTION_SUMMARY" and prev_perception_count < args.prev_perception:
            selected_before.append(e)
            prev_perception_count += 1

        if prev_motion_count >= args.prev_motion and prev_perception_count >= args.prev_perception:
            break

    selected_before = list(reversed(selected_before))

    selected_after = []
    next_motion_count = 0
    next_perception_count = 0

    for e in after:
        et = e.get("event_type")
        if et == "MOTION_SUMMARY" and next_motion_count < args.next_motion:
            selected_after.append(e)
            next_motion_count += 1
        elif et == "PERCEPTION_SUMMARY" and next_perception_count < args.next_perception:
            selected_after.append(e)
            next_perception_count += 1

        if next_motion_count >= args.next_motion and next_perception_count >= args.next_perception:
            break

    events = selected_before + [seed_event] + selected_after
    elapsed = time.time() - started
    con.close()

    chain = {
        "schema_version": SCHEMA_VERSION,
        "chain_type": "focused_candidate_chain",
        "source_log": str(log_path),
        "source_index": str(index_path),
        "seed_event_id": args.seed_event,
        "seed_sequence_index": seed_seq,
        "focus_policy": {
            "mode": "sequence_neighborhood_type_filtered",
            "preset": args.preset,
            "preset_type": "observation_context_only",
            "scan_radius": args.scan_radius,
            "previous_motion_limit": args.prev_motion,
            "previous_perception_limit": args.prev_perception,
            "next_motion_limit": args.next_motion,
            "next_perception_limit": args.next_perception,
            "include_topics": sorted(include_topics),
        },
        "retrieval_summary": {
            "rows_scanned_from_index_window": len(rows),
            "events_returned": len(events),
            "previous_events_returned": len(selected_before),
            "next_events_returned": len(selected_after),
            "skipped_by_topic": skipped_by_topic,
            "extract_time_seconds": round(elapsed, 6),
            "file_handle_reuse": True,
        },
        "events": events,
        "policy": {
            "source_log_mutated": False,
            "index_disposable": True,
            "focused_chain_used": True,
            "sequence_window_used": True,
            "time_window_used": False,
            "causal_discovery_used": False,
            "analysis_preset_used": False,
            "observation_preset_used": bool(args.preset),
            "ranking_used": False,
            "risk_scoring_used": False,
            "root_cause_used": False,
            "liability_used": False,
        },
        "non_judgment_statement": (
            "This extractor exports a focused candidate event chain by sequence neighborhood and observation-type limits only. "
            "Presets are observation-context presets, not incident analysis modes. "
            "It does not assign fault, liability, risk score, blame, causal discovery, or root cause."
        )
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(chain, ensure_ascii=False, indent=2), encoding="utf-8")

    print("VELUNE_CHAIN_EXTRACTOR_V0_2_REPORT")
    print(f"SEED_EVENT={args.seed_event}")
    print(f"SEED_SEQUENCE_INDEX={seed_seq}")
    print(f"PRESET={args.preset}")
    print(f"PRESET_TYPE=observation_context_only")
    print(f"SCAN_RADIUS={args.scan_radius}")
    print(f"ROWS_SCANNED_FROM_INDEX_WINDOW={len(rows)}")
    print(f"EVENTS_RETURNED={len(events)}")
    print(f"PREVIOUS_EVENTS_RETURNED={len(selected_before)}")
    print(f"NEXT_EVENTS_RETURNED={len(selected_after)}")
    print(f"SKIPPED_BY_TOPIC={skipped_by_topic}")
    print(f"OUTPUT={out_path}")
    print(f"EXTRACT_TIME_SECONDS={round(elapsed, 6)}")
    print("FILE_HANDLE_REUSE=TRUE")
    print("FOCUSED_CHAIN_USED=TRUE")
    print("TIME_WINDOW_USED=FALSE")
    print("CAUSAL_DISCOVERY_USED=FALSE")
    print("ANALYSIS_PRESET_USED=FALSE")
    print("OBSERVATION_PRESET_USED=" + ("TRUE" if args.preset else "FALSE"))
    print("RANKING_USED=FALSE")
    print("RISK_SCORING_USED=FALSE")
    print("ROOT_CAUSE_USED=FALSE")
    print("LIABILITY_USED=FALSE")
    print("RESULT=PASS" if len(events) > 0 else "RESULT=FAIL")

if __name__ == "__main__":
    main()
