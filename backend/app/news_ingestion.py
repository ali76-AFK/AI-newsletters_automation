from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from typing import Iterable
from urllib.parse import urlparse

import feedparser
import requests

from .config import load_settings


class NewsIngestionError(Exception):
    pass


@dataclass(frozen=True)
class NewsArticle:
    source: str
    external_id: str
    url: str
    published_at: str
    topic: str
    title: str
    body: str

    @property
    def content_hash(self) -> str:
        raw = (
            f"{self.source}|{self.external_id}|{self.url}|"
            f"{self.title}|{self.body}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


STUB_ARTICLES: tuple[NewsArticle, ...] = (
    NewsArticle(
        source="spiegel_wissenschaft_technik",
        external_id="spiegel-ai-001",
        url="https://example.invalid/spiegel/ai-001",
        published_at="2026-08-17T08:00:00Z",
        topic="ai_news",
        title="AI research collaboration highlights",
        body=(
            "A research consortium published a summary of its latest work on "
            "evaluating language-model reliability. The report describes test "
            "methodology, limitations, and plans for independent replication."
        ),
    ),
    NewsArticle(
        source="spiegel_wissenschaft_technik",
        external_id="spiegel-ai-002",
        url="https://example.invalid/spiegel/ai-002",
        published_at="2026-08-17T10:00:00Z",
        topic="ai_news",
        title="New dataset supports AI safety research",
        body=(
            "Researchers released documentation for a benchmark dataset used "
            "to evaluate factual consistency in generated summaries. The "
            "documentation includes known limitations and licensing details."
        ),
    ),
    NewsArticle(
        source="spiegel_wissenschaft_technik",
        external_id="spiegel-ai-003",
        url="https://example.invalid/spiegel/ai-003",
        published_at="2026-08-17T12:00:00Z",
        topic="ai_news",
        title="Public consultation on AI transparency opens",
        body=(
            "A public consultation invites comments on transparency practices "
            "for automated systems. The announcement describes the submission "
            "process and the consultation timetable."
        ),
    ),
    # Business stub articles
    NewsArticle(
        source="spiegel_wirtschaft",
        external_id="spiegel-business-001",
        url="https://example.invalid/spiegel/business-001",
        published_at="2026-08-17T09:00:00Z",
        topic="business",
        title="German manufacturing orders rise in Q3",
        body=(
            "Industry associations reported a moderate increase in new orders "
            "for manufactured goods. Analysts cite stabilizing demand and "
            "improved supply-chain conditions as key factors."
        ),
    ),
    NewsArticle(
        source="spiegel_wirtschaft",
        external_id="spiegel-business-002",
        url="https://example.invalid/spiegel/business-002",
        published_at="2026-08-17T11:00:00Z",
        topic="business",
        title="Energy prices stabilize after volatile quarter",
        body=(
            "Wholesale energy prices showed reduced volatility in recent "
            "trading sessions. Market participants point to diversified "
            "supply sources and strategic reserve management."
        ),
    ),
    NewsArticle(
        source="spiegel_wirtschaft",
        external_id="spiegel-business-003",
        url="https://example.invalid/spiegel/business-003",
        published_at="2026-08-17T13:00:00Z",
        topic="business",
        title="Tech sector hiring remains resilient",
        body=(
            "Despite broader economic uncertainty, technology companies "
            "continued to post job openings in engineering and product "
            "roles. Recruiters highlight demand for automation expertise."
        ),
    ),
    # World news stub articles (ausland)
    NewsArticle(
        source="spiegel_ausland",
        external_id="spiegel-world-001",
        url="https://example.invalid/spiegel/world-001",
        published_at="2026-08-17T08:30:00Z",
        topic="world_news",
        title="EU summit addresses migration policy",
        body=(
            "Leaders discussed burden-sharing mechanisms and border-control "
            "coordination. The final communique emphasized humanitarian "
            "standards and regional cooperation."
        ),
    ),
    NewsArticle(
        source="spiegel_ausland",
        external_id="spiegel-world-002",
        url="https://example.invalid/spiegel/world-002",
        published_at="2026-08-17T10:30:00Z",
        topic="world_news",
        title="Climate talks focus on adaptation funding",
        body=(
            "Negotiators reviewed proposals for a dedicated adaptation fund "
            "to support vulnerable regions. Discussions included governance "
            "structures and disbursement criteria."
        ),
    ),
    NewsArticle(
        source="spiegel_ausland",
        external_id="spiegel-world-003",
        url="https://example.invalid/spiegel/world-003",
        published_at="2026-08-17T12:30:00Z",
        topic="world_news",
        title="Trade delegation visits Southeast Asia",
        body=(
            "A high-level delegation met with counterparts to discuss trade "
            "facilitation and regulatory alignment. The visit included "
            "roundtables on digital economy and logistics."
        ),
    ),
    # World news stub articles (politik)
    NewsArticle(
        source="spiegel_politik",
        external_id="spiegel-politik-001",
        url="https://example.invalid/spiegel/politik-001",
        published_at="2026-08-17T09:30:00Z",
        topic="world_news",
        title="Coalition talks enter final phase",
        body=(
            "Party leaders reported progress on key policy areas including "
            "fiscal rules and infrastructure investment. A joint statement "
            "is expected within days."
        ),
    ),
    NewsArticle(
        source="spiegel_politik",
        external_id="spiegel-politik-002",
        url="https://example.invalid/spiegel/politik-002",
        published_at="2026-08-17T11:30:00Z",
        topic="world_news",
        title="Parliament debates electoral reform",
        body=(
            "Proposed changes to the electoral system sparked discussions on "
            "representation thresholds and district boundaries. Legal experts "
            "weighed in on constitutional implications."
        ),
    ),
    NewsArticle(
        source="spiegel_politik",
        external_id="spiegel-politik-003",
        url="https://example.invalid/spiegel/politik-003",
        published_at="2026-08-17T13:30:00Z",
        topic="world_news",
        title="Defense budget review underway",
        body=(
            "A parliamentary committee began examining defense spending "
            "priorities. Testimony covered procurement timelines and "
            "international cooperation frameworks."
        ),
    ),
)

SPIEGEL_TECH_RSS = (
    "https://www.spiegel.de/wissenschaft/technik/index.rss"
)

RSS_SOURCE_ALLOWLIST = {
    # Technology/Science feed (existing)
    "spiegel_wissenschaft_technik": {
        "ai_news": "https://www.spiegel.de/wissenschaft/technik/index.rss",
        "robotics": "https://www.spiegel.de/wissenschaft/technik/index.rss",
        "data_eng": "https://www.spiegel.de/wissenschaft/technik/index.rss",
        "devops": "https://www.spiegel.de/wissenschaft/technik/index.rss",
        "llm_workflows": "https://www.spiegel.de/wissenschaft/technik/index.rss",
        "technology_science": "https://www.spiegel.de/wissenschaft/technik/index.rss",
    },
    # Business feed
    "spiegel_wirtschaft": {
        "business": "https://www.spiegel.de/wirtschaft/index.rss",
    },
    # World news feeds
    "spiegel_ausland": {
        "world_news": "https://www.spiegel.de/ausland/index.rss",
    },
    "spiegel_politik": {
        "world_news": "https://www.spiegel.de/politik/index.rss",
    },
}

TOPIC_KEYWORDS = {
    "ai_news": (
        "ai",
        "ki",
        "artificial intelligence",
        "künstliche intelligenz",
        "machine learning",
        "maschinelles lernen",
        "algorithm",
        "modell",
        "model",
        "neural",
    ),
    "robotics": (
        "robot",
        "robotik",
        "robotics",
        "autonomous",
        "autonom",
        "drone",
    ),
    "data_eng": (
        "data",
        "daten",
        "database",
        "datenbank",
        "analytics",
        "analyse",
        "data platform",
        "datenplattform",
    ),
    "devops": (
        "devops",
        "cloud",
        "kubernetes",
        "container",
        "infrastructure",
        "infrastruktur",
        "deployment",
    ),
    "llm_workflows": (
        "llm",
        "large language model",
        "language model",
        "sprachmodell",
        "rag",
        "retrieval augmented",
        "prompt",
        "agent",
        "workflow",
    ),
    "technology_science": (),
    "business": (),
    "world_news": (),
}

MAX_RSS_ENTRIES = 15
MAX_RSS_RESPONSE_BYTES = 1_000_000
RSS_TIMEOUT_SECONDS = 10
RSS_USER_AGENT = "newsletter-orchestrator/0.5 (+local development)"


def get_stub_articles(
    source: str | None = None,
    topic: str | None = None,
) -> list[NewsArticle]:
    articles: Iterable[NewsArticle] = STUB_ARTICLES

    if source:
        articles = (
            article
            for article in articles
            if article.source.lower() == source.lower()
        )

    if topic:
        articles = (
            article
            for article in articles
            if article.topic == topic
        )

    return list(articles)


def _safe_text(value: object) -> str:
    if value is None:
        return ""

    text = str(value)
    return " ".join(unescape(text).split())


def _validated_rss_url(source: str, topic: str) -> str:
    source_mapping = RSS_SOURCE_ALLOWLIST.get(source)

    if source_mapping is None:
        raise NewsIngestionError(
            f"RSS source is not allowlisted: {source!r}"
        )

    feed_url = source_mapping.get(topic)

    if feed_url is None:
        raise NewsIngestionError(
            f"RSS topic is not allowlisted for {source!r}: {topic!r}"
        )

    parsed = urlparse(feed_url)

    if parsed.scheme != "https" or not parsed.netloc:
        raise NewsIngestionError(
            "RSS allowlist contains an invalid HTTPS URL."
        )

    return feed_url


def _entry_timestamp(entry: object) -> str:
    published = getattr(entry, "published", None)
    updated = getattr(entry, "updated", None)

    timestamp = _safe_text(published or updated)

    if timestamp:
        return timestamp

    return datetime.now(timezone.utc).isoformat()


def _keyword_matches(
    text: str,
    keyword: str,
) -> bool:
    pattern = rf"(?<!\w){re.escape(keyword.lower())}(?!\w)"
    return re.search(pattern, text.lower()) is not None


def is_relevant_for_topic(
    article: NewsArticle,
    topic: str,
    settings: Settings | None = None,
) -> bool:
    """
    Check if article is relevant to topic using AI scoring.

    For technology_science, always return True (broad routing).
    For other topics, use AI relevance scorer if settings provided,
    otherwise fall back to keyword matching for backward compatibility.
    """
    if topic == "technology_science":
        return True

    # Use AI scoring if settings provided
    if settings is not None:
        from .ai_relevance_scorer import score_article_relevance

        result = score_article_relevance(
            title=article.title,
            body=article.body,
            topic=topic,
            settings=settings,
        )

        # Default threshold: 0.7
        threshold = getattr(settings, "relevance_threshold", 0.7)
        return result["score"] >= threshold

    # Fallback to keyword matching for backward compatibility
    keywords = TOPIC_KEYWORDS.get(topic)

    if keywords is None:
        return False

    haystack = f"{article.title} {article.body}"

    return any(
        _keyword_matches(haystack, keyword)
        for keyword in keywords
    )


def filter_relevant_articles(
    articles: list[NewsArticle],
    topic: str,
    settings: Settings | None = None,
) -> list[NewsArticle]:
    return [
        article
        for article in articles
        if is_relevant_for_topic(article, topic, settings)
    ]


def fetch_rss_articles(
    source: str,
    topic: str,
) -> list[NewsArticle]:
    feed_url = _validated_rss_url(source, topic)
    settings = load_settings()

    try:
        response = requests.get(
            feed_url,
            headers={"User-Agent": RSS_USER_AGENT},
            timeout=RSS_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise NewsIngestionError(
            f"RSS fetch failed for {source!r}: {exc}"
        ) from exc

    content = response.content

    if len(content) > MAX_RSS_RESPONSE_BYTES:
        raise NewsIngestionError(
            f"RSS response exceeded {MAX_RSS_RESPONSE_BYTES} bytes."
        )

    parsed_feed = feedparser.parse(content)

    if parsed_feed.bozo and not parsed_feed.entries:
        raise NewsIngestionError(
            f"RSS parsing failed for {source!r}."
        )

    articles: list[NewsArticle] = []

    for entry in parsed_feed.entries[:MAX_RSS_ENTRIES]:
        url = _safe_text(getattr(entry, "link", None))

        if not url:
            continue

        parsed_url = urlparse(url)

        if parsed_url.scheme != "https" or not parsed_url.netloc:
            continue

        title = _safe_text(getattr(entry, "title", None))
        summary = _safe_text(
            getattr(entry, "summary", None)
            or getattr(entry, "description", None)
        )

        if not title or not summary:
            continue

        external_id = _safe_text(
            getattr(entry, "id", None)
            or getattr(entry, "guid", None)
            or url
        )

        articles.append(
            NewsArticle(
                source=source,
                external_id=external_id,
                url=url,
                published_at=_entry_timestamp(entry),
                topic=topic,
                title=title,
                body=summary,
            )
        )

    return filter_relevant_articles(articles, topic, settings)


def get_articles(
    source: str | None = None,
    topic: str | None = None,
) -> list[NewsArticle]:
    if not source or not topic:
        raise NewsIngestionError(
            "Source and topic are required for article retrieval."
        )

    settings = load_settings()
    mode = settings.news_source_mode.strip().lower()

    if mode == "stub":
        return get_stub_articles(source=source, topic=topic)

    if mode == "rss":
        return fetch_rss_articles(source=source, topic=topic)

    raise NewsIngestionError(
        f"Unsupported NEWS_SOURCE_MODE: {mode!r}. "
        "Use 'stub' or 'rss'."
    )


def build_stub_newsletter_content(
    source: str,
    topic: str,
) -> dict[str, str]:
    articles = get_stub_articles(source=source, topic=topic)

    if not articles:
        raise NewsIngestionError(
            f"No local stub articles for "
            f"source={source!r}, topic={topic!r}."
        )

    article = articles[0]

    return {
        "title": article.title,
        "body": article.body,
        "source": article.source,
        "source_external_id": article.external_id,
        "source_url": article.url,
        "content_hash": article.content_hash,
        "published_at": article.published_at,
    }
