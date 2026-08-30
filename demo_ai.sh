#!/bin/bash
set -e

echo "🤖 AI Workflow Demo"
echo "===================="

echo -e "\n1️⃣  Creating newsletter for AI processing..."
NL_ID=$(curl -s -X POST http://localhost:8000/api/newsletters \
  -H "Content-Type: application/json" \
  -d '{
    "title": "AI Demo Newsletter",
    "topic": "ai_news",
    "body": "AI will enhance this content",
    "source": "spiegel_wissenschaft_technik",
    "source_external_id": "ai-demo-001",
    "source_url": "https://example.com/ai-demo"
  }' | jq -r '.id')
echo "Created newsletter #$NL_ID"

echo -e "\n2️⃣  Running AI workflow..."
RESULT=$(curl -s -X POST http://localhost:8000/api/workflows/newsletter/$NL_ID/run-ai | jq -r '.result')

echo -e "\n📊 Results:"
echo "$RESULT" | jq

DECISION=$(echo "$RESULT" | jq -r '.ai_send_decision // "N/A"')
RELEVANCE=$(echo "$RESULT" | jq -r '.ai_avg_relevance // "N/A"')

echo -e "\n📊 AI Decision: $DECISION"
echo "📈 Avg Relevance: $RELEVANCE"

echo -e "\n✅ AI demo complete!"
