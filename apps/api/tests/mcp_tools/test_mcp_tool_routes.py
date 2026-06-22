import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient
from mcp_tools.test_mcp_tool_service import InMemoryMcpToolRepository, make_ticket

from app.api.routes.mcp_tools import get_mcp_tool_service
from app.main import app
from app.modules.mcp_tools.service import McpToolService


def test_call_low_risk_mcp_tool_through_api() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryMcpToolRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id))

    with _client(repository) as client:
        response = client.post(
            "/api/v1/mcp/tools/ticket.get_context/call",
            headers=_auth_headers(tenant_id, uuid.uuid4(), "mcp-tools:call"),
            json={
                "agent_run_id": str(uuid.uuid4()),
                "input_payload": {"ticket_id": str(ticket.id)},
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["output_payload"]["ticket_id"] == str(ticket.id)


def test_call_high_risk_mcp_tool_through_api_returns_pending_approval() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryMcpToolRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id))

    with _client(repository) as client:
        response = client.post(
            "/api/v1/mcp/tools/ticket.transition_status/call",
            headers=_auth_headers(tenant_id, uuid.uuid4(), "mcp-tools:call"),
            json={
                "agent_run_id": str(uuid.uuid4()),
                "input_payload": {
                    "ticket_id": str(ticket.id),
                    "to_status": "triaged",
                    "reason_text": "API 审批",
                },
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "waiting_approval"
    assert payload["approval_request_id"] == str(repository.approval_requests[0].id)
    assert ticket.status == "new"


def test_mcp_tool_call_rejects_client_controlled_security_fields() -> None:
    with _client(InMemoryMcpToolRepository()) as client:
        response = client.post(
            "/api/v1/mcp/tools/ticket.get_context/call",
            headers=_auth_headers(uuid.uuid4(), uuid.uuid4(), "mcp-tools:call"),
            json={
                "tenant_id": str(uuid.uuid4()),
                "agent_run_id": str(uuid.uuid4()),
                "input_payload": {},
            },
        )

    assert response.status_code == 422


def test_mcp_tool_call_requires_permission() -> None:
    with _client(InMemoryMcpToolRepository()) as client:
        response = client.post(
            "/api/v1/mcp/tools/ticket.get_context/call",
            headers=_auth_headers(uuid.uuid4(), uuid.uuid4(), "tickets:read"),
            json={"agent_run_id": str(uuid.uuid4()), "input_payload": {}},
        )

    assert response.status_code == 403


@contextmanager
def _client(repository: InMemoryMcpToolRepository) -> Iterator[TestClient]:
    app.dependency_overrides[get_mcp_tool_service] = lambda: McpToolService(repository)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _auth_headers(tenant_id: uuid.UUID, user_id: uuid.UUID, permissions: str) -> dict[str, str]:
    return {
        "X-ServiceMind-Tenant-Id": str(tenant_id),
        "X-ServiceMind-User-Id": str(user_id),
        "X-ServiceMind-Permissions": permissions,
    }
