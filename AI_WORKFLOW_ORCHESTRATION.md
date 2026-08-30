# AI Workflow Orchestration

Enhanced LangGraph workflow with AI-driven content selection, generation, and automated send decisions.

## Features

### 1. AI Scoring for Content Selection
- Scores each article using the existing `ai_relevance_scorer` module
- Filters articles below the relevance threshold (default: 0.6)
- Selects top 3 most relevant articles for newsletter generation

### 2. AI-Driven Draft Generation
- Generates newsletter title and body from multiple articles
- Synthesizes key points across articles into cohesive content
- Personalizes drafts per subscriber using AI refinement

### 3. Automated Send Decisions
- Classifies newsletter risk level (low, medium, high, critical)
- Combines risk + relevance to decide: **send**, **review**, or **skip**
- Decision rules:
  - High/critical risk → always hold for human review
  - Low risk + high relevance (≥0.8) + ≥2 articles → auto-send
  - Low/medium risk + moderate relevance (≥0.6) → auto-send
  - Low relevance (<0.6) → skip

## Architecture
┌─────────────────────┐
│ Score & Select │ ← AI relevance scoring
└─────────┬───────────┘
│
┌─────────▼───────────┐
│ Generate Newsletter│ ← AI content synthesis
└─────────┬───────────┘
│
┌─────────▼───────────┐
│ Classify & Decide │ ← Risk + relevance decision
└─────────┬───────────┘
│
┌─────┴─────┐
│ │
┌───▼──┐ ┌────▼─────┐
│ Send │ │ Review │
└──────┘ └──────────┘


## Configuration

Set the workflow mode via environment variable:

```bash
# Use standard workflow (existing behavior)
export WORKFLOW_MODE=standard

# Use AI-enhanced workflow
export WORKFLOW_MODE=ai
```

### Relevance Threshold

Adjust the minimum relevance score:

```bash
export RELEVANCE_THRESHOLD=0.7  # Default: 0.6
```

## API Endpoints

### Run AI Workflow

```bash
POST /api/workflows/newsletter/{newsletter_id}/run-ai
```

Response:
```json
{
  "status": "ok",
  "result": {
    "newsletter_id": 123,
    "workflow_id": 456,
    "created_drafts": 10,
    "subscriber_count": 10,
    "send_summary": {
      "sender": "newsletter-orchestrator@example.com",
      "recipients": ["user@example.com"],
      "subject": "Top AI News",
      "count": 10
    },
    "ai_avg_relevance": 0.85,
    "ai_send_decision": "send"
  }
}
```

## Files Added/Modified

### New Files
- `app/ai_workflow_orchestrator.py` - Enhanced workflow with AI scoring and generation
- `AI_WORKFLOW_ORCHESTRATION.md` - This documentation

### Modified Files
- `app/langgraph_state.py` - Added AI workflow state fields
- `app/routes_workflows.py` - Added `/run-ai` endpoint
- `app/config.py` - Added `workflow_mode` configuration
- `app/schedule_service.py` - Integrated AI workflow based on config

## Usage Example

### Enable AI Workflow

```bash
export WORKFLOW_MODE=ai
export LLM_PROVIDER=groq  # or ollama
export GROQ_API_KEY=your_key_here
```

### Run Schedule

The schedule service automatically uses the AI workflow when `WORKFLOW_MODE=ai`:

```python
from app.schedule_service import run_schedule_now
from app.db import SessionLocal

db = SessionLocal()
schedule = db.query(NewsletterSchedule).filter_by(id=1).first()
result = run_schedule_now(db, schedule)
print(result["status"])  # "sent", "pending_review", or "skipped_no_relevant_articles"
```

## Testing

Run the test script to verify AI workflow components:

```bash
python scripts/test_schedule_runs.py
```

## Troubleshooting

### AI scoring fails
- Ensure `LLM_PROVIDER` is set to `mock`, `groq`, or `ollama`
- For Groq: set `GROQ_API_KEY` environment variable
- Check logs for `RelevanceScorerError` details

### Workflow skips all articles
- Articles may be below relevance threshold
- Lower `RELEVANCE_THRESHOLD` or check article content quality

### High/critical risk always requires review
- This is expected behavior for safety
- Review newsletters in the admin UI and approve if appropriate
