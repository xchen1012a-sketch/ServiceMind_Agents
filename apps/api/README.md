# ServiceMind API

FastAPI backend for ServiceMind Agents.

## Current scope

This directory currently contains the database foundation and the first workflow APIs:

- SQLAlchemy 2.0 declarative models.
- Alembic migration environment.
- First bootstrap migration for PostgreSQL + pgvector.
- FastAPI application entrypoint.
- `/health` smoke endpoint for frontend integration.
- Ticket workflow endpoints.
- LangGraph-backed Agent run trigger and approval resume endpoints.
- Knowledge space and manual document import endpoints with chunk persistence.

## Commands

```powershell
cd apps/api
alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
python -m compileall app alembic
```

With the local virtual environment:

```powershell
cd G:\ServiceMind_Agents\apps\api
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest tests/db
.\.venv\Scripts\python -m pytest tests
.\.venv\Scripts\ruff check app tests alembic
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
.\.venv\Scripts\alembic upgrade head
```

Or run the verification wrapper:

```powershell
.\scripts\verify-db.ps1
```

Ticket workflow PostgreSQL smoke:

```powershell
.\scripts\verify-ticket-workflow.ps1
```

The same wrapper now also runs the default test suite where PostgreSQL smoke tests are skipped unless `SERVICEMIND_RUN_POSTGRES_SMOKE=1`.

If the database runs on a custom endpoint:

```powershell
.\scripts\verify-ticket-workflow.ps1 -DatabaseUrl "postgresql+psycopg://user:password@localhost:5432/servicemind?connect_timeout=5"
```

## Environment

`SERVICEMIND_DATABASE_URL` defaults to:

```text
postgresql+psycopg://servicemind:servicemind@localhost:5432/servicemind?connect_timeout=5
```

If the database runs on a custom endpoint for DB foundation verification:

```powershell
.\scripts\verify-db.ps1 -DatabaseUrl "postgresql+psycopg://user:password@localhost:5432/servicemind?connect_timeout=5"
```

## Health check

```powershell
Invoke-RestMethod http://localhost:8000/health
```

## Ticket workflow endpoints

Phase 03 exposes the first ticket workflow:

```text
POST   /api/v1/tickets
GET    /api/v1/tickets?tenant_id=<uuid>
GET    /api/v1/tickets/{ticket_id}?tenant_id=<uuid>
POST   /api/v1/tickets/{ticket_id}/status
```

The first version uses explicit `tenant_id` request fields until backend auth context is implemented.

## Agent workflow endpoints

Phase 04 exposes the first LangGraph-backed Agent trigger and approval resume path:

```text
POST /api/v1/tickets/{ticket_id}/agent-runs
POST /api/v1/agent-runs/{agent_run_id}/resume
```

Request body:

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000000"
}
```

Resume request body:

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000000",
  "decision": "approved",
  "decision_reason": "operator checked the run",
  "decided_by_user_id": null
}
```

Low-risk tickets complete deterministic placeholder nodes. High-risk tickets stop at `waiting_approval`; approval resume records `approval_decision` and either continues to a deterministic `generate_summary` step or ends the run as `rejected`.

## Knowledge RAG endpoints

Phase 05 exposes the first knowledge base import path:

```text
POST /api/v1/knowledge/spaces
POST /api/v1/knowledge/documents/import
GET  /api/v1/knowledge/documents/{document_id}?tenant_id=<uuid>
POST /api/v1/knowledge/documents/{document_id}/embeddings
POST /api/v1/knowledge/search
```

The first import endpoint accepts plain text content, stores a document version, and persists generated chunks with source anchors. The embedding endpoint uses a deterministic local provider (`local/deterministic-hash-v1`) so tests and audit records do not depend on external model credentials. Search uses the same deterministic embedding, returns ranked chunks, and persists `rag_queries` plus `rag_retrieval_hits` for audit. Agent citation wiring is reserved for the next Phase 05 slice.
