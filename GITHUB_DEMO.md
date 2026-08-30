# Newsletter Orchestrator - Demo Guide

This guide demonstrates the complete workflow of the AI-powered newsletter orchestrator.

## Table of Contents

1. [Setup](#setup)
2. [Basic Workflow](#basic-workflow)
3. [AI Workflow](#ai-workflow)
4. [Schedule Automation](#schedule-automation)
5. [Monitoring & Observability](#monitoring--observability)

---

## Setup

### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/yourusername/newsletter-orchestrator.git
cd newsletter-orchestrator/backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
```

### 2. Configure Environment

```bash
# Create .env file
cat > .env << 'ENVEOF'
# App settings
APP_ENV=development
API_HOST=127.0.0.1
API_PORT=8000

# Database
DB_HOST=127.0.0.1
DB_PORT=55432
DB_NAME=newsletter
DB_USER=newsletter_user
DB_PASSWORD=newsletter_password

# AI/LLM settings
LLM_PROVIDER=mock  # Use "mock" for demo, "groq" or "ollama" for real AI
WORKFLOW_MODE=standard  # Use "standard" or "ai"

# Email settings
EMAIL_MODE=mock  # Use "mock" for demo

# News source settings
NEWS_SOURCE_MODE=stub  # Use "stub" for demo, "rss" for real feeds
ENVEOF
```

### 3. Initialize Database

```bash
# Start PostgreSQL (if not running)
# docker run -d --name newsletter-db -p 55432:5432 -e POSTGRES_DB=newsletter -e POSTGRES_USER=newsletter_user -e POSTGRES_PASSWORD=newsletter_password postgres:15

# Run migrations (if you have alembic)
# alembic upgrade head

# Or let the app auto-create tables on first run
```

### 4. Start the API Server

```bash
# Start uvicorn
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Expected output:
INFO: Uvicorn running on http://127.0.0.1:8000
INFO: Application startup complete.


---

## Basic Workflow

### Step 1: Create a Subscriber

```bash
curl -X POST http://localhost:8000/api/subscribers \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@example.com",
    "name": "Demo User",
    "topics": ["ai_news"]
  }' | jq
```

Expected output:
```json
{
  "id": 1,
  "email": "demo@example.com",
  "name": "Demo User",
  "is_active": true,
  "created_at": "2026-08-30T08:00:00Z"
}
```

### Step 2: View Available Articles

```bash
# Fetch stub articles for AI topic
curl -s "http://localhost:8000/api/news/articles?source=spiegel_wissenschaft_technik&topic=ai_news" | jq
```

Expected output:
```json
[
  {
    "source": "spiegel_wissenschaft_technik",
    "title": "AI research collaboration highlights",
    "body": "A research consortium published...",
    "topic": "ai_news"
  },
  ...
]
```

### Step 3: Create a Newsletter

```bash
curl -X POST http://localhost:8000/api/newsletters \
  -H "Content-Type: application/json" \
  -d '{
    "title": "AI Research Updates",
    "topic": "ai_news",
    "body": "Latest developments in AI research...",
    "source": "spiegel_wissenschaft_technik",
    "source_external_id": "demo-001",
    "source_url": "https://example.com/ai-news"
  }' | jq
```

Expected output:
```json
{
  "id": 1,
  "title": "AI Research Updates",
  "topic": "ai_news",
  "status": "pending_review",
  "risk_level": "low",
  "approved": false
}
```

### Step 4: Run Standard Workflow

```bash
# Approve the newsletter first (if needed)
curl -X POST http://localhost:8000/api/newsletters/1/approve | jq

# Run the workflow
curl -X POST http://localhost:8000/api/workflows/newsletter/1/run | jq
```

Expected output:
```json
{
  "status": "ok",
  "result": {
    "newsletter_id": 1,
    "workflow_id": 1,
    "created_drafts": 1,
    "subscriber_count": 1,
    "send_summary": {
      "sender": "newsletter-orchestrator@example.com",
      "recipients": ["demo@example.com"],
      "subject": "AI Research Updates",
      "count": 1
    }
  }
}
```

---

## AI Workflow

### Step 1: Enable AI Mode

```bash
# Stop the server (Ctrl+C)

# Set AI workflow mode
export WORKFLOW_MODE=ai
export LLM_PROVIDER=mock  # or "groq" for real AI

# Restart the server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 2: Create a Newsletter for AI Processing

```bash
curl -X POST http://localhost:8000/api/newsletters \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Initial Title",
    "topic": "ai_news",
    "body": "Initial content",
    "source": "spiegel_wissenschaft_technik",
    "source_external_id": "ai-demo-001",
    "source_url": "https://example.com/ai-demo"
  }' | jq
```

### Step 3: Run AI-Enhanced Workflow

```bash
curl -X POST http://localhost:8000/api/workflows/newsletter/2/run-ai | jq
```

Expected output:
```json
{
  "status": "ok",
  "result": {
    "newsletter_id": 2,
    "workflow_id": 2,
    "created_drafts": 1,
    "subscriber_count": 1,
    "send_summary": {
      "sender": "newsletter-orchestrator@example.com",
      "recipients": ["demo@example.com"],
      "subject": "Top AI News: Enhanced Title by AI",
      "count": 1
    },
    "ai_avg_relevance": 0.85,
    "ai_send_decision": "send"
  }
}
```

**Key differences from standard workflow:**
- `ai_avg_relevance`: Shows average relevance score of selected articles
- `ai_send_decision`: Shows automated decision ("send", "review", or "skip")
- Content may be AI-generated from multiple articles

---

## Schedule Automation

### Step 1: Create a Schedule

```bash
curl -X POST http://localhost:8000/api/schedules \
  -H "Content-Type: application/json" \
  -d '{
    "email": "schedule@example.com",
    "name": "Daily AI News",
    "topics_json": ["ai_news"],
    "sources_json": ["spiegel_wissenschaft_technik"],
    "weekdays_json": ["monday", "wednesday", "friday"],
    "delivery_time": "09:00",
    "timezone": "Europe/Berlin",
    "enabled": true
  }' | jq
```

Expected output:
```json
{
  "id": 1,
  "email": "schedule@example.com",
  "name": "Daily AI News",
  "topics_json": "[\"ai_news\"]",
  "sources_json": "[\"spiegel_wissenschaft_technik\"]",
  "enabled": true,
  "delivery_time": "09:00",
  "timezone": "Europe/Berlin"
}
```

### Step 2: Manually Trigger Schedule

```bash
curl -X POST http://localhost:8000/api/schedules/1/run | jq
```

Expected output:
```json
{
  "status": "sent",
  "schedule_id": 1,
  "run": {
    "id": 1,
    "status": "sent",
    "newsletter_id": 3,
    "message": "Newsletter #3 was sent through the bounded schedule workflow.",
    "started_at": "2026-08-30T09:00:00Z",
    "completed_at": "2026-08-30T09:00:05Z"
  },
  "newsletter": {
    "id": 3,
    "title": "AI Research Updates",
    "risk_level": "low",
    "approved": true,
    "status": "sent"
  }
}
```

### Step 3: View Schedule Run History

```bash
# Using the test script
cd scripts
python test_schedule_runs.py
```

Expected output:
Found 1 schedule(s):
Schedule ID: 1
Email: schedule@example.com
Enabled: True
Timezone: Europe/Berlin
Delivery time: 09:00
Runs by status: {'sent': 3}
Recent runs (3):
- 2026-08-30 09:00:00 | status=sent | newsletter_id=3
- 2026-08-29 09:00:00 | status=sent | newsletter_id=2
- 2026-08-28 09:00:00 | status=skipped_no_relevant_articles | newsletter_id=None

---

## Monitoring & Observability

### Step 1: View All Newsletters

```bash
curl -s http://localhost:8000/api/newsletters | jq '.[] | {id, title, status, risk_level}'
```

### Step 2: View All Schedules

```bash
curl -s http://localhost:8000/api/schedules | jq '.[] | {id, email, enabled, delivery_time}'
```

### Step 3: View Workflow Executions

```bash
curl -s http://localhost:8000/api/workflows/executions | jq '.[] | {id, newsletter_id, state, started_at}'
```

### Step 4: Check API Health

```bash
curl -s http://localhost:8000/health | jq
```

Expected output:
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "0.8.0"
}
```

---

## Demo Scripts

### Quick Demo Script

Save as `demo_quick.sh`:

```bash
#!/bin/bash
set -e

echo "🚀 Newsletter Orchestrator - Quick Demo"
echo "========================================"

echo -e "\n1️⃣  Creating subscriber..."
curl -s -X POST http://localhost:8000/api/subscribers \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@example.com", "name": "Demo", "topics": ["ai_news"]}' | jq -r '.email'

echo -e "\n2️⃣  Creating newsletter..."
NL_ID=$(curl -s -X POST http://localhost:8000/api/newsletters \
  -H "Content-Type: application/json" \
  -d '{"title": "Demo Newsletter", "topic": "ai_news", "body": "Demo content", "source": "spiegel_wissenschaft_technik", "source_external_id": "demo-001", "source_url": "https://example.com"}' | jq -r '.id')
echo "Created newsletter #$NL_ID"

echo -e "\n3️⃣  Approving newsletter..."
curl -s -X POST http://localhost:8000/api/newsletters/$NL_ID/approve | jq -r '.status'

echo -e "\n4️⃣  Running workflow..."
curl -s -X POST http://localhost:8000/api/workflows/newsletter/$NL_ID/run | jq -r '.result.send_summary.subject'

echo -e "\n✅ Demo complete!"
```

Run it:
```bash
chmod +x demo_quick.sh
./demo_quick.sh
```

### AI Workflow Demo Script

Save as `demo_ai.sh`:

```bash
#!/bin/bash
set -e

echo "🤖 AI Workflow Demo"
echo "===================="

echo -e "\n1️⃣  Creating newsletter for AI processing..."
NL_ID=$(curl -s -X POST http://localhost:8000/api/newsletters \
  -H "Content-Type: application/json" \
  -d '{"title": "AI Demo", "topic": "ai_news", "body": "AI will enhance this", "source": "spiegel_wissenschaft_technik", "source_external_id": "ai-demo", "source_url": "https://example.com"}' | jq -r '.id')
echo "Created newsletter #$NL_ID"

echo -e "\n2️⃣  Running AI workflow..."
RESULT=$(curl -s -X POST http://localhost:8000/api/workflows/newsletter/$NL_ID/run-ai | jq -r '.result')
echo "$RESULT" | jq

echo -e "\n📊 AI Decision: $(echo "$RESULT" | jq -r '.ai_send_decision')"
echo "📈 Avg Relevance: $(echo "$RESULT" | jq -r '.ai_avg_relevance')"

echo -e "\n✅ AI demo complete!"
```

Run it:
```bash
chmod +x demo_ai.sh
./demo_ai.sh
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find and kill the process
lsof -ti:8000 | xargs kill -9
```

### Database Connection Error

```bash
# Check if PostgreSQL is running
docker ps | grep newsletter-db

# Restart if needed
docker restart newsletter-db
```

### Module Not Found

```bash
# Reinstall in development mode
cd backend
pip install -e .
```

### API Returns 500 Error

```bash
# Check logs
tail -f uvicorn.log

# Look for specific error messages
```

---

## Next Steps

- Explore the Swagger UI: http://localhost:8000/docs
- Read the full documentation: [AI_WORKFLOW_ORCHESTRATION.md](AI_WORKFLOW_ORCHESTRATION.md)
- Check implementation details: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
