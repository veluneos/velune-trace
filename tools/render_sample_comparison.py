#!/usr/bin/env python3
"""Render site/sample-comparison.html directly from a REAL, unmodified
VeluneOS Compare `comparison_report.json` -- the canonical structural
comparison engine's own output, at whatever schema version it currently
produces (observed and asserted here: 0.2.0). This script renders
canonical Compare output; it does not re-derive, re-rank, or reinterpret
it. `review_intervals` are walked in the exact order the engine already
produced them (class priority -> persistence -> normalized ratio -> tie
breakers) -- this script performs no sorting of its own. The "top
finding" is simply the first Stream group encountered in that
engine-emitted order; if the engine had ranked a different Stream first,
this script would say so instead.

Usage:
  render_sample_comparison.py <comparison_report.json> <bundle_manifest.json> <output.html>

The displayed Adapter version is read from <bundle_manifest.json>'s own
"adapter.version" field -- the real generated artifact -- never a
hardcoded literal.

Design (see PRODUCTIZATION_VALIDATION.md alongside this script for the
full evidence mapping): a three-level progressive-disclosure page --

  Level 1 (hero): what to look at first, in plain language, with a
    visual "full run vs. review window" bar. No jargon, no bucket
    indices, no schema/engine internals.
  Level 2 (evidence): the top finding's Reference/Target behavior in
    plain terms, plus a compact, de-emphasized list of the other,
    shorter-lived differences Compare also found but ranked lower.
  Level 3 (technical detail, collapsed <details>): Bucket-level counts,
    difference_type, schema/bundle/Adapter provenance -- present for an
    engineer who wants it, never required to get the headline value.

The base color tokens and typography (BASE_STYLE) are the ones the sample
page carried inline before the site moved to external stylesheets; they
are kept here verbatim so this renderer no longer reads
site/sample-comparison.html. Component styles (EXTRA_STYLE) use the same
variables, not a new design system.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

from stream_display import resolve_stream_display_name


CLASS_LABELS = {
    "reference_nonempty_target_empty": "Reference active, Target empty",
    "reference_empty_target_nonempty": "Reference empty, Target active",
    "message_count_difference": "Message-count difference",
    "out_of_order_difference": "Out-of-order difference",
    "alternating_empty_nonempty_pattern": (
        "Alternating empty/non-empty pattern (possible phase offset; "
        "cause not determined)"
    ),
}

# Difference classes that represent a Stream going fully silent on one
# side (a complete Reference/Target activity mismatch for that Bucket).
FULL_MISMATCH_TYPES = (
    "reference_nonempty_target_empty",
    "reference_empty_target_nonempty",
)

# Verbatim first <style> block of site/sample-comparison.html at ff51cf7,
# the last commit whose page carried inline styles.
BASE_STYLE = """<style>
.sample-banner {
  max-width: 760px;
  margin: 0 auto 1.5rem;
  padding: 0.85rem 1.1rem;
  border: 1px solid #33445c;
  border-radius: 10px;
  background: rgba(66, 149, 255, 0.1);
  color: #cbd8e8;
  font-size: 0.9rem;
  font-weight: 650;
}
.sample-banner strong { color: #68a9ff; letter-spacing: 0.06em; }
.sample-banner a { color: #f4f7fb; text-decoration: underline; }
.sample-return {
  max-width: 760px;
  margin: 2rem auto 0;
  padding-top: 1.5rem;
  border-top: 1px solid #202a38;
  text-align: center;
}
.sample-return a {
  display: inline-block;
  padding: 12px 18px;
  border: 1px solid #4295ff;
  border-radius: 9px;
  background: #4295ff;
  color: #06101d;
  font-weight: 700;
  text-decoration: none;
}
:root {
  --bg: #080b10;
  --bg-secondary: #152133;
  --card-bg: rgba(18, 25, 35, 0.82);
  --fg: #f4f7fb;
  --muted: #b8c2cf;
  --muted-2: #8491a1;
  --accent: #68a9ff;
  --border: #33445c;
  --border-2: #273447;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 2rem 1.5rem 4rem;
  background: radial-gradient(circle at top, var(--bg-secondary) 0, var(--bg) 42%);
  color: var(--fg);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  line-height: 1.5;
}
main { max-width: 760px; margin: 0 auto; }
header h1 {
  font-size: 0.95rem;
  letter-spacing: 0.14em;
  font-weight: 750;
  color: var(--accent);
  margin: 0 0 0.4rem;
}
header p.scope {
  color: var(--fg);
  margin: 0 0 0.3rem;
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}
header p.scope-meta {
  color: var(--muted-2);
  margin: 0 0 1.75rem;
  font-size: 0.8rem;
}
section.summary {
  margin-bottom: 2rem;
}
.summary-line {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.summary-line-secondary {
  font-size: 1rem;
  font-weight: 500;
  color: var(--muted);
  margin-top: 0.15rem;
}
.chip-list {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 1rem 0 0;
  padding: 0;
}
.chip {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0.3rem 0.75rem;
  font-size: 0.75rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--muted);
}
section.status {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  background: var(--card-bg);
}
section.status h2 { margin: 0 0 0.25rem; font-size: 1.15rem; }
section.status p { margin: 0; color: var(--muted); }
section.findings {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
article.card {
  border: 1px solid var(--border-2);
  border-radius: 10px;
  background: var(--card-bg);
  padding: 1.5rem;
}
.card-eyebrow {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  font-weight: 600;
  margin: 0 0 0.6rem;
}
.card-metric {
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--muted);
  margin: 0 0 0.9rem;
}
.value-row {
  display: flex;
  align-items: baseline;
  gap: 1.25rem;
  flex-wrap: wrap;
}
.value-col {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.value-role {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted-2);
}
.value-number {
  font-size: 1.9rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  font-variant-numeric: tabular-nums;
}
.value-arrow { font-size: 1.3rem; color: var(--muted); }
.value-delta {
  margin: 0.5rem 0 0;
  font-size: 1rem;
  font-weight: 500;
  color: var(--fg);
  font-variant-numeric: tabular-nums;
}
.inspect-row {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin-top: 1.1rem;
  padding-top: 1.1rem;
  border-top: 1px solid var(--border-2);
  flex-wrap: wrap;
}
.inspect-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted-2);
}
.inspect-target {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--fg);
  overflow-wrap: anywhere;
}
.interval-block { margin-top: 1.1rem; }
.interval-heading {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted-2);
  margin: 0 0 0.5rem;
}
.window-block { margin-top: 0.75rem; }
.window-label {
  font-size: 0.78rem;
  color: var(--muted);
  margin-bottom: 0.15rem;
}
.window-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.window-value {
  font-variant-numeric: tabular-nums;
  font-size: 0.95rem;
}
.copy-button {
  font-size: 0.75rem;
  padding: 0.15rem 0.55rem;
  border-radius: 5px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--fg);
  cursor: pointer;
}
.copy-button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.copy-fallback {
  font-size: 0.68rem;
  color: var(--muted);
  overflow-wrap: anywhere;
  user-select: all;
}
details {
  border: 1px solid var(--border-2);
  border-radius: 10px;
  padding: 0.6rem 1rem;
  margin-bottom: 0.75rem;
  background: var(--card-bg);
}
details summary {
  cursor: pointer;
  font-weight: 600;
  font-size: 0.85rem;
  letter-spacing: 0.02em;
}
details summary:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
details ul, details p { color: var(--muted); }
details ul { margin: 0.5rem 0 0; padding-left: 1.25rem; }
details p:first-child { margin-top: 0.5rem; }
footer {
  max-width: 760px;
  margin: 3rem auto 0;
  color: var(--muted-2);
  font-size: 0.85rem;
  border-top: 1px solid var(--border-2);
  padding-top: 1rem;
}
@media (max-width: 480px) {
  body { padding: 1.5rem 1rem 3rem; }
  .value-row { gap: 0.75rem; }
  .value-number { font-size: 1.5rem; }
}
</style>"""

EXTRA_STYLE = """
<style>
.hero {
  max-width: 760px;
  margin: 0 auto 2.5rem;
  text-align: left;
}
.hero-eyebrow {
  font-size: 0.78rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--accent);
  font-weight: 700;
  margin: 0 0 0.9rem;
}
.hero-headline {
  font-size: 2.1rem;
  font-weight: 800;
  letter-spacing: -0.01em;
  margin: 0 0 1rem;
  line-height: 1.15;
}
.hero-stream {
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--fg);
  margin: 0 0 0.35rem;
}
.hero-persist {
  font-size: 0.98rem;
  color: var(--muted);
  margin: 0 0 1.6rem;
}
.hero-persist strong { color: var(--fg); font-weight: 650; }
.timeline-block { margin: 0 0 1.75rem; }
.timeline-caption {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--muted-2);
  margin: 0 0 0.35rem;
}
.timeline-track {
  position: relative;
  height: 10px;
  border-radius: 6px;
  background: var(--border-2);
  margin-bottom: 1.1rem;
}
.timeline-window {
  position: absolute;
  top: 0;
  bottom: 0;
  border-radius: 6px;
  background: var(--accent);
}
.timeline-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: var(--muted-2);
  font-variant-numeric: tabular-nums;
  margin-top: -0.85rem;
}
.review-track {
  position: relative;
  height: 10px;
  margin-bottom: 0.35rem;
}
.review-window {
  position: absolute;
  top: 0;
  bottom: 0;
  border-radius: 6px;
  background: var(--accent);
  box-shadow: 0 0 0 3px rgba(104, 169, 255, 0.18);
}
.review-window-label {
  font-size: 0.85rem;
  color: var(--fg);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.hero-cta {
  display: inline-block;
  margin-top: 0.6rem;
  padding: 12px 20px;
  border-radius: 9px;
  background: var(--accent);
  color: #06101d;
  font-weight: 700;
  text-decoration: none;
  font-size: 0.95rem;
}
.rank-context {
  max-width: 760px;
  margin: 0 auto 1.75rem;
  padding: 1rem 1.25rem;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--card-bg);
  font-size: 0.95rem;
  color: var(--muted);
}
.rank-context strong { color: var(--fg); }
.section-label {
  max-width: 760px;
  margin: 0 auto 0.75rem;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted-2);
  font-weight: 700;
}
.background-list {
  max-width: 760px;
  margin: 0 auto 2rem;
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.background-item {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.65rem 0.9rem;
  border: 1px solid var(--border-2);
  border-radius: 8px;
  background: rgba(18, 25, 35, 0.4);
  font-size: 0.85rem;
  color: var(--muted);
}
.background-item .bg-stream { color: var(--fg); font-weight: 600; }
.background-item .bg-note { color: var(--muted-2); font-size: 0.8rem; }
</style>
"""


def esc(value: object) -> str:
    return html.escape(str(value))


def mmss(ns: int) -> str:
    total_sec = round(ns / 1_000_000_000)
    return f"{total_sec // 60:02d}:{total_sec % 60:02d}"


def group_by_stream(intervals: list[dict]) -> tuple[list[str], dict[str, list[dict]]]:
    """Group review_intervals by stream_key, preserving the engine's own
    emitted order (first-seen order == engine rank order). No Stream is
    re-sorted; this is a presentational grouping only."""
    order: list[str] = []
    by_stream: dict[str, list[dict]] = {}
    for interval in intervals:
        key = interval["stream_key"]
        if key not in by_stream:
            by_stream[key] = []
            order.append(key)
        by_stream[key].append(interval)
    return order, by_stream


def describe_group(stream_intervals: list[dict]) -> tuple[str, int, int]:
    """Return (plain-language shape description, first_bucket, last_bucket)."""
    types = [iv["difference_type"] for iv in stream_intervals]
    buckets = [iv["bucket_index"] for iv in stream_intervals]
    first_bucket, last_bucket = min(buckets), max(buckets)
    span = last_bucket - first_bucket + 1
    all_full_mismatch = all(t in FULL_MISMATCH_TYPES for t in types)

    if all_full_mismatch and span == len(stream_intervals) and span > 1:
        direction = (
            "Target activity disappears here"
            if types[0] == "reference_nonempty_target_empty"
            else "New activity appears in Target here"
        )
        return f"{direction}, persistently, across {span} consecutive seconds.", first_bucket, last_bucket
    if all_full_mismatch and len(stream_intervals) == 1:
        direction = (
            "briefly disappears" if types[0] == "reference_nonempty_target_empty"
            else "briefly appears"
        )
        return f"Activity {direction} for one second, then returns to normal.", first_bucket, last_bucket
    if all_full_mismatch:
        return (
            f"Activity mismatch across {len(stream_intervals)} separate seconds.",
            first_bucket, last_bucket,
        )
    return (
        f"A small message-count change, isolated to {len(stream_intervals)} second"
        f"{'s' if len(stream_intervals) != 1 else ''}.",
        first_bucket, last_bucket,
    )


def hero_direction(top_intervals: list[dict]) -> str | None:
    """A short, single-clause description of WHAT happened for the top
    finding, with no persistence/count language (that is stated
    separately in the hero). Returns None when the top finding's own
    difference_type isn't a full activity mismatch (e.g. it is a
    message-count-only difference) -- callers must handle that case
    rather than assume this always returns a phrase."""
    types = {iv["difference_type"] for iv in top_intervals}
    if types == {"reference_nonempty_target_empty"}:
        return "Target activity disappears here"
    if types == {"reference_empty_target_nonempty"}:
        return "New activity appears in Target here"
    return None


def build_background_list(
    order: list[str],
    by_stream: dict[str, list[dict]],
    alias_mapping: dict[str, str] | None = None,
) -> str:
    if len(order) <= 1:
        return ""
    rows = []
    for stream_key in order[1:]:
        intervals = by_stream[stream_key]
        description, first_bucket, last_bucket = describe_group(intervals)
        window = (
            f"second {first_bucket}" if first_bucket == last_bucket
            else f"seconds {first_bucket}–{last_bucket}"
        )
        label = resolve_stream_display_name(stream_key, alias_mapping)
        rows.append(
            f'<li class="background-item">'
            f'<span><span class="bg-stream">{esc(label)}</span> '
            f'&mdash; {esc(description)}</span>'
            f'<span class="bg-note">{esc(window)}</span>'
            f"</li>"
        )
    return "\n".join(rows)


def load_style_block() -> str:
    return BASE_STYLE + EXTRA_STYLE


def build_report_body(
    report: dict,
    adapter_version: str,
    alias_mapping: dict[str, str] | None = None,
) -> tuple[str, bool]:
    """Build the hero/rank-context/evidence/Level-3-details HTML for a
    Compare Report. Returns (body_html, has_findings).

    This is the ONLY place review_intervals are grouped, described, and
    ranked for display -- both the public sample page (render(), below)
    and a local/private renderer call this same function, so ranking and
    grouping can never drift between the two paths. `alias_mapping`, when
    supplied, only ever changes which label string is shown for a
    Stream; it never changes which Streams appear, their grouping, or
    their order."""
    summary = report["summary"]
    bundle_id = report["input"]["bundle_id"]
    schema_version = report["schema_version"]
    bucket_duration_ns = report["bucket_contract"]["duration_ns"]
    comparable_bucket_count = report["comparison_range"]["comparable_bucket_count"]
    total_duration_ns = comparable_bucket_count * bucket_duration_ns
    total_intervals = summary["review_interval_count"]
    stream_comparisons = {
        sc["stream_key"]: sc for sc in report["stream_comparisons"]
    }

    order, by_stream = group_by_stream(report["review_intervals"])

    if not order:
        # No findings at all -- handled honestly, not hidden.
        hero_html = """
