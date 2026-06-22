import uuid

import pytest

from agent.fakes import (
    InMemoryAgentRepository,
    StaticKnowledgeSearchService,
    StaticRuntime,
    make_ticket,
)
from app.modules.agent.runtime import RuntimeResult, RuntimeStep
from app.modules.agent.schemas import AgentRunResume, AgentRunStart
from app.modules.agent.service import AgentRunResumeError, AgentRunService, AgentTicketNotFoundError
from app.modules.approval.schemas import ApprovalDecisionCreate, ApprovalRequestRead
from app.modules.mcp_tools.schemas import ToolCallCreate, ToolCallRead


def test_start_ticket_run_records_completed_steps() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryAgentRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id))
    knowledge_service = StaticKnowledgeSearchService()
    service = AgentRunService(repository, runtime=StaticRuntime(), knowledge_service=knowledge_service)

    run = service.start_ticket_run(ticket.id, AgentRunStart(tenant_id=tenant_id))

    assert run.runtime_type == "langgraph"
    assert run.status == "completed"
    assert run.finished_at is not None
    assert [step.step_name for step in run.steps] == [
        "classify_ticket",
        "retrieve_knowledge",
        "generate_summary",
    ]
    assert knowledge_service.requests[0].agent_run_id == run.id
    assert knowledge_service.requests[0].agent_run_step_id == run.steps[1].id
    assert knowledge_service.requests[0].used_in_answer is True
    assert run.steps[1].output_payload["citations"][0]["document_title"] == "Refund policy"
    assert run.steps[2].output_payload["citations"] == run.steps[1].output_payload["citations"]
    assert run.citations == run.steps[2].output_payload["citations"]
    assert repository.commits == 1


def test_start_ticket_run_records_low_risk_mcp_tool_step_when_tool_service_is_available() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryAgentRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id))
    tool_service = RecordingMcpToolService()
    service = AgentRunService(
        repository,
        runtime=StaticRuntime(),
        mcp_tool_service=tool_service,
    )

    run = service.start_ticket_run(ticket.id, AgentRunStart(tenant_id=tenant_id))

    assert [step.step_name for step in run.steps] == [
        "classify_ticket",
        "call_tools",
        "retrieve_knowledge",
        "generate_summary",
    ]
    assert tool_service.calls[0].tool_name == "ticket.get_context"
    assert run.steps[1].output_payload["tool_call_id"] == str(tool_service.tool_call_id)


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


def test_start_ticket_run_creates_high_risk_tool_call_and_approval_request() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryAgentRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id, priority="urgent", risk_level="high"))
    tool_service = RecordingMcpToolService()
    service = AgentRunService(
        repository,
        runtime=StaticRuntime(_waiting_approval_result()),
        mcp_tool_service=tool_service,
    )

    run = service.start_ticket_run(ticket.id, AgentRunStart(tenant_id=tenant_id))

    assert tool_service.calls[0].tool_name == "ticket.transition_status"
    assert tool_service.calls[0].input_payload == {
        "ticket_id": str(ticket.id),
        "to_status": "triaged",
        "reason_text": "manual approval required before continuing",
    }
    assert run.steps[0].output_payload["tool_call_id"] == str(tool_service.tool_call_id)
    assert run.steps[0].output_payload["approval_request_id"] == str(tool_service.approval_request_id)


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
        "retrieve_knowledge",
        "generate_summary",
    ]
    assert resumed_run.steps[0].status == "completed"
    assert resumed_run.steps[1].input_payload == {
        "decision": "approved",
        "decision_reason": "looks safe",
        "decided_by_user_id": None,
    }
    assert resumed_run.steps[2].status == "completed"
    assert resumed_run.steps[3].output_payload["citations"] == resumed_run.citations
    assert repository.commits == 2


