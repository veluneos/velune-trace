#!/usr/bin/env python3

import sys
import math
import json
import bisect
import shlex
from mcap.reader import make_reader

from velune_trace.adapters.mcap_reader import VeluneMcapReader, VeluneError
from velune_trace.utils.formatter import ns_to_sec


EPSILON = 1e-9


def sec_to_ns(sec: float) -> int:
    return int(sec * 1_000_000_000)


def parse_args(argv):
    if len(argv) < 2:
        print("[ERROR] Usage:")
        print("  velune windowed-verify <file.mcap> --topic <topic> --window-sec <sec> [--top 10] [--export-json report.json]")
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
    window_sec_raw = get_option("--window-sec")
    top_raw = get_option("--top", required=False, default="10")
    export_json = get_option("--export-json", required=False, default=None)

    if topic is None or window_sec_raw is None:
        return None

    try:
        window_sec = float(window_sec_raw)
        top = int(top_raw)
    except ValueError:
        print("[ERROR] --window-sec must be number, --top must be integer.")
        return None

    if window_sec <= 0:
        print("[ERROR] --window-sec must be greater than 0.")
        return None

    if top <= 0:
        print("[ERROR] --top must be greater than 0.")
        return None

    return {
        "filename": filename,
        "topic": topic,
        "window_sec": window_sec,
        "top": top,
        "export_json": export_json,
    }


def calculate_window_stats(times_ns, window_duration_sec):
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

    window_hz = count / window_duration_sec if window_duration_sec > EPSILON else 0.0

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
    observed_hz = (count - 1) / span_sec if span_sec > EPSILON else 0.0

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


def build_windows(start_ns, end_ns, window_ns):
    windows = []
    boundaries = []

    current = start_ns

    while current < end_ns:
        window_end = min(current + window_ns, end_ns)

        windows.append({
            "start_ns": current,
            "end_ns": window_end,
            "times": [],
        })

        boundaries.append(current)
        current = window_end

    return windows, boundaries


def estimate_baseline(rows):
    non_empty = [r for r in rows if r["stats"]["count"] >= 2]

    if not non_empty:
        return {
            "median_count": 0,
            "median_max_gap": 0.0,
            "median_jitter": 0.0,
        }

    counts = sorted(r["stats"]["count"] for r in non_empty)
    max_gaps = sorted(r["stats"]["max_gap"] for r in non_empty)
    jitters = sorted(r["stats"]["jitter"] for r in non_empty)

    mid = len(non_empty) // 2

    return {
        "median_count": counts[mid],
        "median_max_gap": max_gaps[mid],
        "median_jitter": jitters[mid],
    }


def safe_log_ratio(value, baseline):
    if baseline <= EPSILON:
        if value <= EPSILON:
            return 0.0
        return 10.0

    if value <= EPSILON:
        return 10.0

    return abs(math.log(value / baseline))


def normalized_window_score(stats, baseline):
    score = 0.0

    median_count = baseline["median_count"]
    median_max_gap = baseline["median_max_gap"]
    median_jitter = baseline["median_jitter"]

    if median_count > 0:
        if stats["count"] == 0:
            score += 10.0
        else:
            score += abs(math.log(stats["count"] / median_count))

    score += safe_log_ratio(stats["max_gap"], median_max_gap)
    score += safe_log_ratio(stats["jitter"], median_jitter)

    return score


def build_evidence_command(filename, topic, start_sec, end_sec, expected_count):
    parts = [
        "./bin/velune",
        "evidence-window",
        filename,
        "--topic",
        topic,
        "--start-sec",
        start_sec,
        "--end-sec",
        end_sec,
        "--expected-count",
        str(expected_count),
    ]

    return " ".join(shlex.quote(str(part)) for part in parts)


