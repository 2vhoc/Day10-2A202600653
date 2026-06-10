from __future__ import annotations

from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline phase report as Markdown."""
    lines = [
        "# Day 10 Phase 1 Report",
        "",
        "## Source",
        "",
        f"- API: {source_summary.get('source_api', 'unknown')}",
        f"- Query: `{source_summary.get('source_query', '')}`",
        f"- Filter: `{source_summary.get('source_filter', '')}`",
        f"- Raw records: {source_summary.get('raw_records', 0)}",
        f"- Clean records: {source_summary.get('clean_records', 0)}",
        "",
        "## Evaluation Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Samples | {metrics.get('samples', 0)} |",
        f"| Retrieval hit rate | {_pct(metrics.get('retrieval_hit_rate'))} |",
        f"| Mean token F1 | {_pct(metrics.get('mean_token_f1'))} |",
        f"| Judge accuracy | {_pct(metrics.get('judge_accuracy'))} |",
        f"| Mean judge score | {_num(metrics.get('mean_judge_score'))} |",
        f"| Judge mode | {metrics.get('judge_mode', 'unknown')} |",
        f"| LLM judge fallback count | {metrics.get('llm_judge_fallback_count', 0)} |",
        "",
        "## Data Quality",
        "",
        f"- Overall status: {'PASS' if quality.get('passed') else 'FAIL'}",
        f"- Failed checks: {', '.join(quality.get('failed_checks', [])) or 'none'}",
        "",
        "| Check | Status | Details |",
        "| --- | --- | --- |",
    ]
    for check in quality.get("checks", []):
        lines.append(
            f"| {check['name']} | {'PASS' if check['passed'] else 'FAIL'} | `{check.get('details', {})}` |"
        )

    lines.extend(
        [
            "",
            "## Freshness",
            "",
            f"- Latest published: {freshness.get('latest_published')}",
            f"- Oldest published: {freshness.get('oldest_published')}",
            f"- Stale rows: {freshness.get('stale_rows', 0)} / {freshness.get('total_rows', 0)}",
            f"- Status: {'FRESH' if freshness.get('is_fresh') else 'STALE'}",
            "",
        ]
    )
    write_text(report_path, "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write the baseline/corrupted/repaired comparison report."""
    lines = [
        "# Day 10 Corruption Comparison Report",
        "",
        "## Metrics Comparison",
        "",
        "| Metric | Baseline | Corrupted | Repaired | Corrupted delta | Repaired delta |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for metric in ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]:
        baseline_value = baseline_metrics.get(metric)
        corrupted_value = corrupted_metrics.get(metric)
        repaired_value = repaired_metrics.get(metric)
        lines.append(
            "| "
            f"{metric} | "
            f"{_metric(metric, baseline_value)} | "
            f"{_metric(metric, corrupted_value)} | "
            f"{_metric(metric, repaired_value)} | "
            f"{_signed_delta(metric, corrupted_value, baseline_value)} | "
            f"{_signed_delta(metric, repaired_value, baseline_value)} |"
        )

    lines.extend(
        [
            "",
            "## Corrupted Data Quality",
            "",
            f"- Overall status: {'PASS' if corrupted_quality.get('passed') else 'FAIL'}",
            f"- Failed checks: {', '.join(corrupted_quality.get('failed_checks', [])) or 'none'}",
            f"- Freshness: {'FRESH' if corrupted_freshness.get('is_fresh') else 'STALE'}",
            f"- Stale rows: {corrupted_freshness.get('stale_rows', 0)} / {corrupted_freshness.get('total_rows', 0)}",
            "",
            "## Repaired Data Quality",
            "",
            f"- Overall status: {'PASS' if repaired_quality.get('passed') else 'FAIL'}",
            f"- Failed checks: {', '.join(repaired_quality.get('failed_checks', [])) or 'none'}",
            f"- Freshness: {'FRESH' if repaired_freshness.get('is_fresh') else 'STALE'}",
            f"- Stale rows: {repaired_freshness.get('stale_rows', 0)} / {repaired_freshness.get('total_rows', 0)}",
            "",
            "## Interpretation",
            "",
            "- Corrupted data should reduce retrieval and/or answer quality because selected records are removed or damaged.",
            "- Repaired data is rebuilt from raw source records, so metrics and quality checks should move back toward the baseline.",
            "",
        ]
    )
    write_text(report_path, "\n".join(lines))


def _pct(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.1f}%"


def _num(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.3f}"


def _metric(metric: str, value: Any) -> str:
    return _num(value) if metric == "mean_judge_score" else _pct(value)


def _signed_delta(metric: str, value: Any, baseline: Any) -> str:
    if value is None or baseline is None:
        return "n/a"
    delta = float(value) - float(baseline)
    if metric == "mean_judge_score":
        return f"{delta:+.3f}"
    return f"{delta * 100:+.1f} pp"