<div class="hero">
  <p class="hero-eyebrow">Compare Result</p>
  <h1 class="hero-headline">No structural differences found</h1>
  <p class="hero-persist">Reference Run and Target Run matched across every comparable Bucket.</p>
</div>
"""
        return hero_html, False

    top_stream = order[0]
    top_label = resolve_stream_display_name(top_stream, alias_mapping)
    top_intervals = by_stream[top_stream]
    top_sc = stream_comparisons[top_stream]
    top_ref_count = top_sc["reference"]["message_count"]
    top_tgt_count = top_sc["target"]["message_count"]
    description, first_bucket, last_bucket = describe_group(top_intervals)
    span_buckets = last_bucket - first_bucket + 1
    is_persistent = span_buckets > 1
    direction = hero_direction(top_intervals) or description

    window_start_ns = first_bucket * bucket_duration_ns
    window_end_ns = (last_bucket + 1) * bucket_duration_ns
    window_duration_sec = round((window_end_ns - window_start_ns) / 1_000_000_000)

    left_pct = 100 * window_start_ns / total_duration_ns
    width_pct = 100 * (window_end_ns - window_start_ns) / total_duration_ns

    headline = (
        "1 change stands out" if len(order) >= 1
        else "No structural differences found"
    )
    total_duration_sec = round(total_duration_ns / 1_000_000_000)
    finding_word = "sustained change" if is_persistent else "top-ranked finding"
    persistence_line = (
        f"Persistent across {span_buckets} consecutive seconds"
        if is_persistent
        else "An isolated, single-second difference"
    )
    compression_line = (
        f"Compare narrowed {summary['common_stream_count']} Streams across "
        f"{total_duration_sec} seconds to one {window_duration_sec}-second "
        f"review window."
    )

    other_count = total_intervals - len(top_intervals)
    if other_count > 0:
        rank_context_html = f"""
