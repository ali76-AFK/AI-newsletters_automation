from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import requests

from .config import Settings


class RelevanceScorerError(Exception):
    """Raised when relevance scoring fails."""


def _article_hash(title: str, body: str, topic: str) -> str:
    """Create a deterministic hash for caching."""
    raw = f"{title}|{body}|{topic}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _word_boundary_match(text: str, keyword: str) -> bool:
    """Check if keyword appears as a whole word (not substring)."""
    pattern = rf"\b{re.escape(keyword)}\b"
    return re.search(pattern, text, re.IGNORECASE) is not None


def _mock_score_article_relevance(
    title: str,
    body: str,
    topic: str,
) -> dict[str, Any]:
    """
    Deterministic mock scorer for offline development.

    Returns scores based on simple keyword heuristics.
    """
    text = f"{title} {body}".lower()

    # AI/ML topics
    if topic == "ai_news":
        if any(_word_boundary_match(text, kw) for kw in ["ai", "machine learning", "language model", "neural"]):
            return {
                "score": 0.9,
                "reason": "Mock: AI/ML keywords detected",
                "model": "mock",
            }
        else:
            return {
                "score": 0.3,
                "reason": "Mock: Low relevance to AI topic",
                "model": "mock",
            }

    # Business topics
    elif topic == "business":
        if any(_word_boundary_match(text, kw) for kw in ["economy", "market", "industry", "company"]):
            return {
                "score": 0.8,
                "reason": "Mock: Business keywords detected",
                "model": "mock",
            }
        else:
            return {
                "score": 0.4,
                "reason": "Mock: Weak business relevance",
                "model": "mock",
            }

    # World news topics
    elif topic == "world_news":
        if any(_word_boundary_match(text, kw) for kw in ["government", "international", "policy", "summit"]):
            return {
                "score": 0.85,
                "reason": "Mock: World news keywords detected",
                "model": "mock",
            }
        else:
            return {
                "score": 0.5,
                "reason": "Mock: General news content",
                "model": "mock",
            }

    # Default: moderate score for unknown topics
    return {
        "score": 0.5,
        "reason": f"Mock: Default score for topic '{topic}'",
        "model": "mock",
    }


def _groq_score_article_relevance(
    title: str,
    body: str,
    topic: str,
    settings: Settings,
) -> dict[str, Any]:
    """
    Score article relevance using Groq API.

    Returns score (0-1), reason, and model used.
    """
    if not getattr(settings, "groq_api_key", None):
        raise RelevanceScorerError(
            "Groq API key not configured. Set GROQ_API_KEY environment variable."
        )

    system_prompt = (
        "You are a relevance classifier for news articles. "
        "Score how relevant an article is to a given topic on a scale from 0.0 (not relevant) to 1.0 (highly relevant). "
        "Return JSON only with the following structure: "
        '{"score": 0.85, "reason": "Brief explanation (1 sentence)"}'
    )

    user_prompt = (
        f"Topic: {topic}\n\n"
        f"Article title: {title}\n\n"
        f"Article body: {body}\n\n"
        "Score relevance."
    )

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": getattr(settings, "groq_model", None) or "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,  # Low temperature for consistency
                "max_tokens": 150,
            },
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        # Parse JSON response
        try:
            result = json.loads(content)
            score = float(result.get("score", 0.5))
            reason = result.get("reason", "No reason provided")
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            raise RelevanceScorerError(
                f"Failed to parse Groq response as JSON: {content}"
            ) from exc

        # Validate score range
        if not (0.0 <= score <= 1.0):
            raise RelevanceScorerError(
                f"Groq returned invalid score {score}. Expected 0.0-1.0."
            )

        return {
            "score": score,
            "reason": reason,
            "model": getattr(settings, "groq_model", None) or "llama-3.1-8b-instant",
        }

    except requests.RequestException as exc:
        raise RelevanceScorerError(f"Groq API request failed: {exc}") from exc


def score_article_relevance(
    title: str,
    body: str,
    topic: str,
    settings: Settings,
) -> dict[str, Any]:
    """
    Score article relevance using configured AI provider.

    Args:
        title: Article title.
        body: Article body text.
        topic: Target topic (e.g., "ai_news", "business").
        settings: App settings with AI provider configuration.

    Returns:
        dict with keys:
            - score: float (0.0-1.0)
            - reason: str (explanation)
            - model: str (provider/model used)

    Raises:
        RelevanceScorerError: If scoring fails.
    """
    provider = getattr(settings, "llm_provider", "mock").lower()

    if provider == "mock":
        return _mock_score_article_relevance(title, body, topic)

    elif provider == "groq":
        return _groq_score_article_relevance(title, body, topic, settings)

    else:
        raise RelevanceScorerError(
            f"Unsupported LLM provider for relevance scoring: '{provider}'. "
            "Supported: 'mock', 'groq'."
        )
