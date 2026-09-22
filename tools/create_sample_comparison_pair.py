#!/usr/bin/env python3
"""Build a Reference/Target MCAP pair for the public website's Sample
Comparison page that is rich enough to exercise canonical VeluneOS
Compare's real ranking behavior -- not just prove integration.

Design (ten seconds, five Streams):

  /lidar_top (10 Hz, both runs, unchanged)
    An always-on Stream present identically in both runs. Anchors the
    full ten-second comparable range (CG-003 envelope: at least one
    genuinely continuous common Stream) and gives the report one Stream
    that correctly shows NO difference at all.

  /imu (10 Hz in Reference; stops at t=5.0s and never resumes in Target)
    THE meaningful, persistent structural change: a real one-sided
    activity dropout sustained across multiple consecutive Buckets
    (5, 6, 7, 8 -- four Buckets), not a single blip.

  /battery_state (1 Hz, both runs)
    Isolated background jitter: exactly one Bucket (Bucket 2) has one
    extra message in Target. A single-Bucket message-count difference,
    not sustained.

  /cpu_temp (1 Hz, both runs)
    A second, independent isolated background jitter: one Bucket
    (Bucket 3) has one fewer message in Target. Deliberately placed
    outside the /imu dropout window so it reads as an unrelated,
    short-lived variation elsewhere in the run.

  /diagnostics (2 Hz, both runs)
    A small, transient, ONE-Bucket full dropout in Target only (Bucket 1)
    -- the same difference TYPE as /imu's finding (a complete Reference/
    Target activity mismatch), but isolated to a single Bucket rather
    than sustained. This is what makes the sample a genuine test of
    Compare's persistence-based ranking rather than only its difference-
    class priority: /imu and /diagnostics share the same class tier, and
    only persistence should separate them.

This is a real five-Stream, two-file Reference/Target pair matching the
actual Velune Adapter input contract (one MCAP per Run). It is run
through the real, unmodified Adapter and Compare -- the resulting
comparison_report.json is not hand-written, and this script makes no
claim about what the engine will rank first; that is verified separately
after generation.
"""

from __future__ import annotations

from pathlib import Path

from mcap.writer import Writer

DURATION_SEC = 10
START_NS = 1_700_000_000_000_000_000


def add_periodic(writer, channel_id, hz, duration_sec, seq_start, *, stop_at_sec=None):
    """Publish at `hz` for `duration_sec`, optionally stopping permanently
    at `stop_at_sec` (exclusive) if given. Returns the next free seq."""
    step_ns = 1_000_000_000 // hz
    total_ticks = duration_sec * hz
    seq = seq_start
    for i in range(total_ticks):
        sec = i / hz
        if stop_at_sec is not None and sec >= stop_at_sec:
            break
        t = START_NS + i * step_ns
        writer.add_message(
            channel_id=channel_id,
            log_time=t,
            publish_time=t,
            data=f'{{"seq":{seq}}}'.encode("utf-8"),
        )
        seq += 1
    return seq


def add_at_second(writer, channel_id, second, seq):
    """Publish exactly one message at a specific whole-second offset."""
    t = START_NS + second * 1_000_000_000
    writer.add_message(
        channel_id=channel_id,
        log_time=t,
        publish_time=t,
        data=f'{{"seq":{seq}}}'.encode("utf-8"),
    )
    return seq + 1


def write_run(path: Path, *, role: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    is_target = role == "target"

    with path.open("wb") as f:
        writer = Writer(f)
        writer.start()

        schema_id = writer.register_schema(
            name="velune.SampleMessage",
            encoding="jsonschema",
            data=b'{"type":"object","properties":{"seq":{"type":"integer"}}}',
        )
        channels = {
            topic: writer.register_channel(
                topic=topic, message_encoding="json", schema_id=schema_id,
            )
            for topic in (
                "/lidar_top", "/imu", "/battery_state",
                "/cpu_temp", "/diagnostics",
            )
        }

        seq = 0

        # /lidar_top: 10 Hz, identical in both runs.
        seq = add_periodic(
            writer, channels["/lidar_top"], hz=10,
            duration_sec=DURATION_SEC, seq_start=seq,
        )

        # /imu: 10 Hz in Reference; stops permanently at t=5.0s in Target.
        seq = add_periodic(
            writer, channels["/imu"], hz=10,
            duration_sec=DURATION_SEC, seq_start=seq,
            stop_at_sec=(5 if is_target else None),
        )

        # /battery_state: 1 Hz baseline (one message per whole second),
        # both runs; Target gets one EXTRA message inside Bucket 2 only.
        seq = add_periodic(
            writer, channels["/battery_state"], hz=1,
            duration_sec=DURATION_SEC, seq_start=seq,
        )
        if is_target:
            t = START_NS + 2 * 1_000_000_000 + 500_000_000
            writer.add_message(
                channel_id=channels["/battery_state"],
                log_time=t, publish_time=t,
                data=f'{{"seq":{seq}}}'.encode("utf-8"),
            )
            seq += 1

        # /cpu_temp: 1 Hz baseline, both runs; Target is MISSING the
        # Bucket-3 message only (one fewer message, isolated).
        step_ns = 1_000_000_000
        for i in range(DURATION_SEC):
            if is_target and i == 3:
                continue
            t = START_NS + i * step_ns
            writer.add_message(
                channel_id=channels["/cpu_temp"],
                log_time=t, publish_time=t,
                data=f'{{"seq":{seq}}}'.encode("utf-8"),
            )
            seq += 1

        # /diagnostics: 2 Hz baseline, both runs; Target is completely
        # silent for Bucket 1 only (one isolated Bucket, not sustained),
        # then resumes normally for the rest of the run.
        step_ns = 500_000_000
        total_ticks = DURATION_SEC * 2
        for i in range(total_ticks):
            sec = i / 2
            if is_target and 1 <= sec < 2:
                continue
            t = START_NS + i * step_ns
            writer.add_message(
                channel_id=channels["/diagnostics"],
                log_time=t, publish_time=t,
                data=f'{{"seq":{seq}}}'.encode("utf-8"),
            )
            seq += 1

        writer.finish()


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "examples" / "sample_comparison_pair"
    write_run(out_dir / "reference.mcap", role="reference")
    write_run(out_dir / "target.mcap", role="target")
    print(f"wrote {out_dir / 'reference.mcap'}")
    print(f"wrote {out_dir / 'target.mcap'}")


if __name__ == "__main__":
    main()
