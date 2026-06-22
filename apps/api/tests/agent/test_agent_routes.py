import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient

from agent.fakes import (
    InMemoryAgentRepository,
    StaticKnowledgeSearchService,
    StaticRuntime,
    make_ticket,
)
from app.api.routes.agent import get_agent_run_service
from app.main import app
from app.modules.agent.runtime import RuntimeResult, RuntimeStep
from app.modules.agent.service import AgentRunService


def test_start_ticket_agent_run_through_api() -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    repository = InMemoryAgentRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id))

    with _client(repository) as client:
        response = client.post(
            f"/api/v1/tickets/{ticket.id}/agent-runs",
            headers=_auth_headers(tenant_id, user_id, "agent:run"),
            json={},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["ticket_id"] == str(ticket.id)
    assert payload["runtime_type"] == "langgraph"
    assert payload["steps"][0]["step_name"] == "classify_ticket"
    assert payload["steps"][1]["step_name"] == "retrieve_knowledge"
    assert payload["citations"][0]["document_title"] == "Refund policy"


def test_start_ticket_agent_run_returns_404_for_missing_ticket() -> None:
    tenant_id = uuid.uuid4()
    with _client(InMemoryAgentRepository()) as client:
        response = client.post(
            f"/api/v1/tickets/{uuid.uuid4()}/agent-runs",
            headers=_auth_headers(tenant_id, uuid.uuid4(), "agent:run"),
            json={},
        )

    assert response.status_code == 404


def test_resume_agent_run_through_api() -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    repository = InMemoryAgentRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id, priority="urgent", risk_level="high"))

    with _client(repository, runtime=StaticRuntime(_waiting_approval_result())) as client:
        create_response = client.post(
            f"/api/v1/tickets/{ticket.id}/agent-runs",
            headers=_auth_headers(tenant_id, user_id, "agent:run,agent:approve"),
            json={},
        )
        run_id = create_response.json()["id"]
        resume_response = client.post(
            f"/api/v1/agent-runs/{run_id}/resume",
            headers=_auth_headers(tenant_id, user_id, "agent:approve"),
            json={"decision": "approved"},
        )

    assert resume_response.status_code == 200
    payload = resume_response.json()
    assert payload["status"] == "completed"
    assert [step["step_name"] for step in payload["steps"]] == [
        "approval_gate",
        "approval_decision",
        "retrieve_knowledge",
        "generate_summary",
    ]
    assert payload["citations"][0]["chunk"]["source_anchor"] == "chunk:0"
    approval_decision = payload["steps"][1]
    assert approval_decision["input_payload"]["decided_by_user_id"] == str(user_id)


def test_resume_agent_run_returns_409_for_non_waiting_run() -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    repository = InMemoryAgentRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id))

    with _client(repository) as client:
        create_response = client.post(
            f"/api/v1/tickets/{ticket.id}/agent-runs",
            headers=_auth_headers(tenant_id, user_id, "agent:run,agent:approve"),
            json={},
        )
        run_id = create_response.json()["id"]
        response = client.post(
            f"/api/v1/agent-runs/{run_id}/resume",
            headers=_auth_headers(tenant_id, user_id, "agent:approve"),
            json={"decision": "approved"},
        )

    assert response.status_code == 409


def test_agent_routes_reject_client_controlled_security_fields() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryAgentRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id))

    with _client(repository) as client:
        response = client.post(
            f"/api/v1/tickets/{ticket.id}/agent-runs",
            headers=_auth_headers(tenant_id, uuid.uuid4(), "agent:run"),
            json={"tenant_id": str(uuid.uuid4())},
        )

    assert response.status_code == 422


def test_agent_resume_rejects_client_supplied_decider() -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    repository = InMemoryAgentRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id, priority="urgent", risk_level="high"))

    with _client(repository, runtime=StaticRuntime(_waiting_approval_result())) as client:
        create_response = client.post(
            f"/api/v1/tickets/{ticket.id}/agent-runs",
            headers=_auth_headers(tenant_id, user_id, "agent:run,agent:approve"),
            json={},
        )
        response = client.post(
            f"/api/v1/agent-runs/{create_response.json()['id']}/resume",
            headers=_auth_headers(tenant_id, user_id, "agent:approve"),
            json={"decision": "approved", "decided_by_user_id": str(uuid.uuid4())},
        )

    assert response.status_code == 422


def test_agent_routes_require_permission() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryAgentRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id))

    with _client(repository) as client:
        response = client.post(
            f"/api/v1/tickets/{ticket.id}/agent-runs",
            headers=_auth_headers(tenant_id, uuid.uuid4(), "tickets:read"),
            json={},
        )

    assert response.status_code == 403


@contextmanager
def _client(
    repository: InMemoryAgentRepository,
    runtime: StaticRuntime | None = None,
) -> Iterator[TestClient]:
    service = AgentRunService(
        repository,
        runtime=runtime or StaticRuntime(),
        knowledge_service=StaticKnowledgeSearchService(),
    )
    app.dependency_overrides[get_agent_run_service] = lambda: service
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _waiting_approval_result() -> RuntimeResult:
    return RuntimeResult(
        status="waiting_approval",
        steps=[
            RuntimeStep(
                name="approval_gate",
                step_type="approval",
                status="waiting_approval",
                input_payload={"risk_level": "high"},
                output_payload={"pause_reason": "manual_approval_required"},
            )
        ],
    )


def _auth_headers(tenant_id: uuid.UUID, user_id: uuid.UUID, permissions: str) -> dict[str, str]:
    return {
        "X-ServiceMind-Tenant-Id": str(tenant_id),
        "X-ServiceMind-User-Id": str(user_id),
        "X-ServiceMind-Permissions": permissions,
    }
