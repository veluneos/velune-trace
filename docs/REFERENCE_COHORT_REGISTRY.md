# Velune Reference Cohort Registry v0.1

This document defines which reference sources may be used for validation, comparison, benchmark language, and customer feedback.

It exists to prevent overclaiming.

Velune must not describe a result as a global average, industry percentile, or company-to-company comparison unless a validated matched cohort exists.

## Core Rule

Velune reports observable timing evidence.

Velune may compare reports only when the comparison basis is clearly defined.

Velune does not infer root cause, assign fault, assign liability, or make safety-risk determinations.

## Reference Source Classes

### 1. Synthetic Sample

Synthetic samples are used to verify that the CLI, report generator, and onboarding flow work.

They are not benchmark sources.

Allowed claim:

    Sample execution verified.

Forbidden claim:

    Industry benchmark.
    Global average.
    Robot performance comparison.
    Customer quality ranking.

### 2. Public Reference Dataset

Public reference datasets may be used as external compatibility or timing-profile references.

They are not automatically global averages.

Allowed claim:

    Compared against a public reference timing profile.

Forbidden claim:

    Global industry average.
    Global percentile.
    Representative robotics market benchmark.
    Company-to-company comparison.

### 3. Internal Benchmark Corpus

Internal benchmark corpora may be used to validate processing scale, extraction latency, indexing behavior, and reproducibility.

They are not customer quality benchmarks.

Allowed claim:

    Large-log processing benchmark.
    Evidence extraction performance validation.
    Indexing or chain-extraction validation.

Forbidden claim:

    Robot quality comparison.
    Operational safety comparison.
    Industry percentile.

### 4. Controlled Fixture

Controlled fixtures are used to validate specific known conditions such as dropout, timing gaps, or incremental indexing failure modes.

They are test fixtures, not market benchmarks.

Allowed claim:

    Controlled dropout recovery validated.
    Evidence-window extraction behavior verified.

Forbidden claim:

    Customer fleet comparison.
    Real-world average.
    Industry percentile.

### 5. Partner Anonymous Report

Partner anonymous reports are submitted through the Validation Partner Program.

They may become part of a matched anonymous cohort only after schema validation, normalization, and compatibility checks.

Allowed claim before cohort maturity:

    Local timing evidence feedback.
    Investigation starting points.
    Limited reference comparison when applicable.

Allowed claim after cohort maturity:

    Compared against a matched anonymous cohort.

Required disclosure:

    Cohort size.
    Schema version.
    Window size.
    Sensor category.
    Expected publish-rate band.
    Domain or deployment class when available.

Forbidden claim:

    Global average without sufficient cohort.
    Global percentile without disclosed cohort conditions.
    Named competitor comparison.
    Root-cause or safety-risk determination.

## Initial Registry

### sample_mcap_v0_2

Source Type:

    synthetic_sample

Dataset / Report:

    examples/sample.mcap

Domain:

    synthetic robotics timing sample

Sensor Category:

    lidar-like topic and imu-like topic

Expected Rate:

    /lidar_top: inferred 20 Hz
    /imu: inferred 100 Hz

Window Size:

    1 second

Schema Version:

    validation-report schema v0.2.0

Use Case:

    CLI smoke test.
    README quick start.
    Report generation verification.

Allowed Claim:

    Velune validation-report can generate local timing evidence reports from MCAP input.

Forbidden Claim:

    This sample represents global robotics timing behavior.
    This sample is an industry benchmark.
    This sample proves customer robot quality.

Status:

    active

Limitations:

    Synthetic sample only.
    Not representative of real-world fleet behavior.

### nuscenes_mini_mcap_reference_v0_1

Source Type:

    public_reference_dataset

Dataset / Report:

    nuScenes mini converted to MCAP through an external conversion pipeline.

Domain:

    autonomous driving public dataset

Sensor Category:

    dataset-dependent

Expected Rate:

    dataset-dependent

Window Size:

    validation-dependent

Schema Version:

    external validation record

Use Case:

    External MCAP compatibility validation.
    Public reference timing-profile comparison when applicable.

Allowed Claim:

    Velune has been validated against an external autonomous-driving MCAP reference dataset.
    A submitted report may be compared against a public reference timing profile when conditions are compatible.

