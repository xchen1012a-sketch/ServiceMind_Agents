import uuid
from datetime import UTC, datetime

import pytest
from mcp_tools.test_mcp_tool_service import InMemoryMcpToolRepository, make_ticket

from app.models import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovedActionExecution,
    McpServer,
    McpTool,
    Ticket,
    TicketStatusEvent,
    ToolCall,
)
from app.modules.approval.schemas import ApprovalDecisionCreate
from app.modules.approval.service import ApprovalDecisionError, ApprovalService
from app.modules.mcp_tools.schemas import ToolCallCreate
from app.modules.mcp_tools.service import McpToolService


def test_approval_service_approves_and_executes_pending_tool_call() -> None:
    tenant_id = uuid.uuid4()
    decider_id = uuid.uuid4()
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
                "reason_text": "审批执行",
            },
        )
    )
    service = ApprovalService(repository, mcp_service)

    result = service.decide(
        pending_call.approval_request_id,
        ApprovalDecisionCreate(
            tenant_id=tenant_id,
            decided_by_user_id=decider_id,
            decision="approved",
            decision_reason="可以执行",
        ),
    )

    assert result.status == "approved"
    assert result.decisions[0].decided_by_user_id == decider_id
    assert result.executions[0].execution_status == "completed"
    assert result.executions[0].execution_result_payload["to_status"] == "triaged"
    assert ticket.status == "triaged"
    assert repository.tool_calls[0].status == "completed"


def test_approval_service_rejects_without_executing_tool_call() -> None:
    tenant_id = uuid.uuid4()
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
                "reason_text": "审批拒绝",
            },
        )
    )
    service = ApprovalService(repository, mcp_service)

    result = service.decide(
        pending_call.approval_request_id,
        ApprovalDecisionCreate(
            tenant_id=tenant_id,
            decided_by_user_id=uuid.uuid4(),
            decision="rejected",
            decision_reason="信息不足",
        ),
    )

    assert result.status == "rejected"
    assert result.executions == []
    assert ticket.status == "new"
    assert repository.tool_calls[0].status == "rejected"


def test_approval_service_rejects_repeated_decision() -> None:
    tenant_id = uuid.uuid4()
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
                "reason_text": "重复审批",
            },
        )
    )
    service = ApprovalService(repository, mcp_service)
    payload = ApprovalDecisionCreate(
        tenant_id=tenant_id,
        decided_by_user_id=uuid.uuid4(),
        decision="approved",
        decision_reason="第一次",
    )
    service.decide(pending_call.approval_request_id, payload)

    with pytest.raises(ApprovalDecisionError):
        service.decide(pending_call.approval_request_id, payload)


class InMemoryApprovalRepository(InMemoryMcpToolRepository):
    def __init__(self) -> None:
        super().__init__()
        self.decisions: list[ApprovalDecision] = []
        self.executions: list[ApprovedActionExecution] = []

    def get_approval_request(
        self,
        tenant_id: uuid.UUID,
        approval_request_id: uuid.UUID,
    ) -> ApprovalRequest | None:
        return next(
            (
                request
                for request in self.approval_requests
                if request.tenant_id == tenant_id and request.id == approval_request_id
            ),
            None,
        )

    def add_decision(self, decision: ApprovalDecision) -> None:
        self._ensure_identity(decision)
        self.decisions.append(decision)

    def list_decisions(
        self,
        tenant_id: uuid.UUID,
        approval_request_id: uuid.UUID,
    ) -> list[ApprovalDecision]:
        return [
            decision
            for decision in self.decisions
            if decision.tenant_id == tenant_id
            and decision.approval_request_id == approval_request_id
        ]

    def add_execution(self, execution: ApprovedActionExecution) -> None:
        self._ensure_identity(execution)
        self.executions.append(execution)

    def list_executions(
        self,
        tenant_id: uuid.UUID,
        approval_request_id: uuid.UUID,
    ) -> list[ApprovedActionExecution]:
        return [
            execution
            for execution in self.executions
            if execution.tenant_id == tenant_id
            and execution.approval_request_id == approval_request_id
        ]

    def _ensure_identity(
        self,
        item: (
            ApprovalDecision
            | ApprovalRequest
            | ApprovedActionExecution
            | McpServer
            | McpTool
            | Ticket
            | TicketStatusEvent
            | ToolCall
        ),
    ) -> None:
        now = datetime.now(UTC)
        if item.id is None:
            item.id = uuid.uuid4()
        if getattr(item, "created_at", None) is None:
            item.created_at = now
        if hasattr(item, "updated_at") and getattr(item, "updated_at", None) is None:
            item.updated_at = now
