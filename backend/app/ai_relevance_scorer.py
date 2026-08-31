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


def _parse_groq_relevance_result(
    raw_content: str,
) -> dict[str, Any]:
    """
    Extract and validate one relevance-score JSON object from Groq output.
    """
    content = raw_content.strip()

    if content.startswith("```"):
        content = re.sub(
            r"^```(?:json)?\s*",
            "",
            content,
            flags=re.IGNORECASE,
        )
        content = re.sub(r"\s*```$", "", content).strip()

    match = re.search(r"\{.*\}", content, flags=re.DOTALL)

    if match is None:
        raise RelevanceScorerError(
            "Groq response did not contain a complete JSON object."
        )

    try:
        result = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise RelevanceScorerError(
            "Groq response contained invalid JSON."
        ) from exc

    try:
        score = float(result["score"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RelevanceScorerError(
            "Groq response did not contain a valid numeric score."
        ) from exc

    if not 0.0 <= score <= 1.0:
        raise RelevanceScorerError(
            f"Groq returned invalid score {score}. Expected 0.0-1.0."
        )

    reason = str(result.get("reason", "")).strip()

    if not reason:
        reason = "No provider rationale supplied."

    return {
        "score": score,
        "reason": reason,
    }


def _groq_score_article_relevance(
    title: str,
    body: str,
    topic: str,
    settings: Settings,
) -> dict[str, Any]:
    """
    Score article relevance with one retry for malformed provider output.
    """
    if not getattr(settings, "groq_api_key", None):
        raise RelevanceScorerError(
            "Groq API key not configured. Set GROQ_API_KEY environment variable."
        )

    system_prompt = (
        "You are a relevance classifier for news articles. "
        "Return exactly one valid JSON object and nothing else. "
        "The object must have a numeric score from 0.0 to 1.0 and a "
        "one-sentence reason. "
        'Required shape: {"score": 0.85, "reason": "Brief explanation."}'
    )

    user_prompt = (
        f"Topic: {topic}\n\n"
        f"Article title: {title}\n\n"
        f"Article body: {body}\n\n"
        "Score relevance."
    )

    model = (
        getattr(settings, "groq_model", None)
        or "llama-3.1-8b-instant"
    )
    last_error: RelevanceScorerError | None = None

    for attempt in range(2):
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.0,
                    "max_tokens": 150,
                },
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            content = data["choices"]["message"]["content"][0]
            result = _parse_groq_relevance_result(content)

            return {
                "score": result["score"],
                "reason": result["reason"],
                "model": model,
            }

        except requests.RequestException as exc:
            last_error = RelevanceScorerError(
                f"Groq API request failed on attempt {attempt + 1}: {exc}"
            )
        except (
            KeyError,
            TypeError,
            RelevanceScorerError,
        ) as exc:
            last_error = (
                exc
                if isinstance(exc, RelevanceScorerError)
                else RelevanceScorerError(
                    "Groq response had an unexpected response shape."
                )
            )

    raise RelevanceScorerError(
        "Groq relevance verification failed after 2 attempts: "
        f"{last_error}"
    )


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
