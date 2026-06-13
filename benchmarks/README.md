# Velune Trace Benchmark Summary

## Validation Highlights

| Benchmark | Result |
|------------|------------|
| Corpus Size | 10 GB |
| Indexed Events | 9,237,885 |
| Initial Index Build | 276 sec |
| SQLite Index Size | ~4.8 GB |
| Event Chain Retrieval | 0.002 sec |
| Incremental Append | 10,000 events in 0.57 sec |
| Incremental Idle Peak RAM | ~19 MB |

## Included Reports

| File | Purpose |
|--------|--------|
| VELUNE_TRACE_INDEXER_v0_2_INCREMENTAL_VALIDATION_REPORT.txt | Incremental indexing validation |
| VELUNE_TRACE_INDEXER_v0_2_INCREMENTAL_10K_STRESS_REPORT.txt | 10,000 event append stress test |
| VELUNE_TRACE_INDEXER_v0_2_RESOURCE_CHECK_REPORT.txt | Resource utilization report |
| VELUNE_TRACE_INDEXER_v0_2_RESOURCE_CHECK_TIME.txt | Runtime measurements |
| trace_chain_extraction_10gb_benchmark_report.txt | Event chain extraction benchmark |
| chain_extractor_v0_2_validation_report.txt | Chain extractor validation |
| trace_viewer_v0_4_streaming_validation_report.txt | Streaming viewer validation |

## Important Notes

- Retrieval benchmark is measured after indexing.
- Velune Trace does not claim raw 10GB parsing in 0.002 sec.
- Current model: Index once, query fast, append incrementally.
- Current validation scope focuses on ROS2-style structured JSONL traces.
