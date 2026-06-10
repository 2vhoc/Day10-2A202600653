from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def main() -> None:
    """Run the baseline ETL, retrieval, evaluation, and observability flow."""
    settings = load_settings()
    paths = settings.paths

    if paths.raw_records_json.exists() and not settings.refresh_source:
        records = load_raw_records(paths.raw_records_json)
    else:
        records = fetch_source_records(settings)

    clean_df = build_clean_dataframe(records, run_date=now_utc())
    if clean_df.empty:
        raise RuntimeError("No clean records were produced from the raw source.")

    write_csv(clean_df, paths.clean_csv)
    write_json(paths.clean_json, clean_df.to_dict(orient="records"))

    index = LocalEmbeddingIndex.build(clean_df, settings=settings, embeddings_output_path=paths.embeddings_json)

    if paths.eval_testset.exists() and not settings.refresh_test_set:
        test_set = read_json(paths.eval_testset)
    else:
        test_set = build_test_set(clean_df, paths.eval_testset)

    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.baseline_metrics,
        answers_output_path=paths.baseline_answers,
    )
    quality = run_data_quality_checks(clean_df, settings=settings, report_name="baseline")
    freshness = build_freshness_report(clean_df, settings=settings, report_path=paths.freshness_report)

    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "max_results": settings.max_results,
        "raw_records": len(records),
        "clean_records": len(clean_df),
        "generated_at": now_utc().isoformat(),
    }
    generate_phase1_report(
        paths.baseline_report,
        source_summary=source_summary,
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )

    demo_answers = []
    for sample in test_set[:3]:
        answer = answer_question(sample["question"], settings=settings, index=index)
        demo_answers.append(
            {
                "question": sample["question"],
                "answer": answer.answer,
                "retrieved_doc_ids": answer.retrieved_doc_ids,
            }
        )
    write_json(paths.demo_answers, demo_answers)

    print(f"Clean data: {paths.clean_csv}")
    print(f"Baseline metrics: {paths.baseline_metrics}")
    print(f"Baseline report: {paths.baseline_report}")
