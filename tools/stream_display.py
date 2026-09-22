#!/usr/bin/env python3
"""Stream display-name resolution for Compare Report rendering.

`resolve_stream_display_name` is the ONLY place a Compare Report renderer
turns a canonical neutral `stream_key` (e.g. "stream.unmapped.004") into a
customer-facing label. It has exactly two inputs:

  stream_key      -- the neutral identifier from comparison_report.json.
                      This is the ONLY stream identity that ever crosses
                      the transferable-bundle privacy boundary.
  alias_mapping    -- OPTIONAL, LOCAL-ONLY. A stream_key -> original
                      topic name dict, built from a customer's own
                      Adapter alias_mapping.json (see
                      `load_local_alias_mapping` below). It never comes
                      from, and must never be written to, any
                      transferable/shareable artifact.

When alias_mapping is None or has no entry for stream_key, the neutral
label ("Stream 004") is used -- this is the only behavior the public
sample renderer (render_sample_comparison.py) ever exercises, since it
never constructs or passes an alias_mapping. Resolution never infers a
topic name from the stream number itself; only an explicit local mapping
entry can produce anything other than the neutral label, and it changes
display text only -- never ranking, grouping, or which Streams appear.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_STREAM_KEY_RE = re.compile(r"stream\.unmapped\.(\d+)")

ALIAS_MAPPING_SCHEMA_NAME = "velune.adapter.local.alias_mapping"


def resolve_stream_display_name(
    stream_key: str, alias_mapping: dict[str, str] | None = None
) -> str:
    """Resolve `stream_key` to a customer-facing label.

    Returns the original topic name from `alias_mapping` when one is
    supplied and contains a usable entry for `stream_key`; otherwise
    returns the same reformatted neutral label the public renderer has
    always shown (e.g. "stream.unmapped.004" -> "Stream 004"), or the
    raw stream_key unchanged if it doesn't match the expected pattern.
    """
    if alias_mapping:
        alias = alias_mapping.get(stream_key)
        if isinstance(alias, str) and alias.strip():
            return alias
    match = _STREAM_KEY_RE.fullmatch(stream_key)
    if match:
        return f"Stream {match.group(1)}"
    return stream_key


def load_local_alias_mapping(alias_mapping_path: Path) -> dict[str, str]:
    """Read a LOCAL-ONLY Adapter `alias_mapping.json` and return a
    `stream_key -> original_topic_name` dict for display use only.

    This function only ever reads the file; callers must never write
    back to it. Malformed input is handled deterministically and never
    raises: a structurally invalid document (not a JSON object, missing
    or non-list "entries", or an unexpected `schema_name`) resolves to
    an empty mapping, which makes every Stream fall back to its neutral
    label -- the same safe default as passing alias_mapping=None.
    Individual malformed entries within an otherwise valid document are
    skipped one at a time rather than failing the whole file. An entry
    is only used when all of the following hold:

      - "inclusion_decision" == "included"
      - "assigned_stream_key" is a non-empty string
      - "original_topic_name" is a non-empty string

    When more than one valid entry maps the same stream_key (the file
    carries one entry per Reference/Target role), the "reference"-role
    entry wins deterministically; a "target"-role entry is only used as
    a fallback when no "reference"-role entry exists for that stream.
    """
    import json

    try:
        raw_text = Path(alias_mapping_path).read_text(encoding="utf-8")
        data: Any = json.loads(raw_text)
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(data, dict):
        return {}
    if data.get("schema_name") != ALIAS_MAPPING_SCHEMA_NAME:
        return {}
    entries = data.get("entries")
    if not isinstance(entries, list):
        return {}

    mapping: dict[str, str] = {}
    reference_backed: set[str] = set()

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("inclusion_decision") != "included":
            continue
        stream_key = entry.get("assigned_stream_key")
        topic_name = entry.get("original_topic_name")
        if not isinstance(stream_key, str) or not stream_key.strip():
            continue
        if not isinstance(topic_name, str) or not topic_name.strip():
            continue

        is_reference = entry.get("role") == "reference"
        if stream_key in mapping and stream_key in reference_backed and not is_reference:
            continue  # a reference-role entry already won this key
        mapping[stream_key] = topic_name
        if is_reference:
            reference_backed.add(stream_key)

    return mapping
