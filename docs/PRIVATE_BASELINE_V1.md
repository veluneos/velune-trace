# Velune Private Baseline v1

## Contract Metadata

- Contract status: `DRAFT_FOR_REVIEW`
- Product phase: `PHASE_2_PRIVATE_BASELINE`
- Contract scope: `PRIVATE_LOCAL_REFERENCE_SET_AND_TARGET_EVALUATION`
- Schema family version: `0.1.0`
- Required prerequisite: `Core Bundle Comparison v1`
- Visibility: `private_local_only`
- Network policy: `no_telemetry_no_automatic_upload`
- Root-cause judgment: prohibited
- Automatic regression judgment: prohibited
- Automatic improvement judgment: prohibited
- Human review labels: permitted only when explicitly authored by a human

## Purpose

Private Baseline v1 defines a local, customer-private structure for:

1. preserving a user-selected set of verified Reference Bundles;
2. versioning changes to that Reference set;
3. evaluating a Target Bundle against every Reference Bundle;
4. aggregating repeated observed differences without interpreting them;
5. attaching append-only human review labels;
6. preserving which baseline revision and evidence artifacts were used.

Private Baseline v1 builds on Core Bundle Comparison v1.

It does not replace or alter the Comparison v1 engine.

The Comparison v1 engine remains responsible for pairwise observed
difference calculation.

Private Baseline v1 adds an explicit private registry, immutable
Reference membership, Target evaluation history, and human review
records above that pairwise comparison layer.

## Product Statement

Private Baseline v1 answers:

> Against this user-selected private Reference set, which observable
> evidence differences were present in the Target Bundle?

It does not answer:

> Is the Target normal, abnormal, better, worse, regressed, improved,
> safe, unsafe, at fault, or the cause of an incident?

Engineers determine the meaning of observed differences.

## Terminology

### Within-Run Inferred Timing Baseline

The existing `windowed-verify` command calculates median timing values
from windows inside one log.

That value is named in this contract as:

~~~text
within-run inferred timing baseline
~~~

It is:

- calculated from one input log;
- temporary;
- used for timing-irregularity ranking;
- not a saved organization baseline;
- not a Reference Bundle registry;
- not a normality judgment;
- not part of Private Baseline membership.

The existing implementation and JSON field name do not need to be
renamed in Private Baseline v1.

Documentation must distinguish it from the persistent Private Baseline
defined below.

### Core Report Bundle

A completed, verified Velune Core Report Bundle containing the stable
machine-readable evidence artifacts required by Comparison v1.

### Reference Bundle

One verified Core Report Bundle explicitly selected by a user for
membership in a Private Baseline Revision.

A Reference Bundle is not automatically selected.

A Reference Bundle is not automatically classified as normal, correct,
safe, ideal, or representative.

### Private Baseline

A stable local identity that groups an append-only sequence of Private
Baseline Revisions.

A Private Baseline is not a single Bundle.

A Private Baseline is not a statistical population claim.

A Private Baseline is not a global or public cohort.

### Private Baseline Revision

An immutable record containing:

- the Private Baseline identity;
- its parent revision, when one exists;
- the dimension policy;
- the sorted Reference Bundle membership;
- the verified identity of each Reference Bundle;
- the judgment boundary.

Any membership or dimension-policy change creates a new revision.

An existing revision is never edited in place.

### Reference Membership

A stable record associating one verified Reference Bundle with one
Private Baseline Revision and user-authored private dimensions.

### Target Bundle

One verified Core Report Bundle evaluated against every Reference
Bundle in one Private Baseline Revision.

A Target Bundle is not automatically assigned a regression,
improvement, incident, fault, or normality label.

### Baseline Evaluation

One immutable local evaluation of a Target Bundle against one immutable
Private Baseline Revision.

### Observed Difference Aggregation

A deterministic count of how often a topic or field difference appears
across the pairwise Comparison v1 reports produced for one evaluation.

Observed Difference Aggregation is not:

- a severity score;
- a risk score;
- a probability;
- a percentile;
- a statistical significance result;
- a regression decision;
- an improvement decision;
- a root-cause conclusion.

### Human Review Record

An append-only record explicitly authored by a human and attached to:

- an entire Baseline Evaluation;
- one topic within an evaluation; or
- one field within one topic.

A human may use an organization-specific label such as `regression`,
`improvement`, `accepted_variation`, or another local term.