<div class="rank-context">
  Compare found <strong>{total_intervals} review interval{"s" if total_intervals != 1 else ""}</strong>
  across {summary['changed_common_stream_count']} affected Stream{"s" if summary['changed_common_stream_count'] != 1 else ""}.
  The {finding_word} ranked above
  <strong>{other_count} shorter variation{"s" if other_count != 1 else ""}</strong>.
</div>
"""
    else:
        rank_context_html = f"""
<div class="rank-context">
  Compare found <strong>{total_intervals} review interval{"s" if total_intervals != 1 else ""}</strong>,
  all part of this one finding.
</div>
"""

    background_rows = build_background_list(order, by_stream, alias_mapping)
    background_section = ""
    if background_rows:
        background_section = f"""
<p class="section-label">Level 2 &middot; Also detected, ranked lower</p>
<ul class="background-list">
{background_rows}
</ul>
"""

    hero_html = f"""
<div class="hero">
  <p class="hero-eyebrow">Compare Result</p>
  <h1 class="hero-headline">{esc(headline)}</h1>
  <p class="hero-stream">{esc(top_label)}<br>{esc(direction)}</p>
  <p class="hero-persist">{esc(persistence_line)}</p>
  <p class="hero-persist">{esc(compression_line)}</p>

  <div class="timeline-block">
    <p class="timeline-caption">Full Run</p>
    <div class="timeline-track">
      <div class="timeline-window" style="left:{left_pct:.2f}%;width:{width_pct:.2f}%;"></div>
    </div>
    <div class="timeline-labels"><span>{mmss(0)}</span><span>{mmss(total_duration_ns)}</span></div>
    <p class="timeline-caption" style="margin-top:1.1rem;">Review First</p>
    <div class="review-track">
      <div class="review-window" style="left:{left_pct:.2f}%;width:{max(width_pct, 3):.2f}%;"></div>
    </div>
    <p class="review-window-label">{mmss(window_start_ns)} &rarr; {mmss(window_end_ns)}</p>
  </div>

  <a class="hero-cta" href="#evidence">Explore evidence &darr;</a>
