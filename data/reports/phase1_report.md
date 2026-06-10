# Day 10 Phase 1 Report

## Source

- API: Crossref REST API
- Query: `agentic retrieval augmented generation large language model`
- Filter: `from-pub-date:2025-12-12,until-pub-date:2026-06-10,has-abstract:true`
- Raw records: 24
- Clean records: 24

## Evaluation Metrics

| Metric | Value |
| --- | ---: |
| Samples | 24 |
| Retrieval hit rate | 100.0% |
| Mean token F1 | 100.0% |
| Judge accuracy | 100.0% |
| Mean judge score | 5.000 |
| Judge mode | llm |
| LLM judge fallback count | 0 |

## Data Quality

- Overall status: PASS
- Failed checks: none

| Check | Status | Details |
| --- | --- | --- |
| row_count_minimum | PASS | `{'row_count': 24, 'minimum': 8}` |
| paper_id_not_null | PASS | `{'null_count': 0}` |
| paper_id_unique | PASS | `{'duplicate_count': 0}` |
| title_not_blank | PASS | `{'blank_count': 0}` |
| summary_not_blank | PASS | `{'blank_count': 0}` |
| summary_min_length | PASS | `{'too_short_count': 0, 'minimum_chars': 40}` |
| freshness_threshold | PASS | `{'stale_count': 0, 'threshold_days': 180}` |

## Freshness

- Latest published: 2026-06-10
- Oldest published: 2026-06-10
- Stale rows: 0 / 24
- Status: FRESH
