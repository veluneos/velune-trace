# Core Bundle Comparison v1 Operational Validation Record

## Record Metadata

- Record type: `OPERATIONAL_VALIDATION_RECORD`
- Validation status: `PASS`
- Validation date: `2026-07-16`
- Validation scope: `CORE_BUNDLE_COMPARISON_V1_ZERO_AND_POSITIVE_PATHS`
- Repository branch: `phase1-evidence-report-bundle`
- Source commit: `db2ce9e63425d45ffccf2b3ecc6f6e4cef464e62`
- Source commit short form: `db2ce9e`
- Source commit date: `2026-07-16T16:05:12+09:00`
- Source commit subject: `Improve comparison Markdown safety and density`
- Comparison schema: `velune.bundle_comparison_report`
- Comparison schema version: `0.1.0`
- Visibility: `private_local_only`
- Semantics: `observed_comparison_only`

## Executive Result

Velune Trace successfully compared existing verified Core Report
Bundles through the complete local `compare-bundles` CLI path.

Two complementary operational paths were validated:

| Validation path | Common topics | Changed topics | Changed fields | Wall time | Maximum RSS | Result |
|---|---:|---:|---:|---:|---:|---|
| Same evidence, independent cold/warm Bundle generation | 41 | 0 | 0 | 0.08 seconds | 23,084 KB (22.54 MiB) | PASS |
| Different real nuScenes-derived scenes | 41 | 39 | 425 | 0.08 seconds | 23,604 KB (23.05 MiB) | PASS |

The zero-difference path demonstrated that volatile provenance
differences such as Bundle ID and generation timestamp were not
misclassified as evidence changes.

The positive-difference path demonstrated that the comparison engine
detected observed profile and evidence-summary differences across
different scene Bundles.

Neither result assigns meaning, importance, severity, normality,
superiority, regression, improvement, cause, fault, liability, or
safety status.

## Validated Pipeline

~~~text
existing Reference Core Report Bundle
    -> Bundle directory and required-artifact validation
    -> manifest-declared artifact size and SHA-256 verification
    -> existing Target Core Report Bundle validation
    -> compatibility gate
    -> pure observed-difference calculation
    -> deterministic machine-readable JSON serialization
    -> derived bounded Markdown presentation
    -> atomic private output installation
    -> exactly two local output files
~~~

The CLI inputs were existing Core Report Bundle directories.

Raw MCAP paths were not command inputs, and the comparison operation
did not rescan raw MCAP files.

The external wall-clock measurements were taken with `/usr/bin/time`
around the complete `compare-bundles` CLI process.

They include process startup, Bundle loading, artifact verification,
comparison, output rendering, atomic installation, and process
termination.

No telemetry or automatic upload was performed.

## Validation Environment

| Item | Value |
|---|---|
| Host | `velune-lab` |
| Operating system | `Ubuntu 24.04.4 LTS` |
| Kernel | `6.17.0-35-generic` |
| Architecture | `x86_64` |
| Logical CPUs | 16 |
| Python | `3.12.3` |
| Python implementation | `CPython` |
| Repository root | `/home/hyunwoo/veluneos/github_release_v0_2` |
| Comparison command | `./bin/velune compare-bundles` |

## Validation Case A — Zero-Difference Reproducibility

### Purpose

Confirm that two independently generated Core Bundles representing the
same extracted evidence do not produce false-positive evidence changes.

### Inputs

| Field | Reference | Target |
|---|---|---|
| Bundle directory | `/home/hyunwoo/veluneos/benchmarks/mcap_corpus_10g/core_bundle_cold` | `/home/hyunwoo/veluneos/benchmarks/mcap_corpus_10g/core_bundle_warm` |
| Report Bundle ID | `vrb_sha256_dd37c3768b435526f87047d4264508c38ec66825b1ff9db3d2c2a3586670c187` | `vrb_sha256_28451e6f4678282609116d8f0dfa4815081f807396d0962046f17df2b67a5c8b` |
| Bundle generated at | `2026-07-16T02:24:48.487798+00:00` | `2026-07-16T02:25:19.522925+00:00` |
| Source file | `nuscenes-replicated-real-payload-min-10gib.mcap` | `nuscenes-replicated-real-payload-min-10gib.mcap` |
| Source file size | 10,856,616,900 bytes | 10,856,616,900 bytes |
| Engine | `velune_trace 0.3.6` | `velune_trace 0.3.6` |

The Reference and Target Bundle IDs and generation timestamps differ.

The source file name, source size, extraction contract, and observed
evidence content are equivalent for this validation path.

### Results