Such a label is a human review record, not an engine conclusion.

## Architectural Position

~~~text
Verified Core Report Bundles
        |
        v
Private Baseline Revision
        |
        +-- Reference Bundle A
        +-- Reference Bundle B
        +-- Reference Bundle C
        |
        v
Target Bundle
        |
        v
Comparison v1 against each Reference
        |
        v
Observed Difference Aggregation
        |
        v
Private Baseline Evaluation
        |
        v
Optional Human Review Records
~~~

## Local Directory Model

Private Baseline v1 uses a local directory.

The initial contract shape is:

~~~text
private_baseline/
├── baseline_registry.json
├── revisions/
│   └── <baseline_revision_id>/
│       └── baseline_revision.json
├── evaluations/
│   └── <evaluation_id>/
│       ├── baseline_evaluation_report.json
│       └── baseline_evaluation_summary.md
└── reviews/
    └── <review_record_id>.json
~~~

The directory is private local state.

Default permissions:

- Private Baseline root directory: `700`
- subdirectories: `700`
- JSON and Markdown files: `600`

No file is uploaded automatically.

## Source-of-Truth Policy

Machine-readable JSON is the source of truth.

Markdown is a derived human-readable view.

Source-of-truth files:

- `baseline_revision.json`
- `baseline_evaluation_report.json`
- human review JSON records

Derived file:

- `baseline_evaluation_summary.md`

`baseline_registry.json` is a local mutable index and locator.

It is not the historical source of truth for an immutable revision,
evaluation, or review record.

## Baseline Registry

`baseline_registry.json` maintains the local index for one Private
Baseline.

Initial top-level contract:

~~~json
{
  "schema_name": "velune.private_baseline_registry",
  "schema_version": "0.1.0",
  "visibility": "private_local_only",
  "semantics": "local_atomic_baseline_index",
  "baseline_id": "opaque stable identifier",
  "display_name": "human-readable local name",
  "created_at": "ISO-8601 timestamp",
  "current_revision_id": "baseline revision identifier",
  "revisions": [],
  "evaluations": [],
  "reviews": [],
  "bundle_locations": {}
}
~~~

Each entry in `revisions`, `evaluations`, and `reviews` contains:

~~~json
{
  "record_id": "immutable record identifier",
  "relative_path": "root-relative record path",
  "size_bytes": 1234,
  "sha256": "lowercase SHA-256 of the immutable file"
}
~~~

The containing Registry array determines the immutable record type and
the identifier field that must equal `record_id`:

| Registry array | Immutable record | Required identifier field |
|---|---|---|
| `revisions` | Baseline Revision | `baseline_revision_id` |
| `evaluations` | Baseline Evaluation | `evaluation_id` |
| `reviews` | Human Review Record | `review_record_id` |

A record placed in the wrong Registry array is rejected even when its
size and SHA-256 are valid.

Registry record paths must:

- be relative to the Private Baseline root;
- use normalized path components;
- reject `..`;
- reject absolute paths;
- reject symbolic links.

Before an immutable record is loaded:

1. the resolved path must remain inside the Private Baseline root;
2. the path must identify a regular file and not a symbolic link;
3. the physical file size must equal `size_bytes`;
4. the lowercase SHA-256 must equal `sha256`;
5. the loaded record identifier must equal the registry `record_id`.

A size, digest, path, type, or identifier mismatch blocks loading.

The mutable registry is not itself an immutable historical record.

Its size and digest entries provide local artifact-integrity
verification, not a global identity or anchoring claim.

### Initial Registry Creation

A new Private Baseline must not exist as an empty Registry.

Baseline creation and installation of the first immutable Revision are
one atomic operation.

The initial Registry therefore requires:

- one installed Baseline Revision;
- at least one verified Reference membership in that Revision;
- `current_revision_id` equal to the first Revision identifier;
- one corresponding entry in `revisions`;
- empty `evaluations` and `reviews` arrays.

If installation of the first Revision fails, neither the Registry nor a
partial Private Baseline directory may remain.

### Mutable Registry Fields

The registry may be updated atomically when:

- a new immutable revision is added;
- a new immutable evaluation is added;
- a new immutable review record is added;
- a local Bundle path changes;
- the current revision pointer changes;
- the local display name changes.

### Bundle Location Policy

`bundle_locations` maps a verified `report_bundle_id` to a current local
Bundle directory.

