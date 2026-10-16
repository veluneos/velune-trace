# VeluneOS Structural Comparison — Engineering Change Review

**Presentation mode:** SHAREABLE (neutral aliases only)

## Result

- **Result:** Structural differences observed for review.
- **Supported differences:** 4 (limited evidence: 0)
- **Inconclusive observations:** 0
- **First supported difference:** T+0s — Stream 004
- **Streams:** Structural difference observed: 2; No material difference observed: 1; Present in Reference only: 1; Present in Target only: 1
- **Compared range:** 29 complete common one-second buckets (T+0s → T+29s)

## Structural differences observed

### Stream present in Reference only — Stream 004

- **What:** Stream present in Reference only
- **Stream:** Stream 004
- **When:** T+0s → T+29.8s (observed messages)
- **Magnitude:** 150 messages in Reference
- **After the window:** Not applicable
- **Evidence:** Comparable: the recorded evidence on both sides supports this observation.
- **ID:** candidate:STREAM\_PRESENCE\_CHANGE:stream.unmapped.004:0-29

### Stream present in Target only — Stream 005

- **What:** Stream present in Target only
- **Stream:** Stream 005
- **When:** T+0s → T+29s (observed messages)
- **Magnitude:** 30 messages in Target
- **After the window:** Not applicable
- **Evidence:** Comparable: the recorded evidence on both sides supports this observation.
- **ID:** candidate:STREAM\_PRESENCE\_CHANGE:stream.unmapped.005:0-29

### Recorded message interval longer in Target — Stream 003

- **What:** Recorded message interval longer in Target
- **Stream:** Stream 003
- **When:** T+10s → T+20s (buckets 10–19)
- **Magnitude:** Median interval Reference 100.0 ms → Target 200.0 ms (×2.00); messages in the window 100 → 50
- **After the window:** Returned to the Reference pattern at T+20s
- **Evidence:** Comparable: the recorded evidence on both sides supports this observation.
- **ID:** candidate:CADENCE\_DIVERGENCE:INTERVAL\_INCREASE:stream.unmapped.003:10-19

### Target recorded no messages while Reference did — Stream 001

- **What:** Target recorded no messages while Reference did
- **Stream:** Stream 001
- **When:** T+12s → T+17s (buckets 12–16)
- **Magnitude:** Reference messages in the window: 100; Target: 0
- **After the window:** Returned to the Reference pattern at T+17s
- **Evidence:** Comparable: the recorded evidence on both sides supports this observation.
- **ID:** candidate:ACTIVITY\_LOSS:stream.unmapped.001:12-16

## Streams

| Stream | Observed status | Findings | Cadence assessable | Recorded-time comparability | Small count differences (max \|Δ\|) |
|---|---|---|---|---|---|
| Stream 001 | Structural difference observed | 1 | yes | COMPARABLE | 5 (20) |
| Stream 002 | No material difference observed | 0 | yes | COMPARABLE | 0 (0) |
| Stream 003 | Structural difference observed | 1 | yes | COMPARABLE | 10 (5) |
| Stream 004 | Present in Reference only | 1 | no | n/a | 0 (0) |
| Stream 005 | Present in Target only | 1 | no | n/a | 0 (0) |

_"No material difference" is bounded to the listed streams and the compared buckets. It is not a statement about other streams, other periods, or system health._

## What was not compared

Run durations: Reference 29.99 s, Target 29.99 s (difference +0.0 ms).

Messages after the last complete common bucket were not compared on 3 stream(s). Differences there, including at the end of a recording, cannot be established from this comparison (per-stream counts in Level 3).

## Level 3 — Evidence trace

### Evidence trace: structural events

| Event ID | Type | Stream key | Buckets | Pattern | Evidence quality | Supporting evidence IDs |
|---|---|---|---|---|---|---|
| event:STREAM\_PRESENCE\_CHANGE:stream.unmapped.004:0-29 | STREAM\_PRESENCE\_CHANGE | stream.unmapped.004 | 0–29 | NOT\_APPLICABLE | COMPARABLE | presence:REFERENCE\_ONLY:stream.unmapped.004 |
| event:STREAM\_PRESENCE\_CHANGE:stream.unmapped.005:0-29 | STREAM\_PRESENCE\_CHANGE | stream.unmapped.005 | 0–29 | NOT\_APPLICABLE | COMPARABLE | presence:TARGET\_ONLY:stream.unmapped.005 |
| event:CADENCE\_DIVERGENCE:INTERVAL\_INCREASE:stream.unmapped.003:10-19 | CADENCE\_DIVERGENCE | stream.unmapped.003 | 10–19 | RECOVERED | COMPARABLE | cadence:INTERVAL\_INCREASE:stream.unmapped.003:10-19 |
| event:ACTIVITY\_LOSS:stream.unmapped.001:12-16 | ACTIVITY\_LOSS | stream.unmapped.001 | 12–16 | RECOVERED | COMPARABLE | review:stream.unmapped.001:12, review:stream.unmapped.001:13, review:stream.unmapped.001:14, review:stream.unmapped.001:15, review:stream.unmapped.001:16 |

### Cadence evidence (both directions)

