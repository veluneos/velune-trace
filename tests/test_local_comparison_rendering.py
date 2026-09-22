"""Tests for the LOCAL/PRIVATE Compare Report source-identity join.

Covers tools/stream_display.py and tools/render_local_comparison.py:
resolving a neutral stream_key back to an original topic name using a
LOCAL-ONLY Adapter alias_mapping.json, while guaranteeing the public
sample path (tools/render_sample_comparison.py) never exposes original
identity and neither input file is ever mutated by rendering.
"""

from __future__ import annotations

import hashlib
import html.parser
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from render_local_comparison import render_local  # noqa: E402
from render_sample_comparison import render as render_public  # noqa: E402
from stream_display import (  # noqa: E402
    load_local_alias_mapping,
    resolve_stream_display_name,
)


def _bounded_report() -> dict:
    """A small, self-contained fixture shaped like a real
    velune.structural_comparison_report v0.2.0 document (verified
    against examples/sample_comparison_pair/compare_output/
    comparison_report.json) -- not the real public sample data, used
    only to exercise local rendering deterministically."""
    return {
        "schema_name": "velune.structural_comparison_report",
        "schema_version": "0.2.0",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "bucket_contract": {
            "comparison_rule": "complete_common_one_second_buckets_only",
            "duration_ns": 1_000_000_000,
            "representation": "sparse_nonempty_buckets_zero_implicit",
        },
        "comparison_range": {
            "comparable_bucket_count": 4,
            "comparable_range_start_offset_ns": 0,
            "comparable_range_end_offset_ns": 4_000_000_000,
            "common_observation_duration_ns": 4_000_000_000,
            "excluded_common_partial_tail_ns": 0,
            "reference_unmatched_coverage_ns": 0,
            "target_unmatched_coverage_ns": 0,
        },
        "input": {
            "bundle_contract": {
                "name": "velune.comparison_input_bundle",
                "version": "0.1.0",
            },
            "bundle_id": "vcib_sha256_testfixture" + "0" * 40,
            "mapping_profile": {
                "profile_id": "generic.mcap.structural",
                "profile_version": "0.1.0",
                "content_sha256": "0" * 64,
            },
        },
        "judgment_boundary": {
            "cause_inference": False,
            "fault_assignment": False,
            "improvement_judgment": False,
            "liability_calculation": False,
            "regression_judgment": False,
            "root_cause_conclusion": False,
            "safety_judgment": False,
        },
        "review_intervals": [
            {
                "stream_key": "stream.unmapped.004",
                "bucket_index": 0,
                "difference_type": "reference_nonempty_target_empty",
                "start_offset_ns": 0,
                "end_offset_ns": 1_000_000_000,
                "reference_message_count": 5,
                "target_message_count": 0,
                "message_count_delta": -5,
                "absolute_message_count_delta": 5,
                "out_of_order_count_delta": 0,
                "reference_out_of_order_count": 0,
                "target_out_of_order_count": 0,
            },
            {
                "stream_key": "stream.unmapped.004",
                "bucket_index": 1,
                "difference_type": "reference_nonempty_target_empty",
                "start_offset_ns": 1_000_000_000,
                "end_offset_ns": 2_000_000_000,
                "reference_message_count": 5,
                "target_message_count": 0,
                "message_count_delta": -5,
                "absolute_message_count_delta": 5,
                "out_of_order_count_delta": 0,
                "reference_out_of_order_count": 0,
                "target_out_of_order_count": 0,
            },
            {
                "stream_key": "stream.unmapped.002",
                "bucket_index": 2,
                "difference_type": "message_count_difference",
                "start_offset_ns": 2_000_000_000,
                "end_offset_ns": 3_000_000_000,
                "reference_message_count": 1,
                "target_message_count": 2,
                "message_count_delta": 1,
                "absolute_message_count_delta": 1,
                "out_of_order_count_delta": 0,
                "reference_out_of_order_count": 0,
                "target_out_of_order_count": 0,
            },
            {
                "stream_key": "stream.unmapped.009",
                "bucket_index": 3,
                "difference_type": "message_count_difference",
                "start_offset_ns": 3_000_000_000,
                "end_offset_ns": 4_000_000_000,
                "reference_message_count": 1,
                "target_message_count": 2,
                "message_count_delta": 1,
                "absolute_message_count_delta": 1,
                "out_of_order_count_delta": 0,
                "reference_out_of_order_count": 0,
                "target_out_of_order_count": 0,
            },
        ],
        "run_comparison": {
            "reference": {
                "included_stream_count": 3, "out_of_order_count": 0,
                "run_duration_ns": 4_000_000_000, "total_bucket_count": 4,
                "total_message_count": 20,
            },
            "target": {
                "included_stream_count": 3, "out_of_order_count": 0,
                "run_duration_ns": 4_000_000_000, "total_bucket_count": 4,
                "total_message_count": 16,
            },
            "difference": {
                "included_stream_count": 0, "out_of_order_count": 0,
                "run_duration_ns": 0, "total_bucket_count": 0,
                "total_message_count": -4,
            },
        },
        "stream_comparisons": [
            {
                "stream_key": "stream.unmapped.002", "schema_key_equal": True,
                "reference": {
                    "message_count": 5, "out_of_order_count": 0,
                    "duration_ns": 4_000_000_000, "first_message_offset_ns": 0,
                    "last_message_offset_ns": 4_000_000_000,
                    "schema_key": "schema.unmapped.001",
                },
                "target": {
                    "message_count": 6, "out_of_order_count": 0,
                    "duration_ns": 4_000_000_000, "first_message_offset_ns": 0,
                    "last_message_offset_ns": 4_000_000_000,
                    "schema_key": "schema.unmapped.001",
                },
                "difference": {
                    "message_count": 1, "out_of_order_count": 0,
                    "duration_ns": 0, "first_message_offset_ns": 0,
                    "last_message_offset_ns": 0,
                },
            },
            {
                "stream_key": "stream.unmapped.004", "schema_key_equal": True,
                "reference": {
                    "message_count": 10, "out_of_order_count": 0,
                    "duration_ns": 2_000_000_000, "first_message_offset_ns": 0,
                    "last_message_offset_ns": 2_000_000_000,
                    "schema_key": "schema.unmapped.001",
                },
                "target": {
                    "message_count": 0, "out_of_order_count": 0,
                    "duration_ns": 0, "first_message_offset_ns": 0,
                    "last_message_offset_ns": 0,
                    "schema_key": "schema.unmapped.001",
                },
                "difference": {
                    "message_count": -10, "out_of_order_count": 0,
                    "duration_ns": -2_000_000_000, "first_message_offset_ns": 0,
                    "last_message_offset_ns": -2_000_000_000,
                },
            },
            {
                "stream_key": "stream.unmapped.009", "schema_key_equal": True,
                "reference": {
                    "message_count": 5, "out_of_order_count": 0,
                    "duration_ns": 4_000_000_000, "first_message_offset_ns": 0,
                    "last_message_offset_ns": 4_000_000_000,
                    "schema_key": "schema.unmapped.001",
                },
                "target": {
                    "message_count": 6, "out_of_order_count": 0,
                    "duration_ns": 4_000_000_000, "first_message_offset_ns": 0,
                    "last_message_offset_ns": 4_000_000_000,
                    "schema_key": "schema.unmapped.001",
                },
                "difference": {
                    "message_count": 1, "out_of_order_count": 0,
                    "duration_ns": 0, "first_message_offset_ns": 0,
                    "last_message_offset_ns": 0,
                },
            },
        ],
        "stream_set": {
            "common_streams": [
                "stream.unmapped.002", "stream.unmapped.004", "stream.unmapped.009",
            ],
            "reference_only_streams": [],
            "target_only_streams": [],
        },
        "summary": {
            "common_stream_count": 3,
            "changed_common_stream_count": 3,
            "reference_only_stream_count": 0,
            "target_only_stream_count": 0,
            "message_count_difference_count": 2,
            "out_of_order_difference_count": 0,
            "reference_nonempty_target_empty_count": 2,
            "reference_empty_target_nonempty_count": 0,
            "alternating_empty_nonempty_pattern_count": 0,
            "review_interval_count": 4,
        },
        "visibility": "private_cloud_only",
    }