Local paths are operational locators.

They are:

- private;
- mutable;
- excluded from evidence-change evaluation;
- excluded from Reference membership identity;
- not proof of Bundle integrity.

A Bundle must still be loaded and verified before use.

A changed local path does not create a new Baseline Revision when the
verified Bundle identity remains unchanged.

## Baseline Identity

A `baseline_id` remains stable across all revisions.

The initial identifier is an implementation-generated opaque local
identifier.

The identifier must not encode:

- a customer name;
- a robot serial number;
- a site name;
- an email address;
- a local filesystem path.

Private dimension values belong in the private revision record, not in
the identifier.

The exact canonical content-addressing algorithm is deferred until its
canonicalization and migration behavior are independently specified
and tested.

Private Baseline v1 must not invent an unvalidated hash identity scheme.

## Baseline Revision Contract

Each immutable `baseline_revision.json` uses:

~~~json
{
  "schema_name": "velune.private_baseline_revision",
  "schema_version": "0.1.0",
  "visibility": "private_local_only",
  "semantics": "user_selected_reference_set",
  "baseline_id": "baseline identifier",
  "baseline_revision_id": "revision identifier",
  "parent_revision_id": null,
  "created_at": "ISO-8601 timestamp",
  "created_by": "local human identity",
  "dimension_policy": {},
  "reference_memberships": [],
  "judgment_boundary": {}
}
~~~

### Revision Immutability

After successful installation, a Baseline Revision is immutable.

The following changes require a new revision:

- adding a Reference Bundle;
- removing a Reference Bundle;
- replacing a Reference Bundle;
- changing a Reference dimension;
- changing a dimension-policy rule;
- changing the comparison compatibility contract.

A new revision records its `parent_revision_id`.

The first revision uses `null`.

### Revision Installation

A revision must be:

1. assembled in a staging directory;
2. fully validated;
3. serialized deterministically;
4. written with private permissions;
5. synchronized to storage;
6. atomically installed;
7. added to the registry only after installation succeeds.

A partial revision directory must not remain after failure.

## Dimension Policy

Private dimensions describe the intended comparison context.

Dimensions are always explicitly supplied by the user or customer
configuration.

Velune must not infer dimensions from:

- file names;
- directory names;
- topic names;
- host names;
- Bundle generation timestamps;
- sensor values;
- customer identity guesses.

The initial dimension policy contains:

~~~json
{
  "match_values": {
    "robot_model": "example-model",
    "site_id": "example-site"
  },
  "vary_keys": [
    "robot_id",
    "software_version",
    "run_role"
  ],
  "required_keys": [
    "robot_model",
    "site_id",
    "robot_id",
    "software_version",
    "run_role"
  ]
}
~~~

### Match Values

`match_values` defines dimensions that must equal the recorded value for:

- every Reference membership; and
- every Target evaluation.

A mismatch blocks the evaluation before comparison.

Examples may include:

- robot model;
- customer-private fleet family;
- test course;
- site;
- sensor configuration.

### Vary Keys

`vary_keys` defines dimensions that are permitted to differ and must be
preserved as provenance.

Examples may include:

- robot ID;
- software version;
- firmware version;
- run role;
- before/after state;
- test condition.

A varying value is not automatically interpreted as the reason for an
observed evidence difference.

### Required Keys

Every Reference membership and Target evaluation must include all
`required_keys`.

The three dimension-policy sets must be internally consistent.

A key must not be both a fixed `match_values` key and a `vary_keys` key.

Additional private keys may be preserved when allowed by the revision
schema.

## Reference Membership Contract

Each Reference membership contains:

~~~json
{
  "membership_id": "revision-local identifier",
  "report_bundle_id": "verified Core Bundle identifier",
  "report_manifest_sha256": "lowercase SHA-256",
  "dimensions": {},
  "selection": {
    "selected_by": "local human identity",
    "selected_at": "ISO-8601 timestamp",
    "selection_note": "optional human note"
  }
}
~~~

### Membership Rules

A Baseline Revision must contain at least one Reference membership.

Reference memberships must be:

- sorted deterministically by `report_bundle_id`;
- unique by `report_bundle_id`;
- loaded through the verified Comparison Bundle loader;
- hash-verified against their own manifest;
- compatible under the Comparison v1 compatibility gate;
- compliant with the Baseline dimension policy;
- explicitly selected by a human or customer configuration.

