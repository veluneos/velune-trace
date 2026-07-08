# Example Velune Validation Feedback Report

This is an example of the feedback a Validation Partner may receive after submitting only:

    velune_report/shareable_anonymous_report.json

Raw MCAP files are not required.

This example uses synthetic sample data and is provided only to show the expected report format.

## 1. Submission Summary

Report ID:

    example_partner_001

Schema Version:

    0.2.0

Analysis Mode:

    bounded_streaming_aggregation

Raw MCAP Received:

    No

Analysis Basis:

    Anonymous timing evidence only

Submitted Artifact:

    shareable_anonymous_report.json

Submitted Artifact SHA-256:

    example_sha256_6d7f0e3b9a1c4f2e8b5a0c9d3e7f1a2b4c6d8e0f1234567890abcdef12345678

Input Log Signature:

    Not required for submission

Note:

    Velune does not require the raw MCAP file or raw sensor payloads.
    A raw input hash may be kept locally by the participant for internal traceability.
    The feedback report references the submitted anonymous report artifact.

## 2. Observed Summary

Topics observed:

    2

Total messages observed:

    599

Out-of-order messages:

    0

Late dropped messages:

    0

Maximum active windows observed:

    6

## 3. Primary Evidence Topic

Topic:

    /lidar_top

Expected count per 1-second window:

    20

Expected source:

    inferred_from_observed_median

Observed message count:

    99

Average gap:

    50.51 ms

Maximum gap:

    100.00 ms

Observed jitter:

    5.02 ms

## 4. Evidence Window Recommended for Review

Window ID:

    2

Window start:

    1700000002.000000000

Window end:

    1700000003.000000000

Observed count:

    19

Expected count:

    20

Observed count ratio:

    0.95

Maximum gap in window:

    100.00 ms

Jitter in window:

    11.45 ms

Evidence score:

    1.557265

## 5. Co-occurring Timing Context

This section summarizes timing behavior observed in the same evidence window.

It does not inspect raw sensor payloads.

Primary topic:

    /lidar_top

Primary observation:

    One 1-second window showed 19 observed messages against an inferred local baseline of 20.

Co-occurring topic:

    /imu

Expected count per 1-second window:

    100

Observed count in same window:

    100

Observed count ratio:

    1.00

Out-of-order messages in same window:

    0

Late dropped messages in same window:

    0

Context observation:

    The /lidar_top topic showed a timing irregularity in this window.
    The /imu topic did not show a matching count drop in the same window.

Investigation implication:

    Start review from the /lidar_top publication, transport, QoS, or driver path.
    Then compare adjacent timing signals from /imu, /odom, /tf, and /clock if available.

Boundary:

    This is not a root-cause conclusion.
    This is an evidence-based investigation starting point.

## 6. Interpretation

One 1-second window showed 19 observed messages against an inferred local baseline of 20 messages.

The maximum observed timing gap in that window was approximately 2.0x the local baseline interval.

The same timing window did not show a matching count drop on the co-occurring /imu topic in this example.

This window is recommended as an investigation starting point.

## 7. Quick-Check Checklist

Recommended checks for the engineering team:

- [ ] Confirm whether the /lidar_top publisher emitted messages continuously during this window.
- [ ] Inspect /lidar_top driver logs from T-100ms to T+100ms around the evidence window.
- [ ] Check ROS 2 QoS settings for /lidar_top, including reliability, history, depth, and durability.
- [ ] Compare /lidar_top cadence with /imu, /odom, /tf, and /clock in the same time window.
- [ ] Check whether CPU load, network jitter, disk I/O, or middleware backpressure changed near the window.
- [ ] Verify whether the same timing pattern repeats across additional runs.
- [ ] Confirm whether timestamps are based on sensor time, ROS time, or system time.
- [ ] Review whether message batching, compression, or bridge behavior affected publication cadence.

## 8. Benchmark Status

Reference comparison:

    Limited sample reference only

Global percentile:

    Not available

Matched anonymous cohort comparison:

    Not available yet

Reason:

    This example does not represent a validated global benchmark or industry average.

Future benchmark reports may compare this result against a matched anonymous cohort when enough compatible reports are available.

A valid matched cohort should define conditions such as:

    sensor category
    expected publish rate
    window size
    schema version
    robot or deployment class
    timing source assumptions

## 9. Boundary

Velune reports observable timing evidence.

Velune identifies evidence windows worth reviewing first.

Velune does not infer root cause.

Velune does not assign fault.

Velune does not make safety, liability, or risk determinations.

Engineers determine cause.
