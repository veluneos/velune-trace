#!/usr/bin/env python3

"""
Velune Trace Read CLI

Purpose:
  Read messages from a selected MCAP chunk or time window.
  Optional topic filtering is supported.

This command is retrieval-only.
It does not detect, judge, score, or infer causality.

Usage:
  ./bin/velune read <file.mcap> --chunk 37
  ./bin/velune read <file.mcap> --chunk 37 --topic /scan
  ./bin/velune read <file.mcap> --start-sec 1780576732 --end-sec 1780576736
  ./bin/velune read <file.mcap> --start-sec 1780576732 --end-sec 1780576736 --topic /scan
"""

import sys
from mcap.reader import make_reader

from velune_trace.adapters.mcap_reader import VeluneMcapReader, VeluneError
from velune_trace.utils.formatter import ns_to_sec


def sec_to_ns(sec: float) -> int:
    return int(sec * 1_000_000_000)


def parse_args(argv):
    if len(argv) < 4:
        print("[ERROR] Usage:")
        print("  velune read <file.mcap> --chunk <chunk_id> [--topic <topic>]")
        print("  velune read <file.mcap> --start-sec <sec> --end-sec <sec> [--topic <topic>]")
        return None

    filename = argv[1]
    topic_filter = None

    if "--topic" in argv:
        topic_index = argv.index("--topic")

        if topic_index + 1 >= len(argv):
            print("[ERROR] --topic requires a topic name.")
            return None

        topic_filter = argv[topic_index + 1]
        argv = argv[:topic_index] + argv[topic_index + 2:]

    if argv[2] == "--chunk":
        if len(argv) != 4:
            print("[ERROR] Usage: velune read <file.mcap> --chunk <chunk_id> [--topic <topic>]")
            return None

        try:
            chunk_id = int(argv[3])
        except ValueError:
            print("[ERROR] chunk_id must be an integer.")
            return None

        return {
            "filename": filename,
            "mode": "chunk",
            "chunk_id": chunk_id,
            "start_ns": None,
            "end_ns": None,
            "topic_filter": topic_filter,
        }

    if argv[2] == "--start-sec":
        if len(argv) != 6 or argv[4] != "--end-sec":
            print("[ERROR] Usage: velune read <file.mcap> --start-sec <sec> --end-sec <sec> [--topic <topic>]")
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

        return {
            "filename": filename,
            "mode": "time",
            "chunk_id": None,
            "start_ns": sec_to_ns(start_sec),
            "end_ns": sec_to_ns(end_sec),
            "topic_filter": topic_filter,
        }

    print(f"[ERROR] Unknown read option: {argv[2]}")
    print("[ERROR] Supported:")
    print("  --chunk <chunk_id>")
    print("  --start-sec <sec> --end-sec <sec>")
    return None


def find_overlapping_chunks(chunks, start_ns, end_ns):
    matches = []

    for chunk in chunks:
        chunk_start = chunk["message_start_time_ns"]
        chunk_end = chunk["message_end_time_ns"]

        if chunk_start is None or chunk_end is None:
            continue

        overlaps = chunk_start <= end_ns and chunk_end >= start_ns

        if overlaps:
            matches.append(chunk["chunk_id"])

    return matches


def print_no_result_diagnostics(
    inspect_result,
    start_ns,
    end_ns,
    topic_filter,
    overlapping_chunks,
):
    print()
    print("=== NO RESULT DIAGNOSTICS ===")
    print()

    dataset_start = inspect_result.start_time_ns
    dataset_end = inspect_result.end_time_ns

    print(f"Dataset Start sec   : {ns_to_sec(dataset_start)}")
    print(f"Dataset End sec     : {ns_to_sec(dataset_end)}")
    print(f"Requested Start sec : {ns_to_sec(start_ns)}")
    print(f"Requested End sec   : {ns_to_sec(end_ns)}")

    print()

    if dataset_start is not None and dataset_end is not None:
        if end_ns < dataset_start or start_ns > dataset_end:
            print("[LIKELY REASON] Requested time window is outside the MCAP time range.")
            print("[HINT] Use ./bin/velune inspect <file.mcap> to check valid time range.")
            return

    if not overlapping_chunks:
        print("[LIKELY REASON] No chunk overlaps the requested time window.")
        print("[HINT] Use ./bin/velune chunks <file.mcap> to inspect available chunks.")
        return

    if topic_filter:
        print("[LIKELY REASON] Topic exists, but no messages were found for this topic in the selected time window.")
        print("[HINT] Try the same time window without --topic to check whether other topics exist.")
        print("[HINT] Or widen the time window.")
        return

    print("[LIKELY REASON] The selected time window overlaps chunks, but no messages were returned.")
    print("[HINT] This may indicate sparse data, boundary precision issues, or an unusual MCAP index.")
    print("[HINT] Try widening the time window slightly.")


