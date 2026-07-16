# Velune Core Bundle Comparison v1

## Status

- Design status: `V1_CONTRACT_FROZEN_FOR_IMPLEMENTATION`
- Comparison type: `REFERENCE_BUNDLE_VS_TARGET_BUNDLE`
- Semantics: `observed_comparison_only`
- Visibility: `private_local_only`
- Root-cause conclusion: prohibited
- Fault assignment: prohibited
- Liability calculation: prohibited
- Regression judgment: prohibited in v1

## Purpose

Core Bundle Comparison v1 compares two completed Velune Evidence
Report Bundles without reopening or rescanning their raw MCAP files.

The two logical roles are:

- Reference Bundle
- Target Bundle

The comparison reports observable differences between derived timing
evidence. It does not determine whether a system became better,
worse, safer, defective, responsible, or causal.

## Command Boundary

The new CLI command will be:

~~~text
velune compare-bundles \
  <reference_bundle_dir> \
  <target_bundle_dir> \
  --export-dir <comparison_output_dir>
~~~

This command is separate from:

- `velune compare`
- `velune compare-all`

The existing commands compare selected time windows directly from raw
MCAP inputs.

`compare-bundles` compares completed Core Report Bundle artifacts.

## Required Input Files

Each input directory must contain:

- `report_manifest.json`
- `topic_profile.json`
- `evidence_windows.json`

The following files may exist but are not parsed as comparison input:

- `summary.md`
- `SCHEMA.md`
- `shareable_anonymous_report.json`

Markdown is never used as the machine-readable source of truth.

## Input Integrity Validation

Before comparison, the implementation must:

1. Parse both `report_manifest.json` files.
2. Confirm that each manifest declares the required artifacts.
3. Verify the manifest-recorded SHA-256 for:
   - `topic_profile.json`
   - `evidence_windows.json`
4. Reject symbolic links for required input artifacts.
5. Reject missing, malformed, non-finite, or unexpected structures.
6. Produce no partial comparison output after validation failure.

The comparison does not require access to the original MCAP file.

## Compatibility Gate

Comparison proceeds only when all blocking fields are compatible.

### Blocking Compatibility Fields

The following values must match:

- manifest schema name
- manifest schema version
- Bundle schema name
- Bundle schema version
- engine name
- extraction semantics
- extraction mode
- timestamp unit
- window duration
- allowed lateness
- top evidence-window count

Expected current values include:

~~~text
bundle_schema.name=velune.evidence_report_bundle
bundle_schema.version=0.1.0
engine.name=velune_trace
extraction.semantics=observed_timing_metadata_only
extraction.mode=bounded_streaming_aggregation
extraction.timestamp_unit=nanoseconds_int
~~~

### Allowed Differences

The following differences do not block comparison:

- engine version
- source file name
- source file size
- total message count
- source format
- generation timestamp
- report Bundle ID
- artifact hashes
- topic set
- report output path

Engine-version differences are explicitly allowed because
version-to-version comparison is a target use case.

A source-format difference is recorded as a compatibility warning.

## Volatile Provenance Policy

The following fields may be preserved as input provenance but must
never be treated as behavioral or evidence changes:

- `generated_at`
- `report_bundle_id`
- artifact hash values
- local Bundle path
- output file modification time

A different Bundle ID does not, by itself, mean that the evidence
changed.

## Compared Source Artifacts

Comparison v1 uses only:

- stable manifest contract fields;
- `topic_profile.json`;
- `evidence_windows.json`.

`shareable_anonymous_report.json` is excluded because it contains
run-specific `generated_at` metadata and duplicates information
available in the machine-readable Core artifacts.

`summary.md` is excluded because it is a derived human-readable view.

## Topic Set Comparison

The report must classify topics into:

- common topics;
- reference-only topics;
- target-only topics.

Reference-only and target-only topics are observable topic-set
differences. They are not automatically classified as failures or
regressions.

All topic names must be sorted lexicographically in generated output.

## Topic Profile Comparison

For each common topic, v1 compares these raw profile fields:

- `count`
- `duration_ns`
- `avg_gap_ns`
- `max_gap_ns`
- `jitter_ns`
- `expected_count_per_window`
- `finalized_window_count`
- `out_of_order_count`
- `late_dropped_count`

The following contextual fields are preserved and checked for change:

- `sensor_category`
- `expected_count_source`
- `expected_hz`

The following absolute timestamp fields are preserved as provenance
but excluded from direct delta and ratio interpretation:

- `first_ns`
- `last_ns`

Absolute timestamps from separate runs are not assumed to refer to
the same physical event.

## Numeric Comparison Record

Each comparable numeric metric uses this structure:

~~~json
{
  "reference": 100,
  "target": 120,
  "delta": 20,
  "ratio": 1.2,
  "ratio_state": "finite"
}
~~~

Ratio semantics are:

~~~text
ratio = target / reference
~~~

Allowed `ratio_state` values:

- `finite`
- `both_zero`
- `reference_zero`

Rules:

- reference nonzero:
  - calculate a finite numeric ratio;
- reference zero and target zero:
  - ratio is `1.0`;
  - ratio state is `both_zero`;
- reference zero and target nonzero:
  - ratio is `null`;
  - ratio state is `reference_zero`.

The report must not emit NaN or Infinity.

## Evidence Window Comparison

Evidence windows from separate Bundles must not be paired by:

- absolute timestamp;
- window index;
- list position;
- assumed incident identity.

