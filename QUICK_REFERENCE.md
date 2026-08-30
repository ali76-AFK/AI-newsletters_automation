# AI Workflow Orchestration - Quick Reference

## Enable AI Workflow

```bash
export WORKFLOW_MODE=ai
export LLM_PROVIDER=groq  # or "ollama" or "mock"
export GROQ_API_KEY=your_key_here  # if using Groq
```

## API Endpoints

### Standard Workflow
```bash
POST /api/workflows/newsletter/{id}/run
```

### AI Workflow (NEW)
```bash
POST /api/workflows/newsletter/{id}/run-ai
```

## Decision Logic

| Risk Level | Avg Relevance | Articles | Decision |
|------------|---------------|----------|----------|
| Low        | ≥0.8          | ≥2       | **Send** |
| Low        | ≥0.6          | ≥1       | **Send** |
| Medium     | ≥0.6          | ≥1       | **Review** |
| High       | Any           | Any      | **Review** |
| Critical   | Any           | Any      | **Review** |
| Any        | <0.6          | Any      | **Skip** |

## Key Files

- `app/ai_workflow_orchestrator.py` - Core AI workflow
- `app/langgraph_state.py` - State with AI fields
- `app/routes_workflows.py` - API endpoints
- `app/config.py` - Configuration
- `app/schedule_service.py` - Scheduler integration

## Test Commands

```bash
# Test AI workflow components
cd backend
python scripts/test_ai_workflow.py

# Test schedule runs
python scripts/test_schedule_runs.py
```

## Configuration Options

```bash
# Workflow mode
WORKFLOW_MODE=standard  # Default
WORKFLOW_MODE=ai        # AI-enhanced

# Relevance threshold (0.0-1.0)
RELEVANCE_THRESHOLD=0.6  # Default

# LLM provider
LLM_PROVIDER=mock   # Default (offline)
LLM_PROVIDER=ollama # Local LLM
LLM_PROVIDER=groq   # Cloud LLM
```
