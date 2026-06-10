from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import html
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, safe_slug, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref works payload into normalized paper records."""
    records: list[PaperRecord] = []
    seen_ids: set[str] = set()

    for item in payload.get("message", {}).get("items", []):
        title = _first_text(item.get("title"))
        summary = _clean_abstract(item.get("abstract", ""))
        doi = normalize_whitespace(str(item.get("DOI", ""))).lower()
        paper_id = doi or safe_slug(title)

        if not paper_id or not title or not summary:
            continue
        if paper_id in seen_ids:
            continue

        authors = _parse_authors(item.get("author", []))
        categories = _parse_categories(item.get("subject", []))
        published = (
            _date_from_parts(item.get("published-print"))
            or _date_from_parts(item.get("published-online"))
            or _date_from_parts(item.get("published"))
            or _date_from_parts(item.get("issued"))
            or _date_from_parts(item.get("created"))
        )
        updated = (
            _date_from_parts(item.get("updated"))
            or _date_from_parts(item.get("deposited"))
            or _date_from_parts(item.get("indexed"))
            or published
        )

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "uncategorized",
                published=published,
                updated=updated,
                abs_url=str(item.get("URL", "")),
                pdf_url=_pdf_url(item.get("link", [])),
                comment=_comment(item),
            )
        )
        seen_ids.add(paper_id)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref works, persist the raw payload, and return parsed records."""
    endpoint = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "sort": "published",
        "order": "desc",
    }
    headers = {"User-Agent": "day10-data-observability-lab/0.1 (mailto:student@example.com)"}

    payload: dict[str, Any] | None = None
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = requests.get(endpoint, params=params, headers=headers, timeout=30)
            if response.status_code in {429, 500, 502, 503, 504}:
                time.sleep(2 * attempt)
                continue
            response.raise_for_status()
            payload = response.json()
            break
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(2 * attempt)

    if payload is None:
        raise RuntimeError(f"Failed to fetch Crossref records: {last_error}")

    write_json(settings.paths.raw_api_response, payload)
    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load previously parsed paper records from JSON."""
    payload = read_json(path)
    records_payload = payload.get("records", payload) if isinstance(payload, dict) else payload
    return [PaperRecord(**item) for item in records_payload]


def _first_text(value: Any) -> str:
    if isinstance(value, list):
        value = next((item for item in value if item), "")
    return normalize_whitespace(html.unescape(str(value or "")))


def _clean_abstract(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(text)


def _parse_authors(value: Any) -> list[str]:
    authors: list[str] = []
    if not isinstance(value, list):
        return authors
    for author in value:
        if not isinstance(author, dict):
            continue
        full_name = author.get("name")
        if not full_name:
            full_name = " ".join(part for part in [author.get("given"), author.get("family")] if part)
        full_name = normalize_whitespace(str(full_name or ""))
        if full_name:
            authors.append(full_name)
    return authors or ["Unknown authors"]


def _parse_categories(value: Any) -> list[str]:
    if not isinstance(value, list):
        return ["uncategorized"]
    categories = [normalize_whitespace(str(item)) for item in value if normalize_whitespace(str(item))]
    return categories or ["uncategorized"]


def _date_from_parts(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    date_parts = value.get("date-parts") or []
    if not date_parts or not isinstance(date_parts[0], list):
        return ""
    parts = [int(part) for part in date_parts[0] if str(part).isdigit()]
    if not parts:
        return ""
    year = parts[0]
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def _pdf_url(links: Any) -> str:
    if not isinstance(links, list):
        return ""
    for link in links:
        if not isinstance(link, dict):
            continue
        url = str(link.get("URL", ""))
        content_type = str(link.get("content-type", "")).lower()
        if url and ("pdf" in content_type or url.lower().endswith(".pdf")):
            return url
    return ""


def _comment(item: dict[str, Any]) -> str:
    container = _first_text(item.get("container-title"))
    publisher = normalize_whitespace(str(item.get("publisher", "")))
    pieces = [piece for piece in [container, publisher] if piece]
    return " | ".join(pieces)
