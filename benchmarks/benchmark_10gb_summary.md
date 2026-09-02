# 10GB Benchmark Summary

## Corpus

- Input size: 10,737,418,410 bytes
- Events indexed: 9,237,885
- SQLite index size: approximately 4.8 GB

## Initial Index Build

- Build time: 276.084394 seconds
- Result: PASS

## Chain Extraction

- Seed event: 0cf8e895-79c6-4783-9409-58380a23fa65
- Events returned: 17
- Chain extraction time: 0.002076 seconds
- Result: PASS

## Incremental Indexing

- 10,000 append events indexed
- Incremental index time: 0.569805 seconds
- Full source SHA256 recalculation: NOT USED
- Result: PASS

## Scope

These results are measured after the corpus has been normalized into structured JSONL trace events.

Velune Trace does not claim raw 10GB parsing and chain extraction in 0.002 seconds.
The 0.002 second figure refers to chain extraction after SQLite indexing.
