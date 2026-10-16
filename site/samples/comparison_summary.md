# Velune Structural Comparison — Engineering Change Review

## 1. Comparison scope

- Input Bundle: `vcib_sha256_5173b991aecffc7d48af2b9fb83cc9a5ef1402fb963ad27c16652adf5fd034df`
- Compared range: 29 complete common one-second Buckets (Buckets 0–28)
- Time axes: each run is measured from its own first message; a matching Bucket does not claim the same physical moment.
- Run durations: Reference 29,990.0 ms, Target 29,990.0 ms (difference +0.0 ms)
- Streams: 3 common, 1 Reference-only, 1 Target-only

## 2. Result

- Result: Structural differences observed for review. (`REVIEW_REQUIRED`)
- Supported material differences: 4 (0 with limited evidence); inconclusive: 0
- First supported divergence: `stream.unmapped.004`, STREAM_PRESENCE_CHANGE, Bucket 0

## 3. Material differences

1. `stream.unmapped.004`: stream observed only in Reference — 150 messages, Buckets 0–29. Evidence: COMPARABLE; `candidate:STREAM_PRESENCE_CHANGE:stream.unmapped.004:0-29`.
2. `stream.unmapped.005`: stream observed only in Target — 30 messages, Buckets 0–29. Evidence: COMPARABLE; `candidate:STREAM_PRESENCE_CHANGE:stream.unmapped.005:0-29`.
3. `stream.unmapped.003`: recorded message interval longer in Target — Buckets 10–19 (10–20 s on each run's own time axis). Median mean interval Reference 100.0 ms -> Target 200.0 ms (x2.00); messages in the window 100 -> 50. Returned to the Reference pattern at Bucket 20. Evidence: COMPARABLE; `candidate:CADENCE_DIVERGENCE:INTERVAL_INCREASE:stream.unmapped.003:10-19`.
4. `stream.unmapped.001`: Target recorded no messages while Reference did — Buckets 12–16 (12–17 s on each run's own time axis); Reference messages there 100. Target was active before. Returned to the Reference pattern at Bucket 17. Evidence: COMPARABLE; `candidate:ACTIVITY_LOSS:stream.unmapped.001:12-16`.

## 5. Streams

| Stream | Observed status | Findings | Lower-level count differences (max abs delta) |
|---|---|---|---|
| `stream.unmapped.001` | material difference | 1 | 5 (20) |
| `stream.unmapped.002` | no material difference observed | 0 | 0 (0) |
| `stream.unmapped.003` | material difference | 1 | 10 (5) |
| `stream.unmapped.004` | present in Reference only | 1 | 0 (0) |
| `stream.unmapped.005` | present in Target only | 1 | 0 (0) |

"No material difference" is bounded to the listed streams and the compared Buckets; it is not a statement about other streams, other periods, or system health.

## 6. Evidence limits and coverage

- Messages after the last complete common Bucket were not compared (INSUFFICIENT_COVERAGE) on 3 stream(s): Reference 130, Target 130 messages. Differences there, including at the end of a recording, cannot be established from this comparison; per-stream counts are in `temporal_coverage`.

## 7. Lower-level evidence (not promoted)

15 Bucket-level count differences. Shown by absolute delta (display order only; `comparison_report.json` keeps the contract order). Count-only differences are not promoted to findings.

1. `stream.unmapped.001`, Bucket 12: Reference 20, Target 0 (-20; `reference_nonempty_target_empty`)
2. `stream.unmapped.001`, Bucket 13: Reference 20, Target 0 (-20; `reference_nonempty_target_empty`)
3. `stream.unmapped.001`, Bucket 14: Reference 20, Target 0 (-20; `reference_nonempty_target_empty`)
4. `stream.unmapped.001`, Bucket 15: Reference 20, Target 0 (-20; `reference_nonempty_target_empty`)
5. `stream.unmapped.001`, Bucket 16: Reference 20, Target 0 (-20; `reference_nonempty_target_empty`)
6. `stream.unmapped.003`, Bucket 10: Reference 10, Target 5 (-5; `message_count_difference`)
7. `stream.unmapped.003`, Bucket 11: Reference 10, Target 5 (-5; `message_count_difference`)
8. `stream.unmapped.003`, Bucket 12: Reference 10, Target 5 (-5; `message_count_difference`)
9. `stream.unmapped.003`, Bucket 13: Reference 10, Target 5 (-5; `message_count_difference`)
10. `stream.unmapped.003`, Bucket 14: Reference 10, Target 5 (-5; `message_count_difference`)
Showing 10 of 15; see `comparison_report.json`.

## 8. Detailed trace

- Cadence evidence `cadence:INTERVAL_INCREASE:stream.unmapped.003:10-19`: INTERVAL_INCREASE, triggers mean_interval; window median mean interval Reference 100.0 ms, Target 200.0 ms; baseline (reference) 100.0 ms
- Event `event:STREAM_PRESENCE_CHANGE:stream.unmapped.004:0-29` <- `presence:REFERENCE_ONLY:stream.unmapped.004`
- Event `event:STREAM_PRESENCE_CHANGE:stream.unmapped.005:0-29` <- `presence:TARGET_ONLY:stream.unmapped.005`
- Event `event:CADENCE_DIVERGENCE:INTERVAL_INCREASE:stream.unmapped.003:10-19` <- `cadence:INTERVAL_INCREASE:stream.unmapped.003:10-19`
- Event `event:ACTIVITY_LOSS:stream.unmapped.001:12-16` <- `review:stream.unmapped.001:12`, `review:stream.unmapped.001:13`, `review:stream.unmapped.001:14`, `review:stream.unmapped.001:15`, `review:stream.unmapped.001:16`

## Interpretation boundary

Observed structural differences in the recordings only. Direction words (longer, shorter, silent) describe the recordings, not improvement or degradation. No cause, fault, severity, or safety judgment.

**Find the events. Engineers find the cause.**
