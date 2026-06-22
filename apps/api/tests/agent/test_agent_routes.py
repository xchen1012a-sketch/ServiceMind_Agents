import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient

from agent.fakes import InMemoryAgentRepository, StaticRuntime, make_ticket
from app.api.routes.agent import get_agent_run_service
from app.main import app
from app.modules.agent.runtime import RuntimeResult, RuntimeStep
from app.modules.agent.service import AgentRunService


def test_start_ticket_agent_run_through_api() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryAgentRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id))

    with _client(repository) as client:
        response = client.post(
            f"/api/v1/tickets/{ticket.id}/agent-runs",
            json={"tenant_id": str(tenant_id)},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["ticket_id"] == str(ticket.id)
    assert payload["runtime_type"] == "langgraph"
    assert payload["steps"][0]["step_name"] == "classify_ticket"


def test_start_ticket_agent_run_returns_404_for_missing_ticket() -> None:
    with _client(InMemoryAgentRepository()) as client:
        response = client.post(
            f"/api/v1/tickets/{uuid.uuid4()}/agent-runs",
            json={"tenant_id": str(uuid.uuid4())},
        )

    assert response.status_code == 404


def test_resume_agent_run_through_api() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryAgentRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id, priority="urgent", risk_level="high"))

    with _client(repository, runtime=StaticRuntime(_waiting_approval_result())) as client:
        create_response = client.post(
            f"/api/v1/tickets/{ticket.id}/agent-runs",
            json={"tenant_id": str(tenant_id)},
        )
        run_id = create_response.json()["id"]
        resume_response = client.post(
            f"/api/v1/agent-runs/{run_id}/resume",
            json={"tenant_id": str(tenant_id), "decision": "approved"},
        )

    assert resume_response.status_code == 200
    payload = resume_response.json()
    assert payload["status"] == "completed"
    assert [step["step_name"] for step in payload["steps"]] == [
        "approval_gate",
        "approval_decision",
        "generate_summary",
    ]


def test_resume_agent_run_returns_409_for_non_waiting_run() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryAgentRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id))

    with _client(repository) as client:
        create_response = client.post(
            f"/api/v1/tickets/{ticket.id}/agent-runs",
            json={"tenant_id": str(tenant_id)},
        )
        run_id = create_response.json()["id"]
        response = client.post(
            f"/api/v1/agent-runs/{run_id}/resume",
            json={"tenant_id": str(tenant_id), "decision": "approved"},
        )

    assert response.status_code == 409


@contextmanager
def _client(
    repository: InMemoryAgentRepository,
    runtime: StaticRuntime | None = None,
) -> Iterator[TestClient]:
    service = AgentRunService(repository, runtime=runtime or StaticRuntime())
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
