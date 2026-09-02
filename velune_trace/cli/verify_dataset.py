#!/usr/bin/env python3

import sys
import json
import math
from pathlib import Path

import yaml

EPSILON = 1e-9
MIN_CANDIDATE_HZ = 0.1

EXPECTED_TOPIC_KEYWORDS = {
    "scan": "/scan",
    "lidar": "/scan",
    "laser": "/scan",
    "imu": "/imu",
    "odom": "/odom",
    "cmd": "/cmd_vel",
    "command": "/cmd_vel",
    "tf": "/tf",
}


def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_dataset_record(metadata_path):
    dataset_dir = metadata_path.parent
    dataset_name = dataset_dir.name
    data = load_yaml(metadata_path)
    info = data["rosbag2_bagfile_information"]

    duration_sec = info["duration"]["nanoseconds"] / 1_000_000_000

    topics = {}
    for item in info["topics_with_message_count"]:
        topics[item["topic_metadata"]["name"]] = item["message_count"]

    path_text = str(metadata_path)

    if "/incident/" in path_text:
        dataset_type = "incident"
    elif "/normal/" in path_text:
        dataset_type = "normal"
    else:
        dataset_type = "unknown"

    return {
        "dataset_name": dataset_name,
        "dataset_type": dataset_type,
        "metadata_path": path_text,
        "message_count": info["message_count"],
        "duration_sec": duration_sec,
        "topics": topics,
    }


def rate(count, duration_sec):
    if duration_sec <= EPSILON:
        return 0.0
    return count / duration_sec


def ratio_text(value):
    if value is None:
        return "N/A"
    if value == math.inf:
        return "INF"
    return f"{value:.3f}x"


def safe_ratio(incident_value, normal_value):
    if abs(normal_value) <= EPSILON:
        if abs(incident_value) <= EPSILON:
            return None
        return math.inf
    return incident_value / normal_value


def average_normal_rates(normal_records):
    topic_values = {}

    for record in normal_records:
        for topic, count in record["topics"].items():
            hz = rate(count, record["duration_sec"])
            topic_values.setdefault(topic, []).append(hz)

    return {
        topic: sum(values) / len(values)
        for topic, values in topic_values.items()
    }


def anomaly_score_from_rates(normal_hz, incident_hz):
    normal_missing = abs(normal_hz) <= EPSILON
    incident_missing = abs(incident_hz) <= EPSILON

    if not normal_missing and incident_missing:
        return math.inf
    if normal_missing and not incident_missing:
        return math.inf
    if normal_missing and incident_missing:
        return 0.0

    ratio = incident_hz / normal_hz

    if ratio <= EPSILON:
        return math.inf

    return abs(math.log(ratio))


def expected_topic_from_metadata_or_name(record):
    metadata_path = Path(record["metadata_path"])

    try:
        data = load_yaml(metadata_path)
        custom_data = data.get("rosbag2_bagfile_information", {}).get("custom_data")

        if isinstance(custom_data, dict):
            explicit = custom_data.get("velune_expected_topic")
            if explicit:
                return {
                    "status": "DECLARED",
                    "expected_topic": explicit,
                    "matched_keywords": [],
                }
    except Exception:
        pass

    name = record["dataset_name"].lower()
    matches = []

    for keyword, topic in EXPECTED_TOPIC_KEYWORDS.items():
        if keyword in name:
            matches.append((keyword, topic))

    unique_topics = sorted(set(topic for _, topic in matches))

    if len(unique_topics) == 0:
        return {
            "status": "NO_DECLARATION",
            "expected_topic": None,
            "matched_keywords": [],
        }

    if len(unique_topics) > 1:
        return {
            "status": "AMBIGUOUS",
            "expected_topic": None,
            "matched_keywords": matches,
        }

    return {
        "status": "INFERRED_FROM_NAME",
        "expected_topic": unique_topics[0],
        "matched_keywords": matches,
    }


def parse_args(argv):
    if len(argv) < 2:
        print("[ERROR] Usage:")
        print("  velune verify-dataset <datasets_dir> [--export-json report.json]")
        return None

    datasets_dir = Path(argv[1])
    tokens = argv[2:]

    export_json = None

    if "--export-json" in tokens:
        idx = tokens.index("--export-json")
        if idx + 1 >= len(tokens):
            print("[ERROR] --export-json requires a file path.")
            return None
        export_json = tokens[idx + 1]

    return {
        "datasets_dir": datasets_dir,
        "export_json": export_json,
    }


