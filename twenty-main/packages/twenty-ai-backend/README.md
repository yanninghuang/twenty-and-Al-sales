# Twenty AI Sales Assistant — Backend

AI-powered sales assistant backend for Twenty CRM, providing 5 AI modules:

1. **AI Knowledge Base** — Enterprise knowledge RAG Q&A
2. **AI Customer Profile** — Customer 360° analysis with sentiment, churn risk, upsell potential
3. **AI Sales Suggestions** — Actionable sales suggestions with priority ranking
4. **Document Q&A** — Contract/product document Q&A with citation verification
5. **Risk Alerts** — Payment/opportunity risk monitoring with AI analysis

## Architecture

```
Twenty CRM (Frontend + Backend)
        │
        │ REST API
        ▼
Twenty AI Backend (FastAPI)
  ├── FastAPI REST API
  ├── PostgreSQL + pgvector
  ├── LangGraph Agents
  ├── Embedding Service (OpenAI text-embedding-3-small)
  └── LLM Service (Anthropic Claude / OpenAI GPT-4o)
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ with pgvector extension
- OpenAI API key (for embeddings) and/or Anthropic API key (for LLM)

### Setup

```bash
cd packages/twenty-ai-backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys and database URL

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

## API Overview

All endpoints are namespaced under `/api/v1/workspaces/{workspace_id}/`.

| Module | Base Path | Description |
|--------|-----------|-------------|
| Knowledge Base | `/knowledge-base/` | Document upload, semantic search, RAG Q&A |
| Customer Profile | `/customer-profiles/` | Profile generation, search |
| Sales Suggestions | `/sales-suggestions/` | Suggestion generation, feedback |
| Document QA | `/document-qa/` | Document upload, Q&A conversations |
| Risk Alerts | `/risk-alerts/` | Rules management, alert monitoring |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async PostgreSQL URL |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `DEFAULT_LLM_MODEL` | `claude-sonnet-4-20250514` | Default LLM model |
| `INTERNAL_API_KEY` | — | API key for internal auth |
| `TWENTY_CRM_DEFAULT_URL` | `http://localhost:3000` | Twenty CRM URL |