A Bundle path is not stored in immutable membership identity.

### No Automatic Reference Selection

Private Baseline v1 must not automatically select a Reference Bundle
because it:

- has a low irregularity score;
- has few differences;
- is the oldest run;
- is the newest run;
- is labeled normal by a filename;
- appears statistically central;
- belongs to a particular robot;
- resembles the Target.

Reference membership is an explicit user decision.

## Reference Compatibility

All Reference Bundles in one revision must be mutually compatible under
the existing Comparison v1 compatibility gate.

Blocking compatibility fields remain:

- Core schema name and version;
- Bundle schema name and version;
- engine name;
- extraction semantics;
- extraction mode;
- timestamp unit;
- window size;
- allowed lateness;
- review depth.

Engine-version differences remain warnings where Comparison v1 permits
them.

Source-format differences remain warnings where Comparison v1 permits
them.

Private Baseline v1 must not weaken the Comparison v1 compatibility
contract.

## Target Evaluation Contract

One Baseline Evaluation evaluates:

- exactly one immutable Baseline Revision;
- exactly one verified Target Bundle;
- against every Reference Bundle in the revision.

Initial machine-readable output:

~~~json
{
  "schema_name": "velune.private_baseline_evaluation",
  "schema_version": "0.1.0",
  "visibility": "private_local_only",
  "semantics": "observed_against_user_selected_reference_set",
  "evaluation_id": "evaluation identifier",
  "generated_at": "ISO-8601 timestamp",
  "baseline_id": "baseline identifier",
  "baseline_revision_id": "revision identifier",
  "evaluation_context": {},
  "target": {},
  "reference_comparisons": [],
  "aggregate_observations": {},
  "judgment_boundary": {}
}
~~~

An immutable Evaluation must not store a mutable human-review count or
current review outcome.

Review counts and current supersession state are derived from:

- the registry review entries; and
- the immutable review records associated with the Evaluation.

Appending a review record must never modify an existing Evaluation
report.

### Evaluation Context

`evaluation_context` records user-authored context.

Initial fields:

~~~json
{
  "comparison_axis": "version_to_version",
  "axis_keys": [
    "software_version"
  ],
  "dimensions": {
    "robot_model": "example-model",
    "site_id": "example-site",
    "robot_id": "robot-01",
    "software_version": "2.4.0",
    "run_role": "target"
  },
  "note": "optional human note"
}
~~~

Allowed initial `comparison_axis` values:

- `before_after`
- `robot_to_robot`
- `site_to_site`
- `version_to_version`
- `incident_deviation`
- `custom`

The comparison axis is declared by the user.

It is not inferred by Velune.

The axis does not imply a causal relationship.

`axis_keys` identifies the private dimensions intentionally varied for
this Evaluation.

Rules:

- `axis_keys` must contain at least one key;
- keys must be unique and sorted lexicographically;
- every axis key must exist in the Evaluation dimensions;
- every axis key must be permitted by the Baseline Revision's
  `vary_keys`;
- an axis key must not appear in `match_values`;
- Velune must not infer the axis keys from the selected
  `comparison_axis`.

Examples:

- `version_to_version` may declare `software_version`;
- `robot_to_robot` may declare `robot_id`;
- `site_to_site` may declare `site_id`;
- `before_after` may declare a user-defined state dimension.

These examples are descriptive and do not create causal semantics.

An Evaluation axis is valid only when every corresponding `axis_keys`
entry is permitted to vary under the selected Baseline Revision.

For example, a Revision that places `site_id` in `match_values` cannot
be used for a `site_to_site` Evaluation with `site_id` as an axis key.

That workflow requires a different immutable Revision whose
dimension policy places `site_id` in `vary_keys`.

Velune must reject an axis that conflicts with the selected Revision
rather than silently changing the Revision policy.

### Evaluation Preconditions

Before pairwise comparison begins:

1. load the immutable Baseline Revision;
2. load and verify every Reference Bundle;
3. load and verify the Target Bundle;
4. validate required dimensions;
5. validate all `match_values`;
6. confirm the Target is compatible with every Reference;
7. reject duplicate Reference identities;
8. reject missing or tampered artifacts.

Private Baseline v1 uses all-or-nothing evaluation.

If any Reference or the Target fails verification or compatibility, the
evaluation is blocked.

No partial evaluation report is installed.