</div>
"""

    evidence_html = f"""
<p class="section-label" id="evidence">Level 2 &middot; Evidence</p>
<section class="findings">
<article class="card">
  <p class="card-eyebrow">{esc(top_label)}</p>
  <h3 class="card-metric">Message count, whole Run</h3>
  <div class="value-row">
    <div class="value-col">
      <span class="value-role">Reference</span>
      <span class="value-number">{top_ref_count}</span>
    </div>
    <span class="value-arrow" aria-hidden="true">&rarr;</span>
    <div class="value-col">
      <span class="value-role">Target</span>
      <span class="value-number">{top_tgt_count}</span>
    </div>
  </div>
  <p class="value-delta">{top_tgt_count - top_ref_count:+d} messages</p>

  <div class="inspect-row">
    <span class="inspect-label">Affected window</span>
    <span class="inspect-target">{mmss(window_start_ns)} &rarr; {mmss(window_end_ns)}</span>
  </div>
</article>
</section>
{background_section}
"""

    if alias_mapping:
        original_identity_note = (
            'Original topic/source names are not included in the canonical '
            'bundle transferred to Compare ("original_topic_name_included": '
            'false) -- the labels above were resolved locally from your '
            "Adapter's alias_mapping.json; Compare itself only ever "
            "received the neutral Stream identifier below."
        )
    else:
        original_identity_note = (
            'Original topic/source names are not included in the canonical '
            'bundle by design ("original_topic_name_included": false) -- '
            "Stream labels above are the neutral identifier Compare itself "
            "receives."
        )

    details_html = f"""
