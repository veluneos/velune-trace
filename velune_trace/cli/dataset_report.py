#!/usr/bin/env python3

import sys
import json
from pathlib import Path

import yaml


def load_metadata(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def main():
    if len(sys.argv) < 2:
        print("Usage: velune dataset-report <datasets_dir> [--export-json file]")
        return 2

    datasets_dir = Path(sys.argv[1])

    export_json = None

    if len(sys.argv) == 4:
        if sys.argv[2] != "--export-json":
            print("[ERROR] Unknown option")
            return 2
        export_json = sys.argv[3]

    report = {"datasets": []}

    print()
    print("=== VELUNE DATASET REPORT ===")
    print()

    for metadata_file in sorted(datasets_dir.rglob("metadata.yaml")):

        dataset_dir = metadata_file.parent
        dataset_name = dataset_dir.name

        data = load_metadata(metadata_file)

        info = data["rosbag2_bagfile_information"]

        duration_sec = (
            info["duration"]["nanoseconds"] / 1_000_000_000
        )

        topics = {}

        for item in info["topics_with_message_count"]:
            topics[item["topic_metadata"]["name"]] = item["message_count"]

        dataset_record = {
            "dataset_name": dataset_name,
            "message_count": info["message_count"],
            "duration_sec": duration_sec,
            "topics": topics,
        }

        report["datasets"].append(dataset_record)

        print(dataset_name)
        print("-" * 60)
        print(f"messages      : {info['message_count']}")
        print(f"duration_sec  : {duration_sec:.3f}")
        print()

        for topic, count in sorted(
            topics.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            print(f"{topic:<20} {count}")

        print()
        print()

    if export_json:
        with open(export_json, "w") as f:
            json.dump(report, f, indent=2)

        print(f"[OK] JSON exported: {export_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