## Pairwise Comparison Reuse

For each Reference membership, Private Baseline v1 invokes the existing
pure Comparison v1 engine in memory.

The Evaluation captures one `generated_at` timestamp before any
pairwise comparison begins.

That exact timestamp must be supplied to:

- the top-level Baseline Evaluation report; and
- every embedded Comparison v1 report generated for that Evaluation.

The Reference Bundle changes for each pairwise invocation.

The Target Bundle and Evaluation timestamp remain fixed.

This prevents pairwise reports from acquiring unrelated generation
timestamps during one Evaluation and supports deterministic
serialization from a fixed Evaluation input.

Conceptual flow:

~~~text
Reference Bundle 1 + Target Bundle -> Comparison v1 report
Reference Bundle 2 + Target Bundle -> Comparison v1 report
Reference Bundle 3 + Target Bundle -> Comparison v1 report
~~~

`reference_comparisons` stores one record per Reference Bundle:

~~~json
{
  "reference_report_bundle_id": "verified Reference Bundle identifier",
  "comparison_report": {
    "schema_name": "velune.bundle_comparison_report"
  }
}
~~~

The complete JSON-ready Comparison v1 report is embedded without
semantic reduction under `comparison_report`.

Reference comparison records must be sorted lexicographically by
`reference_report_bundle_id`.

Private Baseline v1 does not create separate pairwise comparison files.

Embedding the complete reports preserves the Comparison v1 contract,
prevents broken relative references, and keeps the Evaluation output
set fixed at exactly two files.

Private Baseline v1 must not:

- rescan raw MCAP;
- decode sensor payloads;
- align windows by timestamp;
- zip window lists;
- assume the same incident;
- alter Comparison v1 numeric ratio rules;
- remove Comparison v1 provenance exclusions;
- enable a Comparison v1 judgment capability.

## Aggregate Observation Contract

Aggregation counts the appearance of observed differences across
Reference comparisons.

The initial aggregation model is descriptive only.

For each topic and field:

~~~json
{
  "topic": "/example",
  "field": "profile.count",
  "eligible_reference_count": 3,
  "changed_against_reference_count": 2,
  "unchanged_against_reference_count": 1,
  "observation_scope": "some_references"
}
~~~

`eligible_reference_count` is the number of pairwise Comparison reports
in which:

- the topic is common to the Reference and Target;
- the field exists under the Comparison v1 contract; and
- the field is numerically or structurally comparable.

It is not automatically equal to the total Reference count.

The following invariant is required:

~~~text
changed_against_reference_count
+ unchanged_against_reference_count
= eligible_reference_count
~~~

An aggregate field record is emitted only when
`changed_against_reference_count` is greater than zero.

Fields unchanged against every eligible Reference are omitted from the
changed-field aggregation and counted only in summary totals.

Allowed `observation_scope` values:

- `all_references`
- `some_references`

Rules:

- `all_references` means the field differed in every eligible pairwise
  report;
- `some_references` means the field differed in at least one but not all
  eligible pairwise reports.

These terms describe occurrence only.

They do not mean:

- universally abnormal;
- statistically significant;
- severe;
- causal;
- regressed;
- improved;
- safe or unsafe.

### Topic-Set Aggregation

Topic-set occurrence is aggregated separately from common-topic field
comparison.

For each observed topic, the aggregation may record:

~~~json
{
  "topic": "/example",
  "total_reference_count": 3,
  "common_with_target_count": 1,
  "target_only_against_reference_count": 1,
  "reference_only_against_target_count": 0,
  "absent_from_both_count": 1
}
~~~

Required invariant:

~~~text
common_with_target_count
+ target_only_against_reference_count
+ reference_only_against_target_count
+ absent_from_both_count
= total_reference_count
~~~

For one Reference pair, exactly one of the four directional states
applies:

- `common_with_target`: present in both the Reference and Target;
- `target_only_against_reference`: present only in the Target;
- `reference_only_against_target`: present only in the Reference;
- `absent_from_both`: absent from both the Reference and Target.

`absent_from_both_count` is required because a topic appearing in one
Reference Bundle may be absent from the Target and from other Reference
Bundles.

A topic aggregation record is emitted only when the topic appears in
at least one Target or Reference Bundle participating in the
Evaluation.

A topic present only in the Target is still an observed topic-set
difference.

A topic present only in a Reference is also an observed topic-set
difference.

