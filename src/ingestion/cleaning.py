from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw paper records into an embedding-ready dataframe."""
    rows: list[dict[str, Any]] = []
    reference_date = run_date.astimezone(UTC).date() if run_date.tzinfo else run_date.date()

    for record in records:
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        if not record.paper_id or not title or len(summary) < 40:
            continue

        published_date = _parse_date(record.published)
        updated_date = _parse_date(record.updated) or published_date
        if published_date is None:
            continue

        authors = _clean_list(record.authors, ["Unknown authors"])
        categories = _clean_list(record.categories, ["uncategorized"])
        primary_category = normalize_whitespace(record.primary_category) or categories[0]
        age_days = max(0, (reference_date - published_date.date()).days)
        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)

        row = {
            "paper_id": normalize_whitespace(record.paper_id).lower(),
            "title": title,
            "summary": summary,
            "authors": authors,
            "categories": categories,
            "primary_category": primary_category,
            "published": published_date.date().isoformat(),
            "updated": updated_date.date().isoformat() if updated_date else published_date.date().isoformat(),
            "age_days": age_days,
            "authors_joined": authors_joined,
            "categories_joined": categories_joined,
            "summary_chars": len(summary),
            "abs_url": normalize_whitespace(record.abs_url),
            "pdf_url": normalize_whitespace(record.pdf_url),
            "comment": normalize_whitespace(record.comment),
        }
        row["text_for_embedding"] = _build_embedding_text(row)
        rows.append(row)

    if not rows:
        return pd.DataFrame(
            columns=[
                "paper_id",
                "title",
                "summary",
                "authors",
                "categories",
                "primary_category",
                "published",
                "updated",
                "age_days",
                "authors_joined",
                "categories_joined",
                "summary_chars",
                "abs_url",
                "pdf_url",
                "comment",
                "text_for_embedding",
            ]
        )

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df.drop_duplicates(subset=["title"], keep="first")
    df = df.sort_values(["published", "title"], ascending=[False, True]).reset_index(drop=True)
    return df


def _parse_date(value: str) -> datetime | None:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def _clean_list(values: list[str], default: list[str]) -> list[str]:
    cleaned = [normalize_whitespace(str(value)) for value in values if normalize_whitespace(str(value))]
    return cleaned or default


def _build_embedding_text(row: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Title: {row['title']}",
            f"Authors: {row['authors_joined']}",
            f"Published: {row['published']}",
            f"Categories: {row['categories_joined']}",
            f"Abstract: {row['summary']}",
        ]
    )
