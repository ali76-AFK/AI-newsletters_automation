#!/usr/bin/env python3
"""
Test script for AI workflow orchestration.

Demonstrates:
- Article scoring
- Newsletter generation
- Send decision logic
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai_workflow_orchestrator import (
    _score_articles,
    _select_top_articles,
    _assess_send_decision,
    ScoredArticle,
)
from app.news_ingestion import get_articles


def test_article_scoring():
    """Test AI relevance scoring."""
    print("=" * 60)
    print("TEST: Article Scoring")
    print("=" * 60)
    
    try:
        articles = get_articles(source="spiegel_wissenschaft_technik", topic="ai_news")
        print(f"Fetched {len(articles)} articles\n")
        
        scored = _score_articles(articles, "ai_news")
        print(f"Scored {len(scored)} articles:\n")
        
        for i, s in enumerate(scored, 1):
            print(f"{i}. {s.article.title}")
            print(f"   Score: {s.score:.2f}")
            print(f"   Reason: {s.reason}\n")
        
        selected = _select_top_articles(scored, max_articles=3)
        print(f"Selected {len(selected)} articles above threshold\n")
        
    except Exception as exc:
        print(f"Error: {exc}\n")


def test_send_decision():
    """Test automated send decision logic."""
    print("=" * 60)
    print("TEST: Send Decision Logic")
    print("=" * 60)
    
    test_cases = [
        # (risk_level, avg_relevance, article_count, expected_decision)
        ("low", 0.85, 3, "send"),
        ("low", 0.65, 2, "send"),
        ("medium", 0.70, 2, "review"),
        ("high", 0.90, 3, "review"),
        ("critical", 0.95, 3, "review"),
        ("low", 0.50, 1, "skip"),
        ("low", 0.40, 0, "skip"),
    ]
    
    print("\nDecision Rules:\n")
    print("Risk Level | Avg Relevance | Articles | → Decision")
    print("-" * 60)
    
    for risk, relevance, count, expected in test_cases:
        decision = _assess_send_decision(risk, relevance, count)
        status = "✓" if decision == expected else "✗"
        print(f"{status} {risk:10} | {relevance:.2f}          | {count:8} | → {decision}")
    
    print()


def main():
    print("\nAI Workflow Orchestration Test Suite\n")
    print("=" * 60)
    
    test_article_scoring()
    test_send_decision()
    
    print("=" * 60)
    print("Tests completed!\n")


if __name__ == "__main__":
    main()
