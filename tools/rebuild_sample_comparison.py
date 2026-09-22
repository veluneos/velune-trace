#!/usr/bin/env python3
"""Reproducibly rebuild the public Sample Comparison end to end:

  synthetic Reference/Target MCAP (create_sample_comparison_pair.py)
  -> real Velune Adapter, pinned to the exact baseline in
     tools/sample_comparison_baseline.json (installed into a fresh,
     throwaway venv -- never the Adapter repo's own .venv, never
     "whatever Adapter happens to be on PATH")
  -> real canonical structural Compare (bin/velune compare-structural,
     run unmodified, in place, via PYTHONPATH -- it has no console
     script and is not installed)
  -> comparison_report.json
  -> the public, privacy-neutral renderer (render_sample_comparison.py)
  -> site/sample-comparison.html

This script only ever READS the Adapter and Compare repositories; it
never modifies, installs into, or writes inside either one. All
generated output lands in a throwaway staging directory first. The
generated "product story" (stream inventory, comparable range, top
finding, its window, and how many shorter findings it outranks) is
compared against the CURRENTLY CHECKED-IN examples/sample_comparison_pair
before anything under examples/ or site/ is touched. If Adapter 0.2.0
genuinely changes that story, this script stops and reports the exact
difference instead of silently overwriting the public page.

Fails closed: a wheel hash mismatch, a wrong installed version, a
missing/malformed generated artifact, or a changed product story all
stop the script with a clear, specific error -- never a silent
fallback to a different Adapter build or a best-effort partial write.

Installing the pinned Adapter wheel resolves its declared runtime
dependencies (mcap, jsonschema) via pip, which requires network access
unless those packages are already available to pip's resolver. This is
not hidden: it happens in the open "installing Adapter wheel..." step
below and fails with pip's own error if it cannot be satisfied -- it
never falls back to a different, unpinned Adapter.

Usage:
  rebuild_sample_comparison.py
      [--adapter-repo PATH]   (default: sibling ../velune-adapter)
      [--compare-repo PATH]   (default: sibling ../velune-cloud-structural-comparison)
      [--keep-staging]        (do not delete the staging directory on exit;
                                useful to inspect a failed run)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = REPO_ROOT / "tools" / "sample_comparison_baseline.json"
EXAMPLE_DIR = REPO_ROOT / "examples" / "sample_comparison_pair"
SITE_SAMPLE_PAGE = REPO_ROOT / "site" / "sample-comparison.html"

DEFAULT_ADAPTER_REPO = REPO_ROOT.parent / "velune-adapter"
DEFAULT_COMPARE_REPO = REPO_ROOT.parent / "velune-cloud-structural-comparison"

sys.path.insert(0, str(REPO_ROOT / "tools"))
from render_sample_comparison import (  # noqa: E402
    read_adapter_version_from_bundle_manifest,
    render,
)


class BaselineMismatch(SystemExit):
    """A baseline/reproducibility gate failed -- always fails closed."""


def load_baseline() -> dict:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_adapter_wheel(adapter_repo: Path, baseline: dict) -> Path:
    wheel_path = adapter_repo / "dist" / baseline["adapter"]["wheel_filename"]
    if not wheel_path.is_file():
        raise BaselineMismatch(
            f"pinned Adapter wheel not found: {wheel_path}\n"
            "This script never falls back to a different Adapter build."
        )
    actual_sha256 = sha256_of(wheel_path)
    expected_sha256 = baseline["adapter"]["wheel_sha256"]
    if actual_sha256 != expected_sha256:
        raise BaselineMismatch(
            f"Adapter wheel SHA-256 mismatch for {wheel_path}\n"
            f"  expected: {expected_sha256}\n"
            f"  actual:   {actual_sha256}\n"
            "Refusing to execute an unverified Adapter build."
        )
    print(f"[baseline] wheel OK: {wheel_path.name} sha256={actual_sha256}")

    # Informational only -- HEAD may move forward without changing which
    # wheel we pin to; the wheel hash above is the hard gate.
    try:
        head = subprocess.run(
            ["git", "-C", str(adapter_repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        expected_commit = baseline["adapter"]["git_commit"]
        if head != expected_commit:
            print(
                f"[baseline] NOTE: {adapter_repo} HEAD is {head}, "
                f"baseline recorded {expected_commit} -- wheel hash still "
                "verified above; this is informational only."
            )
        else:
            print(f"[baseline] adapter repo HEAD matches baseline: {head}")
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"[baseline] NOTE: could not read {adapter_repo} HEAD ({exc}); "
              "continuing on wheel-hash verification alone.")

    return wheel_path


def create_adapter_venv(staging: Path, wheel_path: Path, expected_version: str) -> Path:
    venv_dir = staging / "adapter-venv"
    print(f"[venv] creating throwaway venv at {venv_dir}")
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)], check=True,
    )
    venv_python = venv_dir / "bin" / "python"

    print(
        f"[venv] installing pinned wheel {wheel_path.name} -- this resolves "
        "its declared runtime dependencies (mcap, jsonschema) via pip and "
        "requires network access unless already cached"
    )
    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "--quiet", str(wheel_path)],
        check=True,
    )

    installed_version = subprocess.run(
        [str(venv_python), "-c", "import velune_adapter; print(velune_adapter.__version__)"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if installed_version != expected_version:
        raise BaselineMismatch(
            f"installed velune_adapter.__version__ is {installed_version!r}, "
            f"expected {expected_version!r} -- refusing to proceed with an "
            "unverified Adapter build."
        )
    print(f"[venv] verified installed Adapter version: {installed_version}")
    return venv_dir


def generate_mcap_pair(staging: Path, venv_dir: Path) -> tuple[Path, Path]:
    """Write the synthetic Reference/Target MCAP pair using the SAME
    throwaway Adapter venv (it already has the `mcap` package installed
    as a declared Adapter dependency) rather than requiring `mcap` to be
    importable in whatever environment runs this orchestrator script."""
    out_dir = staging / "mcap"
    out_dir.mkdir(parents=True, exist_ok=True)
    reference = out_dir / "reference.mcap"
    target = out_dir / "target.mcap"
    tools_dir = REPO_ROOT / "tools"
    venv_python = venv_dir / "bin" / "python"

    subprocess.run(
        [
            str(venv_python), "-c",
            "import sys, pathlib; sys.path.insert(0, sys.argv[1]); "
            "import create_sample_comparison_pair as m; "
            "m.write_run(pathlib.Path(sys.argv[2]), role='reference'); "
            "m.write_run(pathlib.Path(sys.argv[3]), role='target')",
            str(tools_dir), str(reference), str(target),
        ],
        check=True,
    )
    print(f"[mcap] wrote {reference}")
    print(f"[mcap] wrote {target}")
    return reference, target


def run_adapter_build(
    venv_dir: Path, reference: Path, target: Path, output_dir: Path
) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    adapter_cli = venv_dir / "bin" / "velune-adapter"
    print(f"[adapter] running: velune-adapter build --reference {reference} "
          f"--target {target} --output {output_dir}")
    subprocess.run(
        [
            str(adapter_cli), "build",
            "--reference", str(reference),
            "--target", str(target),
            "--output", str(output_dir),
        ],
        check=True,
    )


def run_structural_compare(compare_repo: Path, bundle_dir: Path, export_dir: Path) -> None:
    if export_dir.exists():
        shutil.rmtree(export_dir)
    bin_velune = compare_repo / "bin" / "velune"
    if not bin_velune.is_file():
        raise BaselineMismatch(
            f"structural Compare entrypoint not found: {bin_velune} "
            "(this script never modifies the Compare repo -- it only runs it in place)"
        )
    print(f"[compare] running: {bin_velune} compare-structural {bundle_dir} "
          f"--export-dir {export_dir}")
    # cwd is deliberately the Compare repo itself: `bin/velune` invokes
    # `python -m velune_trace.cli.main`, and Python's `-m` inserts the
    # CALLER's cwd at sys.path[0] ahead of the PYTHONPATH entry `bin/velune`
    # sets up. This repo (velune-public-deploy) has its own legacy, older
    # velune_trace/ package at its root that would otherwise shadow the
    # Compare repo's current one if this ran from this repo's cwd.
    subprocess.run(
        [str(bin_velune), "compare-structural", str(bundle_dir), "--export-dir", str(export_dir)],
        check=True,
        cwd=str(compare_repo),
    )


def validate_generated_contract(bundle_manifest: dict, report: dict, baseline: dict) -> None:
    expected_bundle = baseline["transferable_bundle_contract"]
    actual_bundle = bundle_manifest.get("bundle_contract", {})
    if (
        actual_bundle.get("name") != expected_bundle["name"]
        or actual_bundle.get("version") != expected_bundle["version"]
    ):
        raise BaselineMismatch(
            f"generated bundle_contract {actual_bundle} does not match "
            f"expected {expected_bundle}"
        )

    adapter_field = bundle_manifest.get("adapter", {})
    if adapter_field.get("version") != baseline["adapter"]["package_version"]:
        raise BaselineMismatch(
            f"generated bundle_manifest.json adapter.version "
            f"{adapter_field.get('version')!r} does not match pinned baseline "
            f"{baseline['adapter']['package_version']!r}"
        )

    expected_report_schema = baseline["compare_report_schema"]
    if (
        report.get("schema_name") != expected_report_schema["name"]
        or report.get("schema_version") != expected_report_schema["version"]
    ):
        raise BaselineMismatch(
            f"generated comparison_report.json schema "
            f"{report.get('schema_name')}@{report.get('schema_version')} does not "
            f"match expected {expected_report_schema['name']}@{expected_report_schema['version']}"
        )
    print("[validate] bundle_contract, adapter.version, and report schema all match baseline")


def extract_story(report: dict) -> dict:
    """The comparable "product story" facts a regenerated sample must
    still support -- deliberately independent of exact byte content
    (generated_at timestamps, bundle_id hashes, etc. are allowed to
    differ)."""
    from render_sample_comparison import describe_group, group_by_stream

    summary = report["summary"]
    bucket_duration_ns = report["bucket_contract"]["duration_ns"]
    order, by_stream = group_by_stream(report["review_intervals"])

    story = {
        "common_stream_count": summary["common_stream_count"],
        "changed_common_stream_count": summary["changed_common_stream_count"],
        "comparable_bucket_count": report["comparison_range"]["comparable_bucket_count"],
        "review_interval_count": summary["review_interval_count"],
        "other_finding_groups": max(len(order) - 1, 0),
    }
    if order:
        top_intervals = by_stream[order[0]]
        _description, first_bucket, last_bucket = describe_group(top_intervals)
        story["top_difference_type"] = top_intervals[0]["difference_type"]
        story["top_window_start_sec"] = first_bucket * bucket_duration_ns // 1_000_000_000
        story["top_window_end_sec"] = (last_bucket + 1) * bucket_duration_ns // 1_000_000_000
        story["top_span_buckets"] = last_bucket - first_bucket + 1
    else:
        story["top_difference_type"] = None
    return story


def load_old_story() -> dict | None:
    old_report_path = EXAMPLE_DIR / "compare_output" / "comparison_report.json"
    if not old_report_path.is_file():
        return None
    return extract_story(json.loads(old_report_path.read_text(encoding="utf-8")))


PRIVATE_TOPIC_NAMES = ("/imu", "/lidar_top", "/battery_state", "/cpu_temp", "/diagnostics")


def assert_public_html_is_privacy_neutral(html_text: str) -> None:
    for name in PRIVATE_TOPIC_NAMES:
        if name in html_text:
            raise BaselineMismatch(
                f"regenerated public sample HTML contains original topic name "
                f"{name!r} -- refusing to write it"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter-repo", type=Path, default=DEFAULT_ADAPTER_REPO)
    parser.add_argument("--compare-repo", type=Path, default=DEFAULT_COMPARE_REPO)
    parser.add_argument("--keep-staging", action="store_true")
    args = parser.parse_args()

    baseline = load_baseline()
    old_story = load_old_story()

    staging = Path(tempfile.mkdtemp(prefix="velune-sample-rebuild-"))
    try:
        wheel_path = verify_adapter_wheel(args.adapter_repo, baseline)
        venv_dir = create_adapter_venv(
            staging, wheel_path, baseline["adapter"]["package_version"]
        )

        reference, target = generate_mcap_pair(staging, venv_dir)

        adapter_output = staging / "adapter_output"
        run_adapter_build(venv_dir, reference, target, adapter_output)

        bundle_dir = adapter_output / "transferable-bundle"
        compare_output = staging / "compare_output"
        run_structural_compare(args.compare_repo, bundle_dir, compare_output)

        bundle_manifest = json.loads(
            (bundle_dir / "bundle_manifest.json").read_text(encoding="utf-8")
        )
        report = json.loads(
            (compare_output / "comparison_report.json").read_text(encoding="utf-8")
        )
        validate_generated_contract(bundle_manifest, report, baseline)

        new_story = extract_story(report)
        if old_story is not None and old_story != new_story:
            print("PRODUCT STORY CHANGED -- stopping without touching "
                  "examples/ or site/. Old vs new:")
            print(f"  old: {json.dumps(old_story, indent=2)}")
            print(f"  new: {json.dumps(new_story, indent=2)}")
            return 1
        print("[story] regenerated product story matches the currently "
              f"checked-in sample: {json.dumps(new_story, indent=2)}")

        adapter_version = read_adapter_version_from_bundle_manifest(
            bundle_dir / "bundle_manifest.json"
        )
        html_text = render(report, adapter_version)
        assert_public_html_is_privacy_neutral(html_text)

        # All gates passed -- now, and only now, replace the checked-in
        # example fixture and the public page.
        if EXAMPLE_DIR.exists():
            shutil.rmtree(EXAMPLE_DIR)
        EXAMPLE_DIR.mkdir(parents=True)
        shutil.copy2(reference, EXAMPLE_DIR / "reference.mcap")
        shutil.copy2(target, EXAMPLE_DIR / "target.mcap")
        shutil.move(str(adapter_output), str(EXAMPLE_DIR / "adapter_output"))
        shutil.move(str(compare_output), str(EXAMPLE_DIR / "compare_output"))

        SITE_SAMPLE_PAGE.write_text(html_text, encoding="utf-8")
        print(f"[write] {EXAMPLE_DIR} regenerated")
        print(f"[write] {SITE_SAMPLE_PAGE} regenerated")
        return 0
    finally:
        if args.keep_staging:
            print(f"[staging] kept at {staging} (--keep-staging)")
        else:
            shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