Forbidden Claim:

    This represents the global robotics average.
    This provides a global percentile.
    This represents all autonomous systems.

Status:

    limited_reference

Limitations:

    Public dataset.
    Not a customer cohort.
    Not a global industry baseline.

### synthetic_10gb_benchmark_v0_1

Source Type:

    internal_benchmark_corpus

Dataset / Report:

    synthetic 10.7 GB benchmark corpus

Domain:

    synthetic large-log benchmark

Sensor Category:

    synthetic event stream

Expected Rate:

    synthetic

Window Size:

    benchmark-dependent

Schema Version:

    benchmark validation record

Use Case:

    Large-log processing validation.
    Evidence-chain extraction latency validation.
    Indexing performance validation.

Allowed Claim:

    Velune processed a 10.7 GB benchmark corpus.
    Velune indexed 9,237,885 events.
    Velune extracted a small evidence chain from a large indexed corpus.

Forbidden Claim:

    This proves customer robot quality.
    This is an industry safety benchmark.
    This provides operational reliability ranking.

Status:

    active_internal_benchmark

Limitations:

    Synthetic benchmark.
    Performance evidence only.
    Not a customer-comparison cohort.

### controlled_dropout_fixture_v0_1

Source Type:

    controlled_fixture

Dataset / Report:

    controlled dropout recovery fixture

Domain:

    controlled ROS2 validation

Sensor Category:

    controlled topic stream

Expected Rate:

    fixture-defined

Window Size:

    fixture-defined

Schema Version:

    validation-dependent

Use Case:

    Dropout evidence-window validation.
    Recovery behavior validation.
    Reproducibility checks.

Allowed Claim:

    Velune can identify evidence windows in a controlled dropout fixture.

Forbidden Claim:

    This represents real-world average dropout behavior.
    This proves field reliability.
    This provides industry percentile.

Status:

    active_fixture

Limitations:

    Controlled condition.
    Not a market benchmark.

### future_partner_anonymous_reports_v0_1

Source Type:

    partner_anonymous_report

Dataset / Report:

    shareable_anonymous_report.json submitted by Validation Partners

Domain:

    partner-dependent

Sensor Category:

    report-dependent

Expected Rate:

    report-dependent

Window Size:

    report-dependent

Schema Version:

    validation-report schema version required

Use Case:

    Local evidence feedback.
    Matched anonymous cohort comparison after enough compatible reports exist.
    Future benchmark report generation.

Allowed Claim Before Cohort Maturity:

    Local timing evidence feedback.
    Investigation starting points.
    Limited reference comparison when applicable.

Allowed Claim After Cohort Maturity:

    Compared against a matched anonymous cohort of N compatible reports.

Forbidden Claim:

    Global average without sufficient cohort.
    Global percentile without disclosed cohort conditions.
    Named company comparison.
    Fault, liability, safety-risk, or root-cause judgment.

Status:

    future_cohort_source

Limitations:

    Requires real partner submissions.
    Requires schema validation.
    Requires normalization.
    Requires cohort-size disclosure.

## Claim Language Policy

Use:

    local timing evidence
    evidence window
    observed count ratio
    max timing gap
    jitter
    matched anonymous cohort
    public reference timing profile
    investigation starting point

Avoid:

    risk score
    failure probability
    fault detection
    root cause
    liability
    safety rating
    global average
    industry percentile

Use global or industry-level language only when the cohort is large enough, compatible, documented, and disclosed.

## Minimum Requirements for Matched Cohort Comparison

A matched cohort comparison requires:

- compatible schema version
- compatible window size
- compatible sensor category
- compatible expected publish-rate band
- compatible timestamp basis
- disclosed cohort size
- exclusion of raw payloads
- no named competitor disclosure

Until these conditions are met, Velune should provide local evidence feedback rather than percentile claims.

## Current Status

Current Velune public comparison capability:

    Local evidence feedback: available
    Public reference comparison: limited
    Matched anonymous cohort comparison: not yet available
    Global percentile dashboard: not yet available

The next milestone is to receive the first external shareable_anonymous_report.json from a Validation Partner.