def _bounded_alias_mapping() -> dict:
    """Shaped like a real Adapter local-review/alias_mapping.json
    (schema_name "velune.adapter.local.alias_mapping", verified against
    examples/sample_comparison_pair/adapter_output/local-review/
    alias_mapping.json), with deliberately malformed entries mixed in."""
    return {
        "schema_name": "velune.adapter.local.alias_mapping",
        "schema_version": "0.1.0",
        "customer_local_only": True,
        "network_transfer_performed": False,
        "profile_id": "generic.mcap.structural",
        "profile_version": "0.1.0",
        "entries": [
            # 1. A cleanly mapped stream: stream.unmapped.004 -> /imu.
            {
                "assigned_stream_key": "stream.unmapped.004",
                "assigned_schema_key": "schema.unmapped.001",
                "original_topic_name": "/imu",
                "original_schema_name": "velune.SampleMessage",
                "inclusion_decision": "included",
                "mapping_status": "unmapped_aliased",
                "exclusion_reason": None,
                "role": "reference",
                "channel_id": 2, "paired_channel_id": 2,
                "pairing_stage": "exact_topic", "schema_id": 1,
            },
            {
                "assigned_stream_key": "stream.unmapped.004",
                "assigned_schema_key": "schema.unmapped.001",
                "original_topic_name": "/imu",
                "original_schema_name": "velune.SampleMessage",
                "inclusion_decision": "included",
                "mapping_status": "unmapped_aliased",
                "exclusion_reason": None,
                "role": "target",
                "channel_id": 2, "paired_channel_id": 2,
                "pairing_stage": "exact_topic", "schema_id": 1,
            },
            # 2. A second cleanly mapped stream: another real-looking alias.
            {
                "assigned_stream_key": "stream.unmapped.002",
                "assigned_schema_key": "schema.unmapped.001",
                "original_topic_name": "/cmd_vel",
                "original_schema_name": "velune.SampleMessage",
                "inclusion_decision": "included",
                "mapping_status": "unmapped_aliased",
                "exclusion_reason": None,
                "role": "reference",
                "channel_id": 3, "paired_channel_id": 3,
                "pairing_stage": "exact_topic", "schema_id": 1,
            },
            # 3. stream.unmapped.009 has NO entry at all -- must fall
            #    back to the neutral "Stream 009" label.
            # 4a. Malformed: missing/None original_topic_name.
            {
                "assigned_stream_key": "stream.unmapped.777",
                "original_topic_name": None,
                "inclusion_decision": "included",
                "role": "reference",
            },
            # 4b. Malformed: not even a dict.
            "not-a-dict-entry",
            # 4c. Malformed for our purposes: excluded, must not leak
            #     its topic name even though the name field is present.
            {
                "assigned_stream_key": "stream.unmapped.666",
                "original_topic_name": "/should_never_appear",
                "inclusion_decision": "excluded",
                "role": "reference",
            },
        ],
    }


