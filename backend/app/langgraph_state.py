from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel


class SubscriberState(BaseModel):
    id: int
    email: str
    name: Optional[str] = None


class DraftSummary(BaseModel):
    id: int
    subscriber_id: Optional[int] = None
    subject: str


class SendSummary(BaseModel):
    sender: str
    recipients: List[str]
    subject: str
    count: int


class WorkflowState(BaseModel):
    newsletter_id: int
    workflow_id: int
    topic: Optional[str] = None
    subscribers: List[SubscriberState] = []
    created_drafts: List[DraftSummary] = []
    send_summary: Optional[SendSummary] = None

    # AI workflow fields
    ai_selected_articles: Optional[List[Any]] = None
    ai_avg_relevance: Optional[float] = None
    ai_send_decision: Optional[Literal["send", "review", "skip"]] = None
