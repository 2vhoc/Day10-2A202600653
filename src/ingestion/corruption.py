from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from core.utils import compact_join, normalize_whitespace, write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Create a deterministic corrupted copy of the clean dataframe."""
    corrupted = df.copy(deep=True).reset_index(drop=True)
    log: dict[str, Any] = {
        "input_rows": int(len(corrupted)),
        "dropped_latest_paper_ids": [],
        "blank_summary_paper_ids": [],
        "noisy_summary_paper_ids": [],
        "truncated_title_paper_ids": [],
        "stale_date_paper_ids": [],
        "duplicated_paper_ids": [],
    }
    if corrupted.empty:
        write_json(output_log_path, log | {"output_rows": 0})
        return corrupted

    corrupted = corrupted.sort_values(["published", "title"], ascending=[False, True]).reset_index(drop=True)

    drop_count = min(2, max(1, len(corrupted) // 10))
    drop_indices = list(range(drop_count))
    log["dropped_latest_paper_ids"] = corrupted.loc[drop_indices, "paper_id"].astype(str).tolist()
    corrupted = corrupted.drop(index=drop_indices).reset_index(drop=True)

    blank_indices = list(range(0, min(2, len(corrupted))))
    if blank_indices:
        log["blank_summary_paper_ids"] = corrupted.loc[blank_indices, "paper_id"].astype(str).tolist()
        corrupted.loc[blank_indices, "summary"] = ""

    noisy_indices = list(range(2, min(5, len(corrupted))))
    if noisy_indices:
        log["noisy_summary_paper_ids"] = corrupted.loc[noisy_indices, "paper_id"].astype(str).tolist()
        noise = " DATA_QUALITY_DRIFT UNKNOWN_TOKEN NULL_VALUE BROKEN_CONTEXT"
        corrupted.loc[noisy_indices, "summary"] = corrupted.loc[noisy_indices, "summary"].astype(str) + noise

    truncate_indices = list(range(5, min(8, len(corrupted))))
    if truncate_indices:
        log["truncated_title_paper_ids"] = corrupted.loc[truncate_indices, "paper_id"].astype(str).tolist()
        corrupted.loc[truncate_indices, "title"] = corrupted.loc[truncate_indices, "title"].astype(str).str.slice(0, 24)

    stale_indices = list(range(8, min(11, len(corrupted))))
    if stale_indices:
        log["stale_date_paper_ids"] = corrupted.loc[stale_indices, "paper_id"].astype(str).tolist()
        stale_dates = pd.to_datetime(corrupted.loc[stale_indices, "published"], errors="coerce") - pd.Timedelta(days=3650)
        corrupted.loc[stale_indices, "published"] = stale_dates.dt.date.astype(str)

    duplicate_count = min(2, len(corrupted))
    if duplicate_count:
        duplicates = corrupted.tail(duplicate_count).copy()
        log["duplicated_paper_ids"] = duplicates["paper_id"].astype(str).tolist()
        corrupted = pd.concat([corrupted, duplicates], ignore_index=True)

    corrupted = _rebuild_helpers(corrupted)
    log["output_rows"] = int(len(corrupted))
    write_json(output_log_path, log)
    return corrupted


def _rebuild_helpers(df: pd.DataFrame) -> pd.DataFrame:
    rebuilt = df.copy(deep=True)
    reference_date = datetime.now(UTC).date()
    published = pd.to_datetime(rebuilt["published"], errors="coerce", utc=True)
    rebuilt["age_days"] = published.apply(
        lambda value: max(0, (reference_date - value.date()).days) if not pd.isna(value) else None
    )
    rebuilt["summary"] = rebuilt["summary"].fillna("").astype(str).map(normalize_whitespace)
    rebuilt["title"] = rebuilt["title"].fillna("").astype(str).map(normalize_whitespace)
    rebuilt["summary_chars"] = rebuilt["summary"].str.len()

    if "authors_joined" not in rebuilt.columns:
        rebuilt["authors_joined"] = rebuilt.get("authors", "").map(_join_maybe_list)
    if "categories_joined" not in rebuilt.columns:
        rebuilt["categories_joined"] = rebuilt.get("categories", "").map(_join_maybe_list)

    rebuilt["text_for_embedding"] = rebuilt.apply(
        lambda row: "\n".join(
            [
                f"Title: {row['title']}",
                f"Authors: {row['authors_joined']}",
                f"Published: {row['published']}",
                f"Categories: {row['categories_joined']}",
                f"Abstract: {row['summary']}",
            ]
        ),
        axis=1,
    )
    return rebuilt.reset_index(drop=True)


def _join_maybe_list(value: Any) -> str:
    if isinstance(value, list):
        return compact_join([str(item) for item in value])
    return normalize_whitespace(str(value or ""))
