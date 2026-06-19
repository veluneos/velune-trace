#!/usr/bin/env python3

import sys
import json
import math
from pathlib import Path
from mcap.reader import make_reader

from velune_trace.adapters.mcap_reader import VeluneMcapReader, VeluneError
from velune_trace.utils.formatter import ns_to_sec


EPSILON_SEC = 1e-9
HIGHLIGHT_RATIO = 1.5
MIN_CONFIDENT_COUNT = 5


def sec_to_ns(sec: float) -> int:
    return int(sec * 1_000_000_000)


def ratio_value(incident_value, normal_value):
    if abs(float(normal_value)) <= EPSILON_SEC:
        return None
    return float(incident_value) / float(normal_value)


def ratio_text(incident_value, normal_value):
    v = ratio_value(incident_value, normal_value)
    return "N/A" if v is None else f"{v:.3f}x"


def highlight_ratio(v):
    if v is None:
        return False
    return v >= HIGHLIGHT_RATIO or v <= (1.0 / HIGHLIGHT_RATIO)


def calculate_stats(times_ns, duration_sec):
    count = len(times_ns)

    if count == 0:
        return {"count": 0, "window_hz": 0.0, "observed_hz": 0.0, "avg_gap": 0.0, "max_gap": 0.0, "jitter": 0.0}

    window_hz = count / duration_sec if duration_sec > EPSILON_SEC else 0.0

    if count < 2:
        return {"count": count, "window_hz": window_hz, "observed_hz": 0.0, "avg_gap": 0.0, "max_gap": 0.0, "jitter": 0.0}

    times_ns = sorted(times_ns)
    span_sec = (times_ns[-1] - times_ns[0]) / 1_000_000_000
    observed_hz = (count - 1) / span_sec if span_sec > EPSILON_SEC else 0.0

    gaps = [(times_ns[i] - times_ns[i - 1]) / 1_000_000_000 for i in range(1, len(times_ns))]
    avg_gap = sum(gaps) / len(gaps) if gaps else 0.0
    max_gap = max(gaps) if gaps else 0.0

    if len(gaps) > 1:
        variance = sum((gap - avg_gap) ** 2 for gap in gaps) / len(gaps)
        jitter = math.sqrt(variance)
    else:
        jitter = 0.0

    return {"count": count, "window_hz": window_hz, "observed_hz": observed_hz, "avg_gap": avg_gap, "max_gap": max_gap, "jitter": jitter}


def confidence_label(normal_stats, incident_stats):
    min_count = min(normal_stats["count"], incident_stats["count"])

    if normal_stats["count"] == 0 and incident_stats["count"] == 0:
        return "none"

    if min_count < MIN_CONFIDENT_COUNT:
        return "low"

    return "normal"


def explain_reason(normal_stats, incident_stats):
    if normal_stats["count"] > 0 and incident_stats["count"] == 0:
        return "incident_missing"

    candidates = []

    for name, value in [
        ("count", ratio_value(incident_stats["count"], normal_stats["count"])),
        ("max_gap", ratio_value(incident_stats["max_gap"], normal_stats["max_gap"])),
        ("jitter", ratio_value(incident_stats["jitter"], normal_stats["jitter"])),
    ]:
        if value is None:
            continue

        if highlight_ratio(value):
            distance = abs(math.log(value)) if value > EPSILON_SEC else math.inf
            candidates.append((distance, name, value))

    if not candidates:
        return "within_threshold"

    candidates.sort(reverse=True)
    _, name, value = candidates[0]
    return f"{name}_ratio={value:.3f}x"


def anomaly_score(normal_stats, incident_stats):
    if normal_stats["count"] > 0 and incident_stats["count"] == 0:
        return math.inf

    score = 0.0

    for r in [
        ratio_value(incident_stats["count"], normal_stats["count"]),
        ratio_value(incident_stats["max_gap"], normal_stats["max_gap"]),
        ratio_value(incident_stats["jitter"], normal_stats["jitter"]),
    ]:
        if r is None or r <= EPSILON_SEC:
            continue
        score = max(score, abs(math.log(r)))

    return score


def read_all_topic_times(filename, start_ns, end_ns, topics):
    topic_times = {}

    with open(filename, "rb") as f:
        reader = make_reader(f)

        for schema, channel, message in reader.iter_messages(
            topics=topics,
            start_time=start_ns,
            end_time=end_ns,
        ):
            topic_times.setdefault(channel.topic, []).append(message.log_time)

    return topic_times


def parse_args(argv):
    if len(argv) < 11:
        print("[ERROR] Usage:")
        print("  velune compare-all <normal.mcap> <incident.mcap> --normal-start-sec <sec> --normal-end-sec <sec> --incident-start-sec <sec> --incident-end-sec <sec> [--sort anomaly_score] [--export-json report.json]")
        return None

    normal_file = argv[1]
    incident_file = argv[2]
    tokens = argv[3:]

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

    normal_start_raw = get_option("--normal-start-sec")
    normal_end_raw = get_option("--normal-end-sec")
    incident_start_raw = get_option("--incident-start-sec")
    incident_end_raw = get_option("--incident-end-sec")
    sort_key = get_option("--sort", required=False, default="anomaly_score")
    export_json = get_option("--export-json", required=False, default=None)

    if None in [normal_start_raw, normal_end_raw, incident_start_raw, incident_end_raw]:
        return None

    allowed_sort = {"anomaly_score", "max_gap_ratio", "jitter_ratio", "count_ratio", "topic"}

    if sort_key not in allowed_sort:
        print(f"[ERROR] Unsupported sort key: {sort_key}")
        return None

    normal_start_sec = float(normal_start_raw)
    normal_end_sec = float(normal_end_raw)
    incident_start_sec = float(incident_start_raw)
    incident_end_sec = float(incident_end_raw)

    return {
        "normal_file": normal_file,
        "incident_file": incident_file,
        "normal_start_ns": sec_to_ns(normal_start_sec),
        "normal_end_ns": sec_to_ns(normal_end_sec),
        "incident_start_ns": sec_to_ns(incident_start_sec),
        "incident_end_ns": sec_to_ns(incident_end_sec),
        "sort_key": sort_key,
        "export_json": export_json,
    }


