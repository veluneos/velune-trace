# Velune Trace v0.5.1

## Release Focus

v0.5.1 is a documentation and public claim-hygiene patch.
It does not change Velune Trace engine behavior, benchmark results,
or validation measurements.

## Changed

- Renamed nuScenes validation terminology from `External Validation`
  to `Public Dataset Validation` to distinguish Velune-run validation
  on a publicly available dataset from independent third-party
  evaluation.
- Clarified that the validated MCAP files were generated from the
  publicly available nuScenes dataset through the Foxglove
  `nuscenes2mcap` pipeline.
- Replaced the illustrative `400GB MCAP` workflow label with
  `Large Robotics Log` because no public 400GB validation evidence
  is currently published.
- Renamed the nuScenes validation summary and updated affected
  documentation and release-package references.
- Clarified historical evaluation wording so `external evaluation`
  is not confused with independent third-party evaluation.

## Release validation

- Full automated test suite passes after the documentation and
  packaging-reference changes: 107 tests and 58 subtests.
- The public nuScenes validation measurements are unchanged.
- The published 10.7 GB benchmark results are unchanged.
- No evidence-extraction behavior or public CLI behavior is changed.

## Product boundary

Velune Trace does not automatically determine:

- root cause
- fault or liability
- safety or severity
- normality or superiority
- regression or improvement

Find the events. Engineers find the cause.
