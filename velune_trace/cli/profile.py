#!/usr/bin/env python3

"""
Velune Trace Profile CLI

Purpose:
  Profile topic frequency and timing stability in a selected MCAP time window.

This command is observational only.
It does not detect, judge, score, or infer causality.

Usage:
  ./bin/velune profile <file.mcap> --start-sec <sec> --end-sec <sec>
  ./bin/velune profile <file.mcap> --start-sec <sec> --end-sec <sec> --sort max_gap
"""

import sys
import math
from mcap.reader import make_reader

from velune_trace.adapters.mcap_reader import VeluneMcapReader, VeluneError
from velune_trace.utils.formatter import ns_to_sec


EPSILON_SEC = 1e-9


def sec_to_ns(sec: float) -> int:
    return int(sec * 1_000_000_000)


def parse_args(argv):
    if len(argv) not in (6, 8):
        print("[ERROR] Usage:")
        print("  velune profile <file.mcap> --start-sec <sec> --end-sec <sec>")
        print("  velune profile <file.mcap> --start-sec <sec> --end-sec <sec> --sort <topic|count|window_hz|observed_hz|max_gap|jitter>")
        return None

    filename = argv[1]

    if argv[2] != "--start-sec" or argv[4] != "--end-sec":
        print("[ERROR] Usage: velune profile <file.mcap> --start-sec <sec> --end-sec <sec>")
        return None

    try:
        start_sec = float(argv[3])
        end_sec = float(argv[5])
    except ValueError:
        print("[ERROR] start-sec and end-sec must be numbers.")
        return None

    if end_sec <= start_sec:
        print("[ERROR] end-sec must be greater than start-sec.")
        return None

    sort_key = "topic"

    if len(argv) == 8:
        if argv[6] != "--sort":
            print(f"[ERROR] Unknown option: {argv[6]}")
            return None

        sort_key = argv[7]

        allowed = {"topic", "count", "window_hz", "observed_hz", "max_gap", "jitter"}

        if sort_key not in allowed:
            print(f"[ERROR] Unsupported sort key: {sort_key}")
            print("[HINT] Supported sort keys: topic, count, window_hz, observed_hz, max_gap, jitter")
            return None

    return filename, sec_to_ns(start_sec), sec_to_ns(end_sec), sort_key


def calculate_gap_stats(times_ns):
    """
    Return timing statistics for a topic.

    No causality is inferred.
    This only describes observed timing intervals.
    """
    if len(times_ns) < 2:
        return {
            "observed_span_sec": 0.0,
            "observed_hz": 0.0,
            "avg_gap_sec": 0.0,
            "max_gap_sec": 0.0,
            "jitter_sec": 0.0,
        }

    times_ns = sorted(times_ns)

    observed_span_sec = (times_ns[-1] - times_ns[0]) / 1_000_000_000

    observed_hz = (
        (len(times_ns) - 1) / observed_span_sec
        if observed_span_sec > EPSILON_SEC
        else 0.0
    )

    gaps_sec = [
        (times_ns[i] - times_ns[i - 1]) / 1_000_000_000
        for i in range(1, len(times_ns))
    ]

    if not gaps_sec:
        avg_gap_sec = 0.0
        max_gap_sec = 0.0
        jitter_sec = 0.0
    else:
        avg_gap_sec = sum(gaps_sec) / len(gaps_sec)
        max_gap_sec = max(gaps_sec)

        if len(gaps_sec) > 1:
            variance = sum((gap - avg_gap_sec) ** 2 for gap in gaps_sec) / len(gaps_sec)
            jitter_sec = math.sqrt(variance)
        else:
            jitter_sec = 0.0

    return {
        "observed_span_sec": observed_span_sec,
        "observed_hz": observed_hz,
        "avg_gap_sec": avg_gap_sec,
        "max_gap_sec": max_gap_sec,
        "jitter_sec": jitter_sec,
    }


def sort_rows(rows, sort_key):
    if sort_key == "topic":
        return sorted(rows, key=lambda r: r["topic"])

    return sorted(rows, key=lambda r: r[sort_key], reverse=True)


def main() -> int:
    parsed = parse_args(sys.argv)
    if parsed is None:
        return 2

    filename, start_ns, end_ns, sort_key = parsed
    duration_sec = (end_ns - start_ns) / 1_000_000_000

    try:
        inspect_result = VeluneMcapReader(filename).inspect()

        if not inspect_result.has_summary:
            print("[ERROR] MCAP summary not found. Profile unavailable.")
            return 1

        print()
        print("=== VELUNE PROFILE ===")
        print()
        print(f"File               : {filename}")
        print(f"Start sec          : {ns_to_sec(start_ns)}")
        print(f"End sec            : {ns_to_sec(end_ns)}")
        print(f"Window Duration sec: {duration_sec:.6f}")
        print(f"Sort               : {sort_key}")

        topic_times = {}

        with open(filename, "rb") as f:
            reader = make_reader(f)

            for schema, channel, message in reader.iter_messages(
                start_time=start_ns,
                end_time=end_ns,
            ):
                topic = channel.topic
                topic_times.setdefault(topic, []).append(message.log_time)

        if not topic_times:
            print()
            print("[WARN] No messages found in selected time window.")
            return 0

        rows = []

        for topic, times_ns in topic_times.items():
            count = len(times_ns)
            window_hz = count / duration_sec if duration_sec > EPSILON_SEC else 0.0
            gap_stats = calculate_gap_stats(times_ns)

            rows.append(
                {
                    "topic": topic,
                    "count": count,
                    "window_hz": window_hz,
                    "observed_span_sec": gap_stats["observed_span_sec"],
                    "observed_hz": gap_stats["observed_hz"],
                    "avg_gap": gap_stats["avg_gap_sec"],
                    "max_gap": gap_stats["max_gap_sec"],
                    "jitter": gap_stats["jitter_sec"],
                }
            )

        rows = sort_rows(rows, sort_key)

        print()
        print("topic                | count      | window_hz    | observed_hz  | avg_gap    | max_gap    | jitter")
        print("---------------------|------------|--------------|--------------|------------|------------|------------")

        for row in rows:
            print(
                f"{row['topic']:<20} | "
                f"{row['count']:<10} | "
                f"{row['window_hz']:<12.3f} | "
                f"{row['observed_hz']:<12.3f} | "
                f"{row['avg_gap']:<10.6f} | "
                f"{row['max_gap']:<10.6f} | "
                f"{row['jitter']:<10.6f}"
            )

        return 0

    except VeluneError as e:
        print()
        print("=== VELUNE PROFILE ERROR ===")
        print()
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
