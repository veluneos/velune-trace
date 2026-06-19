#!/usr/bin/env python3
from pathlib import Path
import json
from mcap.writer import Writer

out = Path("examples/sample.mcap")
out.parent.mkdir(parents=True, exist_ok=True)

schema_text = json.dumps({
    "type": "object",
    "properties": {
        "seq": {"type": "integer"},
        "topic": {"type": "string"},
        "value": {"type": "number"}
    }
})

start_ns = 1_700_000_000_000_000_000

with out.open("wb") as f:
    writer = Writer(f)
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

    seq = 0

    for i in range(100):
        # /lidar_top: 20Hz for 5 seconds
        # intentionally skip one message near second 2 to create a small timing irregularity
        if i != 45:
            t = start_ns + i * 50_000_000
            payload = json.dumps({"seq": seq, "topic": "/lidar_top", "value": float(i)}).encode("utf-8")
            writer.add_message(
                channel_id=lidar_channel,
                log_time=t,
                publish_time=t,
                data=payload,
            )
            seq += 1

    for i in range(500):
        # /imu: 100Hz for 5 seconds
        t = start_ns + i * 10_000_000
        payload = json.dumps({"seq": seq, "topic": "/imu", "value": float(i)}).encode("utf-8")
        writer.add_message(
            channel_id=imu_channel,
            log_time=t,
            publish_time=t,
            data=payload,
        )
        seq += 1

    writer.finish()

print(f"created {out}")