def main() -> int:
    parsed = parse_args(sys.argv)
    if parsed is None:
        return 2

    filename = parsed["filename"]
    topic_filter = parsed["topic_filter"]

    try:
        inspect_result = VeluneMcapReader(filename).inspect()

        if not inspect_result.has_summary:
            print("[ERROR] MCAP summary not found. Read unavailable.")
            return 1

        available_topics = sorted(topic["topic"] for topic in inspect_result.topics)

        if topic_filter is not None and topic_filter not in available_topics:
            print(f"[ERROR] Topic not found: {topic_filter}")
            print()
            print("Available topics:")
            for topic in available_topics:
                print(f"  {topic}")
            return 1

        if parsed["mode"] == "chunk":
            chunk_id = parsed["chunk_id"]

            if chunk_id < 0 or chunk_id >= len(inspect_result.chunks):
                print(f"[ERROR] chunk_id out of range: {chunk_id}")
                print(f"[HINT] Valid range: 0 ~ {len(inspect_result.chunks) - 1}")
                return 1

            chunk = inspect_result.chunks[chunk_id]
            start_ns = chunk["message_start_time_ns"]
            end_ns = chunk["message_end_time_ns"]
            overlapping_chunks = [chunk_id]
            selection_label = f"Chunk ID           : {chunk_id}"

        else:
            start_ns = parsed["start_ns"]
            end_ns = parsed["end_ns"]
            overlapping_chunks = find_overlapping_chunks(inspect_result.chunks, start_ns, end_ns)
            selection_label = f"Overlapping Chunks : {overlapping_chunks}"

        duration_sec = None
        if start_ns is not None and end_ns is not None:
            duration_sec = (end_ns - start_ns) / 1_000_000_000

        print()
        print("=== VELUNE READ ===")
        print()
        print(f"File               : {filename}")
        print(f"Mode               : {parsed['mode']}")
        print(selection_label)
        print(f"Topic Filter       : {topic_filter if topic_filter else 'ALL'}")
        print(f"Start ns           : {start_ns}")
        print(f"End ns             : {end_ns}")
        print(f"Start sec          : {ns_to_sec(start_ns)}")
        print(f"End sec            : {ns_to_sec(end_ns)}")
        print(
            f"Window Duration sec: {duration_sec:.6f}"
            if duration_sec is not None
            else "Window Duration sec: N/A"
        )

        count = 0
        first = None
        last = None
        topic_counts = {}

        with open(filename, "rb") as f:
            reader = make_reader(f)

            topics_arg = [topic_filter] if topic_filter else None

            for schema, channel, message in reader.iter_messages(
                topics=topics_arg,
                start_time=start_ns,
                end_time=end_ns,
            ):
                count += 1

                topic = channel.topic

                item = {
                    "topic": topic,
                    "log_time": message.log_time,
                    "log_time_sec": ns_to_sec(message.log_time),
                    "publish_time": message.publish_time,
                    "publish_time_sec": ns_to_sec(message.publish_time),
                    "sequence": message.sequence,
                    "message_size": len(message.data),
                }

                if first is None:
                    first = item

                last = item
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

        print()
        print(f"Messages Read      : {count}")

        print()
        print("=== TOPIC COUNTS ===")
        print()

        if topic_counts:
            for topic, topic_count in sorted(topic_counts.items()):
                print(f"{topic:<20} {topic_count}")
        else:
            print("[WARN] No messages matched the selected window/topic.")
            print_no_result_diagnostics(
                inspect_result=inspect_result,
                start_ns=start_ns,
                end_ns=end_ns,
                topic_filter=topic_filter,
                overlapping_chunks=overlapping_chunks,
            )

        print()

        if first:
            print("=== FIRST MESSAGE ===")
            print()
            for k, v in first.items():
                print(f"{k:<17}: {v}")
            print()

        if last:
            print("=== LAST MESSAGE ===")
            print()
            for k, v in last.items():
                print(f"{k:<17}: {v}")

        return 0

    except VeluneError as e:
        print()
        print("=== VELUNE READ ERROR ===")
        print()
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
