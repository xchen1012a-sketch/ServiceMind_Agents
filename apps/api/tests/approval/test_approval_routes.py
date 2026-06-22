import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from approval.test_approval_service import InMemoryApprovalRepository
from fastapi.testclient import TestClient
from mcp_tools.test_mcp_tool_service import make_ticket

from app.api.routes.approval import get_approval_service
from app.main import app
from app.modules.approval.service import ApprovalService
from app.modules.mcp_tools.schemas import ToolCallCreate
from app.modules.mcp_tools.service import McpToolService


def test_approval_decision_route_approves_and_executes() -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    repository = InMemoryApprovalRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id, status="new"))
    mcp_service = McpToolService(repository)
    pending_call = mcp_service.call_tool(
        ToolCallCreate(
            tenant_id=tenant_id,
            agent_run_id=uuid.uuid4(),
            tool_name="ticket.transition_status",
            input_payload={
                "ticket_id": str(ticket.id),
                "to_status": "triaged",
                "reason_text": "路由审批",
            },
        )
    )

    with _client(repository) as client:
        response = client.post(
            f"/api/v1/approval-requests/{pending_call.approval_request_id}/decision",
            headers=_auth_headers(tenant_id, user_id, "approval:decide"),
            json={"decision": "approved", "decision_reason": "同意"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "approved"
    assert payload["decisions"][0]["decided_by_user_id"] == str(user_id)
    assert payload["executions"][0]["execution_status"] == "completed"
    assert ticket.status == "triaged"


def test_approval_decision_route_rejects_client_controlled_decider() -> None:
    with _client(InMemoryApprovalRepository()) as client:
        response = client.post(
            f"/api/v1/approval-requests/{uuid.uuid4()}/decision",
            headers=_auth_headers(uuid.uuid4(), uuid.uuid4(), "approval:decide"),
            json={"decision": "approved", "decided_by_user_id": str(uuid.uuid4())},
        )

    assert response.status_code == 422


def test_approval_decision_route_requires_permission() -> None:
    with _client(InMemoryApprovalRepository()) as client:
        response = client.post(
            f"/api/v1/approval-requests/{uuid.uuid4()}/decision",
            headers=_auth_headers(uuid.uuid4(), uuid.uuid4(), "agent:approve"),
            json={"decision": "approved"},
        )

    assert response.status_code == 403


@contextmanager
def _client(repository: InMemoryApprovalRepository) -> Iterator[TestClient]:
    mcp_service = McpToolService(repository)
    app.dependency_overrides[get_approval_service] = lambda: ApprovalService(
        repository,
        mcp_service,
    )
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