Comparison v1 summarizes each topic's ranked windows independently.

For each Bundle and topic, calculate:

- selected window count;
- maximum observed irregularity score;
- mean observed irregularity score;
- minimum count ratio;
- maximum `max_gap_ns`;
- maximum `jitter_ns`.

The report then records reference, target, delta, and ratio for those
summary metrics where numeric comparison is defined.

The implementation must preserve this score boundary:

~~~text
ranking_heuristic_only_no_root_cause_inference
~~~

A higher or lower score is an observed ranking difference only.

## No Window Alignment Claim

Comparison v1 must not claim that a reference window and a target
window are:

- the same event;
- the same incident;
- causally related;
- temporally aligned;
- semantically equivalent.

Cross-run event alignment requires a future explicit alignment
contract and is outside v1.

## Output Files

The command produces exactly two files:

- `comparison_report.json`
- `comparison_summary.md`

`comparison_report.json` is the machine-readable source of truth.

`comparison_summary.md` is a derived human-readable view.

Comparison v1 does not create:

- a new Core Report Bundle;
- a comparison manifest;
- a comparison Bundle ID;
- an upload artifact;
- a public cohort result.

## Machine-Readable Report Contract

The top-level JSON structure is:

~~~json
{
  "schema_name": "velune.bundle_comparison_report",
  "schema_version": "0.1.0",
  "visibility": "private_local_only",
  "semantics": "observed_comparison_only",
  "generated_at": "ISO-8601 timestamp",
  "reference": {},
  "target": {},
  "compatibility": {},
  "topic_set": {},
  "topic_comparisons": [],
  "summary": {},
  "excluded_from_change_evaluation": [],
  "judgment_boundary": {}
}
~~~

## Reference and Target Provenance

Each input provenance record contains:

- report Bundle ID;
- Bundle generation timestamp;
- Bundle schema name and version;
- engine name and version;
- source format;
- source file name;
- source file size;
- extraction configuration;
- total messages observed;
- topic count.

Bundle IDs are labels for input provenance only.

## Compatibility Record

The compatibility object contains:

- status;
- required field checks;
- warnings;
- blocking reasons.

Allowed status values:

- `compatible`
- `incompatible`

No comparison output is installed when status is incompatible.

## Topic Comparison Record

Each common-topic record contains:

- topic name;
- reference profile context;
- target profile context;
- profile metric comparisons;
- evidence-window summary comparisons;
- changed-field names.

It must not contain:

- root-cause statements;
- fault statements;
- liability statements;
- safety classifications;
- severity classifications;
- automatic regression labels;
- automatic improvement labels.

## Summary Record

The summary object contains only counts:

- reference topic count;
- target topic count;
- common topic count;
- reference-only topic count;
- target-only topic count;
- identical profile topic count;
- changed profile topic count;
- identical evidence-summary topic count;
- changed evidence-summary topic count.

The summary does not label the Target Bundle as better or worse.

## Deterministic Ordering

The implementation must ensure:

- topic names are lexicographically sorted;
- changed-field names are lexicographically sorted;
- reference-only topics are sorted;
- target-only topics are sorted;
- JSON keys are emitted deterministically;
- output uses UTF-8;
- JSON rejects NaN and Infinity;
- Markdown is generated from the final JSON object.

`generated_at` is volatile provenance and must not participate in any
future content-derived comparison identity.

## Output Installation

Both output files must be written through temporary files and then
atomically installed.

The implementation must not leave a partially completed comparison
directory after a failed write.

The command performs no telemetry and no automatic upload.

## Judgment Boundary

Every output must include:

~~~json
{
  "root_cause_conclusion": false,
  "fault_assignment": false,
  "liability_calculation": false,
  "safety_certification": false,
  "automatic_regression_judgment": false
}
~~~

Required human-readable statement:

> Velune reports observable differences between the Reference Bundle
> and Target Bundle. Engineers determine their meaning and cause.

## Explicit Non-Goals for v1

Comparison v1 does not provide:

- raw MCAP rescanning;
- payload decoding;
- semantic sensor-value comparison;
- causal discovery;
- incident matching;
- window-to-window alignment;
- statistical significance testing;
- fleet percentile ranking;
- public cohort comparison;
- safety scoring;
- risk scoring;
- fault assignment;
- liability calculation;
- automatic pass or fail;
- automatic regression or improvement conclusions.

## Initial Acceptance Tests

Implementation is accepted only when tests prove:

1. Identical evidence Bundles with different `generated_at` and
   Bundle IDs produce zero evidence changes.
2. Added and removed topics are reported deterministically.
3. Numeric deltas and ratios follow the zero-reference rules.
4. Absolute timestamps are not treated as aligned events.
5. Window lists are summarized independently and never zipped.
6. Incompatible extraction settings are rejected.
7. Engine-version differences are allowed and recorded.
8. Tampered artifact hashes are rejected.
9. Missing required artifacts are rejected.
10. NaN and Infinity are rejected.
11. Output ordering is deterministic.
12. No root-cause, fault, liability, safety, or regression judgment is
    emitted.
13. Both files are installed atomically.
14. Existing Core Bundle and raw-MCAP comparison tests remain passing.

## Product Boundary

Core Bundle Comparison v1 is the first local Reference-vs-Target
evidence comparison layer.

It is a prerequisite for future private baseline and regression
workflows, but it is not yet the full Phase 2 baseline product.

Velune Trace finds and organizes candidate evidence.

Engineers determine the cause.
