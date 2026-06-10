# Day 10 - Data Pipeline And Data Observability

Project này xây dựng một pipeline nhỏ nhưng đầy đủ cho bài toán RAG trên dữ liệu paper học thuật. Pipeline lấy dữ liệu thật từ Crossref, làm sạch dữ liệu, tạo embedding, xây local vector index bằng ChromaDB, đánh giá chất lượng retrieval/answer, giả lập dữ liệu bị lỗi, repair lại từ raw source và sinh báo cáo data quality/data observability.

## Mục Tiêu

- Lấy paper metadata thật từ Crossref REST API.
- Parse raw API response thành schema ổn định `PaperRecord`.
- Làm sạch title, abstract, authors, categories, publication date và URL.
- Tạo trường `text_for_embedding` để đưa vào vector search.
- Tạo ChromaDB index bằng model `sentence-transformers/all-MiniLM-L6-v2`.
- Tạo evaluation set tự động từ cleaned dataset.
- Đánh giá baseline retrieval và answer quality.
- Chạy data quality checks và freshness checks.
- Giả lập corrupted data:
  - xóa một số latest records
  - làm trống summary
  - thêm noise vào summary
  - truncate title
  - làm publication date bị stale
  - thêm duplicate rows
- Re-evaluate trên corrupted data.
- Repair dữ liệu bằng cách rebuild lại từ raw Crossref records.
- Re-evaluate repaired data và sinh report so sánh baseline/corrupted/repaired.

## Cấu Trúc Project

```text
src/
  core/             Config, paths, settings, utility helpers
  ingestion/        Fetch/parse Crossref, cleaning, corruption
  retrieval/        Embeddings, ChromaDB index, QA helper, LLM providers
  evaluation/       Tạo test set và tính metrics
  observability/    Quality checks, freshness checks, Markdown reports
  pipelines/        Baseline flow và corruption/repair flow
script/
  run_phase1.py
  run_corruption_flow.py
data/
  raw/              Raw Crossref response và parsed records
  clean/            Clean, corrupted và repaired datasets
  embeddings/       Embedding/index manifests
  eval/             Evaluation test set
  results/          Metrics, answers, corruption log
  quality/          Quality/freshness JSON reports
  reports/          Final Markdown reports
```

## Cài Đặt

Có thể cài dependencies bằng `uv` hoặc `pip`.

Dùng `uv`:

```bash
uv sync
```

Dùng `pip`:

```bash
pip install -r requirements.txt
```

Crossref không cần API key. Phần LLM judge cần một LLM provider hoạt động, ví dụ OpenAI-compatible endpoint, Gemini, OpenAI, Anthropic, OpenRouter hoặc Ollama.

Tạo file `.env` từ `.env.example`. Với custom OpenAI-compatible endpoint, cấu hình như sau:

```bash
LLM_PROVIDER=custom
LLM_URL=https://your-openai-compatible-endpoint/v1
LLM_MODEL=your-model-name
LLM_KEY=your-api-key
```

Project cũng hỗ trợ các biến sau:

```bash
GOOGLE_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OLLAMA_BASE_URL=http://localhost:11434
CUSTOM_LLM_BASE_URL=
CUSTOM_LLM_API_KEY=
```

Không commit file `.env`. File này đã được ignore trong `.gitignore`.

## Cách Chạy

Chạy baseline pipeline:

```bash
PYTHONPATH=src python script/run_phase1.py
```

Chạy corruption, repair và comparison pipeline:

```bash
PYTHONPATH=src python script/run_corruption_flow.py
```

Nếu đã cài bằng `uv`, có thể chạy:

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

Nếu muốn fetch lại Crossref data và rebuild test set:

```bash
REFRESH_SOURCE=1 REFRESH_TEST_SET=1 PYTHONPATH=src python script/run_phase1.py
PYTHONPATH=src python script/run_corruption_flow.py
```

## Output Chính

Sau khi chạy đủ hai pipeline, các artifact quan trọng nằm ở:

```text
data/raw/crossref_response.json
data/raw/crossref_records.json

data/clean/papers_clean.csv
data/clean/papers_clean.json
data/clean/papers_clean_corrupted.csv
data/clean/papers_clean_corrupted.json
data/clean/papers_clean_repaired.csv
data/clean/papers_clean_repaired.json

data/eval/test_set.json

data/results/baseline_metrics.json
data/results/corrupted_metrics.json
data/results/repaired_metrics.json
data/results/baseline_answers.json
data/results/corrupted_answers.json
data/results/repaired_answers.json
data/results/corruption_log.json

data/quality/baseline_quality.json
data/quality/corrupted_quality.json
data/quality/repaired_quality.json
data/quality/freshness_report.json
data/quality/corrupted_freshness_report.json
data/quality/repaired_freshness_report.json

data/reports/phase1_report.md
data/reports/corruption_report.md
```

## Kết Quả Đánh Giá Hiện Tại

Lần chạy hiện tại dùng 24 records thật từ Crossref và 24 câu hỏi evaluation được tạo tự động. LLM judge đã chạy bằng configured custom LLM endpoint.

| Dataset | Samples | Retrieval Hit Rate | Mean Token F1 | Judge Accuracy | Mean Judge Score | Judge Mode | LLM Fallbacks |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| Baseline | 24 | 100.0% | 100.0% | 100.0% | 5.000 | `llm` | 0 |
| Corrupted | 24 | 66.7% | 76.7% | 75.0% | 4.000 | `llm` | 0 |
| Repaired | 24 | 100.0% | 100.0% | 100.0% | 5.000 | `llm` | 0 |

Kết quả cho thấy đúng pattern cần chứng minh:

- Baseline data pass quality checks và cho retrieval/answer metrics tốt.
- Corrupted data fail quality checks và làm giảm retrieval/answer quality.
- Repaired data pass quality checks trở lại và metrics phục hồi về mức baseline.

## Kết Quả Data Quality

Lưu ý: `Corrupted = FAIL` là kết quả đúng kỳ vọng. Mục tiêu của corruption flow là cố tình làm hỏng dữ liệu để data quality checks phát hiện được lỗi. Nếu corrupted data vẫn `PASS` thì phần observability chưa chứng minh được tác dụng.

| Dataset | Overall Status | Failed Checks |
| --- | --- | --- |
| Baseline | PASS | none |
| Corrupted | FAIL | `paper_id_unique`, `summary_not_blank`, `summary_min_length`, `freshness_threshold` |
| Repaired | PASS | none |

Freshness summary:

- Baseline: fresh, `0 / 24` stale rows
- Corrupted: stale, `3 / 24` stale rows
- Repaired: fresh, `0 / 24` stale rows

## Report

Hai report cuối cùng:

- `data/reports/phase1_report.md`
- `data/reports/corruption_report.md`

Các report này tóm tắt source data, evaluation metrics, data quality checks, freshness status và so sánh baseline/corrupted/repaired.

## Ghi Chú

- Dữ liệu không phải fake data. Raw records được lấy từ Crossref REST API và lưu ở `data/raw/`.
- Corrupted dataset được tạo có chủ đích từ clean dataset để chứng minh impact của data quality lên RAG/retrieval.
- `data/chroma/` chứa local ChromaDB index. Có thể regenerate bằng cách chạy lại pipeline.
- Ragas là optional và mặc định đang skip. Nếu muốn chạy Ragas, set `RUN_RAGAS=1`, nhưng sẽ chậm hơn và cần LLM config hoạt động ổn định.
