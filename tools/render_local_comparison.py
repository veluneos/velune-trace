#!/usr/bin/env python3
"""Render a LOCAL/PRIVATE Compare Report view that resolves canonical
neutral `stream_key` identifiers (e.g. "stream.unmapped.004") back to
meaningful original topic names (e.g. "/imu") using a customer's own
LOCAL-ONLY Velune Adapter `alias_mapping.json`.

This is a presentation-layer join only, meant to run entirely on the
customer's own machine:

  - comparison_report.json is read only, never mutated.
  - alias_mapping.json is read only, never mutated.
  - Original topic/source names are used only to choose a display label;
    they are never written into comparison_report.json, a transferable
    Bundle artifact, or anywhere under site/.
  - Ranking, grouping, and review-interval order come from
    render_sample_comparison.build_report_body(), the SAME function the
    public sample page uses -- so this script can never diverge from
    Compare's own engine-emitted ordering. Only which label string is
    shown for a Stream can differ; alias_mapping never affects ordering.
  - A Stream with no usable alias entry falls back to the same neutral
    "Stream NNN" label the public sample page shows. This never fails
    merely because some Stream has no alias.

Do not point <output.html> at anything under site/ -- this output is
LOCAL/PRIVATE and must never be published.

Usage:
  render_local_comparison.py <comparison_report.json> <alias_mapping.json> <output.html> [adapter_version]

`adapter_version` is optional, purely cosmetic (Level 3 technical
provenance display), and defaults to "unknown" when omitted -- this tool
has no other way to learn which Adapter build produced a given bundle.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from render_sample_comparison import build_report_body, load_style_block
from stream_display import load_local_alias_mapping


def render_local(
    report: dict, adapter_version: str, alias_mapping: dict[str, str]
) -> str:
    """Assemble the LOCAL/PRIVATE page around build_report_body()'s
    output. This is a separate template from render_sample_comparison's
    public render() -- its banner and title make the local/private
    nature of the file explicit, and it is never used for
    site/sample-comparison.html."""
    style_block = load_style_block()
    body_html, has_findings = build_report_body(report, adapter_version, alias_mapping)

    if not has_findings:
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Local Compare Report (Private)</title>{style_block}</head>
<body><main>{body_html}</main></body></html>"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Local Compare Report (Private)</title>
{style_block}
</head>
<body>
<main>
<p class="sample-banner">
  <strong>LOCAL / PRIVATE COMPARE REPORT</strong> &mdash; generated on
  this machine using your local Adapter <code>alias_mapping.json</code>
  to show original source/topic names next to Compare's neutral Stream
  identifiers. This file is for local use only &mdash; do not publish
  it, upload it, or place it under a shared or public site directory.
  <code>comparison_report.json</code> and <code>alias_mapping.json</code>
  are read only; neither is modified by this renderer.
</p>

{body_html}

<footer>
  <p>VeluneOS identifies comparative observations.<br>Engineers determine the cause.</p>
</footer>
</main>
</body>
</html>
"""


def main() -> int:
    if len(sys.argv) not in (4, 5):
        print(__doc__)
        return 1
    report_path = Path(sys.argv[1])
    alias_path = Path(sys.argv[2])
    out_path = Path(sys.argv[3])
    adapter_version = sys.argv[4] if len(sys.argv) == 5 else "unknown"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report["schema_name"] != "velune.structural_comparison_report":
        raise SystemExit(
            f"unexpected schema_name: {report['schema_name']!r}"
        )

    alias_mapping = load_local_alias_mapping(alias_path)

    html_text = render_local(report, adapter_version, alias_mapping)
    out_path.write_text(html_text, encoding="utf-8")
    print(f"wrote {out_path} -- LOCAL/PRIVATE output, do not publish under site/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