| Metric | Observed |
|---|---:|
| Compatibility status | `compatible` |
| Reference topics | 41 |
| Target topics | 41 |
| Common topics | 41 |
| Reference-only topics | 0 |
| Target-only topics | 0 |
| Changed profile topics | 0 |
| Changed evidence-summary topics | 0 |
| Changed topic records | 0 |
| Changed fields | 0 |
| Detailed Markdown topic sections | 0 |
| External wall time | 0.08 seconds |
| Maximum RSS | 23,084 KB (22.54 MiB) |
| Result | PASS |

The Markdown output reports:

> No changed common topics were observed.

Unchanged topics are not expanded into detailed Markdown sections.

## Validation Case B — Positive Difference Detection

### Purpose

Confirm that different real nuScenes-derived scene Bundles produce
structured observed differences without automatic interpretation.

### Inputs

| Field | Reference | Target |
|---|---|---|
| Bundle directory | `/home/hyunwoo/veluneos/benchmarks/core_bundle_scene_1100` | `/home/hyunwoo/veluneos/benchmarks/mcap_roundtrip/core_bundle_scene_0553_shifted` |
| Report Bundle ID | `vrb_sha256_01df81a98ce891f2f2364fe49bcd25561315a74517e2a072a03943d9e4b674aa` | `vrb_sha256_e1f6251f9d96747a8d22326d57773b95bebe1837f824fc56763321cbfc84c4a2` |
| Bundle generated at | `2026-07-16T01:35:09.967484+00:00` | `2026-07-16T01:47:10.654367+00:00` |
| Source file | `nuscenes-scene-1100.mcap` | `nuscenes-scene-0553-shifted.mcap` |
| Source file size | 652,549,844 bytes | 393,801,949 bytes |
| Engine | `velune_trace 0.3.6` | `velune_trace 0.3.6` |

### Results

| Metric | Observed |
|---|---:|
| Compatibility status | `compatible` |
| Reference topics | 41 |
| Target topics | 41 |
| Common topics | 41 |
| Reference-only topics | 0 |
| Target-only topics | 0 |
| Changed profile topics | 39 |
| Changed evidence-summary topics | 39 |
| Identical profile topics | 2 |
| Identical evidence-summary topics | 2 |
| Changed topic records | 39 |
| Changed fields | 425 |
| Markdown preview topics | 5 |
| Detailed Markdown topic sections | 20 |
| Omitted detailed Markdown topics | 19 |
| External wall time | 0.08 seconds |
| Maximum RSS | 23,604 KB (23.05 MiB) |
| Result | PASS |

The 425 changed fields consist of:

| Field namespace | Count |
|---|---:|
| `profile` | 230 |
| `evidence_summary` | 195 |
| Total | 425 |

The Markdown presentation:

- previews the first five changed topics in lexicographic order;
- provides detailed sections for the first 20 changed topics;
- omits 19 additional detailed topic sections;
- directs engineers to `comparison_report.json` for complete data;
- explicitly states that ordering does not imply importance, severity,
  or priority.

## Output Integrity

### Zero-Difference Output

| File | Size | Mode | SHA-256 |
|---|---:|---:|---|
| `comparison_report.json` | 204,066 bytes | `600` | `643e6e36658a506207b6efdd6956147cd1212095f3af3c6e667cd9c51566075e` |
| `comparison_summary.md` | 1,645 bytes | `600` | `de27f17706be9001760e9ce70a4ca16cd8e039ef031d78dad05d8b104c86a733` |

Output directory mode: `700`

### Positive-Difference Output

| File | Size | Mode | SHA-256 |
|---|---:|---:|---|
| `comparison_report.json` | 232,432 bytes | `600` | `92aa09b8e0b67e472c677f8a3b02f0aad17cb8b6a9521a712e32265f02543268` |
| `comparison_summary.md` | 10,756 bytes | `600` | `63c3bc49585e6628dd1d2ad3a6d4a6a0dcf37b533ffdf88a2359587ffa924381` |

Output directory mode: `700`

Each comparison directory contains exactly:

~~~text
comparison_report.json
comparison_summary.md
~~~

No comparison manifest, comparison Bundle ID, upload artifact, or
public cohort artifact was generated.

## Judgment Boundary Verification

Every Boolean field in both generated `judgment_boundary` objects was
`false`.

The validated boundary includes disabled:

- root-cause conclusion;
- cause inference;
- fault assignment;
- liability calculation;
- safety certification and classification;
- severity judgment;
- normality judgment;
- superiority judgment;
- regression judgment;
- automatic regression judgment;
- automatic improvement judgment.

Required human-readable boundary:

> Velune reports observable differences between the Reference Bundle
> and Target Bundle. Engineers determine their meaning and cause.

## Acceptance Criteria