<details>
  <summary>Level 3 &middot; Bucket-level detail</summary>
  <ul>
    <li>Comparable range: {comparable_bucket_count} complete one-second Buckets (complete_common_one_second_buckets_only rule).</li>
    <li>Top finding canonical Stream identifier: {esc(top_stream)}, Buckets {first_bucket}&ndash;{last_bucket}.</li>
    <li>Top finding difference type: {esc(CLASS_LABELS.get(top_intervals[0]['difference_type'], top_intervals[0]['difference_type']))}.</li>
    <li>{original_identity_note}</li>
    <li>Candidate-D (alternating empty/non-empty pattern) findings: {summary['alternating_empty_nonempty_pattern_count']} &mdash; a sustained phase-offset-shaped pattern is a structural classification, not a determination of cause.</li>
  </ul>
</details>

<details>
  <summary>Level 3 &middot; How the ranking works</summary>
  <p>Comparison basis: Reference Run and Target Run were both processed by
  the same Adapter bundle (one bucket contract), so this comparison is
  exact by construction.</p>
  <p>Findings are ordered by Compare's own deterministic ranking
  rule: a complete Reference/Target activity mismatch always ranks above
  a partial message-count difference; within the same kind of difference,
  a Stream that differs more persistently across the comparable Buckets
  ranks above one that differs only briefly. This is a fixed, reproducible
  ordering rule &mdash; never a severity, fault, or root-cause judgment.
  There is no AI decision stage in this ranking.</p>