def test_resume_waiting_approval_run_decides_linked_approval_request() -> None:
    tenant_id = uuid.uuid4()
    decider_id = uuid.uuid4()
    repository = InMemoryAgentRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id, priority="urgent", risk_level="high"))
    tool_service = RecordingMcpToolService()
    approval_service = RecordingApprovalService()
    service = AgentRunService(
        repository,
        runtime=StaticRuntime(_waiting_approval_result()),
        mcp_tool_service=tool_service,
        approval_service=approval_service,
    )
    paused_run = service.start_ticket_run(ticket.id, AgentRunStart(tenant_id=tenant_id))

    resumed_run = service.resume_run(
        paused_run.id,
        AgentRunResume(
            tenant_id=tenant_id,
            decision="approved",
            decision_reason="looks safe",
            decided_by_user_id=decider_id,
        ),
    )

    assert approval_service.approval_request_id == tool_service.approval_request_id
    assert approval_service.payload == ApprovalDecisionCreate(
        tenant_id=tenant_id,
        decided_by_user_id=decider_id,
        decision="approved",
        decision_reason="looks safe",
    )
    assert resumed_run.steps[1].output_payload["approval_request_id"] == str(
        tool_service.approval_request_id
    )
    assert resumed_run.steps[1].output_payload["execution_status"] == "completed"


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


class RecordingMcpToolService:
    def __init__(self) -> None:
        self.tool_call_id = uuid.uuid4()
        self.approval_request_id = uuid.uuid4()
        self.calls: list[ToolCallCreate] = []

    def call_tool(self, payload: ToolCallCreate) -> ToolCallRead:
        self.calls.append(payload)
        if payload.tool_name == "ticket.get_context":
            return ToolCallRead(
                id=self.tool_call_id,
                tenant_id=payload.tenant_id,
                agent_run_id=payload.agent_run_id,
                agent_run_step_id=payload.agent_run_step_id,
                mcp_server_id=uuid.uuid4(),
                mcp_tool_id=uuid.uuid4(),
                status="completed",
                input_payload=payload.input_payload,
                output_payload={"ticket_id": payload.input_payload["ticket_id"]},
                error_code=None,
                error_message=None,
                approval_request_id=None,
                created_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            )
        return ToolCallRead(
            id=self.tool_call_id,
            tenant_id=payload.tenant_id,
            agent_run_id=payload.agent_run_id,
            agent_run_step_id=payload.agent_run_step_id,
            mcp_server_id=uuid.uuid4(),
            mcp_tool_id=uuid.uuid4(),
            status="waiting_approval",
            input_payload=payload.input_payload,
            output_payload=None,
            error_code=None,
            error_message=None,
            approval_request_id=self.approval_request_id,
            created_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        )


class RecordingApprovalService:
    def __init__(self) -> None:
        self.approval_request_id: uuid.UUID | None = None
        self.payload: ApprovalDecisionCreate | None = None

    def decide(
        self,
        approval_request_id: uuid.UUID | None,
        payload: ApprovalDecisionCreate,
    ) -> ApprovalRequestRead:
        self.approval_request_id = approval_request_id
        self.payload = payload
        now = __import__("datetime").datetime.now(__import__("datetime").UTC)
        return ApprovalRequestRead(
            id=approval_request_id or uuid.uuid4(),
            tenant_id=payload.tenant_id,
            ticket_id=uuid.uuid4(),
            agent_run_id=uuid.uuid4(),
            tool_call_id=uuid.uuid4(),
            action_type="ticket.transition_status",
            risk_level="high",
            reason_text=payload.decision_reason or "",
            proposed_payload={},
            status=payload.decision,
            requested_by_type="agent",
            requested_by_user_id=None,
            expires_at=None,
            created_at=now,
            updated_at=now,
            decisions=[],
            executions=[
                {
                    "id": uuid.uuid4(),
                    "approval_request_id": approval_request_id or uuid.uuid4(),
                    "tool_call_id": uuid.uuid4(),
                    "execution_status": "completed" if payload.decision == "approved" else "skipped",
                    "execution_payload": {},
                    "execution_result_payload": {},
                    "error_code": None,
                    "error_message": None,
                    "executed_at": now,
                    "created_at": now,
                }
            ]
            if payload.decision == "approved"
            else [],
        )
