from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a small deterministic evaluation set from the cleaned corpus."""
    if len(df) < 4:
        raise ValueError("Need at least 4 cleaned documents to build the evaluation set.")

    samples: list[dict[str, Any]] = []
    selected = df.sort_values(["published", "title"], ascending=[False, True]).head(min(6, len(df)))

    for row_number, row in enumerate(selected.to_dict(orient="records"), start=1):
        title = row["title"]
        paper_id = row["paper_id"]
        doc_ids = [paper_id]

        samples.extend(
            [
                {
                    "id": f"q{row_number:02d}_summary",
                    "question_type": "summary",
                    "question": f"What is the main summary of '{title}'?",
                    "ground_truth": first_sentence(row["summary"]),
                    "ground_truth_doc_ids": doc_ids,
                },
                {
                    "id": f"q{row_number:02d}_authors",
                    "question_type": "authors",
                    "question": f"Who authored '{title}'?",
                    "ground_truth": row["authors_joined"],
                    "ground_truth_doc_ids": doc_ids,
                },
                {
                    "id": f"q{row_number:02d}_date",
                    "question_type": "published_date",
                    "question": f"When was '{title}' published?",
                    "ground_truth": row["published"],
                    "ground_truth_doc_ids": doc_ids,
                },
                {
                    "id": f"q{row_number:02d}_categories",
                    "question_type": "categories",
                    "question": f"What categories are listed for '{title}'?",
                    "ground_truth": row["categories_joined"],
                    "ground_truth_doc_ids": doc_ids,
                },
            ]
        )

    write_json(output_path, samples)
    return samples
