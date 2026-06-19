#!/usr/bin/env python3

"""
Velune Trace Compare CLI

Purpose:
  Compare observed topic timing statistics between two MCAP windows.

This command is observational only.
It does not detect, judge, score, or infer causality.

Usage:
  ./bin/velune compare <normal.mcap> <incident.mcap> \
    --normal-start-sec <sec> --normal-end-sec <sec> \
    --incident-start-sec <sec> --incident-end-sec <sec> \
    --topic /scan

Optional:
  --export-json report.json
"""

import sys
import json
import math
from pathlib import Path
from mcap.reader import make_reader

from velune_trace.adapters.mcap_reader import VeluneMcapReader, VeluneError
from velune_trace.utils.formatter import ns_to_sec


EPSILON_SEC = 1e-9


def sec_to_ns(sec: float) -> int:
    return int(sec * 1_000_000_000)


def calculate_stats(times_ns, duration_sec):
    count = len(times_ns)

    if count == 0:
        return {
            "count": 0,
            "window_hz": 0.0,
            "observed_hz": 0.0,
            "avg_gap": 0.0,
            "max_gap": 0.0,
            "jitter": 0.0,
        }

    window_hz = count / duration_sec if duration_sec > EPSILON_SEC else 0.0

    if count < 2:
        return {
            "count": count,
            "window_hz": window_hz,
            "observed_hz": 0.0,
            "avg_gap": 0.0,
            "max_gap": 0.0,
            "jitter": 0.0,
        }

    times_ns = sorted(times_ns)
    span_sec = (times_ns[-1] - times_ns[0]) / 1_000_000_000

    observed_hz = (count - 1) / span_sec if span_sec > EPSILON_SEC else 0.0

    gaps = [
        (times_ns[i] - times_ns[i - 1]) / 1_000_000_000
        for i in range(1, len(times_ns))
    ]

    avg_gap = sum(gaps) / len(gaps) if gaps else 0.0
    max_gap = max(gaps) if gaps else 0.0

    if len(gaps) > 1:
        variance = sum((gap - avg_gap) ** 2 for gap in gaps) / len(gaps)
        jitter = math.sqrt(variance)
    else:
        jitter = 0.0

    return {
        "count": count,
        "window_hz": window_hz,
        "observed_hz": observed_hz,
        "avg_gap": avg_gap,
        "max_gap": max_gap,
        "jitter": jitter,
    }


def read_topic_times(filename, start_ns, end_ns, topic):
    times = []

    with open(filename, "rb") as f:
        reader = make_reader(f)

        for schema, channel, message in reader.iter_messages(
            topics=[topic],
            start_time=start_ns,
            end_time=end_ns,
        ):
            times.append(message.log_time)

    return times


def parse_args(argv):
    if len(argv) < 13:
        print("[ERROR] Usage:")
        print("  velune compare <normal.mcap> <incident.mcap> \\")
        print("    --normal-start-sec <sec> --normal-end-sec <sec> \\")
        print("    --incident-start-sec <sec> --incident-end-sec <sec> \\")
        print("    --topic <topic> [--export-json report.json]")
        return None

    normal_file = argv[1]
    incident_file = argv[2]
    tokens = argv[3:]

    def get_option(name, required=True):
        if name not in tokens:
            if required:
                print(f"[ERROR] Missing required option: {name}")
            return None

        idx = tokens.index(name)

        if idx + 1 >= len(tokens):
            print(f"[ERROR] Option requires value: {name}")
            return None

        return tokens[idx + 1]

    normal_start_raw = get_option("--normal-start-sec")
    normal_end_raw = get_option("--normal-end-sec")
    incident_start_raw = get_option("--incident-start-sec")
    incident_end_raw = get_option("--incident-end-sec")
    topic = get_option("--topic")
    export_json = get_option("--export-json", required=False)

    if None in [normal_start_raw, normal_end_raw, incident_start_raw, incident_end_raw, topic]:
        return None

    try:
        normal_start_sec = float(normal_start_raw)
        normal_end_sec = float(normal_end_raw)
        incident_start_sec = float(incident_start_raw)
        incident_end_sec = float(incident_end_raw)
    except ValueError:
        print("[ERROR] Time values must be numbers.")
        return None

    if normal_end_sec <= normal_start_sec:
        print("[ERROR] normal-end-sec must be greater than normal-start-sec.")
        return None

    if incident_end_sec <= incident_start_sec:
        print("[ERROR] incident-end-sec must be greater than incident-start-sec.")
        return None

    return {
        "normal_file": normal_file,
        "incident_file": incident_file,
        "normal_start_ns": sec_to_ns(normal_start_sec),
        "normal_end_ns": sec_to_ns(normal_end_sec),
        "incident_start_ns": sec_to_ns(incident_start_sec),
        "incident_end_ns": sec_to_ns(incident_end_sec),
        "topic": topic,
        "export_json": export_json,
    }