Neither direction is automatically an error, regression,
incompatibility, or improvement.

### Numeric Aggregation Boundary

Private Baseline v1 does not calculate across-Reference:

- means of ratios;
- medians of deltas;
- percentiles;
- standard deviations;
- confidence intervals;
- anomaly probabilities;
- fleet rankings;
- severity scores;
- weighted scores.

Those operations require a separate statistical contract and are
outside v1.

### No Reference Weighting

All Reference memberships have equal descriptive weight in v1.

Private Baseline v1 does not automatically weight a Reference based on:

- recency;
- similarity;
- robot identity;
- run length;
- irregularity score;
- reviewer preference;
- observed difference count.

## Evaluation Output Files

Each evaluation produces exactly:

- `baseline_evaluation_report.json`
- `baseline_evaluation_summary.md`

`baseline_evaluation_report.json` is the source of truth.

`baseline_evaluation_summary.md` is derived.

The Markdown view must:

- identify the Baseline Revision;
- identify the Target Bundle;
- list Reference count;
- summarize compatibility;
- summarize occurrence counts;
- present topics deterministically;
- bound detailed output at a versioned presentation limit;
- direct engineers to the JSON source of truth;
- state that ordering does not imply importance or severity;
- display the judgment boundary.

## Human Review Record Contract

A human review record uses:

~~~json
{
  "schema_name": "velune.private_baseline_review",
  "schema_version": "0.1.0",
  "visibility": "private_local_only",
  "semantics": "human_authored_review_record",
  "review_record_id": "review identifier",
  "created_at": "ISO-8601 timestamp",
  "baseline_id": "baseline identifier",
  "baseline_revision_id": "revision identifier",
  "evaluation_id": "evaluation identifier",
  "review_scope": "field",
  "subject": {
    "topic": "/example",
    "field": "profile.count"
  },
  "label_source": "human",
  "label": "regression",
  "reviewer": "local human identity",
  "notes": "human-authored note",
  "supersedes_review_record_id": null
}
~~~

### Review Scope

Allowed `review_scope` values:

- `evaluation`
- `topic`
- `field`

Subject requirements:

- `evaluation`: no topic or field required;
- `topic`: topic required;
- `field`: topic and field required.

### Human-Only Rule

`label_source` must equal:

~~~text
human
~~~

Private Baseline v1 must not generate a review label automatically.

The engine must not populate:

- `regression`;
- `improvement`;
- `accepted_variation`;
- `incident_related`;
- `normal`;
- `abnormal`;
- any other organization-specific review outcome.

Those values may appear only when explicitly authored by a human.

The `label` value is treated as opaque organization-private text.

Velune must not assign built-in semantics, ordering, severity, or
workflow behavior to a human label.

The `reviewer` value must be explicitly supplied by the local user or
customer configuration.

Velune must not infer reviewer identity from:

- the operating-system account;
- the host name;
- a filesystem owner;
- Git configuration;
- an email address discovered elsewhere.

### Append-Only Review History

A review record is immutable.

Changing a label or note creates a new review record.

For a normalized review subject with no existing review history, the
first record must use:

~~~json
{
  "supersedes_review_record_id": null
}
~~~

When a valid review chain already exists for the same normalized
subject, every later record must supersede the unique current terminal
record.

Creating another unsuperseded root record for the same normalized
subject is rejected.

The new record may use `supersedes_review_record_id` to point to the
previous record.

A superseding record must preserve the same:

- `baseline_id`;
- `baseline_revision_id`;
- `evaluation_id`;
- `review_scope`;
- normalized review subject.

A review record must not supersede itself.

A supersession chain must not contain a cycle.

One review record may be superseded by at most one later review record
in v1.

Creating two active child records for the same predecessor is rejected
because it would produce an ambiguous current review state.

The effective current review for one subject is the unique terminal
record in its valid supersession chain.

The previous records remain preserved.

Deletion, mutation, branching, or silent overwrite is prohibited in
v1.

### Review Labels Do Not Change Evidence

Human labels do not modify:

- the Baseline Revision;
- Reference membership;
- pairwise Comparison v1 reports;
- aggregate observed counts;
- the Target Bundle;
- the original Core Bundle artifacts.

Human review is a separate interpretation layer.

## Judgment Boundary

Every automated Private Baseline Evaluation must declare:

