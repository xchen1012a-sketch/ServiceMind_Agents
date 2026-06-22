import uuid

import pytest

from agent.fakes import InMemoryAgentRepository, StaticRuntime, make_ticket
from app.modules.agent.runtime import RuntimeResult, RuntimeStep
from app.modules.agent.schemas import AgentRunResume, AgentRunStart
from app.modules.agent.service import AgentRunResumeError, AgentRunService, AgentTicketNotFoundError


def test_start_ticket_run_records_completed_steps() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryAgentRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id))
    service = AgentRunService(repository, runtime=StaticRuntime())

    run = service.start_ticket_run(ticket.id, AgentRunStart(tenant_id=tenant_id))

    assert run.runtime_type == "langgraph"
    assert run.status == "completed"
    assert run.finished_at is not None
    assert [step.step_name for step in run.steps] == ["classify_ticket", "generate_summary"]
    assert repository.commits == 1


def test_start_ticket_run_can_pause_for_approval() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryAgentRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id, priority="urgent", risk_level="high"))
    runtime = StaticRuntime(
        RuntimeResult(
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
    )
    service = AgentRunService(repository, runtime=runtime)

    run = service.start_ticket_run(ticket.id, AgentRunStart(tenant_id=tenant_id))

    assert run.status == "waiting_approval"
    assert run.finished_at is None
    assert run.steps[0].status == "waiting_approval"


def test_resume_waiting_approval_run_records_decision_and_continues() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryAgentRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id, priority="urgent", risk_level="high"))
    service = AgentRunService(repository, runtime=StaticRuntime(_waiting_approval_result()))
    paused_run = service.start_ticket_run(ticket.id, AgentRunStart(tenant_id=tenant_id))

    resumed_run = service.resume_run(
        paused_run.id,
        AgentRunResume(tenant_id=tenant_id, decision="approved", decision_reason="looks safe"),
    )

    assert resumed_run.status == "completed"
    assert resumed_run.finished_at is not None
    assert [step.step_name for step in resumed_run.steps] == [
        "approval_gate",
        "approval_decision",
        "generate_summary",
    ]
    assert resumed_run.steps[0].status == "completed"
    assert resumed_run.steps[1].input_payload == {
        "decision": "approved",
        "decision_reason": "looks safe",
        "decided_by_user_id": None,
    }
    assert repository.commits == 2


def test_resume_waiting_approval_run_can_reject() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryAgentRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id, priority="urgent", risk_level="high"))
    service = AgentRunService(repository, runtime=StaticRuntime(_waiting_approval_result()))
    paused_run = service.start_ticket_run(ticket.id, AgentRunStart(tenant_id=tenant_id))

    resumed_run = service.resume_run(
        paused_run.id,
        AgentRunResume(tenant_id=tenant_id, decision="rejected", decision_reason="needs review"),
    )

    assert resumed_run.status == "rejected"
    assert [step.step_name for step in resumed_run.steps] == ["approval_gate", "approval_decision"]
    assert resumed_run.steps[0].status == "rejected"
    assert resumed_run.steps[1].output_payload == {"resume": False}


def test_resume_run_rejects_non_waiting_run() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryAgentRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id))
    service = AgentRunService(repository, runtime=StaticRuntime())
    run = service.start_ticket_run(ticket.id, AgentRunStart(tenant_id=tenant_id))

    with pytest.raises(AgentRunResumeError):
        service.resume_run(run.id, AgentRunResume(tenant_id=tenant_id))


def test_start_ticket_run_records_runtime_failure() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryAgentRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id))
    service = AgentRunService(repository, runtime=StaticRuntime(error=RuntimeError("boom")))

    run = service.start_ticket_run(ticket.id, AgentRunStart(tenant_id=tenant_id))

    assert run.status == "failed"
    assert run.error_code == "RuntimeError"
    assert run.steps[0].step_name == "runtime_error"
    assert run.steps[0].error_message == "boom"


def test_start_ticket_run_requires_existing_ticket() -> None:
    service = AgentRunService(InMemoryAgentRepository(), runtime=StaticRuntime())

    with pytest.raises(AgentTicketNotFoundError):
        service.start_ticket_run(uuid.uuid4(), AgentRunStart(tenant_id=uuid.uuid4()))


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