def validate_topic(filename, topic):
    result = VeluneMcapReader(filename).inspect()
    available_topics = sorted(t["topic"] for t in result.topics)

    if topic not in available_topics:
        print(f"[ERROR] Topic not found in file: {topic}")
        print(f"File: {filename}")
        print()
        print("Available topics:")
        for t in available_topics:
            print(f"  {t}")
        return False

    return True


def ratio_text(incident_value, normal_value):
    if abs(float(normal_value)) <= EPSILON_SEC:
        return "N/A"
    return f"{float(incident_value) / float(normal_value):.3f}x"


def bar(value, max_value, width=24):
    if max_value <= EPSILON_SEC:
        return ""
    filled = int((value / max_value) * width)
    return "#" * filled


def export_report(path, payload):
    output_path = Path(path)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> int:
    parsed = parse_args(sys.argv)
    if parsed is None:
        return 2

    try:
        normal_file = parsed["normal_file"]
        incident_file = parsed["incident_file"]
        topic = parsed["topic"]

        if not validate_topic(normal_file, topic):
            return 1

        if not validate_topic(incident_file, topic):
            return 1

        normal_duration = (parsed["normal_end_ns"] - parsed["normal_start_ns"]) / 1_000_000_000
        incident_duration = (parsed["incident_end_ns"] - parsed["incident_start_ns"]) / 1_000_000_000

        normal_times = read_topic_times(
            normal_file,
            parsed["normal_start_ns"],
            parsed["normal_end_ns"],
            topic,
        )

        incident_times = read_topic_times(
            incident_file,
            parsed["incident_start_ns"],
            parsed["incident_end_ns"],
            topic,
        )

        normal_stats = calculate_stats(normal_times, normal_duration)
        incident_stats = calculate_stats(incident_times, incident_duration)

        metrics = ["count", "window_hz", "observed_hz", "avg_gap", "max_gap", "jitter"]

        print()
        print("=== VELUNE COMPARE ===")
        print()
        print(f"Topic              : {topic}")
        print()
        print("Normal File        :", normal_file)
        print("Normal Start sec   :", ns_to_sec(parsed["normal_start_ns"]))
        print("Normal End sec     :", ns_to_sec(parsed["normal_end_ns"]))
        print()
        print("Incident File      :", incident_file)
        print("Incident Start sec :", ns_to_sec(parsed["incident_start_ns"]))
        print("Incident End sec   :", ns_to_sec(parsed["incident_end_ns"]))

        print()
        print("metric       | normal       | incident     | ratio")
        print("-------------|--------------|--------------|----------")

        for key in metrics:
            n = normal_stats[key]
            i = incident_stats[key]

            if key == "count":
                n_text = str(n)
                i_text = str(i)
            else:
                n_text = f"{n:.6f}"
                i_text = f"{i:.6f}"

            print(
                f"{key:<12} | "
                f"{n_text:<12} | "
                f"{i_text:<12} | "
                f"{ratio_text(i, n)}"
            )

        print()
        print("=== ASCII RATIO HINT ===")
        print()
        print("metric       | incident / normal")
        print("-------------|------------------")

        for key in ["window_hz", "observed_hz", "avg_gap", "max_gap", "jitter"]:
            n = normal_stats[key]
            i = incident_stats[key]

            if abs(float(n)) <= EPSILON_SEC:
                ratio_value = 0.0
            else:
                ratio_value = float(i) / float(n)

            capped = min(ratio_value, 3.0)
            print(f"{key:<12} | {bar(capped, 3.0)} {ratio_text(i, n)}")

        report = {
            "command": "velune compare",
            "semantics": "observed_comparison_only",
            "notes": [
                "Velune does not infer root cause.",
                "Velune does not assign fault.",
                "Velune does not calculate liability.",
            ],
            "topic": topic,
            "normal": {
                "file": normal_file,
                "start_ns": parsed["normal_start_ns"],
                "end_ns": parsed["normal_end_ns"],
                "start_sec": ns_to_sec(parsed["normal_start_ns"]),
                "end_sec": ns_to_sec(parsed["normal_end_ns"]),
                "duration_sec": normal_duration,
                "stats": normal_stats,
            },
            "incident": {
                "file": incident_file,
                "start_ns": parsed["incident_start_ns"],
                "end_ns": parsed["incident_end_ns"],
                "start_sec": ns_to_sec(parsed["incident_start_ns"]),
                "end_sec": ns_to_sec(parsed["incident_end_ns"]),
                "duration_sec": incident_duration,
                "stats": incident_stats,
            },
            "ratios": {
                key: ratio_text(incident_stats[key], normal_stats[key])
                for key in metrics
            },
        }

        if parsed["export_json"]:
            export_report(parsed["export_json"], report)
            print()
            print(f"[OK] JSON report exported: {parsed['export_json']}")

        print()
        print("[NOTE] This is an observed comparison only.")
        print("[NOTE] Velune does not infer root cause or assign fault.")

        return 0

    except VeluneError as e:
        print()
        print("=== VELUNE COMPARE ERROR ===")
        print()
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
