from __future__ import annotations

from sqlalchemy.orm import Session

from .models import SourceDocument
from .news_ingestion import NewsArticle


def upsert_source_document(
    db: Session,
    article: NewsArticle,
    publisher: str | None = None,
) -> SourceDocument:
    document = (
        db.query(SourceDocument)
        .filter(
            SourceDocument.source == article.source,
            SourceDocument.source_external_id == article.external_id,
        )
        .first()
    )

    if document is None:
        document = SourceDocument(
            source=article.source,
            source_external_id=article.external_id,
            publisher=publisher,
            canonical_url=article.url,
            published_at=_parse_datetime(article.published_at),
            title=article.title,
            normalized_text=article.body,
            content_hash=article.content_hash,
            source_metadata_json="{}",
        )
        db.add(document)
        db.flush()
        return document

    document.publisher = publisher
    document.canonical_url = article.url
    document.published_at = _parse_datetime(article.published_at)
    document.title = article.title
    document.normalized_text = article.body
    document.content_hash = article.content_hash
    db.flush()

    return document


def _parse_datetime(value: str):
    from email.utils import parsedate_to_datetime
    from datetime import datetime, timezone

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = parsedate_to_datetime(value)

    if parsed.tzinfo is None:
        raise ValueError("Source document publication time must be timezone-aware.")

    return parsed.astimezone(timezone.utc).replace(tzinfo=None)
