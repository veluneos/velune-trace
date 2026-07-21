# Private Baseline Initial Creation Operational Validation Record

## Record Metadata

- Record type: `OPERATIONAL_VALIDATION_RECORD`
- Validation status: `PASS`
- Validation date: `2026-07-21`
- Validation scope: `INITIAL_BASELINE_CONCURRENCY_AND_REFERENCE_CAPACITY`
- Repository branch: `phase2-private-baseline-contract`
- Source commit: `5b090c74d859c2c686bd2ee0b70ccf3a74320efd`
- Commit date: `2026-07-21T10:27:46+09:00`
- Commit subject: `Record real Private Baseline Adapter E2E validation`
- Visibility: `private_local_only`
- Network activity: `none`
- Automatic upload: `none`

## Executive Result

Velune Trace passed two operational validations for initial
Private Baseline creation:

1. two independent processes competed for the same first Baseline
   identifier candidate without overwriting one another; and
2. the public creation Service accepted the v1 maximum of 32
   explicitly selected Reference Bundles and rejected a 33rd
   Reference before Bundle I/O.

## Validated Pipeline Boundary

~~~text
completed verified Core Report Bundles
    -> public create_private_baseline() Service
    -> Comparison v1 compatibility gate
    -> atomic initial Baseline installer
    -> immutable first Revision
    -> fail-closed Registry reload
~~~

These validations do not rescan raw MCAP inputs.

## Validation Environment

| Item | Value |
|---|---|
| Host | `velune-lab` |
| Operating system | `Ubuntu 24.04.4 LTS` |
| Kernel | `6.17.0-35-generic` |
| Architecture | `x86_64` |
| CPU model | `AMD Ryzen 7 170 with Radeon Graphics` |
| Logical CPUs | 16 |
| Python | `3.12.3` |
| Python implementation | `CPython` |

## Validation A — Concurrent Identifier Collision

Two separate Linux processes were started with the `fork`
multiprocessing start method.

Both processes received the same first Baseline identifier
candidate:

~~~text
vpb_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
~~~

Observed completed Baseline identities:

~~~text
vpb_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
vpb_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
~~~

The first identity was atomically claimed by one process.

The other process encountered the existing directory claim and
successfully retried with its next candidate without replacing or
modifying the first Baseline.

| Metric | Observed | Result |
|---|---:|---|
| Independent worker processes | 2 | PASS |
| Forced shared first candidate | 1 | PASS |
| Completed Baselines | 2 | PASS |
| Distinct Baseline IDs | 2 | PASS |
| Distinct Revision IDs | 2 | PASS |
| References per Baseline | 2 | PASS |
| Registry reloads | 2 | PASS |
| Partial Baselines | 0 | PASS |
| Temporary installation artifacts | 0 | PASS |
| Directory permissions | `700` | PASS |
| Private file permissions | `600` | PASS |

This validates concurrent creation of separate new Baselines under
one shared parent directory.

It does not validate concurrent mutation of one existing Baseline
Registry.

## Validation B — Maximum Reference Capacity

The capacity set contained 32 finalized Core Report Bundles derived
from one real nuScenes scene-1100 Core Bundle.

Three source-of-truth evidence artifacts were preserved
byte-for-byte in every replica:

- `topic_profile.json`
- `evidence_windows.json`
- `shareable_anonymous_report.json`

Only the derived human-readable `summary.md` received a unique
capacity-validation replica marker.

This produced 32 unique finalized Bundle identities without
altering the source-of-truth evidence artifacts.

The set is classified as:

~~~text
dataset_class=real_derived_replicated_core_bundle_set
independent_robot_runs=false
heterogeneous_evidence_runs=false
source_of_truth_evidence_preserved=true
~~~

### Capacity Acceptance

| Metric | Observed | Result |
|---|---:|---|
| Maximum allowed References | 32 | PASS |
| Installed References | 32 | PASS |
| Bundle loader calls | 32 | PASS |
| Compatibility calls | 31 | PASS |
| Compatibility warnings | 0 | PASS |
| Unique Report Bundle IDs | 32 | PASS |
| Manifest SHA-256 matches | 32 of 32 | PASS |
| Source-of-truth artifact matches | 96 of 96 | PASS |
| Unique derived summary hashes | 32 | PASS |
| Registry reload Reference count | 32 | PASS |
| Temporary Baseline artifacts | 0 | PASS |
| 33rd Reference accepted | No | PASS |
| 33rd Reference triggered Bundle I/O | No | PASS |

### Observed Resource Measurements

| Metric | Observed |
|---|---:|
| Public Service elapsed time | 0.166251 seconds |
| External process elapsed time | `0:00.27` |
| Maximum RSS | 28,300 KB |
| Maximum RSS | 27.637 MiB |
| Validation run physical file bytes | 10,860,267 bytes |

The public Service timing covers:

- loading each of the 32 Core Bundles once;
- verifying declared Bundle artifacts;
- capturing physical manifest SHA-256 values;
- performing 31 anchor compatibility checks;
- constructing 32 immutable Reference memberships;
- atomically installing the initial Baseline and Revision;
- performing the installer's final Registry verification.

The external process measurement includes Python startup and
shutdown in addition to the Service operation.

No performance acceptance threshold was declared before this run.

The timing and memory figures are therefore recorded as observed
measurements, not as proof of compliance with a predefined service
level objective.

## 33rd-Reference Rejection Boundary

The 33-item request was rejected with:

~~~text
VELUNE_PRIVATE_BASELINE_SERVICE_REFERENCE_LIMIT_EXCEEDED
~~~

The Bundle loader was patched only as an observation counter for
this rejection check and was not called.

No output Baseline directory was created by the rejected request.

This confirms that the v1 Reference limit is enforced before
expensive Bundle I/O.

## Validated Claims

This record supports the following statements:

> Initial creation of two separate Private Baselines can safely
> resolve a concurrent collision on the same first opaque Baseline
> identifier candidate without overwriting an existing Baseline.

> The Private Baseline creation Service accepts the v1 maximum of
> 32 explicitly selected compatible Reference Bundles.

> A 33rd Reference is rejected before Bundle loading or Baseline
> installation.

> On the measured host, the 32-Reference Service operation completed
> in 0.166251 seconds with an external
> process maximum RSS of 27.637 MiB.

## Claims Not Supported by This Record

This record does not prove that:

- the 32 replicas represent independent robot executions;
- the 32 replicas contain heterogeneous observed evidence;
- every possible Reference Bundle combination has equivalent
  performance;
- 32 large Core Bundles will always complete in the measured time;
- the observed timing satisfies a predefined production SLO;
- concurrent processes can safely update one existing Registry;
- concurrent append of new Revisions is implemented or safe;
- Target Evaluation is implemented;
- Human Review installation is implemented;
- network, distributed, or multi-user operation is safe;
- payload-level Adapter semantics are correct;
- the References are normal, ideal, safe, or representative;
- any observed difference indicates regression or improvement;
- root cause, fault, liability, severity, risk, or normality was
  determined.

## Relationship to Existing Records

`private_baseline_real_adapter_e2e_validation_record.md` validates:

~~~text
two distinct real nuScenes-derived Core Bundles
    -> initial Private Baseline creation
    -> Registry reload
~~~

This record validates:

~~~text
concurrent initial ID collision
    + maximum 32-Reference initial creation
    + pre-I/O 33rd-Reference rejection
~~~

The records cover different validation boundaries and should not be
substituted for one another.

## Local Path Disclosure

Absolute validation-machine filesystem paths are intentionally
excluded from this repository record.

The full validation outputs remain local on the validation machine.
