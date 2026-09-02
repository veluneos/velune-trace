#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mcap.writer import Writer


def create_sample_mcap(
    output_path: str | Path = "examples/sample.mcap",
) -> Path:
    out = Path(output_path)
    out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    schema_text = json.dumps({
        "type": "object",
        "properties": {
            "seq": {"type": "integer"},
            "topic": {"type": "string"},
            "value": {"type": "number"},
        },
    })

    start_ns = 1_700_000_000_000_000_000

    with out.open("wb") as stream:
        writer = Writer(stream)
        writer.start()

        schema_id = writer.register_schema(
            name="velune.SampleMessage",
            encoding="jsonschema",
            data=schema_text.encode("utf-8"),
        )

        lidar_channel = writer.register_channel(
            topic="/lidar_top",
            message_encoding="json",
            schema_id=schema_id,
        )

        imu_channel = writer.register_channel(
            topic="/imu",
            message_encoding="json",
            schema_id=schema_id,
        )

        sequence = 0

        for index in range(100):
            # /lidar_top: 20 Hz for five seconds.
            # One message is intentionally omitted.
            if index == 45:
                continue

            timestamp = (
                start_ns
                + index * 50_000_000
            )

            payload = json.dumps({
                "seq": sequence,
                "topic": "/lidar_top",
                "value": float(index),
            }).encode("utf-8")

            writer.add_message(
                channel_id=lidar_channel,
                log_time=timestamp,
                publish_time=timestamp,
                data=payload,
            )

            sequence += 1

        for index in range(500):
            # /imu: 100 Hz for five seconds.
            timestamp = (
                start_ns
                + index * 10_000_000
            )

            payload = json.dumps({
                "seq": sequence,
                "topic": "/imu",
                "value": float(index),
            }).encode("utf-8")

            writer.add_message(
                channel_id=imu_channel,
                log_time=timestamp,
                publish_time=timestamp,
                data=payload,
            )

            sequence += 1

        writer.finish()

    return out


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Create the deterministic Velune sample MCAP.",
    )

    parser.add_argument(
        "output",
        nargs="?",
        default="examples/sample.mcap",
        help="Output MCAP path.",
    )

    arguments = parser.parse_args(argv)

    output_path = create_sample_mcap(
        arguments.output
    )

    print(f"created {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
