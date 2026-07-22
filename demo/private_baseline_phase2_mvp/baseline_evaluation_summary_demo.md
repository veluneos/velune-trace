# Public Demonstration Notice

This document was derived from a completed local VeluneOS
Private Baseline Target Evaluation.

It contains no raw robot log and no local filesystem path.

The demonstrated Target was real-derived but was not an independent
commercial robot execution.

The observations below must not be interpreted as defect, severity,
normality, safety, regression, or root-cause judgments.

---

# Private Baseline Target Evaluation

## Evaluation

- Evaluation ID: `vpbe_723ae40736450490c75ea88c83c79f0e`
- Baseline ID: `vpb_fc0d272646283d44be358ea9d84e7f86`
- Baseline Revision ID: `vpbr_43a99be29aded718ebc2ec9ad0fc3851`
- Generated at: `2026-07-21T17:44:43+09:00`
- Comparison axis: `custom`
- Axis keys: `scene_id`
- Target Bundle: `vrb_sha256_dd37c3768b435526f87047d4264508c38ec66825b1ff9db3d2c2a3586670c187`

## Descriptive Occurrence Summary

- Reference count: 2
- Observed topic count: 41
- Topics with changed fields: 41
- Changed field records: 481
- Fields changed against every eligible Reference: 430
- Fields changed against some eligible References: 51

Counts describe where observed differences appeared. They are not severity, probability, regression, improvement, or normality scores.

## Changed Topic Preview

- `/cam_back/annotations`: 12 changed field record(s)
- `/cam_back/camera_info`: 12 changed field record(s)
- `/cam_back/image_rect_compressed`: 12 changed field record(s)
- `/cam_back/lidar`: 12 changed field record(s)
- `/cam_back_left/annotations`: 12 changed field record(s)
- 36 additional changed topic(s) are available in the JSON source of truth.

## Changed Field Details

### `/cam_back/annotations`

- `evidence_summary.max_jitter_ns`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

### `/cam_back/camera_info`

- `evidence_summary.max_jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

### `/cam_back/image_rect_compressed`

- `evidence_summary.max_jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

### `/cam_back/lidar`

- `evidence_summary.max_jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

### `/cam_back_left/annotations`

- `evidence_summary.max_jitter_ns`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

### `/cam_back_left/camera_info`

- `evidence_summary.max_jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

### `/cam_back_left/image_rect_compressed`

- `evidence_summary.max_jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

### `/cam_back_left/lidar`

- `evidence_summary.max_jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

### `/cam_back_right/annotations`

- `evidence_summary.max_jitter_ns`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

### `/cam_back_right/camera_info`

- `evidence_summary.max_jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

### `/cam_back_right/image_rect_compressed`

- `evidence_summary.max_jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

### `/cam_back_right/lidar`

- `evidence_summary.max_jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

### `/cam_front/annotations`

- `evidence_summary.max_jitter_ns`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

### `/cam_front/camera_info`

- `evidence_summary.max_jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

### `/cam_front/image_rect_compressed`

- `evidence_summary.max_jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

### `/cam_front/lidar`

- `evidence_summary.max_jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

### `/cam_front_left/annotations`

- `evidence_summary.max_jitter_ns`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

### `/cam_front_left/camera_info`

- `evidence_summary.max_jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

### `/cam_front_left/image_rect_compressed`

- `evidence_summary.max_jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

### `/cam_front_left/lidar`

- `evidence_summary.max_jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.max_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.mean_observed_irregularity_score`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `evidence_summary.min_count_ratio`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.avg_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.duration_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.expected_count_per_window`: changed against 1 of 2 eligible Reference(s); scope=`some_references`
- `profile.finalized_window_count`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.jitter_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`
- `profile.max_gap_ns`: changed against 2 of 2 eligible Reference(s); scope=`all_references`

21 additional changed topic(s) are omitted from detailed Markdown.

## Topic-Set Occurrence

No Reference-only or Target-only topic occurrence was observed.

## Reference Comparisons

- `vrb_sha256_01df81a98ce891f2f2364fe49bcd25561315a74517e2a072a03943d9e4b674aa`: changed_profile_topics=41, changed_evidence_summary_topics=41
- `vrb_sha256_e1f6251f9d96747a8d22326d57773b95bebe1837f824fc56763321cbfc84c4a2`: changed_profile_topics=41, changed_evidence_summary_topics=41

## Presentation Policy

- Policy version: `0.1.0`
- Ordering is lexicographic and does not represent importance, severity, similarity, or priority.
- Complete pairwise Comparison v1 reports and all aggregate records remain in `baseline_evaluation_report.json`.

## Human Judgment Boundary

> Velune reports observed differences against a user-selected private Reference set. Engineers determine their meaning, cause, and review outcome.

