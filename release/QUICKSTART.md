# Velune Trace v0.4.0 — Quick Start

## 1. Create the deterministic sample MCAP

```bash
.venv/bin/python       tools/create_sample_mcap.py
```

This creates:

```text
examples/sample.mcap
```

## 2. Generate a local evidence report

```bash
env -u PYTHONPATH -u PYTHONHOME       PYTHONNOUSERSITE=1       VELUNE_PYTHON="$PWD/.venv/bin/python"       ./bin/velune validation-report       examples/sample.mcap       --export-dir velune_report       --window-sec 1       --top 5       --allowed-lateness-sec 2
```

## 3. Review the generated artifacts

```text
velune_report/
├── report_manifest.json
├── summary.md
├── shareable_anonymous_report.json
├── topic_profile.json
├── evidence_windows.json
└── SCHEMA.md
```

Review `velune_report/summary.md` first.

## 4. Run on your own MCAP

```bash
env -u PYTHONPATH -u PYTHONHOME       PYTHONNOUSERSITE=1       VELUNE_PYTHON="$PWD/.venv/bin/python"       ./bin/velune validation-report       /path/to/your_log.mcap       --export-dir velune_report       --window-sec 1       --top 5       --allowed-lateness-sec 2
```

## 5. Compare two completed Core Report Bundles

```bash
env -u PYTHONPATH -u PYTHONHOME       PYTHONNOUSERSITE=1       VELUNE_PYTHON="$PWD/.venv/bin/python"       ./bin/velune compare-bundles       /path/to/reference_bundle       /path/to/target_bundle       --export-dir comparison_output
```

Comparison reports observed evidence differences only.
Engineers determine their meaning and cause.
