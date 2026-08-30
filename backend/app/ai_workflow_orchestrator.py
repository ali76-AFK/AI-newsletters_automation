"""
AI Workflow Orchestrator

Enhanced LangGraph workflow with:
- AI scoring for content selection
- AI-driven draft generation from multiple articles
- Automated send decisions based on risk + relevance
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Literal

from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from .ai_relevance_scorer import score_article_relevance, RelevanceScorerError
from .ai_newsletter_service import classify_newsletter_text, AIServiceError
from .config import load_settings
from .langgraph_state import WorkflowState, DraftSummary, SubscriberState, SendSummary
from .models import (
    Newsletter,
    Subscriber,
    SubscriberTopic,
    DraftEmail,
    WorkflowExecution,
    ScheduleRun,
)
from .news_ingestion import NewsArticle, get_articles
from .email_sender import send_email, EmailSendError


class WorkflowOrchestratorError(Exception):
    pass


@dataclass
class ScoredArticle:
    article: NewsArticle
    score: float
    reason: str


RELEVANCE_THRESHOLD = 0.6  # Minimum score to include article
HIGH_RELEVANCE_THRESHOLD = 0.8  # Score above this is "highly relevant"


def _score_articles(
    articles: list[NewsArticle],
    topic: str,
) -> list[ScoredArticle]:
    """Score articles using AI relevance scorer."""
    settings = load_settings()
    scored: list[ScoredArticle] = []

    for article in articles:
        try:
            result = score_article_relevance(
                title=article.title,
                body=article.body,
                topic=topic,
                settings=settings,
            )
            scored.append(
                ScoredArticle(
                    article=article,
                    score=result["score"],
                    reason=result["reason"],
                )
            )
        except RelevanceScorerError as exc:
            # Log but continue with other articles
            print(f"Scoring failed for {article.title}: {exc}")

    # Sort by score descending
    scored.sort(key=lambda x: x.score, reverse=True)
    return scored


def _select_top_articles(
    scored: list[ScoredArticle],
    max_articles: int = 3,
) -> list[ScoredArticle]:
    """Select top articles above relevance threshold."""
    relevant = [s for s in scored if s.score >= RELEVANCE_THRESHOLD]
    return relevant[:max_articles]


def _generate_newsletter_content(
    articles: list[ScoredArticle],
    topic: str,
) -> dict[str, str]:
    """
    Generate newsletter title and body from multiple articles using AI.
    """
    settings = load_settings()

    if settings.llm_provider.lower() == "mock":
        # Mock: use first article
        if not articles:
            raise WorkflowOrchestratorError("No articles to generate newsletter from")
        top = articles[0]
        return {
            "title": f"Top {topic.replace('_', ' ').title()}: {top.article.title}",
            "body": top.article.body,
        }

    # Build prompt with top articles
    article_summaries = []
    for i, scored in enumerate(articles, 1):
        article_summaries.append(
            f"{i}. {scored.article.title}\n"
            f"   {scored.article.body[:300]}\n"
            f"   Relevance: {scored.score:.2f} ({scored.reason})\n"
        )

    system_prompt = (
        "You are a newsletter editor. Create a concise, engaging newsletter "
        "from the provided articles. Return JSON with 'title' and 'body' keys."
    )

    user_prompt = (
        f"Topic: {topic}\n\n"
        f"Articles:\n\n{''.join(article_summaries)}\n\n"
        "Create a newsletter with:\n"
        "- A compelling title\n"
        "- A body that synthesizes the key points from multiple articles\n"
        "- Keep it under 500 words\n"
        "Return JSON: {\"title\": \"...\", \"body\": \"...\"}"
    )

    try:
        from .ai_newsletter_service import _llm_call
        raw = _llm_call(user_prompt, system=system_prompt)

        # Extract JSON
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            return {
                "title": data.get("title", "Newsletter"),
                "body": data.get("body", ""),
            }
        else:
            raise WorkflowOrchestratorError("Failed to parse AI newsletter JSON")

    except Exception as exc:
        raise WorkflowOrchestratorError(f"AI generation failed: {exc}") from exc


def _assess_send_decision(
    risk_level: str,
    avg_relevance: float,
    article_count: int,
) -> Literal["send", "review", "skip"]:
    """
    Decide whether to send, hold for review, or skip based on risk + relevance.

    Rules:
    - High/critical risk → always review
    - Low risk + high relevance (≥0.8) + ≥2 articles → auto-send
    - Low/medium risk + moderate relevance (≥0.6) → auto-send
    - Low relevance (<0.6) or no articles → skip
    """
    if risk_level in {"high", "critical"}:
        return "review"

    if avg_relevance < RELEVANCE_THRESHOLD or article_count == 0:
        return "skip"

    if avg_relevance >= HIGH_RELEVANCE_THRESHOLD and article_count >= 2:
        return "send"

    if risk_level == "low":
        return "send"

    # Medium risk with moderate relevance
    return "review"


def build_ai_workflow_graph(db: Session) -> StateGraph[WorkflowState]:
    """
    Build enhanced workflow with AI scoring and generation.
    """
    graph = StateGraph(WorkflowState)

    def score_and_select_node(state: WorkflowState) -> WorkflowState:
        """Score articles and select top ones."""
        newsletter = db.get(Newsletter, state.newsletter_id)
        if newsletter is None:
            raise WorkflowOrchestratorError(f"Newsletter {state.newsletter_id} not found")

        # Fetch fresh articles for this topic
        try:
            articles = get_articles(
                source=newsletter.source,
                topic=state.topic or newsletter.topic,
            )
        except Exception as exc:
            raise WorkflowOrchestratorError(f"Failed to fetch articles: {exc}") from exc

        # Score articles
        scored = _score_articles(articles, state.topic or newsletter.topic)

        # Select top articles
        selected = _select_top_articles(scored, max_articles=3)

        if not selected:
            raise WorkflowOrchestratorError(
                f"No articles above relevance threshold ({RELEVANCE_THRESHOLD})"
            )

        # Store in state for next node
        state.ai_selected_articles = selected
        state.ai_avg_relevance = sum(s.score for s in selected) / len(selected)

        return state

    def generate_newsletter_node(state: WorkflowState) -> WorkflowState:
        """Generate newsletter content from selected articles."""
        newsletter = db.get(Newsletter, state.newsletter_id)
        if newsletter is None:
            raise WorkflowOrchestratorError(f"Newsletter {state.newsletter_id} not found")

        if not hasattr(state, "ai_selected_articles") or not state.ai_selected_articles:
            raise WorkflowOrchestratorError("No articles selected for generation")

        # Generate content
        content = _generate_newsletter_content(
            state.ai_selected_articles,
            state.topic or newsletter.topic,
        )

        # Update newsletter
        newsletter.title = content["title"]
        newsletter.body = content["body"]
        db.flush()

        return state

    def classify_and_decide_node(state: WorkflowState) -> WorkflowState:
        """Classify risk and decide send/review/skip."""
        newsletter = db.get(Newsletter, state.newsletter_id)
        if newsletter is None:
            raise WorkflowOrchestratorError(f"Newsletter {state.newsletter_id} not found")

        # Classify risk
        try:
            classification = classify_newsletter_text(
                newsletter.title,
                newsletter.body,
            )
        except AIServiceError as exc:
            raise WorkflowOrchestratorError(f"Classification failed: {exc}") from exc

        newsletter.risk_level = classification["risk_level"]
        newsletter.risk_reason = classification["reason"]

        # Decide
        avg_relevance = getattr(state, "ai_avg_relevance", 0.5)
        article_count = len(getattr(state, "ai_selected_articles", []))

        decision = _assess_send_decision(
            risk_level=classification["risk_level"],
            avg_relevance=avg_relevance,
            article_count=article_count,
        )

        state.ai_send_decision = decision

        if decision == "skip":
            newsletter.status = "skipped"
            newsletter.approved = False
        elif decision == "review":
            newsletter.status = "pending_review"
            newsletter.approved = False
        elif decision == "send":
            newsletter.status = "approved"
            newsletter.approved = True

        db.flush()
        return state

    def load_subscribers_node(state: WorkflowState) -> WorkflowState:
        """Load subscribers for the topic."""
        if state.topic is None:
            raise WorkflowOrchestratorError("Topic not set in state")

        subscribers: List[Subscriber] = (
            db.query(Subscriber)
            .join(SubscriberTopic)
            .filter(
                Subscriber.is_active.is_(True),
                SubscriberTopic.topic == state.topic,
            )
            .order_by(Subscriber.created_at.desc())
            .all()
        )

        if not subscribers:
            raise WorkflowOrchestratorError("No active subscribers for this topic")

        state.subscribers = [
            SubscriberState(
                id=sub.id,
                email=sub.email,
                name=sub.name,
            )
            for sub in subscribers
        ]

        return state

    def create_drafts_node(state: WorkflowState) -> WorkflowState:
        """Create personalized drafts using AI."""
        newsletter = db.get(Newsletter, state.newsletter_id)
        if newsletter is None:
            raise WorkflowOrchestratorError(f"Newsletter {state.newsletter_id} not found")

        if not newsletter.approved:
            raise WorkflowOrchestratorError(
                "Newsletter not approved; cannot create drafts"
            )

        created: List[DraftSummary] = []

        for sub_state in state.subscribers:
            # Personalize using AI
            from .ai_newsletter_service import refine_newsletter_draft

            refined = refine_newsletter_draft(
                base_subject=newsletter.title,
                base_body=newsletter.body,
                subscriber_name=sub_state.name,
            )

            subject = refined["subject"]
            body = refined["body"]

            existing = (
                db.query(DraftEmail)
                .filter(
                    DraftEmail.newsletter_id == newsletter.id,
                    DraftEmail.subscriber_id == sub_state.id,
                )
                .first()
            )

            if existing:
                existing.subject = subject
                existing.body = body
                draft = existing
            else:
                draft = DraftEmail(
                    newsletter_id=newsletter.id,
                    subscriber_id=sub_state.id,
                    subject=subject,
                    body=body,
                    status="draft",
                )
                db.add(draft)

            db.flush()
            created.append(
                DraftSummary(
                    id=draft.id,
                    subscriber_id=sub_state.id,
                    subject=subject,
                )
            )

        state.created_drafts = created
        return state

    def send_node(state: WorkflowState) -> WorkflowState:
        """Send newsletters."""
        newsletter = db.get(Newsletter, state.newsletter_id)
        if newsletter is None:
            raise WorkflowOrchestratorError(f"Newsletter {state.newsletter_id} not found")

        if not newsletter.approved:
            raise WorkflowOrchestratorError("Newsletter not approved; cannot send")

        sender = "newsletter-orchestrator@example.com"
        recipients = [s.email for s in state.subscribers]
        subject = newsletter.title
        body = newsletter.body

        try:
            send_email(sender, recipients, subject, body)
        except EmailSendError as exc:
            raise WorkflowOrchestratorError(f"Email sending failed: {exc}") from exc

        state.send_summary = SendSummary(
            sender=sender,
            recipients=recipients,
            subject=subject,
            count=len(recipients),
        )
        return state

    def update_state_node(state: WorkflowState) -> WorkflowState:
        """Update workflow and newsletter state."""
        wf = db.query(WorkflowExecution).filter(
            WorkflowExecution.newsletter_id == state.newsletter_id
        ).first()

        newsletter = db.get(Newsletter, state.newsletter_id)

        if wf is None or newsletter is None:
            raise WorkflowOrchestratorError("Workflow or newsletter not found")

        wf.state = "completed"
        wf.completed_at = datetime.utcnow()
        newsletter.status = "sent"
        db.flush()

        return state

    # Add nodes
    graph.add_node("score_and_select", score_and_select_node)
    graph.add_node("generate_newsletter", generate_newsletter_node)
    graph.add_node("classify_and_decide", classify_and_decide_node)
    graph.add_node("load_subscribers", load_subscribers_node)
    graph.add_node("create_drafts", create_drafts_node)
    graph.add_node("send", send_node)
    graph.add_node("update_state", update_state_node)

    # Define edges
    graph.set_entry_point("score_and_select")
    graph.add_edge("score_and_select", "generate_newsletter")
    graph.add_edge("generate_newsletter", "classify_and_decide")

    # Conditional routing based on decision
    def route_after_decision(state: WorkflowState) -> str:
        decision = getattr(state, "ai_send_decision", "skip")
        if decision == "skip":
            return "update_state"  # Skip to end
        elif decision == "review":
            return "update_state"  # Wait for human review
        elif decision == "send":
            return "load_subscribers"
        return "update_state"

    graph.add_conditional_edges(
        "classify_and_decide",
        route_after_decision,
    )

    graph.add_edge("load_subscribers", "create_drafts")
    graph.add_edge("create_drafts", "send")
    graph.add_edge("send", "update_state")
    graph.add_edge("update_state", END)

    return graph
