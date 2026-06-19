#!/usr/bin/env python3

import sys
import json
from mcap.reader import make_reader

from velune_trace.utils.formatter import ns_to_sec


def parse_args(argv):
    if len(argv) < 2:
        print("[ERROR] Usage:")
        print("  velune evidence-window <file.mcap> --topic <topic> --start-sec <sec> --end-sec <sec> [--expected-count N] [--export-json file]")
        return None

    filename = argv[1]
    tokens = argv[2:]

    def get_option(name, required=True, default=None):
        if name not in tokens:
            if required:
                print(f"[ERROR] Missing required option: {name}")
                return None
            return default

        idx = tokens.index(name)

        if idx + 1 >= len(tokens):
            print(f"[ERROR] Option requires value: {name}")
            return None

        return tokens[idx + 1]

    topic = get_option("--topic")
    start_raw = get_option("--start-sec")
    end_raw = get_option("--end-sec")
    expected_raw = get_option("--expected-count", required=False, default=None)
    export_json = get_option("--export-json", required=False, default=None)

    if None in [topic, start_raw, end_raw]:
        return None

    try:
        start_sec = float(start_raw)
        end_sec = float(end_raw)
    except ValueError:
        print("[ERROR] --start-sec and --end-sec must be numbers.")
        return None

    if end_sec <= start_sec:
        print("[ERROR] --end-sec must be greater than --start-sec.")
        return None

    expected_count = None

    if expected_raw is not None:
        try:
            expected_count = int(expected_raw)
        except ValueError:
            print("[ERROR] --expected-count must be an integer.")
            return None

        if expected_count < 0:
            print("[ERROR] --expected-count must be zero or greater.")
            return None

    return {
        "filename": filename,
        "topic": topic,
        "start_sec": start_sec,
        "end_sec": end_sec,
        "expected_count": expected_count,
        "export_json": export_json,
    }


def build_evidence(
    filename,
    topic,
    start_sec,
    end_sec,
    count,
    expected_count,
    first_time,
    last_time,
):
    window_span = end_sec - start_sec

    if count == 0:
        active_span = 0.0
        silent_span = window_span
        first_message_sec = None
        last_message_sec = None
        evidence_level = "OBSERVED_EMPTY_WINDOW"
    else:
        active_span = (last_time - first_time) / 1_000_000_000
        silent_span = max(0.0, window_span - active_span)
        first_message_sec = ns_to_sec(first_time)
        last_message_sec = ns_to_sec(last_time)
        evidence_level = "OBSERVED_WINDOW"

    count_ratio = None
    if expected_count is not None and expected_count > 0:
        count_ratio = count / expected_count

    return {
        "semantics": "observed_evidence_window",
        "file": filename,
        "topic": topic,
        "window_start_sec": start_sec,
        "window_end_sec": end_sec,
        "window_span_sec": window_span,
        "observed_count": count,
        "expected_count": expected_count,
        "count_ratio": count_ratio,
        "active_span_sec": active_span,
        "silent_span_sec": silent_span,
        "first_message_sec": first_message_sec,
        "last_message_sec": last_message_sec,
        "evidence_level": evidence_level,
        "notes": [
            "Velune does not infer root cause.",
            "Velune does not assign fault.",
            "Velune only reports observed evidence.",
        ],
    }


def print_evidence(evidence):
    print()
    print("=== EVIDENCE WINDOW ===")
    print()

    print(f"Topic             : {evidence['topic']}")
    print(f"Window Start Sec  : {evidence['window_start_sec']:.9f}")
    print(f"Window End Sec    : {evidence['window_end_sec']:.9f}")
    print()

    print(f"Observed Count    : {evidence['observed_count']}")

    if evidence["expected_count"] is not None:
        print(f"Expected Count    : {evidence['expected_count']}")

        if evidence["count_ratio"] is None:
            print("Count Ratio       : N/A")
        else:
            print(f"Count Ratio       : {evidence['count_ratio']:.3f}")

    print(f"Active Span Sec   : {evidence['active_span_sec']:.6f}")
    print(f"Silent Span Sec   : {evidence['silent_span_sec']:.6f}")
    print()

    print(f"First Message Sec : {evidence['first_message_sec']}")
    print(f"Last Message Sec  : {evidence['last_message_sec']}")
    print()

    print(f"Evidence Level    : {evidence['evidence_level']}")
    print()
    print("[NOTE] Velune does not infer root cause.")


def main():
    parsed = parse_args(sys.argv)

    if parsed is None:
        return 2

    filename = parsed["filename"]
    topic = parsed["topic"]
    start_sec = parsed["start_sec"]
    end_sec = parsed["end_sec"]
    expected_count = parsed["expected_count"]
    export_json = parsed["export_json"]

    start_ns = int(start_sec * 1_000_000_000)
    end_ns = int(end_sec * 1_000_000_000)

    times = []

    with open(filename, "rb") as f:
        reader = make_reader(f)

        for schema, channel, message in reader.iter_messages(
            topics=[topic],
            start_time=start_ns,
            end_time=end_ns,
        ):
            times.append(message.log_time)

    count = len(times)

    first_time = min(times) if times else None
    last_time = max(times) if times else None

    evidence = build_evidence(
        filename=filename,
        topic=topic,
        start_sec=start_sec,
        end_sec=end_sec,
        count=count,
        expected_count=expected_count,
        first_time=first_time,
        last_time=last_time,
    )

    print_evidence(evidence)

    if export_json:
        with open(export_json, "w") as f:
            json.dump(evidence, f, indent=2, ensure_ascii=False)

        print()
        print(f"[OK] JSON exported: {export_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
