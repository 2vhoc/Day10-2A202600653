from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run lightweight data quality checks and persist a JSON report."""
    row_count = int(len(df))
    min_rows = min(8, settings.max_results)
    summary_lengths = df.get("summary", pd.Series(dtype=str)).fillna("").astype(str).str.len()
    age_days = pd.to_numeric(df.get("age_days", pd.Series(dtype=float)), errors="coerce")

    checks = [
        _check("row_count_minimum", row_count >= min_rows, {"row_count": row_count, "minimum": min_rows}),
        _check(
            "paper_id_not_null",
            bool(df.get("paper_id", pd.Series(dtype=str)).notna().all()) and row_count > 0,
            {"null_count": int(df.get("paper_id", pd.Series(dtype=str)).isna().sum())},
        ),
        _check(
            "paper_id_unique",
            bool(df.get("paper_id", pd.Series(dtype=str)).is_unique) and row_count > 0,
            {"duplicate_count": int(df.get("paper_id", pd.Series(dtype=str)).duplicated().sum())},
        ),
        _check(
            "title_not_blank",
            _blank_count(df, "title") == 0 and row_count > 0,
            {"blank_count": _blank_count(df, "title")},
        ),
        _check(
            "summary_not_blank",
            _blank_count(df, "summary") == 0 and row_count > 0,
            {"blank_count": _blank_count(df, "summary")},
        ),
        _check(
            "summary_min_length",
            bool((summary_lengths >= 40).all()) and row_count > 0,
            {"too_short_count": int((summary_lengths < 40).sum()), "minimum_chars": 40},
        ),
        _check(
            "freshness_threshold",
            bool((age_days <= settings.freshness_threshold_days).all()) and row_count > 0,
            {
                "stale_count": int((age_days > settings.freshness_threshold_days).sum()),
                "threshold_days": settings.freshness_threshold_days,
            },
        ),
    ]
    failed = [check["name"] for check in checks if not check["passed"]]
    report = {
        "report_name": report_name,
        "row_count": row_count,
        "passed": not failed,
        "failed_checks": failed,
        "checks": checks,
    }
    write_json(settings.paths.quality_dir / f"{report_name}_quality.json", report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build and persist a freshness summary for a dataframe."""
    published = pd.to_datetime(df.get("published", pd.Series(dtype=str)), errors="coerce", utc=True)
    age_days = pd.to_numeric(df.get("age_days", pd.Series(dtype=float)), errors="coerce")
    stale_mask = age_days > settings.freshness_threshold_days

    report = {
        "latest_published": _date_or_none(published.max()),
        "oldest_published": _date_or_none(published.min()),
        "stale_rows": int(stale_mask.sum()),
        "total_rows": int(len(df)),
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": bool(len(df) > 0 and stale_mask.sum() == 0),
    }
    write_json(report_path, report)
    return report


def _check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "details": details}


def _blank_count(df: pd.DataFrame, column: str) -> int:
    if column not in df.columns:
        return len(df)
    return int(df[column].fillna("").astype(str).str.strip().eq("").sum())


def _date_or_none(value) -> str | None:
    if pd.isna(value):
        return None
    return value.date().isoformat()