def main():
    parsed = parse_args(sys.argv)
    if parsed is None:
        return 2

    datasets_dir = parsed["datasets_dir"]
    export_json = parsed["export_json"]

    metadata_files = sorted(datasets_dir.rglob("metadata.yaml"))

    if not metadata_files:
        print(f"[ERROR] No metadata.yaml files found under: {datasets_dir}")
        return 1

    records = [load_dataset_record(path) for path in metadata_files]

    normal_records = [r for r in records if r["dataset_type"] == "normal"]
    incident_records = [r for r in records if r["dataset_type"] == "incident"]

    if not normal_records:
        print("[ERROR] No normal datasets found.")
        return 1

    if not incident_records:
        print("[ERROR] No incident datasets found.")
        return 1

    normal_rates = average_normal_rates(normal_records)

    report = {
        "command": "velune verify-dataset",
        "semantics": "metadata_observed_comparison_only",
        "notes": [
            "Velune does not infer root cause.",
            "Velune does not assign fault.",
            "Velune does not calculate liability.",
            "This verification uses metadata-level topic rates only.",
            "Metadata-level verification may miss localized time-window dropouts.",
            "Control topics such as /cmd_vel may reflect scenario mismatch rather than incident evidence.",
            "Low-frequency topics below MIN_CANDIDATE_HZ are excluded from candidate ranking.",
        ],
        "normal_datasets": [r["dataset_name"] for r in normal_records],
        "incident_results": [],
    }

    print()
    print("=== VELUNE VERIFY DATASET ===")
    print()
    print("Semantics       : metadata_observed_comparison_only")
    print(f"Normal Datasets : {len(normal_records)}")
    print(f"Incident Sets   : {len(incident_records)}")
    print()

    total = 0
    pass_count = 0
    review_count = 0
    ambiguous_count = 0
    no_declaration_count = 0

    for incident in incident_records:
        total += 1

        declaration = expected_topic_from_metadata_or_name(incident)
        expected_topic = declaration["expected_topic"]
        declaration_status = declaration["status"]

        rows = []

        for topic, incident_count in incident["topics"].items():
            incident_hz = rate(incident_count, incident["duration_sec"])
            normal_hz = normal_rates.get(topic, 0.0)

            if max(normal_hz, incident_hz) < MIN_CANDIDATE_HZ:
                continue

            ratio = safe_ratio(incident_hz, normal_hz)
            score = anomaly_score_from_rates(normal_hz, incident_hz)

            if normal_hz <= EPSILON and incident_hz > EPSILON:
                reason = "normal_missing_incident_present"
            elif normal_hz > EPSILON and incident_hz <= EPSILON:
                reason = "normal_present_incident_missing"
            elif topic == "/cmd_vel" and abs((incident_hz / normal_hz) if normal_hz > EPSILON else 0.0) >= 1.5:
                reason = "control_context_shift"
            else:
                reason = "rate_ratio"

            rows.append({
                "topic": topic,
                "normal_hz": normal_hz,
                "incident_hz": incident_hz,
                "ratio": ratio,
                "ratio_text": ratio_text(ratio),
                "anomaly_score": score,
                "reason": reason,
            })

        rows = sorted(rows, key=lambda x: x["anomaly_score"], reverse=True)
        top_topic = rows[0]["topic"] if rows else None

        if declaration_status == "AMBIGUOUS":
            result = "AMBIGUOUS"
            ambiguous_count += 1
        elif declaration_status == "NO_DECLARATION":
            result = "NO_DECLARATION"
            no_declaration_count += 1
        elif expected_topic == top_topic:
            result = "PASS"
            pass_count += 1
        else:
            result = "REVIEW"
            review_count += 1

        print("-" * 72)
        print(f"Incident Dataset : {incident['dataset_name']}")
        print(f"Declaration      : {declaration_status}")
        print(f"Expected Topic   : {expected_topic if expected_topic else 'N/A'}")
        print(f"Top Candidate    : {top_topic if top_topic else 'N/A'}")
        print(f"Result           : {result}")

        if result == "REVIEW":
            print()
            print("[INTERPRETATION]")
            print("Metadata-level rates may be insufficient for localized dropout verification.")
            print("Use time-window profile or compare-all for incident-window analysis.")

        if declaration_status == "AMBIGUOUS":
            print(f"Matched Keywords : {declaration['matched_keywords']}")

        print()
        print("topic                | normal_hz  | incident_hz | ratio    | score     | reason")
        print("---------------------|------------|-------------|----------|-----------|-------------------------------")

        for row in rows[:7]:
            score_text = "INF" if row["anomaly_score"] == math.inf else f"{row['anomaly_score']:.3f}"

            print(
                f"{row['topic']:<20} | "
                f"{row['normal_hz']:<10.3f} | "
                f"{row['incident_hz']:<11.3f} | "
                f"{row['ratio_text']:<8} | "
                f"{score_text:<9} | "
                f"{row['reason']}"
            )

        report["incident_results"].append({
            "dataset_name": incident["dataset_name"],
            "declaration": declaration,
            "expected_topic": expected_topic,
            "top_candidate": top_topic,
            "result": result,
            "rows": rows,
        })

    print()
    print("=" * 72)
    print(f"TOTAL          : {total}")
    print(f"PASS           : {pass_count}")
    print(f"REVIEW         : {review_count}")
    print(f"AMBIGUOUS      : {ambiguous_count}")
    print(f"NO_DECLARATION : {no_declaration_count}")

    if export_json:
        with open(export_json, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print()
        print(f"[OK] JSON exported: {export_json}")

    print()
    print("[NOTE] This is metadata-level verification only.")
    print("[NOTE] Velune does not infer root cause or assign fault.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
