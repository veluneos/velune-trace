# Velune Trace v0.5.3

## Release Focus

v0.5.3 is a `windowed-verify` ranking-correctness patch. It fixes two
scoring defects that could keep windows with real long gaps out of the
top of the ranking. No other command changes; four README links are
corrected.

## Fixed

- **More regular is not more irregular.** The gap and jitter terms used
  the absolute log ratio to the baseline, so a window with unusually
  small gaps or jitter scored as anomalous and could outrank windows that
  contain real long gaps. Only values above the baseline now raise the
  score (the direction `validation-report` already uses). A window whose
  messages all share one timestamp still receives the +10 contribution.
- **Gaps across window boundaries.** `max_gap` is measured only inside a
  window, so a gap whose interval crosses a boundary was invisible. The
  gap term now uses the largest interval that ends in the window,
  including the interval from the previous observed message.
- **README links.** Four README links pointed to files that are not
  part of the release package. The Velune Adapter Beta Kit links now
  point to the same download on veluneos.ai, and the two
  benchmark-record links point to the same files on GitHub, pinned to
  commit ba50e23.

## Changed

- Ranking order and scores can differ from v0.5.2. Window construction,
  counts, `max_gap`, `jitter`, `evidence_command`, and ranking
  eligibility (full windows only) are unchanged.
- Windows with fewer than three messages no longer receive the +10
  "no jitter measurable" contribution, and single-message windows no
  longer receive the +10 "zero gap" contribution; they are still scored
  by the count term and by any real gap that ends in them.
- Human-readable output adds a `median_gap_in` baseline line and a
  `gap_in` table column.

## Added

- `--export-json` fields (additive only): `stats.entry_gap`,
  `stats.max_gap_incl_entry`, `baseline.median_max_gap_incl_entry`, and
  two `notes` lines. No existing field was removed, renamed, or changed
  in meaning.
- Ranking regression tests on synthetic recordings.

## Known limitations

- A gap that ends in the final partial window is reported in
  `all_windows` but not ranked (partial windows are not ranked, as in
  v0.5.2).
- The first windows of a recording that start before the topic's first
  message can still rank high through the count term.
- When the median window jitter is exactly zero, any jittered window
  receives +10.
- Ranking covers message timing only; it does not measure rate targets,
  CPU, or other values outside the recording.

## Release validation

- Full automated test suite passes: 147 tests and 58 subtests.
- The machine-readable `--export-json` contract is additive relative to
  v0.5.2.

## Product boundary

Velune Trace does not automatically determine:

- root cause
- fault or liability
- safety or severity
- normality or superiority
- regression or improvement

Find the events. Engineers find the cause.
