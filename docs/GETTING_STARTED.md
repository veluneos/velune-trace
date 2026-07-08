# Getting Started

## 1. Clone

git clone https://github.com/veluneos/velune-trace.git

cd velune-trace

## 2. Create Python Environment

python3 -m venv .venv

source .venv/bin/activate

python3 -m pip install --upgrade pip

python3 -m pip install -r requirements.txt

## 3. Check CLI

./bin/velune --help

## 4. Run on Your Own MCAP

Inspect metadata:

./bin/velune inspect /path/to/your_log.mcap

Profile timing behavior:

./bin/velune profile /path/to/your_log.mcap \
  --start-sec START_SEC \
  --end-sec END_SEC \
  --sort max_gap

Rank suspicious timing windows:

./bin/velune windowed-verify \
  /path/to/your_log.mcap \
  --topic /lidar_top \
  --window-sec 1 \
  --top 5 \
  --export-json windowed_report.json

Extract an evidence window:

./bin/velune evidence-window \
  /path/to/your_log.mcap \
  --topic /lidar_top \
  --start-sec START_SEC \
  --end-sec END_SEC \
  --expected-count 20 \
  --export-json evidence_window.json

## Notes

Velune Trace does not infer root cause.

Velune Trace does not assign fault.

Velune Trace reports observable timing evidence and reproducible evidence windows.

## 5. Try the Included Sample MCAP

Generate a small sample MCAP:

python3 tools/create_sample_mcap.py

Inspect the sample:

./bin/velune inspect examples/sample.mcap

Rank timing windows:

./bin/velune windowed-verify \
  examples/sample.mcap \
  --topic /lidar_top \
  --window-sec 1 \
  --top 5 \
  --export-json examples/sample_windowed_report.json


## 7. Join the Validation Partner Program

Velune Trace can generate a shareable report without requiring raw MCAP upload.

Submit only:

velune_report/shareable_anonymous_report.json

Send to:

the agreed private validation channel

Participants may receive:

- anonymous benchmark comparison
- timing anomaly summary
- investigation starting points
- validation feedback

Do not send raw MCAP files, sensor payloads, maps, credentials, or private operational data.

This is an early Validation Partner Program. Submission is optional.

