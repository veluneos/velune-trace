import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools.create_sample_mcap import (
    create_sample_mcap,
)
from velune_trace.cli.validation_report import REPORT_FILENAMES, main


def run_report(sample_path, export_dir, *extra):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        exit_code = main([
            str(sample_path),
            "--export-dir",
            str(export_dir),
            *extra,
        ])
    return exit_code, stdout.getvalue(), stderr.getvalue()


class ValidationReportOverwriteTests(unittest.TestCase):
    def test_existing_report_is_left_untouched_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            sample_path = create_sample_mcap(root / "sample.mcap")
            export_dir = root / "report"

            first_code, _, first_err = run_report(sample_path, export_dir)
            self.assertEqual(first_code, 0, msg=first_err)
            before = {
                name: (export_dir / name).read_bytes()
                for name in REPORT_FILENAMES
            }

            code, stdout, stderr = run_report(sample_path, export_dir)

            self.assertEqual(code, 2)
            self.assertEqual(stdout, "")
            self.assertIn("already contains a report", stderr)
            self.assertIn("--overwrite", stderr)
            for name, content in before.items():
                with self.subTest(file_name=name):
                    self.assertEqual((export_dir / name).read_bytes(), content)

    def test_single_existing_report_file_is_protected(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            sample_path = create_sample_mcap(root / "sample.mcap")
            export_dir = root / "report"
            export_dir.mkdir()
            (export_dir / "summary.md").write_text("my notes", encoding="utf-8")

            code, _, stderr = run_report(sample_path, export_dir)

            self.assertEqual(code, 2)
            self.assertIn("summary.md", stderr)
            self.assertEqual((export_dir / "summary.md").read_text(encoding="utf-8"), "my notes")
            self.assertFalse((export_dir / "report_manifest.json").exists())

    def test_overwrite_replaces_report_and_keeps_unrelated_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            sample_path = create_sample_mcap(root / "sample.mcap")
            export_dir = root / "report"

            self.assertEqual(run_report(sample_path, export_dir)[0], 0)
            first_evidence = (export_dir / "evidence_windows.json").read_bytes()
            (export_dir / "notes.txt").write_text("keep", encoding="utf-8")

            code, _, stderr = run_report(sample_path, export_dir, "--overwrite")

            self.assertEqual(code, 0, msg=stderr)
            self.assertEqual((export_dir / "evidence_windows.json").read_bytes(), first_evidence)
            self.assertEqual((export_dir / "notes.txt").read_text(encoding="utf-8"), "keep")
            manifest = json.loads((export_dir / "report_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["engine"]["name"], "velune_trace")

    def test_existing_directory_without_report_files_is_accepted(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            sample_path = create_sample_mcap(root / "sample.mcap")
            export_dir = root / "report"
            export_dir.mkdir()
            (export_dir / "notes.txt").write_text("keep", encoding="utf-8")

            code, _, stderr = run_report(sample_path, export_dir)

            self.assertEqual(code, 0, msg=stderr)
            self.assertEqual((export_dir / "notes.txt").read_text(encoding="utf-8"), "keep")

    def test_export_dir_that_is_a_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            sample_path = create_sample_mcap(root / "sample.mcap")
            not_a_dir = root / "report"
            not_a_dir.write_text("x", encoding="utf-8")

            code, _, stderr = run_report(sample_path, not_a_dir)

            self.assertEqual(code, 2)
            self.assertIn("not a directory", stderr)
            self.assertEqual(not_a_dir.read_text(encoding="utf-8"), "x")


if __name__ == "__main__":
    unittest.main()