def _write_json_tempfile(tmp_dir: Path, name: str, data: dict) -> Path:
    path = tmp_dir / name
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


class ResolveStreamDisplayNameTests(unittest.TestCase):
    def test_mapped_stream_returns_original_topic_name(self):
        alias = {"stream.unmapped.004": "/imu"}
        self.assertEqual(
            resolve_stream_display_name("stream.unmapped.004", alias), "/imu"
        )

    def test_unmapped_stream_falls_back_to_neutral_label(self):
        alias = {"stream.unmapped.004": "/imu"}
        self.assertEqual(
            resolve_stream_display_name("stream.unmapped.009", alias),
            "Stream 009",
        )

    def test_no_alias_mapping_at_all_uses_neutral_label(self):
        self.assertEqual(
            resolve_stream_display_name("stream.unmapped.004", None),
            "Stream 004",
        )

    def test_never_infers_a_topic_name_from_the_stream_number(self):
        alias = {"stream.unmapped.001": "/battery_state"}
        self.assertEqual(
            resolve_stream_display_name("stream.unmapped.002", alias),
            "Stream 002",
        )


class LoadLocalAliasMappingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tmp_path = Path(self.tmp.name)

    def test_real_shape_resolves_expected_streams(self):
        path = _write_json_tempfile(
            self.tmp_path, "alias_mapping.json", _bounded_alias_mapping()
        )
        mapping = load_local_alias_mapping(path)
        self.assertEqual(mapping["stream.unmapped.004"], "/imu")
        self.assertEqual(mapping["stream.unmapped.002"], "/cmd_vel")

    def test_malformed_entries_are_ignored_not_leaked(self):
        path = _write_json_tempfile(
            self.tmp_path, "alias_mapping.json", _bounded_alias_mapping()
        )
        mapping = load_local_alias_mapping(path)
        self.assertNotIn("stream.unmapped.777", mapping)
        self.assertNotIn("stream.unmapped.666", mapping)
        self.assertNotIn("/should_never_appear", mapping.values())

    def test_grossly_malformed_document_returns_empty_mapping(self):
        path = _write_json_tempfile(
            self.tmp_path, "alias_mapping.json", {"not": "the right shape"}
        )
        self.assertEqual(load_local_alias_mapping(path), {})

    def test_wrong_schema_name_returns_empty_mapping(self):
        bad = dict(_bounded_alias_mapping())
        bad["schema_name"] = "something.else"
        path = _write_json_tempfile(self.tmp_path, "alias_mapping.json", bad)
        self.assertEqual(load_local_alias_mapping(path), {})

    def test_missing_file_returns_empty_mapping(self):
        self.assertEqual(
            load_local_alias_mapping(self.tmp_path / "does-not-exist.json"), {}
        )


class LocalRenderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        tmp_path = Path(self.tmp.name)
        self.report_path = _write_json_tempfile(
            tmp_path, "comparison_report.json", _bounded_report()
        )
        self.alias_path = _write_json_tempfile(
            tmp_path, "alias_mapping.json", _bounded_alias_mapping()
        )

    def _load(self):
        report = json.loads(self.report_path.read_text(encoding="utf-8"))
        alias_mapping = load_local_alias_mapping(self.alias_path)
        return report, alias_mapping

    def test_local_render_shows_mapped_topic_names(self):
        report, alias_mapping = self._load()
        html_text = render_local(report, "0.1.0", alias_mapping)
        self.assertIn("/imu", html_text)
        self.assertIn("/cmd_vel", html_text)

    def test_local_render_falls_back_to_neutral_for_unmapped_stream(self):
        report, alias_mapping = self._load()
        html_text = render_local(report, "0.1.0", alias_mapping)
        self.assertIn("Stream 009", html_text)

    def test_local_render_never_leaks_excluded_entry_topic_name(self):
        report, alias_mapping = self._load()
        html_text = render_local(report, "0.1.0", alias_mapping)
        self.assertNotIn("/should_never_appear", html_text)

    def test_local_render_html_parses(self):
        report, alias_mapping = self._load()
        html_text = render_local(report, "0.1.0", alias_mapping)
        html.parser.HTMLParser().feed(html_text)  # must not raise

    def test_rendering_never_mutates_report_or_alias_files(self):
        report_hash_before = hashlib.sha256(self.report_path.read_bytes()).hexdigest()
        alias_hash_before = hashlib.sha256(self.alias_path.read_bytes()).hexdigest()

        report, alias_mapping = self._load()
        render_local(report, "0.1.0", alias_mapping)

        report_hash_after = hashlib.sha256(self.report_path.read_bytes()).hexdigest()
        alias_hash_after = hashlib.sha256(self.alias_path.read_bytes()).hexdigest()
        self.assertEqual(report_hash_before, report_hash_after)
        self.assertEqual(alias_hash_before, alias_hash_after)

    def test_public_render_never_exposes_original_topic_names(self):
        # render() takes no alias_mapping parameter at all -- the public
        # path cannot show original identity even in principle.
        report, _alias_mapping = self._load()
        html_text = render_public(report, "0.1.0")
        self.assertNotIn("/imu", html_text)
        self.assertNotIn("/cmd_vel", html_text)
        self.assertIn("Stream 004", html_text)

    def test_top_finding_identical_between_public_and_local_paths(self):
        # Alias resolution is display-only: the top-ranked finding must
        # be the same Stream/description in both rendering paths.
        report, alias_mapping = self._load()
        public_html = render_public(report, "0.1.0")
        local_html = render_local(report, "0.1.0", alias_mapping)
        self.assertIn("Target activity disappears here", public_html)
        self.assertIn("Target activity disappears here", local_html)


class RealSampleFixtureIntegrationTests(unittest.TestCase):
    """Optional end-to-end proof using the REAL generated sample pair
    under examples/sample_comparison_pair, when present (untracked,
    generated by tools/create_sample_comparison_pair.py)."""

    REAL_REPORT = (
        REPO_ROOT / "examples" / "sample_comparison_pair" / "compare_output"
        / "comparison_report.json"
    )
    REAL_ALIAS = (
        REPO_ROOT / "examples" / "sample_comparison_pair" / "adapter_output"
        / "local-review" / "alias_mapping.json"
    )

    @unittest.skipUnless(
        REAL_REPORT.exists() and REAL_ALIAS.exists(),
        "real generated sample fixture not present in this checkout",
    )
    def test_real_sample_local_render_shows_imu_public_does_not(self):
        report = json.loads(self.REAL_REPORT.read_text(encoding="utf-8"))
        alias_mapping = load_local_alias_mapping(self.REAL_ALIAS)

        local_html = render_local(report, "0.1.0", alias_mapping)
        public_html = render_public(report, "0.1.0")

        self.assertIn("/imu", local_html)
        self.assertNotIn("/imu", public_html)
        self.assertIn("Stream 004", public_html)


if __name__ == "__main__":
    unittest.main()
