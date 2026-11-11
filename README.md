# 📧 Newsletter Orchestrator

AI-powered newsletter automation with intelligent content curation and automated send decisions.

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 🌟 Features

- **Automated Newsletter Generation** - Fetch, filter, and compile news articles
- **AI-Powered Content Selection** - Score articles by relevance using LLMs
- **Smart Send Decisions** - Auto-send, review, or skip based on risk + relevance
- **Flexible Scheduling** - Cron-like delivery with timezone support
- **Risk Management** - Classify content risk level before sending
- **Extensible Architecture** - Pluggable AI providers (Groq, Ollama, Mock)

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/newsletter-orchestrator.git
cd newsletter-orchestrator/backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configure

```bash
export APP_ENV=development
export DB_HOST=127.0.0.1
export DB_PORT=55432
export DB_NAME=newsletter
export DB_USER=newsletter_user
export DB_PASSWORD=newsletter_password

# AI settings
export LLM_PROVIDER=mock  # or "groq", "ollama"
export WORKFLOW_MODE=standard  # or "ai"

# Demo mode
export EMAIL_MODE=mock
export NEWS_SOURCE_MODE=stub
```

### 3. Run

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Visit http://localhost:8000/docs for interactive API docs.

## 📖 Demo

### Quick Demo (Standard Workflow)

```bash
./demo_quick.sh
```

### AI Workflow Demo

```bash
export WORKFLOW_MODE=ai
./demo_ai.sh
```

### Manual Demo

```bash
# 1. Create subscriber
curl -X POST http://localhost:8000/api/subscribers \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "name": "User", "topics": ["ai_news"]}'

# 2. Create newsletter
curl -X POST http://localhost:8000/api/newsletters \
  -H "Content-Type: application/json" \
  -d '{"title": "AI News", "topic": "ai_news", "body": "Content...", "source": "spiegel_wissenschaft_technik", "source_external_id": "001", "source_url": "https://example.com"}'

# 3. Run workflow
curl -X POST http://localhost:8000/api/workflows/newsletter/1/run
```

## 🏗️ Architecture
´´
┌─────────────────┐
│ News Sources │ (RSS feeds, stub data)
└────────┬────────┘
│
┌────────▼────────┐
│ AI Relevance │ (Score articles 0.0-1.0)
│ Scorer │
└────────┬────────┘
│
┌────────▼────────┐
│ Newsletter │ (Generate/Synthesize)
│ Generator │
└────────┬────────┘
│
┌────────▼────────┐
│ Risk + Send │ (Classify + Decide)
│ Decision │
└────────┬────────┘
│
┌────┴────┐
│ │
┌───▼──┐ ┌──▼──────┐
│ Send │ │ Review │
└──────┘ └─────────┘
´´
## 📁 Project Structure
´´´
newsletter-orchestrator/
├── backend/
│ ├── app/
│ │ ├── ai_workflow_orchestrator.py # AI-enhanced workflow
│ │ ├── ai_relevance_scorer.py # Article scoring
│ │ ├── ai_newsletter_service.py # Classification, generation
│ │ ├── schedule_service.py # Scheduler logic
│ │ ├── routes_*.py # API endpoints
│ │ └── models.py # Database models
│ ├── scripts/
│ │ ├── test_ai_workflow.py # AI workflow tests
│ │ └── test_schedule_runs.py # Schedule tests
│ └── demo_*.sh # Demo scripts
├── GITHUB_DEMO.md # Detailed demo guide
├── AI_WORKFLOW_ORCHESTRATION.md # AI workflow docs
└── README.md # This file

´´´
## 🔧 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `WORKFLOW_MODE` | `standard` | Workflow mode: `standard` or `ai` |
| `LLM_PROVIDER` | `mock` | AI provider: `mock`, `groq`, `ollama` |
| `RELEVANCE_THRESHOLD` | `0.6` | Minimum relevance score (0.0-1.0) |
| `EMAIL_MODE` | `mock` | Email mode: `mock` or `smtp` |
| `NEWS_SOURCE_MODE` | `stub` | News mode: `stub` or `rss` |

## 🤖 AI Workflow Decision Matrix

| Risk Level | Relevance | Articles | Decision |
|------------|-----------|----------|----------|
| Low | ≥0.8 | ≥2 | ✅ Auto-send |
| Low | ≥0.6 | ≥1 | ✅ Auto-send |
| Medium | ≥0.6 | ≥1 | ⚠️ Review |
| High | Any | Any | ⚠️ Review |
| Critical | Any | Any | ⚠️ Review |
| Any | <0.6 | Any | ⏭️ Skip |

## 📊 API Endpoints

### Core
- `POST /api/subscribers` - Create subscriber
- `POST /api/newsletters` - Create newsletter
- `POST /api/schedules` - Create schedule

### Workflows
- `POST /api/workflows/newsletter/{id}/run` - Run standard workflow
- `POST /api/workflows/newsletter/{id}/run-ai` - Run AI workflow ✨

### Automation
- `POST /api/automation/enable` - Enable automation
- `POST /api/automation/disable` - Disable automation

## 🧪 Testing

```bash
# Run AI workflow tests
cd backend
python scripts/test_ai_workflow.py

# Run schedule tests
python scripts/test_schedule_runs.py

# Run all tests
pytest tests/
```

## 📚 Documentation

- [GitHub Demo Guide](GITHUB_DEMO.md) - Complete walkthrough
- [AI Workflow Orchestration](AI_WORKFLOW_ORCHESTRATION.md) - AI features
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md) - Technical details
- [Quick Reference](QUICK_REFERENCE.md) - Cheat sheet

## 🛠️ Development

### Run with Real AI (Groq)

```bash
export WORKFLOW_MODE=ai
export LLM_PROVIDER=groq
export GROQ_API_KEY=your_api_key_here
python -m uvicorn app.main:app --reload
```

### Run with Ollama (Local)

```bash
export WORKFLOW_MODE=ai
export LLM_PROVIDER=ollama
export OLLAMA_MODEL=llama3.1:8b
python -m uvicorn app.main:app --reload
```

## 📈 Monitoring

View schedule run history:

```bash
cd backend/scripts
python test_schedule_runs.py
```

Check API health:

```bash
curl http://localhost:8000/health
```

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a PR

## 🙏 Acknowledgments

- FastAPI for the web framework
- LangGraph for workflow orchestration
- Groq/Ollama for AI inference
- SQLAlchemy for database ORM

---

**Built with ❤️ using FastAPI and LangGraph**
