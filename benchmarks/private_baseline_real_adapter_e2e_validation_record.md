# Private Baseline Real Adapter E2E Validation Record

## Record Metadata

- Record type: `END_TO_END_VALIDATION_RECORD`
- Validation status: `PASS`
- Validation date: `2026-07-21`
- Validation scope: `REAL_ADAPTER_OUTPUT_CORE_BUNDLES_TO_INITIAL_PRIVATE_BASELINE`
- Repository branch: `phase2-private-baseline-contract`
- Source commit: `21a174b079f03bf8678249c85480782756f7779a`
- Commit date: `2026-07-21T10:16:07+09:00`
- Commit subject: `Add verified Private Baseline creation service`
- Visibility: `private_local_only`
- Network activity: `none`
- Automatic upload: `none`

## Executive Result

Velune Trace created and reloaded one immutable Private Baseline
from two verified Core Report Bundles produced from real
nuScenes-derived MCAP inputs.

| Metric | Result |
|---|---:|
| Reference Bundles | 2 |
| Aggregate source MCAP size | 1,046,351,793 bytes |
| Aggregate source MCAP size | 0.974491 GiB |
| Public Service creation elapsed time | 0.024302 seconds |
| Registry reload elapsed time | 0.001617 seconds |
| Compatibility warnings | 0 |
| Manifest SHA-256 matches | 2 of 2 |
| Registry reload validation | PASS |
| Result | PASS |

The Service timing was measured with `time.perf_counter()` around
the public `create_private_baseline()` call.

The Registry reload timing was measured immediately after creation
around `load_private_baseline_registry()`.

The Registry reload measurement is not a guaranteed cold-cache
measurement.

## Validated Pipeline

~~~text
real nuScenes-derived source data
    -> Adapter-produced MCAP inputs
    -> completed Core Report Bundles
    -> verified Comparison Bundle loader
    -> Comparison v1 compatibility gate
    -> public Private Baseline Service
    -> atomic initial Baseline installer
    -> immutable first Baseline Revision
    -> mutable local Registry
    -> fail-closed Registry reload
~~~

The Service did not rescan either raw MCAP input.

It operated on the completed Core Report Bundle artifacts.

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

## Real Reference Inputs

| Scene dimension | Source MCAP | Source size | Core artifact bytes | Report Bundle ID |
|---|---|---:|---:|---|
| `scene-1100` | `nuscenes-scene-1100.mcap` | 652,549,844 | 333,143 | `vrb_sha256_01df81a98ce891f2f2364fe49bcd25561315a74517e2a072a03943d9e4b674aa` |
| `scene-0553-shifted` | `nuscenes-scene-0553-shifted.mcap` | 393,801,949 | 337,161 | `vrb_sha256_e1f6251f9d96747a8d22326d57773b95bebe1837f824fc56763321cbfc84c4a2` |

Aggregate source size:

~~~text
652,549,844
+ 393,801,949
= 1,046,351,793 bytes
~~~

The two References represent distinct nuScenes-derived scene
inputs.

The cold-cache and warm-cache Core Bundles generated from the same
10.11 GiB replicated corpus were intentionally not used together as
separate References.

## Manifest Integrity

The Service pinned the physical SHA-256 of each
`report_manifest.json` into immutable Reference membership.

| Scene dimension | Physical manifest SHA-256 | Membership match |
|---|---|---|
| `scene-1100` | `632095bb958efc1deafbdcd8898b789213babff2dddd7bf0722237d6f2985c27` | PASS |
| `scene-0553-shifted` | `180717e6aab370361ccbe453af895d7e0668161428534db8ce178b8c40a24d07` | PASS |

The manifest SHA-256 is distinct from the content-derived
`report_bundle_id`.

## Compatibility Result

All selected Reference Bundles were compatible under the existing
Comparison v1 compatibility gate.

| Metric | Result |
|---|---:|
| Blocking incompatibilities | 0 |
| Compatibility warnings | 0 |
| Reference installation | Allowed |

Compatibility indicates that the Bundles share the required
comparison contract.

It does not mean that the References are equivalent, normal,
correct, safe, or representative.

## Generated Private Baseline

| Field | Value |
|---|---|
| Baseline root | `<LOCAL_VALIDATION_ROOT>/vpb_fc0d272646283d44be358ea9d84e7f86` |
| Baseline ID | `vpb_fc0d272646283d44be358ea9d84e7f86` |
| Initial Revision ID | `vpbr_43a99be29aded718ebc2ec9ad0fc3851` |
| Display name | `nuScenes Real Adapter E2E Baseline` |
| Created at | `2026-07-21T10:20:14+09:00` |
| Reference membership count | 2 |
| Parent Revision | `null` |
| Evaluation count | 0 |
| Review count | 0 |

Local Bundle locators:

