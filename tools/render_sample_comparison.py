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

The existing page's color tokens and base typography are preserved from
the current site/sample-comparison.html; new component styles are
appended to the same <style> block using the same variables, not a new
design system.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

from stream_display import resolve_stream_display_name

REPO_ROOT = Path(__file__).resolve().parent.parent
EXISTING_PAGE = REPO_ROOT / "site" / "sample-comparison.html"

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


def extract_style_block(existing_page_text: str) -> str:
    start = existing_page_text.index("<style>")
    end = existing_page_text.index("</style>") + len("</style>")
    return existing_page_text[start:end]


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
    existing = EXISTING_PAGE.read_text(encoding="utf-8")
    return extract_style_block(existing) + EXTRA_STYLE


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
