"""Ranking regressions for `velune windowed-verify` (v0.5.3).

Two scoring defects were fixed in v0.5.3:

1. A window MORE regular than the baseline (smaller gap or jitter) was
   scored as irregular, because the gap and jitter terms used |log ratio|.
   Such windows could outrank windows that contain real long gaps.
2. A gap whose interval crosses a window boundary was invisible, because
   max_gap is measured only between messages inside one window.

Every recording here is synthetic and written into a temporary directory.
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from mcap.writer import Writer

from velune_trace.cli import windowed_verify as windowed_verify_module


T0_NS = 1_800_000_000 * 1_000_000_000
PERIOD_NS = 100_000_000
TOPIC = "/tick"


def write_mcap(path, times_ns, marker_ns=None):
    """One std_msgs/Header-like topic; an optional /marker message fixes the
    recording start independently of the /tick stream."""
    with open(path, "wb") as f:
        writer = Writer(f)
        writer.start(profile="ros2", library="velune-test")
        schema_id = writer.register_schema(
            "std_msgs/msg/Header",
            "ros2msg",
            b"builtin_interfaces/Time stamp\nstring frame_id\n",
        )
        tick_id = writer.register_channel(TOPIC, "cdr", schema_id)
        data = b"\x00\x01\x00\x00" + b"\x00" * 12
        if marker_ns is not None:
            marker_id = writer.register_channel("/marker", "cdr", schema_id)
            writer.add_message(
                marker_id, log_time=marker_ns, publish_time=marker_ns, data=data
            )
        for t in times_ns:
            writer.add_message(tick_id, log_time=t, publish_time=t, data=data)
        writer.finish()


def pseudo_jitter_ns(i, amplitude_ns):
    """Deterministic jitter in [-amplitude, +amplitude] (non-zero median)."""
    return ((i * 2654435761) % (2 * amplitude_ns + 1)) - amplitude_ns


def run_windowed_verify(path, top=10):
    with tempfile.TemporaryDirectory() as tmpdir:
        export_path = Path(tmpdir) / "report.json"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exit_code = windowed_verify_module.main(
                [
                    str(path),
                    "--topic",
                    TOPIC,
                    "--window-sec",
                    "1",
                    "--top",
                    str(top),
                    "--export-json",
                    str(export_path),
                ]
            )
        report = json.loads(export_path.read_text())
    return exit_code, buf.getvalue(), report


def reported_gap(window):
    stats = window["stats"]
    return max(stats["max_gap"], stats.get("max_gap_incl_entry") or 0.0)


class WindowedVerifyScoringTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory(prefix="velune-test-wv-score-")
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp = Path(self._tmpdir.name)

    def test_regular_windows_do_not_outrank_long_gaps(self):
        # 60 s of 10 Hz with +-3 ms jitter; windows 10-15 are almost perfectly
        # regular (+-0.05 ms); windows 30, 34, 38, 42, 46 each contain one
        # 0.3 s gap (two messages missing).
        regular = set(range(10, 16))
        stalls = {30, 34, 38, 42, 46}
        times = []
        for i in range(600):
            window = i // 10
            if window in stalls and i % 10 in (4, 5):
                continue
            amplitude = 50_000 if window in regular else 3_000_000
            times.append(T0_NS + 50_000_000 + i * PERIOD_NS + pseudo_jitter_ns(i, amplitude))
        path = self.tmp / "regular_vs_gaps.mcap"
        write_mcap(path, times, marker_ns=T0_NS)

        exit_code, _, report = run_windowed_verify(path, top=5)

        self.assertEqual(exit_code, 0)
        top_ids = {w["window_id"] for w in report["ranked_windows"][:5]}
        self.assertEqual(top_ids, stalls)
        for window in report["all_windows"]:
            if window["window_id"] in regular:
                self.assertLess(window["score"], 0.5)

    def test_boundary_straddling_gap_is_reported_and_ranked_first(self):
        # A 0.45 s interval between the last message of window 13 and the
        # first message of window 14.
        times = [
            T0_NS + 30_000_000 + i * PERIOD_NS + pseudo_jitter_ns(i, 150_000)
            for i in range(300)
        ]
        times = [t if i <= 129 else t + 350_000_000 for i, t in enumerate(times)]
        path = self.tmp / "boundary_gap.mcap"
        write_mcap(path, times, marker_ns=T0_NS)

        exit_code, output, report = run_windowed_verify(path)

        self.assertEqual(exit_code, 0)
        self.assertTrue(all(w["stats"]["max_gap"] < 0.2 for w in report["all_windows"]))
        first = report["ranked_windows"][0]
        self.assertGreaterEqual(first["stats"]["max_gap_incl_entry"], 0.44)
        self.assertAlmostEqual(
            first["stats"]["entry_gap"], first["stats"]["max_gap_incl_entry"]
        )
        self.assertIn("gap_in", output)
        self.assertIn("median_gap_in", output)

    def test_nominal_stream_reports_no_false_gap(self):
        times = [
            T0_NS + 30_000_000 + i * PERIOD_NS + pseudo_jitter_ns(i, 2_000_000)
            for i in range(300)
        ]
        path = self.tmp / "nominal.mcap"
        write_mcap(path, times, marker_ns=T0_NS)

        exit_code, _, report = run_windowed_verify(path)

        self.assertEqual(exit_code, 0)
        self.assertLess(max(reported_gap(w) for w in report["all_windows"]), 0.15)

    def test_timestamp_collapse_window_stays_anomalous(self):
        # Window 20 holds ten messages that all share one timestamp.
        times = []
        for i in range(300):
            t = T0_NS + 30_000_000 + i * PERIOD_NS + pseudo_jitter_ns(i, 2_000_000)
            if i // 10 == 20:
                t = T0_NS + 20 * 1_000_000_000 + 500_000_000
            times.append(t)
        path = self.tmp / "collapse.mcap"
        write_mcap(path, times, marker_ns=T0_NS)

        exit_code, _, report = run_windowed_verify(path)

        self.assertEqual(exit_code, 0)
        first = report["ranked_windows"][0]
        self.assertEqual(first["window_id"], 20)
        self.assertGreaterEqual(first["score"], 10.0)

    def test_entry_gap_fields_at_recording_start_and_after_empty_windows(self):
        # Messages only in windows 0-4 and 8-19; windows 5-7 are empty.
        times = [
            T0_NS + 50_000_000 + i * PERIOD_NS
            for i in range(200)
            if not 50 <= i < 80
        ]
        path = self.tmp / "empty_windows.mcap"
        write_mcap(path, times)

        exit_code, _, report = run_windowed_verify(path)

        self.assertEqual(exit_code, 0)
        rows = {w["window_id"]: w["stats"] for w in report["all_windows"]}
        self.assertIsNone(rows[0]["entry_gap"])
        for idx in (5, 6, 7):
            self.assertIsNone(rows[idx]["entry_gap"])
            self.assertEqual(rows[idx]["max_gap_incl_entry"], 0.0)
        self.assertAlmostEqual(rows[8]["entry_gap"], 3.1, places=6)
        self.assertIn("median_max_gap_incl_entry", report["baseline"])
        for key in ("median_count", "median_max_gap", "median_jitter"):
            self.assertIn(key, report["baseline"])


if __name__ == "__main__":
    unittest.main()