| Evidence ID | Stream key | Direction | Buckets | Triggers | Baseline side / median | Window median Reference | Window median Target | Messages Ref → Tgt | Recovered at bucket |
|---|---|---|---|---|---|---|---|---|---|
| cadence:INTERVAL\_INCREASE:stream.unmapped.003:10-19 | stream.unmapped.003 | INTERVAL\_INCREASE | 10–19 | mean\_interval | reference 100.0 ms | 100.0 ms | 200.0 ms | 100 → 50 | 20 |

### Cadence windows kept but not asserted

None.

### Recorded-time constraints

None.

### Recorded-time comparability per stream

| Stream key | State | Reasons | Shared-stamp buckets Ref / Tgt | Interval grid Ref / Tgt | Median interval Ref / Tgt |
|---|---|---|---|---|---|
| stream.unmapped.001 | COMPARABLE | none | 0/29 / 0/24 | 1 ms / 1 ms | 50.0 ms / 50.0 ms |
| stream.unmapped.002 | COMPARABLE | none | 0/29 / 0/29 | 1 ms / 1 ms | 10.0 ms / 10.0 ms |
| stream.unmapped.003 | COMPARABLE | none | 0/29 / 0/29 | 1 ms / 1 ms | 100.0 ms / 100.0 ms |

### Coverage per stream

| Stream key | Messages compared Ref / Tgt | Messages after range Ref / Tgt | First message Ref / Tgt | Last message Ref / Tgt | Tail |
|---|---|---|---|---|---|
| stream.unmapped.001 | 580 / 480 | 20 / 20 | T+0s / T+0s | T+29.9s / T+29.9s | INSUFFICIENT\_COVERAGE |
| stream.unmapped.002 | 2900 / 2900 | 100 / 100 | T+0s / T+0s | T+30.0s / T+30.0s | INSUFFICIENT\_COVERAGE |
| stream.unmapped.003 | 290 / 240 | 10 / 10 | T+0s / T+0s | T+29.9s / T+29.9s | INSUFFICIENT\_COVERAGE |

### Bucket-level count differences (15; largest first, not promoted)

_Display order only; the report JSON keeps the contract order. Count-only differences are not promoted to findings._

| Evidence ID | Stream key | Bucket | Reference | Target | Δ | Type |
|---|---|---|---|---|---|---|
| review:stream.unmapped.001:12 | stream.unmapped.001 | 12 | 20 | 0 | -20 | reference\_nonempty\_target\_empty |
| review:stream.unmapped.001:13 | stream.unmapped.001 | 13 | 20 | 0 | -20 | reference\_nonempty\_target\_empty |
| review:stream.unmapped.001:14 | stream.unmapped.001 | 14 | 20 | 0 | -20 | reference\_nonempty\_target\_empty |
| review:stream.unmapped.001:15 | stream.unmapped.001 | 15 | 20 | 0 | -20 | reference\_nonempty\_target\_empty |
| review:stream.unmapped.001:16 | stream.unmapped.001 | 16 | 20 | 0 | -20 | reference\_nonempty\_target\_empty |
| review:stream.unmapped.003:10 | stream.unmapped.003 | 10 | 10 | 5 | -5 | message\_count\_difference |
| review:stream.unmapped.003:11 | stream.unmapped.003 | 11 | 10 | 5 | -5 | message\_count\_difference |
| review:stream.unmapped.003:12 | stream.unmapped.003 | 12 | 10 | 5 | -5 | message\_count\_difference |
| review:stream.unmapped.003:13 | stream.unmapped.003 | 13 | 10 | 5 | -5 | message\_count\_difference |
| review:stream.unmapped.003:14 | stream.unmapped.003 | 14 | 10 | 5 | -5 | message\_count\_difference |
| review:stream.unmapped.003:15 | stream.unmapped.003 | 15 | 10 | 5 | -5 | message\_count\_difference |
| review:stream.unmapped.003:16 | stream.unmapped.003 | 16 | 10 | 5 | -5 | message\_count\_difference |
| review:stream.unmapped.003:17 | stream.unmapped.003 | 17 | 10 | 5 | -5 | message\_count\_difference |
| review:stream.unmapped.003:18 | stream.unmapped.003 | 18 | 10 | 5 | -5 | message\_count\_difference |
| review:stream.unmapped.003:19 | stream.unmapped.003 | 19 | 10 | 5 | -5 | message\_count\_difference |

### Provenance and method

- **Report schema:** velune.structural\_comparison\_report 0.5.0 (private\_cloud\_only)
- **Bundle ID:** vcib\_sha256\_5173b991aecffc7d48af2b9fb83cc9a5ef1402fb963ad27c16652adf5fd034df
- **Bundle contract:** velune.comparison\_input\_bundle 0.1.0
- **Mapping profile:** generic.mcap.structural 0.1.0
- **Generated at:** 2026-10-16T02:27:17.191588+00:00
- **Comparison rule:** complete common one-second buckets on each run's own time axis
- **Candidate review order:** candidate:STREAM\_PRESENCE\_CHANGE:stream.unmapped.004:0-29, candidate:STREAM\_PRESENCE\_CHANGE:stream.unmapped.005:0-29, candidate:CADENCE\_DIVERGENCE:INTERVAL\_INCREASE:stream.unmapped.003:10-19, candidate:ACTIVITY\_LOSS:stream.unmapped.001:12-16

This report records observed structural differences between two recordings. A matching run-relative time does not claim the same physical moment. Direction words describe the recordings, not improvement or degradation. No cause, fault, severity, or safety judgment is made.

**Find the events. Engineers find the cause.**