</details>

<details>
  <summary>Level 3 &middot; Technical provenance</summary>
  <ul>
    <li>Bundle ID: {esc(bundle_id)}</li>
    <li>Report schema: {esc(schema_version)}</li>
    <li>Adapter version: {esc(adapter_version)}</li>
    <li>Mapping profile: {esc(report['input']['mapping_profile']['profile_id'])} v{esc(report['input']['mapping_profile']['profile_version'])}</li>
  </ul>
</details>
"""

    body_html = f"{hero_html}\n{rank_context_html}\n{evidence_html}\n{details_html}"
    return body_html, True


def render(report: dict, adapter_version: str) -> str:
    """Render the PUBLIC/SAMPLE page (site/sample-comparison.html).

    Never accepts an alias mapping -- this is the privacy-neutral
    rendering path and can only ever show the neutral Stream labels
    Compare itself emits. A local/private renderer is a separate script
    that calls build_report_body() directly with its own alias_mapping
    and assembles its own (non-"SAMPLE COMPARISON") page around it; it
    does not call this function."""
    style_block = load_style_block()
    body_html, has_findings = build_report_body(report, adapter_version)

    if not has_findings:
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Sample Comparison | Velune Compare</title>{style_block}</head>
<body><main>{body_html}</main></body></html>"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="A real Velune Compare report generated from a synthetic sample Reference Run and Target Run — see the product before applying for Beta access.">
<title>Sample Comparison | Velune Compare</title>
{style_block}
</head>
<body>
<main>
<p style="margin:0 0 1rem;"><a href="comparison-beta-en.html" style="color:#8491a1;text-decoration:none;font-size:0.9rem;">&larr; Velune Compare</a></p>
<p class="sample-banner">
  <strong>SAMPLE COMPARISON</strong> &mdash; generated by running the real,
  unmodified Velune Adapter and Velune Compare against a small synthetic
  Reference Run and Target Run, not a live customer run. There is no
  self-service upload workflow live yet; this is the same Compare Report
  produced once you have a Reference Run and Target Run prepared.
</p>

{body_html}

<footer>
  <p>VeluneOS identifies comparative observations.<br>Engineers determine the cause.</p>
</footer>

<div class="sample-return">
  <a href="comparison-beta-en.html">See what it takes to run this on your own logs &rarr;</a>
</div>
</main>
</body>
</html>
"""


def read_adapter_version_from_bundle_manifest(bundle_manifest_path: Path) -> str:
    """Read the REAL Adapter version from a generated
    transferable-bundle/bundle_manifest.json's own "adapter" field.

    This is the only source of truth for the version displayed in Level
    3 technical provenance -- never a hand-maintained literal. Fails
    clearly (does not guess or default) if the file is missing or the
    field isn't a well-formed non-empty string."""
    try:
        manifest = json.loads(bundle_manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(
            f"cannot read bundle_manifest.json at {bundle_manifest_path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"bundle_manifest.json at {bundle_manifest_path} is not valid JSON: {exc}"
        ) from exc

    adapter = manifest.get("adapter")
    if not isinstance(adapter, dict):
        raise SystemExit(
            f'bundle_manifest.json at {bundle_manifest_path} has no "adapter" object'
        )
    version = adapter.get("version")
    if not isinstance(version, str) or not version.strip():
        raise SystemExit(
            f'bundle_manifest.json at {bundle_manifest_path} has no usable '
            '"adapter.version" string'
        )
    return version


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 1
    report_path = Path(sys.argv[1])
    bundle_manifest_path = Path(sys.argv[2])
    out_path = Path(sys.argv[3])

    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report["schema_name"] != "velune.structural_comparison_report":
        raise SystemExit(
            f"unexpected schema_name: {report['schema_name']!r}"
        )

    adapter_version = read_adapter_version_from_bundle_manifest(bundle_manifest_path)

    html_text = render(report, adapter_version)
    out_path.write_text(html_text, encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
