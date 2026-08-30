#!/bin/bash
set -e

echo "🚀 Newsletter Orchestrator - Quick Demo"
echo "========================================"

echo -e "\n1️⃣  Creating subscriber..."
EMAIL=$(curl -s -X POST http://localhost:8000/api/subscribers \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@example.com", "name": "Demo User", "topics": ["ai_news"]}' | jq -r '.email // "already exists"')
echo "Subscriber: $EMAIL"

echo -e "\n2️⃣  Creating newsletter..."
NL_ID=$(curl -s -X POST http://localhost:8000/api/newsletters \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Demo Newsletter",
    "topic": "ai_news",
    "body": "Demo content for newsletter orchestrator",
    "source": "spiegel_wissenschaft_technik",
    "source_external_id": "demo-001",
    "source_url": "https://example.com/demo"
  }' | jq -r '.id')
echo "Created newsletter #$NL_ID"

echo -e "\n3️⃣  Approving newsletter..."
curl -s -X POST http://localhost:8000/api/newsletters/$NL_ID/approve > /dev/null
echo "✓ Newsletter approved"

echo -e "\n4️⃣  Running workflow..."
SUBJECT=$(curl -s -X POST http://localhost:8000/api/workflows/newsletter/$NL_ID/run | jq -r '.result.send_summary.subject // "Workflow completed"')
echo "Subject: $SUBJECT"

echo -e "\n✅ Demo complete! Visit http://localhost:8000/docs for more"