def main():
    parsed = parse_args(sys.argv)

    if parsed is None:
        return 2

    filename = parsed["filename"]
    topic = parsed["topic"]
    window_sec = parsed["window_sec"]
    top = parsed["top"]
    export_json = parsed["export_json"]

    try:
        inspect_result = VeluneMcapReader(filename).inspect()

        available_topics = sorted(t["topic"] for t in inspect_result.topics)

        if topic not in available_topics:
            print(f"[ERROR] Topic not found: {topic}")
            print()
            print("Available topics:")
            for t in available_topics:
                print(f"  {t}")
            return 1

        start_ns = inspect_result.start_time_ns
        end_ns = inspect_result.end_time_ns

        if start_ns is None or end_ns is None:
            print("[ERROR] MCAP time range unavailable.")
            return 1

        window_ns = sec_to_ns(window_sec)
        windows, boundaries = build_windows(start_ns, end_ns, window_ns)

        with open(filename, "rb") as f:
            reader = make_reader(f)

            for schema, channel, message in reader.iter_messages(
                topics=[topic],
                start_time=start_ns,
                end_time=end_ns,
            ):
                idx = bisect.bisect_right(boundaries, message.log_time) - 1

                if idx < 0 or idx >= len(windows):
                    continue

                if windows[idx]["start_ns"] <= message.log_time < windows[idx]["end_ns"]:
                    windows[idx]["times"].append(message.log_time)

        rows = []

        for idx, window in enumerate(windows):
            duration_sec = (window["end_ns"] - window["start_ns"]) / 1_000_000_000
            stats = calculate_window_stats(window["times"], duration_sec)

            rows.append({
                "window_id": idx,
                "start_ns": window["start_ns"],
                "end_ns": window["end_ns"],
                "start_sec": ns_to_sec(window["start_ns"]),
                "end_sec": ns_to_sec(window["end_ns"]),
                "duration_sec": duration_sec,
                "stats": stats,
                "score": 0.0,
                "evidence_command": None,
            })

        baseline = estimate_baseline(rows)

        for row in rows:
            row["score"] = normalized_window_score(row["stats"], baseline)
            row["evidence_command"] = build_evidence_command(
                filename=filename,
                topic=topic,
                start_sec=row["start_sec"],
                end_sec=row["end_sec"],
                expected_count=baseline["median_count"],
            )

        full_window_rows = [
            row for row in rows
            if row["duration_sec"] >= (window_sec * 0.999)
        ]

        ranked = sorted(full_window_rows, key=lambda r: r["score"], reverse=True)

        print()
        print("=== VELUNE WINDOWED VERIFY ===")
        print()
        print("Semantics        : observed_window_ranking_only")
        print(f"File             : {filename}")
        print(f"Topic            : {topic}")
        print(f"Window sec       : {window_sec}")
        print(f"Total Windows    : {len(rows)}")
        print(f"Top              : {top}")
        print()
        print("Baseline")
        print(f"  median_count   : {baseline['median_count']}")
        print(f"  median_max_gap : {baseline['median_max_gap']:.6f}")
        print(f"  median_jitter  : {baseline['median_jitter']:.6f}")

        print()
        print("rank | window | start_sec          | end_sec            | count | hz      | max_gap  | jitter   | score")
        print("-----|--------|--------------------|--------------------|-------|---------|----------|----------|----------")

        for rank, row in enumerate(ranked[:top], start=1):
            stats = row["stats"]

            print(
                f"{rank:<4} | "
                f"{row['window_id']:<6} | "
                f"{row['start_sec']:<18} | "
                f"{row['end_sec']:<18} | "
                f"{stats['count']:<5} | "
                f"{stats['window_hz']:<7.3f} | "
                f"{stats['max_gap']:<8.6f} | "
                f"{stats['jitter']:<8.6f} | "
                f"{row['score']:<8.6f}"
            )

        if ranked:
            print()
            print("Top Evidence Command:")
            print(ranked[0]["evidence_command"])

        report = {
            "command": "velune windowed-verify",
            "semantics": "observed_window_ranking_only",
            "notes": [
                "Velune does not infer root cause.",
                "Velune does not assign fault.",
                "Velune does not calculate liability.",
                "Windows are ranked by baseline-normalized observed timing irregularity only.",
            ],
            "file": filename,
            "topic": topic,
            "window_sec": window_sec,
            "total_windows": len(rows),
            "ranked_full_windows": len(ranked),
            "top": top,
            "baseline": baseline,
            "ranked_windows": ranked,
            "all_windows": rows,
        }

        if export_json:
            with open(export_json, "w") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            print()
            print(f"[OK] JSON exported: {export_json}")

        print()
        print("[NOTE] This is observed window ranking only.")
        print("[NOTE] Velune does not infer root cause or assign fault.")

        return 0

    except VeluneError as e:
        print()
        print("=== VELUNE WINDOWED VERIFY ERROR ===")
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