| Criterion | Required | Observed | Result |
|---|---|---|---|
| Verified Bundle inputs | Both required | Four Bundles accepted with declared artifact integrity verification | PASS |
| Compatibility gate | Compatible for both paths | `compatible` for both paths | PASS |
| Zero-difference false-positive prevention | No evidence changes | 0 changed topics and 0 changed fields | PASS |
| Positive-difference detection | At least one observed difference | 39 changed topics and 425 changed fields | PASS |
| Raw MCAP rescan | Not required | Bundle directories were the only CLI inputs | PASS |
| Output file set | Exactly two files | Exactly two files per comparison | PASS |
| Private permissions | Directory `700`, files `600` | Confirmed for both outputs | PASS |
| Atomic writer path | Required | Complete directories installed without partial files | PASS |
| Judgment boundary | All capabilities disabled | Every declared value was `false` | PASS |
| Local-only execution | Required | No telemetry or automatic upload | PASS |
| Human summary scale bound | At most 20 detailed changed topics | 20 of 39 shown | PASS |
| Non-ranking presentation | Required | Lexicographic order explicitly marked non-prioritized | PASS |
| Process completion | Exit code 0 | Exit code 0 for both paths | PASS |

## Validated Claims

This record supports the following engineering claims:

> Velune Trace compared two verified Core Report Bundles representing
> the same extracted evidence and reported zero observed evidence
> changes despite different Bundle IDs and generation timestamps.

> Velune Trace compared two different real nuScenes-derived scene
> Bundles and structured 425 observed field differences across
> 39 common topics without assigning their meaning or cause.

> On the measured host, both comparison CLI paths completed in
> approximately 0.08 seconds with approximately 23 MiB maximum
> resident memory.

> Core Bundle Comparison v1 operates from existing Core Bundle
> artifacts and does not require raw MCAP rescanning.

## Claims Not Supported by This Record

This record does not prove that:

- zero reported differences imply byte-identical raw MCAP payloads;
- all possible Bundle schemas or future schema versions are supported;
- changed fields are abnormal, severe, important, or prioritized;
- any observed difference is a regression or improvement;
- any observed difference caused an incident;
- the two runs contain aligned or semantically equivalent events;
- evidence windows were paired across runs;
- payload-level sensor values were semantically compared;
- statistical significance was calculated;
- fault, liability, safety, or risk was determined;
- the same performance will be achieved on all hardware;
- the input raw MCAP files or input Bundle directories were anchored by
  this record;
- output SHA-256 values constitute a comparison Bundle identity;
- the positive-difference scene pair represents every robotics domain.

## Relationship to the 10GiB Core Bundle Validation

This record builds on:

`benchmarks/mcap_core_bundle_10gib_validation_record.md`

The prior record validates:

~~~text
10.11 GiB MCAP
    -> bounded streaming aggregation
    -> complete local Core Report Bundle
~~~

This record validates:

~~~text
existing verified Core Report Bundles
    -> compatibility verification
    -> observed-difference calculation
    -> private comparison JSON and Markdown
~~~

The prior 36.89-second result measures complete report generation from
a 10.11 GiB MCAP.

The 0.08-second results in this record measure comparison of already
generated Core Bundle artifacts.

These measurements are not interchangeable.

## Implementation Lineage

- `75d470f554a890a386ad676170335e5cbda40aef` — Define Core Bundle Comparison v1 contract
- `6f17b28e13039d25337ddf54cf1cf402ba8fb2b6` — Add verified Core Bundle comparison loader
- `4c297751a745e62c67a6c1f3e239d0783d3b2cdb` — Add Core Bundle compatibility gate
- `a1b1068ebd7f44794e41f6817310725d410f8236` — Add pure Core Bundle comparison engine
- `1469b45a050ac93e9f12d29120eaa467411d2a6d` — Align comparison judgment boundary contract
- `b176e512a6568b426508c9d6c584ffde8401f496` — Add atomic Core Bundle comparison writer
- `61c9a13198e3790110819c831b3d9d1cdfc24601` — Add portable Core Bundle comparison CLI
- `db2ce9e63425d45ffccf2b3ecc6f6e4cef464e62` — Improve comparison Markdown safety and density

## Final Validation Status

~~~text
ZERO_DIFFERENCE_REPRODUCIBILITY=PASS
POSITIVE_DIFFERENCE_DETECTION=PASS
EXACT_OUTPUT_FILE_SET=PASS
PRIVATE_OUTPUT_PERMISSIONS=PASS
MARKDOWN_SCALE_BOUND=PASS
ALL_JUDGMENT_BOUNDARIES_FALSE=PASS
LOCAL_ONLY_EXECUTION=PASS
CORE_BUNDLE_COMPARISON_V1_OPERATIONAL_VALIDATION=PASS
~~~
