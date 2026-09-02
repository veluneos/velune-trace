# Velune Trace v0.4.1 — Installation

## Validated environment

- Ubuntu 24.04
- Python 3.12
- Local MCAP processing

Other environments may work, but they are not claimed by this release.

## Download

Download both files into the same directory:

- `velune-trace-v0.4.1.zip`
- `SHA256SUMS`

## Verify release integrity

Verify the archive before extracting it:

```bash
sha256sum -c SHA256SUMS
```

Continue only when the result is:

```text
velune-trace-v0.4.1.zip: OK
```

The checksum verifies the downloaded Velune Trace archive. It does not
certify the operating system or third-party Python package repositories.

## Extract

```bash
unzip velune-trace-v0.4.1.zip
cd velune-trace-v0.4.1
```

## Create an isolated Python environment

```bash
python3 -m venv .venv
```

## Install the validated dependency versions

```bash
env -u PYTHONPATH -u PYTHONHOME       PYTHONNOUSERSITE=1       .venv/bin/pip install       --disable-pip-version-check       -r requirements-lock.txt
```

## Verify the CLI

```bash
env -u PYTHONPATH -u PYTHONHOME       PYTHONNOUSERSITE=1       VELUNE_PYTHON="$PWD/.venv/bin/python"       ./bin/velune --help
```

Velune Trace operates locally. It does not perform telemetry,
automatically upload raw MCAP files, infer root cause, or assign fault.
