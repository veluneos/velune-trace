#!/usr/bin/env python3
import argparse
import heapq
import json
import math
import sys
from pathlib import Path
from datetime import datetime, timezone

from velune_trace.adapters.mcap_reader import read_messages


SCHEMA_NAME = "velune.anonymous_validation_report"
SCHEMA_VERSION = "0.2.0"
SEMANTICS = "observed_timing_metadata_only"


def sec_to_ns(sec: float) -> int:
    return int(sec * 1_000_000_000)


def ns_to_sec(ns: int) -> float:
    return ns / 1_000_000_000


def int_stdev_ns(count: int, total: int, total_sq: int) -> int:
    if count <= 1:
        return 0
    numerator = count * total_sq - total * total
    if numerator <= 0:
        return 0
    variance = numerator // (count * count)
    return math.isqrt(variance)


def load_topic_profile(path):
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        raise ValueError(f"topic profile not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def profile_for_topic(topic_profile, topic):
    value = topic_profile.get(topic, {})
    return {
        "sensor_category": value.get("sensor_category", "unknown"),
        "expected_hz": value.get("expected_hz"),
    }


def expected_count_from_profile(meta, window_sec):
    hz = meta.get("expected_hz")
    if hz is None:
        return None
    try:
        return max(1, int(round(float(hz) * window_sec)))
    except Exception:
        return None


def observed_score(count, expected_count, max_gap_ns, jitter_ns):
    count_drop_ratio = 0.0
    if expected_count and expected_count > 0:
        count_drop_ratio = max(0.0, (expected_count - count) / expected_count)

    return (
        count_drop_ratio * 10.0
        + ns_to_sec(max_gap_ns) * 10.0
        + ns_to_sec(jitter_ns) * 5.0
    )


def update_topk(heap, item, top):
    score = item["observed_irregularity_score"]
    entry = (score, item["topic"], item["window"], item)
    if len(heap) < top:
        heapq.heappush(heap, entry)
    elif score > heap[0][0]:
        heapq.heapreplace(heap, entry)


def finalize_window(topic, w, expected_count, top_heap, top):
    jitter_ns = int_stdev_ns(w["gap_count"], w["gap_sum_ns"], w["gap_sum_sq_ns"])
    score = observed_score(
        count=w["count"],
        expected_count=expected_count,
        max_gap_ns=w["max_gap_ns"],
        jitter_ns=jitter_ns,
    )

    item = {
        "topic": topic,
        "window": int(w["window"]),
        "start_ns": int(w["start_ns"]),
        "end_ns": int(w["end_ns"]),
        "start_sec": ns_to_sec(w["start_ns"]),
        "end_sec": ns_to_sec(w["end_ns"]),
        "count": int(w["count"]),
        "expected_count": expected_count,
        "count_ratio": (w["count"] / expected_count) if expected_count else None,
        "max_gap_ns": int(w["max_gap_ns"]),
        "max_gap_sec": ns_to_sec(w["max_gap_ns"]),
        "jitter_ns": int(jitter_ns),
        "jitter_sec": ns_to_sec(jitter_ns),
        "observed_irregularity_score": float(score),
        "score_semantics": "ranking_heuristic_only_no_root_cause_inference",
    }
    update_topk(top_heap, item, top)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="velune validation-report",
        description="Generate bounded streaming anonymous validation reports from an MCAP file."
    )
    parser.add_argument("file", help="Input MCAP file")
    parser.add_argument("--export-dir", default="velune_report", help="Output report directory")
    parser.add_argument("--window-sec", type=float, default=1.0, help="Window size in seconds")
    parser.add_argument("--top", type=int, default=5, help="Top evidence windows per topic")
    parser.add_argument("--allowed-lateness-sec", type=float, default=2.0, help="Allowed lateness before flushing old windows")
    parser.add_argument("--topic-profile", default=None, help="Optional JSON with topic metadata such as expected_hz and sensor_category")
    args = parser.parse_args(argv)

    input_path = Path(args.file)
    export_dir = Path(args.export_dir)

    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}", file=sys.stderr)
        return 2

    if args.window_sec <= 0:
        print("[ERROR] --window-sec must be greater than 0", file=sys.stderr)
        return 2

    if args.allowed_lateness_sec < 0:
        print("[ERROR] --allowed-lateness-sec must be >= 0", file=sys.stderr)
        return 2

    try:
        topic_profile_input = load_topic_profile(args.topic_profile)
    except Exception as e:
        print(f"[ERROR] Invalid topic profile: {e}", file=sys.stderr)
        return 2

    window_ns = sec_to_ns(args.window_sec)
    allowed_lateness_ns = sec_to_ns(args.allowed_lateness_sec)
    export_dir.mkdir(parents=True, exist_ok=True)

    global_start_ns = None
    max_seen_ns = None

    topic_stats = {}
    active_windows = {}
    top_windows = {}
    finalized_window_counts = {}
    inferred_count_samples = {}

    total_messages = 0
    parse_errors = 0
    late_dropped_count = 0
    out_of_order_total = 0
    max_active_windows_observed = 0

    def ensure_topic(topic, t_ns):
        if topic in topic_stats:
            return

        meta = profile_for_topic(topic_profile_input, topic)
        expected_count = expected_count_from_profile(meta, args.window_sec)

        topic_stats[topic] = {
            "count": 0,
            "first_ns": t_ns,
            "last_ns": t_ns,
            "previous_ns": None,
            "gap_count": 0,
            "gap_sum_ns": 0,
            "gap_sum_sq_ns": 0,
            "max_gap_ns": 0,
            "out_of_order_count": 0,
            "late_dropped_count": 0,
            "sensor_category": meta["sensor_category"],
            "expected_hz": meta["expected_hz"],
            "expected_count_per_window": expected_count,
            "expected_count_source": "topic_profile" if expected_count else "inferred_from_observed_median",
        }
        active_windows[topic] = {}
        top_windows[topic] = []
        finalized_window_counts[topic] = 0
        inferred_count_samples[topic] = []

    def make_window(window_id):
        start_ns = global_start_ns + window_id * window_ns
        return {
            "window": int(window_id),
            "start_ns": int(start_ns),
            "end_ns": int(start_ns + window_ns),
            "count": 0,
            "first_ns": None,
            "last_ns": None,
            "previous_ns": None,
            "gap_count": 0,
            "gap_sum_ns": 0,
            "gap_sum_sq_ns": 0,
            "max_gap_ns": 0,
        }

    def flush_old_windows(force=False):
        nonlocal max_active_windows_observed
        if max_seen_ns is None:
            return

        flush_before_ns = max_seen_ns - allowed_lateness_ns

        for topic, windows in active_windows.items():
            stats = topic_stats[topic]
            expected_count = stats["expected_count_per_window"]

            to_delete = []
            for window_id, w in windows.items():
                if force or w["end_ns"] <= flush_before_ns:
                    if expected_count is None:
                        inferred_count_samples[topic].append(w["count"])
                        sample = sorted(inferred_count_samples[topic])
                        expected_count = sample[len(sample) // 2] if sample else 0
                        stats["expected_count_per_window"] = expected_count

                    finalize_window(topic, w, expected_count, top_windows[topic], args.top)
                    finalized_window_counts[topic] += 1
                    to_delete.append(window_id)

            for window_id in to_delete:
                del windows[window_id]

        current_active = sum(len(w) for w in active_windows.values())
        max_active_windows_observed = max(max_active_windows_observed, current_active)

    try:
        for msg in read_messages(input_path):
            try:
                topic = msg["topic"]
                t_ns = int(msg["log_time"])
            except Exception:
                parse_errors += 1
                continue

            if global_start_ns is None:
                global_start_ns = t_ns
                max_seen_ns = t_ns

            if t_ns > max_seen_ns:
                max_seen_ns = t_ns

            total_messages += 1
            ensure_topic(topic, t_ns)

            stats = topic_stats[topic]

            if t_ns < stats["last_ns"]:
                stats["out_of_order_count"] += 1
                out_of_order_total += 1

            if t_ns < max_seen_ns - allowed_lateness_ns:
                stats["late_dropped_count"] += 1
                late_dropped_count += 1
                continue

            prev = stats["previous_ns"]
            if prev is not None and t_ns >= prev:
                gap = t_ns - prev
                stats["gap_count"] += 1
                stats["gap_sum_ns"] += gap
                stats["gap_sum_sq_ns"] += gap * gap
                stats["max_gap_ns"] = max(stats["max_gap_ns"], gap)

            stats["count"] += 1
            stats["first_ns"] = min(stats["first_ns"], t_ns)
            stats["last_ns"] = max(stats["last_ns"], t_ns)
            stats["previous_ns"] = t_ns

            window_id = (t_ns - global_start_ns) // window_ns
            if window_id < 0:
                stats["late_dropped_count"] += 1
                late_dropped_count += 1
                continue

            windows = active_windows[topic]
            if window_id not in windows:
                windows[window_id] = make_window(window_id)

            w = windows[window_id]
            w_prev = w["previous_ns"]
            if w_prev is not None and t_ns >= w_prev:
                w_gap = t_ns - w_prev
                w["gap_count"] += 1
                w["gap_sum_ns"] += w_gap
                w["gap_sum_sq_ns"] += w_gap * w_gap
                w["max_gap_ns"] = max(w["max_gap_ns"], w_gap)

            w["count"] += 1
            w["first_ns"] = t_ns if w["first_ns"] is None else min(w["first_ns"], t_ns)
            w["last_ns"] = t_ns if w["last_ns"] is None else max(w["last_ns"], t_ns)
            w["previous_ns"] = t_ns

            flush_old_windows(force=False)

    except Exception as e:
        print("[ERROR] Invalid or unreadable MCAP file.", file=sys.stderr)
        print(f"[ERROR] Detail: {e}", file=sys.stderr)
        return 1

    if total_messages == 0:
        print("[ERROR] No readable messages found.", file=sys.stderr)
        return 1

    flush_old_windows(force=True)

    topic_profile = {}
    evidence_windows = {}

    for topic, stats in topic_stats.items():
        duration_ns = max(0, stats["last_ns"] - stats["first_ns"])
        avg_gap_ns = stats["gap_sum_ns"] // stats["gap_count"] if stats["gap_count"] else 0
        jitter_ns = int_stdev_ns(stats["gap_count"], stats["gap_sum_ns"], stats["gap_sum_sq_ns"])

        topic_profile[topic] = {
            "sensor_category": stats["sensor_category"],
            "expected_hz": stats["expected_hz"],
            "expected_count_per_window": stats["expected_count_per_window"],
            "expected_count_source": stats["expected_count_source"],
            "count": stats["count"],
            "first_ns": stats["first_ns"],
            "last_ns": stats["last_ns"],
            "duration_ns": duration_ns,
            "duration_sec": ns_to_sec(duration_ns),
            "avg_gap_ns": avg_gap_ns,
            "avg_gap_sec": ns_to_sec(avg_gap_ns),
            "max_gap_ns": stats["max_gap_ns"],
            "max_gap_sec": ns_to_sec(stats["max_gap_ns"]),
            "jitter_ns": jitter_ns,
            "jitter_sec": ns_to_sec(jitter_ns),
            "out_of_order_count": stats["out_of_order_count"],
            "late_dropped_count": stats["late_dropped_count"],
            "finalized_window_count": finalized_window_counts[topic],
        }

        evidence_windows[topic] = [
            item for _, _, _, item in sorted(top_windows[topic], key=lambda x: x[0], reverse=True)
        ]

    anonymous_report = {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "semantics": SEMANTICS,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "file_name": input_path.name,
            "file_size_bytes": input_path.stat().st_size,
            "raw_payload_included": False,
            "messages_included": False,
        },
        "runtime": {
            "mode": "bounded_streaming_aggregation",
            "timestamp_unit": "nanoseconds_int",
            "window_sec": args.window_sec,
            "allowed_lateness_sec": args.allowed_lateness_sec,
            "top": args.top,
            "total_messages_observed": total_messages,
            "parse_errors": parse_errors,
            "out_of_order_total": out_of_order_total,
            "late_dropped_count": late_dropped_count,
            "max_active_windows_observed": max_active_windows_observed,
        },
        "dataset_summary": {
            "topic_count": len(topic_stats),
            "topics": sorted(topic_stats.keys()),
        },
        "topic_profile": topic_profile,
        "top_evidence_windows": evidence_windows,
        "non_judgment_statement": [
            "Velune Trace does not infer root cause.",
            "Velune Trace does not assign fault.",
            "Velune Trace does not calculate liability.",
            "Velune Trace reports observable timing evidence and reproducible evidence windows."
        ],
    }

    (export_dir / "shareable_anonymous_report.json").write_text(json.dumps(anonymous_report, indent=2), encoding="utf-8")
    (export_dir / "topic_profile.json").write_text(json.dumps(topic_profile, indent=2), encoding="utf-8")
    (export_dir / "evidence_windows.json").write_text(json.dumps(evidence_windows, indent=2), encoding="utf-8")

    schema_doc = f"""# Velune Anonymous Validation Report Schema

schema_name: {SCHEMA_NAME}

schema_version: {SCHEMA_VERSION}

semantics: {SEMANTICS}

## Runtime Mode

bounded_streaming_aggregation

## Privacy Boundary

This report does not include raw MCAP payloads.

This report does not include original messages.

This report only includes timing metadata, topic-level statistics, and ranked evidence windows.

## Topic Metadata

Optional topic profile fields:

- sensor_category
- expected_hz

## Judgment Boundary

Velune Trace does not infer root cause.

Velune Trace does not assign fault.

Velune Trace does not calculate liability.
"""
    (export_dir / "SCHEMA.md").write_text(schema_doc, encoding="utf-8")

    lines = []
    lines.append("# Velune Validation Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Source file: `{input_path.name}`")
    lines.append(f"- File size bytes: `{input_path.stat().st_size}`")
    lines.append(f"- Total messages observed: `{total_messages}`")
    lines.append(f"- Topic count: `{len(topic_stats)}`")
    lines.append(f"- Mode: `bounded_streaming_aggregation`")
    lines.append(f"- Timestamp unit: `nanoseconds_int`")
    lines.append(f"- Allowed lateness sec: `{args.allowed_lateness_sec}`")
    lines.append(f"- Max active windows observed: `{max_active_windows_observed}`")
    lines.append("")
    lines.append("## Observed Findings")
    lines.append("")

    for topic, profile in topic_profile.items():
        lines.append(f"### `{topic}`")
        lines.append("")
        lines.append(f"- Sensor category: `{profile['sensor_category']}`")
        lines.append(f"- Expected Hz: `{profile['expected_hz']}`")
        lines.append(f"- Expected count/window: `{profile['expected_count_per_window']}`")
        lines.append(f"- Expected source: `{profile['expected_count_source']}`")
        lines.append(f"- Count: `{profile['count']}`")
        lines.append(f"- Duration sec: `{profile['duration_sec']:.6f}`")
        lines.append(f"- Avg gap sec: `{profile['avg_gap_sec']:.9f}`")
        lines.append(f"- Max gap sec: `{profile['max_gap_sec']:.9f}`")
        lines.append(f"- Jitter sec: `{profile['jitter_sec']:.9f}`")
        lines.append(f"- Out-of-order count: `{profile['out_of_order_count']}`")
        lines.append(f"- Late dropped count: `{profile['late_dropped_count']}`")
        lines.append("")
        lines.append("Top evidence windows:")
        lines.append("")
        for w in evidence_windows.get(topic, []):
            lines.append(
                f"- Window `{w['window']}`: "
                f"start=`{w['start_sec']:.9f}`, "
                f"end=`{w['end_sec']:.9f}`, "
                f"count=`{w['count']}`, "
                f"expected=`{w['expected_count']}`, "
                f"count_ratio=`{w['count_ratio']}`, "
                f"max_gap=`{w['max_gap_sec']:.9f}`, "
                f"jitter=`{w['jitter_sec']:.9f}`, "
                f"score=`{w['observed_irregularity_score']:.6f}`"
            )
        lines.append("")

    lines.append("## Suggested Investigation Starting Points")
    lines.append("")
    lines.append("- Check topic timing stability around the top-ranked evidence windows.")
    lines.append("- Compare related sensor topics in the same time windows.")
    lines.append("- Review synchronization, QoS behavior, and driver throughput only as possible investigation directions.")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append("Velune Trace does not infer root cause.")
    lines.append("")
    lines.append("Velune Trace does not assign fault.")
    lines.append("")
    lines.append("Velune Trace reports observable timing evidence and reproducible evidence windows.")
    lines.append("")

    (export_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    print("VELUNE VALIDATION REPORT")
    print("MODE=bounded_streaming_aggregation")
    print(f"INPUT={input_path}")
    print(f"EXPORT_DIR={export_dir}")
    print(f"TOPIC_COUNT={len(topic_stats)}")
    print(f"TOTAL_MESSAGES_OBSERVED={total_messages}")
    print(f"OUT_OF_ORDER_TOTAL={out_of_order_total}")
    print(f"LATE_DROPPED_COUNT={late_dropped_count}")
    print(f"MAX_ACTIVE_WINDOWS_OBSERVED={max_active_windows_observed}")
    print("OUTPUTS:")
    print(f"- {export_dir / 'summary.md'}")
    print(f"- {export_dir / 'shareable_anonymous_report.json'}")
    print(f"- {export_dir / 'topic_profile.json'}")
    print(f"- {export_dir / 'evidence_windows.json'}")
    print(f"- {export_dir / 'SCHEMA.md'}")
    print("")
    print("UPLOAD_NUDGE=To participate in the Velune Validation Partner Program, send only shareable_anonymous_report.json to: skagusdn1998@gmail.com")
    print("UPLOAD_NUDGE_RAW_MCAP=Raw MCAP files are not required.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
