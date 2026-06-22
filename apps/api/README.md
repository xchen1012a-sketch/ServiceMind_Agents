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
- Knowledge space, manual document import, embedding, search, and Agent citation endpoints.
- Mock MCP tool call endpoints and approval decision execution endpoints.

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

## Request context

Business APIs derive tenant, user, and coarse permissions from backend request context headers. Request bodies must not include `tenant_id`, actor IDs, or Agent/RAG internal audit fields.

```text
X-ServiceMind-Tenant-Id: <tenant uuid>
X-ServiceMind-User-Id: <user uuid>
X-ServiceMind-Permissions: tickets:create,tickets:read
```

This is the local development contract until the auth module replaces these headers with verified session/JWT context.

## Ticket workflow endpoints

Phase 03 exposes the first ticket workflow:

```text
POST   /api/v1/tickets
GET    /api/v1/tickets
GET    /api/v1/tickets/{ticket_id}
POST   /api/v1/tickets/{ticket_id}/status
```

The current protected API derives tenant and actor fields from request context headers.

## Agent workflow endpoints

Phase 04 exposes the first LangGraph-backed Agent trigger and approval resume path:

```text
POST /api/v1/tickets/{ticket_id}/agent-runs
POST /api/v1/agent-runs/{agent_run_id}/resume
```

Request body:

```json
{}
```

Resume request body:

```json
{
  "decision": "approved",
  "decision_reason": "operator checked the run"
}
```

Low-risk tickets complete deterministic placeholder nodes. Before `generate_summary`, the Agent records a `retrieve_knowledge` step, writes `rag_queries` / `rag_retrieval_hits`, and returns citations in both the summary step payload and the top-level run response. High-risk tickets stop at `waiting_approval`; approval resume records `approval_decision` and either runs `retrieve_knowledge` plus deterministic `generate_summary`, or ends the run as `rejected`.

When the MCP tool service is wired, Agent runs also write a `call_tools` step for the mock `ticket.get_context` tool. High-risk runs create a pending `ticket.transition_status` tool call and approval request; the write action is not executed until the approval decision path approves it.

## MCP tool and approval endpoints

Phase 06 exposes the first in-process mock MCP tool path:

```text
GET  /api/v1/mcp/tools
POST /api/v1/mcp/tools/{tool_name}/call
POST /api/v1/approval-requests/{approval_request_id}/decision
```

Current mock tools:

- `ticket.get_context`：low risk，读取工单上下文，立即写入 `tool_calls` 并返回输出。
- `ticket.transition_status`：high risk，先写入 `tool_calls` 和 `approval_requests`，审批通过后才写 `approved_action_executions` 并变更工单状态。

Required permissions:

```text
mcp-tools:read
mcp-tools:call
approval:decide
```

## Knowledge RAG endpoints

Phase 05 exposes the first knowledge base import path:

```text
POST /api/v1/knowledge/spaces
POST /api/v1/knowledge/documents/import
GET  /api/v1/knowledge/documents/{document_id}
POST /api/v1/knowledge/documents/{document_id}/embeddings
POST /api/v1/knowledge/search
```

The first import endpoint accepts plain text content, stores a document version, and persists generated chunks with source anchors. The embedding endpoint uses a deterministic local provider (`local/deterministic-hash-v1`) so tests and audit records do not depend on external model credentials. Search uses the same deterministic embedding, returns ranked chunks, and persists `rag_queries` plus `rag_retrieval_hits` for audit. Agent runs reuse the same search service and expose citations with document, version, chunk, rank, score, and source anchor metadata.

Public knowledge search accepts only query inputs such as `query_text`, `top_k`, and optional `knowledge_space_id`. `agent_run_id`, `agent_run_step_id`, and `used_in_answer` are backend-internal fields set only by Agent service calls.