~~~json
{
  "root_cause_conclusion": false,
  "cause_inference": false,
  "fault_assignment": false,
  "liability_calculation": false,
  "safety_certification": false,
  "safety_classification": false,
  "severity_judgment": false,
  "normality_judgment": false,
  "superiority_judgment": false,
  "regression_judgment": false,
  "automatic_regression_judgment": false,
  "automatic_improvement_judgment": false,
  "automatic_reference_selection": false
}
~~~

Required human-readable statement:

> Velune reports observed differences against a user-selected private
> Reference set. Engineers determine their meaning, cause, and review
> outcome.

## Privacy Boundary

Private Baseline v1 is private local state.

It must not automatically:

- upload a Baseline Registry;
- upload Reference membership;
- upload customer-private dimensions;
- upload Target evaluations;
- upload human review labels;
- compare one named customer against another;
- create a public percentile;
- create a global industry baseline;
- enroll data into a shared cohort;
- disclose local filesystem paths.

Any future anonymous or shared cohort workflow requires the separate
local privacy gate and explicit user action.

## Explicit Non-Goals

Private Baseline v1 does not provide:

- automatic baseline construction;
- automatic Reference selection;
- raw MCAP rescanning;
- payload-level semantic comparison;
- event or incident alignment across runs;
- statistical significance testing;
- anomaly probability;
- global percentile ranking;
- fleet-wide scoring;
- safety scoring;
- risk scoring;
- root-cause analysis;
- fault assignment;
- liability calculation;
- automatic pass or fail;
- automatic regression classification;
- automatic improvement classification;
- automatic normality classification;
- automatic human review labels;
- remote synchronization;
- multi-user access control;
- cloud registry hosting;
- public cohort comparison;
- named customer-to-customer comparison.

## Initial Operations

Private Baseline v1 defines four conceptual operations:

1. create a Private Baseline together with its first immutable
   Revision;
2. create a new immutable Baseline Revision;
3. evaluate one Target Bundle against one revision;
4. append one human review record.

Exact CLI command names are intentionally not frozen in this draft.

The data contract and judgment boundary must be reviewed before the CLI
surface is fixed.

## Initial Acceptance Tests

Implementation is accepted only when tests prove:

1. a Private Baseline can be created locally with private permissions;
2. the first revision requires at least one verified Reference Bundle;
3. duplicate Reference Bundle IDs are rejected;
4. tampered Reference artifacts are rejected;
5. incompatible Reference Bundles are rejected;
6. Reference memberships are sorted deterministically;
7. local Bundle paths are excluded from immutable membership records;
8. a membership change creates a new revision;
9. an existing revision cannot be overwritten;
10. the parent-revision lineage is preserved;
11. required dimensions are enforced;
12. `match_values` mismatches block revision creation or evaluation;
13. dimension values are never inferred from file or directory names;
14. an incompatible Target blocks the complete evaluation;
15. no partial evaluation directory remains after failure;
16. one Comparison v1 report is produced in memory for every Reference;
17. aggregate occurrence counts exactly match pairwise reports;
18. aggregation emits no severity, probability, or regression score;
19. no Reference weighting is applied;
20. Markdown detail output is bounded deterministically;
21. every automated judgment capability remains `false`;
22. a review record requires `label_source=human`;
23. the engine cannot automatically create a review record;
24. review changes create append-only superseding records;
25. registry updates are atomic;
26. revision, evaluation, and review files use mode `600`;
27. baseline directories use mode `700`;
28. no telemetry or automatic upload occurs;
29. existing Core Bundle and Comparison v1 tests remain passing;
30. registry record paths reject absolute paths, `..`, and symbolic
    links;
31. registry SHA-256 verification detects a modified immutable record;
32. an immutable Evaluation contains no mutable review count or current
    review outcome;
33. `axis_keys` are explicit and are a subset of revision `vary_keys`;
34. complete Comparison v1 reports are embedded and sorted by Reference
    Bundle ID;
35. no separate pairwise output files are created;
36. aggregate field denominators use only eligible References;
37. changed and unchanged field counts sum to the eligible Reference
    count;
38. fields unchanged against every eligible Reference are omitted from
    changed-field aggregation;
39. topic-set directional counts sum to the total Reference count;
40. human labels remain opaque and have no engine-defined semantics;
41. reviewer identity is never inferred from the host environment;
42. Registry immutable-record entries include both `size_bytes` and
    SHA-256;