def export_report(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parsed = parse_args(sys.argv)
    if parsed is None:
        return 2

    try:
        normal_file = parsed["normal_file"]
        incident_file = parsed["incident_file"]

        normal_inspect = VeluneMcapReader(normal_file).inspect()
        incident_inspect = VeluneMcapReader(incident_file).inspect()

        common_topics = sorted(
            set(t["topic"] for t in normal_inspect.topics)
            & set(t["topic"] for t in incident_inspect.topics)
        )

        normal_duration = (parsed["normal_end_ns"] - parsed["normal_start_ns"]) / 1_000_000_000
        incident_duration = (parsed["incident_end_ns"] - parsed["incident_start_ns"]) / 1_000_000_000

        normal_times = read_all_topic_times(normal_file, parsed["normal_start_ns"], parsed["normal_end_ns"], common_topics)
        incident_times = read_all_topic_times(incident_file, parsed["incident_start_ns"], parsed["incident_end_ns"], common_topics)

        rows = []

        for topic in common_topics:
            n = calculate_stats(normal_times.get(topic, []), normal_duration)
            i = calculate_stats(incident_times.get(topic, []), incident_duration)

            count_r = ratio_value(i["count"], n["count"])
            max_gap_r = ratio_value(i["max_gap"], n["max_gap"])
            jitter_r = ratio_value(i["jitter"], n["jitter"])

            missing_incident = n["count"] > 0 and i["count"] == 0
            highlighted = missing_incident or any(highlight_ratio(r) for r in [count_r, max_gap_r, jitter_r])

            rows.append({
                "topic": topic,
                "normal": n,
                "incident": i,
                "missing_incident": missing_incident,
                "highlight": highlighted,
                "reason": explain_reason(n, i),
                "confidence": confidence_label(n, i),
                "anomaly_score": anomaly_score(n, i),
                "ratios": {
                    "count_ratio": ratio_text(i["count"], n["count"]),
                    "window_hz_ratio": ratio_text(i["window_hz"], n["window_hz"]),
                    "max_gap_ratio": ratio_text(i["max_gap"], n["max_gap"]),
                    "jitter_ratio": ratio_text(i["jitter"], n["jitter"]),
                },
                "ratio_values": {
                    "count_ratio": count_r,
                    "max_gap_ratio": max_gap_r,
                    "jitter_ratio": jitter_r,
                },
            })

        sort_key = parsed["sort_key"]

        if sort_key == "topic":
            rows = sorted(rows, key=lambda r: r["topic"])
        elif sort_key == "anomaly_score":
            rows = sorted(rows, key=lambda r: r["anomaly_score"], reverse=True)
        else:
            rows = sorted(
                rows,
                key=lambda r: r["ratio_values"].get(sort_key) if r["ratio_values"].get(sort_key) is not None else -math.inf,
                reverse=True,
            )

        print()
        print("=== VELUNE COMPARE ALL ===")
        print()
        print("Semantics          : observed_comparison_only")
        print("Common Topics      :", len(common_topics))
        print("Sort               :", sort_key)
        print("Highlight Rule     : * ratio >= 1.5x or <= 0.667x, or incident missing")

        print()
        print("mark | topic                | n_count | i_count | n_hz     | i_hz     | max_gap_ratio | jitter_ratio | conf   | reason")
        print("-----|----------------------|---------|---------|----------|----------|---------------|--------------|--------|----------------------")

        for row in rows:
            mark = "*" if row["highlight"] else ""
            n = row["normal"]
            i = row["incident"]
            ratios = row["ratios"]

            print(
                f"{mark:<4} | "
                f"{row['topic']:<20} | "
                f"{n['count']:<7} | "
                f"{i['count']:<7} | "
                f"{n['window_hz']:<8.3f} | "
                f"{i['window_hz']:<8.3f} | "
                f"{ratios['max_gap_ratio']:<13} | "
                f"{ratios['jitter_ratio']:<12} | "
                f"{row['confidence']:<6} | "
                f"{row['reason']}"
            )

        report = {
            "command": "velune compare-all",
            "semantics": "observed_comparison_only",
            "highlight_rule": "ratio >= 1.5x or <= 0.667x, or incident missing",
            "normal": {
                "file": normal_file,
                "start_sec": ns_to_sec(parsed["normal_start_ns"]),
                "end_sec": ns_to_sec(parsed["normal_end_ns"]),
                "duration_sec": normal_duration,
            },
            "incident": {
                "file": incident_file,
                "start_sec": ns_to_sec(parsed["incident_start_ns"]),
                "end_sec": ns_to_sec(parsed["incident_end_ns"]),
                "duration_sec": incident_duration,
            },
            "rows": rows,
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
        print("=== VELUNE COMPARE-ALL ERROR ===")
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
