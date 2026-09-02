#!/usr/bin/env python3
import json
import argparse
import heapq
from collections import Counter

NON_JUDGMENT = (
    "Viewer provides searchable timeline views only. "
    "It does not assign fault, liability, risk score, blame, or root cause."
)

def fmt_event(e):
    idx = e.get("sequence_index", 0)
    line = e.get("_file_line", 0)
    t = e.get("ros_time")
    et = e.get("event_type")
    topic = e.get("source_topic")
    s = e.get("event_summary", {})
    cd = e.get("clock_domain", "MISSING")
    ts = e.get("time_source", "MISSING")

    if et == "COMMAND_SUMMARY":
        detail = f"cmd linear_x={s.get('linear_x')} angular_z={s.get('angular_z')} type={s.get('message_type')}"
    elif et == "MOTION_SUMMARY":
        detail = f"motion vx={s.get('linear_velocity_x')} wz={s.get('angular_velocity_z')}"
    elif et == "PERCEPTION_SUMMARY":
        detail = f"scan min_range={s.get('min_range')} valid={s.get('valid_range_count')} invalid={s.get('invalid_range_count')}"
    else:
        detail = str(s)

    return f"[seq={idx:06} line={line:06}] ros_time={t} clock_domain={cd} time_source={ts} {et} topic={topic} | {detail}"

def match_event(line, e, args):
    wanted_type = args.event_type or args.type

    if wanted_type and e.get("event_type") != wanted_type:
        return False
    if args.topic and e.get("source_topic") != args.topic:
        return False
    if args.contains and args.contains not in line:
        return False
    return True

def match_count(line, e, args):
    count = 0
    wanted_type = args.event_type or args.type

    if wanted_type and e.get("event_type") == wanted_type:
        count += 1
    if args.topic and e.get("source_topic") == args.topic:
        count += 1
    if args.contains and args.contains in line:
        count += 1
    return count

def ros_sort_key(e):
    t = e.get("ros_time")
    if not isinstance(t, (int, float)):
        return (1, 0, e.get("sequence_index", 0))
    return (0, t, e.get("sequence_index", 0))

def main():
    ap = argparse.ArgumentParser(description="Velune Trace Viewer v0.4 Streaming Search Viewer")
    ap.add_argument("path")
    ap.add_argument("--type", default=None)
    ap.add_argument("--event-type", default=None)
    ap.add_argument("--topic", default=None)
    ap.add_argument("--contains", default=None)
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--order", choices=["file", "ros_time", "match_count"], default="file")
    ap.add_argument("--max-buffer", type=int, default=10000)
    args = ap.parse_args()

    total_seen = 0
    total_matched = 0
    counts = Counter()
    clock_domains = Counter()
    time_sources = Counter()

    buffered = []

    with open(args.path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue

            total_seen += 1

            if args.contains and args.order == "file" and args.contains not in line:
                continue

            e = json.loads(line)
            e["_file_line"] = line_no

            if not match_event(line, e, args):
                continue

            total_matched += 1
            counts[e.get("event_type", "UNKNOWN")] += 1
            clock_domains[e.get("clock_domain", "MISSING")] += 1
            time_sources[e.get("time_source", "MISSING")] += 1

            if args.order == "file":
                if total_matched <= args.limit:
                    print(fmt_event(e))
            else:
                if len(buffered) >= args.max_buffer:
                    raise SystemExit(
                        "MAX_BUFFER_EXCEEDED: narrow the query or increase --max-buffer. "
                        "Viewer refuses unbounded memory use."
                    )
                buffered.append((line, e))

    if args.order == "ros_time":
        buffered.sort(key=lambda x: ros_sort_key(x[1]))
        for _, e in buffered[:args.limit]:
            print(fmt_event(e))

    elif args.order == "match_count":
        buffered.sort(key=lambda x: (-match_count(x[0], x[1], args), x[1].get("sequence_index", 0)))
        for _, e in buffered[:args.limit]:
            print(fmt_event(e))

    print()
    print("SUMMARY")
    print(f"TOTAL_SEEN={total_seen}")
    print(f"MATCHED_TOTAL={total_matched}")

    for k, v in counts.most_common():
        print(f"{k}={v}")

    print("CLOCK_DOMAINS")
    for k, v in clock_domains.most_common():
        print(f"{k}={v}")

    print("TIME_SOURCES")
    for k, v in time_sources.most_common():
        print(f"{k}={v}")

    print("ORDERING_POLICY=file order by default; ros_time or match_count only when explicitly requested.")
    print("MATCH_COUNT_POLICY=Flat query-match count only. No weighted ranking, no risk scoring, no fault priority.")
    print(f"NON_JUDGMENT_STATEMENT={NON_JUDGMENT}")

if __name__ == "__main__":
    main()