43. a Registry size, digest, path, type, or record-ID mismatch blocks
    loading;
44. Baseline creation and first-Revision installation are atomic;
45. an empty initial Registry cannot be installed;
46. every embedded pairwise Comparison report uses the Evaluation's
    single captured `generated_at` timestamp;
47. review supersession rejects cycles and self-references;
48. review supersession cannot change Evaluation, scope, or subject;
49. one review predecessor cannot have multiple active superseding
    children;
50. the effective current review is derived as the unique terminal
    record in a valid supersession chain;
51. Registry `record_id` is checked against the identifier field
    required by its containing Registry array;
52. a record placed in the wrong Registry array is rejected;
53. topic-set aggregation includes the `absent_from_both` state;
54. all four topic-set directional counts sum to the total Reference
    count;
55. an axis conflicting with the selected Revision dimension policy is
    rejected;
56. a review subject can have only one initial root record;
57. every later review for that subject supersedes its unique current
    terminal record.

## Product Boundary

Private Baseline v1 is the first persistent customer-private
Reference-set layer.

It supports future workflows such as:

- normal-run Reference sets;
- incident deviation review;
- before/after review;
- robot-to-robot review;
- site-to-site review;
- version-to-version review;
- repeated private Target evaluations;
- engineer-authored review history.

It does not yet provide an automated regression product.

It provides the evidence organization needed for a human-led private
regression workflow.

## Relationship to Comparison v1

Comparison v1 answers:

~~~text
How do Reference Bundle A and Target Bundle B differ?
~~~

Private Baseline v1 answers:

~~~text
Across this user-selected Reference set,
which observed differences appeared in this Target Bundle?
~~~

Both layers preserve:

~~~text
Find and organize the evidence.
Engineers determine the meaning and cause.
~~~

## Draft Review Questions

Before implementation is frozen, review:

1. the exact opaque identifier format and collision-handling policy;
2. registry recovery behavior when the mutable index is missing or
   corrupted;
3. the maximum supported Reference count for one revision;
4. maximum lengths and accepted Unicode controls for private dimension,
   label, reviewer, and note values;
5. whether a separate derived review-summary view is needed;
6. whether immutable Baseline records require a later anchoring package;
7. whether Evaluation Markdown needs its own presentation limits rather
   than reusing Comparison v1 values.

## Contract Status

~~~text
PRIVATE_BASELINE_V1_CONTRACT=DRAFT_FOR_REVIEW
COMPARISON_V1_ENGINE_REUSE=REQUIRED
PRIVATE_LOCAL_ONLY=REQUIRED
REFERENCE_SELECTION=HUMAN_EXPLICIT
BASELINE_REVISION_IMMUTABLE=REQUIRED
TARGET_EVALUATION_ALL_OR_NOTHING=REQUIRED
PAIRWISE_COMPARISON_REPORTS=EMBEDDED
PAIRWISE_OUTPUT_FILES=PROHIBITED
EVALUATION_REVIEW_STATE=DERIVED_NOT_STORED
REGISTRY_SEMANTICS=LOCAL_ATOMIC_MUTABLE_INDEX
REGISTRY_IMMUTABLE_RECORD_SIZE_AND_SHA256=REQUIRED
REGISTRY_RECORD_ID_MAPPING=ARRAY_TYPED
INITIAL_BASELINE_AND_FIRST_REVISION=ATOMIC
EVALUATION_GENERATED_AT=SINGLE_CAPTURED_VALUE
EVALUATION_AXIS_KEYS=REVISION_VARY_KEYS_ONLY
REVIEW_SUPERSESSION=ONE_ROOT_LINEAR_ACYCLIC_CHAIN
TOPIC_SET_ABSENT_FROM_BOTH=COUNTED
AGGREGATION_DENOMINATOR=ELIGIBLE_REFERENCES_ONLY
OBSERVED_DIFFERENCE_AGGREGATION=DESCRIPTIVE_ONLY
AUTOMATIC_REFERENCE_SELECTION=PROHIBITED
AUTOMATIC_REGRESSION_JUDGMENT=PROHIBITED
AUTOMATIC_IMPROVEMENT_JUDGMENT=PROHIBITED
HUMAN_REVIEW_LABELS=APPEND_ONLY
NO_TELEMETRY_OR_AUTOMATIC_UPLOAD=REQUIRED
~~~
