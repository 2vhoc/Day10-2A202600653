# Day 10 Corruption Comparison Report

## Metrics Comparison

| Metric | Baseline | Corrupted | Repaired | Corrupted delta | Repaired delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| retrieval_hit_rate | 100.0% | 66.7% | 100.0% | -33.3 pp | +0.0 pp |
| mean_token_f1 | 100.0% | 76.7% | 100.0% | -23.3 pp | +0.0 pp |
| judge_accuracy | 100.0% | 75.0% | 100.0% | -25.0 pp | +0.0 pp |
| mean_judge_score | 5.000 | 4.000 | 5.000 | -1.000 | +0.000 |

## Corrupted Data Quality

- Overall status: FAIL
- Failed checks: paper_id_unique, summary_not_blank, summary_min_length, freshness_threshold
- Freshness: STALE
- Stale rows: 3 / 24

## Repaired Data Quality

- Overall status: PASS
- Failed checks: none
- Freshness: FRESH
- Stale rows: 0 / 24

## Interpretation

- Corrupted data should reduce retrieval and/or answer quality because selected records are removed or damaged.
- Repaired data is rebuilt from raw source records, so metrics and quality checks should move back toward the baseline.