- `scene-1100`: `<LOCAL_BUNDLE_ROOT>/core_bundle_scene_1100`
- `scene-0553-shifted`: `<LOCAL_BUNDLE_ROOT>/mcap_roundtrip/core_bundle_scene_0553_shifted`

Absolute local filesystem paths are intentionally redacted in this
repository validation record.

`<LOCAL_VALIDATION_ROOT>` and `<LOCAL_BUNDLE_ROOT>` identify private
local directories on the validation machine.

Bundle paths are mutable private operational locators.

They are not part of immutable Reference membership identity and
are not proof of Bundle integrity.

## Installed Permission Validation

| Path class | Required mode | Observed | Result |
|---|---:|---:|---|
| Baseline root | `700` | `700` | PASS |
| Baseline subdirectories | `700` | `700` | PASS |
| Revision directory | `700` | `700` | PASS |
| `baseline_registry.json` | `600` | `600` | PASS |
| `baseline_revision.json` | `600` | `600` | PASS |

## Atomicity and Reload Validation

The completed Baseline contains:

~~~text
baseline_registry.json
revisions/vpbr_43a99be29aded718ebc2ec9ad0fc3851/baseline_revision.json
evaluations/
reviews/
~~~

The Registry successfully reloaded through the fail-closed
Private Baseline Registry loader.

The reload verified:

- the Baseline root and Registry path;
- immutable Revision path containment;
- regular-file and symbolic-link restrictions;
- recorded immutable file size;
- recorded immutable file SHA-256;
- Registry and Revision identifiers;
- Baseline identifier consistency;
- first-Revision lineage;
- Reference membership structure.

## Acceptance Criteria

| Criterion | Required | Observed | Result |
|---|---:|---:|---|
| Real Adapter-derived Core Bundles | At least 2 | 2 | PASS |
| Distinct source scenes | Required | 2 | PASS |
| Verified Bundle loading | All References | 2 of 2 | PASS |
| Comparison v1 compatibility | No blocking differences | 0 blocking differences | PASS |
| Manifest digest pinning | All References | 2 of 2 | PASS |
| Initial Revision installation | Exactly 1 | 1 | PASS |
| Reference membership | Exactly 2 | 2 | PASS |
| Registry reload | Required | PASS | PASS |
| Private directory permissions | `700` | `700` | PASS |
| Private file permissions | `600` | `600` | PASS |
| Local-only execution | Required | No network or upload | PASS |

## Validated Claims

This record supports the following claim:

> Velune Trace created and reloaded an immutable Private Baseline
> from two verified Core Report Bundles produced from real
> nuScenes-derived MCAP inputs totaling 1,046,351,793
> source bytes.

It also supports this narrower performance statement:

> On the validation machine, the verified Private Baseline creation
> Service completed in 0.024302 seconds for two
> completed Core Report Bundles.

## Timing Boundary

The 0.024302-second result includes:

- loading each Reference Core Bundle once;
- verifying declared Core artifacts;
- capturing each physical manifest SHA-256;
- validating Reference identities;
- applying the Comparison v1 compatibility gate;
- constructing immutable Reference membership;
- atomically installing the initial Baseline and Revision;
- performing the installer's final Registry verification.

The result does not include:

- downloading nuScenes;
- source-dataset preparation;
- Adapter conversion into MCAP;
- raw MCAP parsing;
- Core Report Bundle generation;
- the earlier evidence-extraction runtime;
- human Reference selection time.

## Claims Not Supported by This Record

This record does not prove that:

- 1,046,351,793 bytes of raw MCAP were processed in
  0.024302 seconds;
- Adapter conversion completed in 0.024302
  seconds;
- payload-level semantic mapping performed by every Adapter is
  correct;
- every MCAP or rosbag2 schema is supported;
- 32 Reference Bundles meet a defined performance target;
- concurrent processes can update one existing Baseline safely;
- a new Revision can yet be appended to an existing Baseline;
- Target Evaluation has been implemented;
- human Review installation has been implemented;
- network, multi-user, or distributed operation has been validated;
- the References are normal, ideal, safe, or representative;
- any observed difference indicates regression or improvement;
- root cause, fault, liability, severity, or normality was
  determined.

## Relationship to Other Validation Records

`mcap_core_bundle_10gib_validation_record.md` measures:

~~~text
10.11 GiB MCAP
    -> bounded streaming evidence extraction
    -> complete Core Report Bundle
~~~

`core_bundle_comparison_v1_validation_record.md` measures:

~~~text
verified Core Bundle A + verified Core Bundle B
    -> Comparison v1
    -> deterministic observed-difference report
~~~

This record measures:

~~~text
two verified compatible Core Report Bundles
    -> public Private Baseline Service
    -> immutable initial Reference Revision
    -> fail-closed Registry reload
~~~

The three records measure separate stages and their elapsed times
must not be combined or substituted for one another.
