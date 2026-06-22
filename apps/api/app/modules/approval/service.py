import uuid
from datetime import UTC, datetime
from typing import Protocol

from app.models import ApprovalDecision, ApprovalRequest, ApprovedActionExecution
from app.modules.approval.repository import ApprovalRepository
from app.modules.approval.schemas import (
    ApprovalDecisionCreate,
    ApprovalDecisionRead,
    ApprovalRequestRead,
    ApprovedActionExecutionRead,
)


class ApprovedToolExecutor(Protocol):
    def execute_approved_tool_call(self, tenant_id: uuid.UUID, tool_call_id: uuid.UUID) -> dict: ...

    def reject_tool_call(self, tenant_id: uuid.UUID, tool_call_id: uuid.UUID) -> None: ...


class ApprovalNotFoundError(Exception):
    pass


class ApprovalDecisionError(Exception):
    pass


class ApprovalService:
    def __init__(
        self,
        repository: ApprovalRepository,
        tool_executor: ApprovedToolExecutor,
    ) -> None:
        self.repository = repository
        self.tool_executor = tool_executor

    def decide(
        self,
        approval_request_id: uuid.UUID | None,
        payload: ApprovalDecisionCreate,
    ) -> ApprovalRequestRead:
        if approval_request_id is None:
            raise ApprovalNotFoundError("approval request not found")
        approval_request = self.repository.get_approval_request(
            payload.tenant_id,
            approval_request_id,
        )
        if approval_request is None:
            raise ApprovalNotFoundError("approval request not found")
        if approval_request.status != "pending":
            raise ApprovalDecisionError("approval request has already been decided")

        now = datetime.now(UTC)
        approval_request.status = payload.decision
        approval_request.updated_at = now
        decision = ApprovalDecision(
            tenant_id=payload.tenant_id,
            approval_request_id=approval_request.id,
            decision=payload.decision,
            decision_reason=payload.decision_reason,
            decided_by_user_id=payload.decided_by_user_id,
            decided_at=now,
            created_at=now,
        )
        self.repository.add_decision(decision)

        if payload.decision == "rejected":
            if approval_request.tool_call_id is not None:
                self.tool_executor.reject_tool_call(payload.tenant_id, approval_request.tool_call_id)
            self.repository.commit()
            return self._request_to_read(approval_request)

        execution = self._execute_approved_action(approval_request)
        self.repository.add_execution(execution)
        self.repository.commit()
        return self._request_to_read(approval_request)

    def _execute_approved_action(
        self,
        approval_request: ApprovalRequest,
    ) -> ApprovedActionExecution:
        now = datetime.now(UTC)
        if approval_request.tool_call_id is None:
            return ApprovedActionExecution(
                tenant_id=approval_request.tenant_id,
                approval_request_id=approval_request.id,
                tool_call_id=None,
                execution_status="skipped",
                execution_payload=approval_request.proposed_payload,
                execution_result_payload=None,
                error_code="missing_tool_call",
                error_message="approval request has no linked tool call",
                executed_at=now,
                created_at=now,
            )

        try:
            output = self.tool_executor.execute_approved_tool_call(
                approval_request.tenant_id,
                approval_request.tool_call_id,
            )
            return ApprovedActionExecution(
                tenant_id=approval_request.tenant_id,
                approval_request_id=approval_request.id,
                tool_call_id=approval_request.tool_call_id,
                execution_status="completed",
                execution_payload=approval_request.proposed_payload,
                execution_result_payload=output,
                executed_at=now,
                created_at=now,
            )
        except Exception as exc:
            return ApprovedActionExecution(
                tenant_id=approval_request.tenant_id,
                approval_request_id=approval_request.id,
                tool_call_id=approval_request.tool_call_id,
                execution_status="failed",
                execution_payload=approval_request.proposed_payload,
                execution_result_payload=None,
                error_code=exc.__class__.__name__,
                error_message=str(exc),
                executed_at=now,
                created_at=now,
            )

    def _request_to_read(self, approval_request: ApprovalRequest) -> ApprovalRequestRead:
        return ApprovalRequestRead(
            id=approval_request.id,
            tenant_id=approval_request.tenant_id,
            ticket_id=approval_request.ticket_id,
            agent_run_id=approval_request.agent_run_id,
            tool_call_id=approval_request.tool_call_id,
            action_type=approval_request.action_type,
            risk_level=approval_request.risk_level,
            reason_text=approval_request.reason_text,
            proposed_payload=approval_request.proposed_payload,
            status=approval_request.status,
            requested_by_type=approval_request.requested_by_type,
            requested_by_user_id=approval_request.requested_by_user_id,
            expires_at=approval_request.expires_at,
            created_at=approval_request.created_at,
            updated_at=approval_request.updated_at,
            decisions=[
                self._decision_to_read(decision)
                for decision in self.repository.list_decisions(
                    approval_request.tenant_id,
                    approval_request.id,
                )
            ],
            executions=[
                self._execution_to_read(execution)
                for execution in self.repository.list_executions(
                    approval_request.tenant_id,
                    approval_request.id,
                )
            ],
        )

    def _decision_to_read(self, decision: ApprovalDecision) -> ApprovalDecisionRead:
        return ApprovalDecisionRead(
            id=decision.id,
            approval_request_id=decision.approval_request_id,
            decision=decision.decision,
            decision_reason=decision.decision_reason,
            decided_by_user_id=decision.decided_by_user_id,
            decided_at=decision.decided_at,
            created_at=decision.created_at,
        )

    def _execution_to_read(
        self,
        execution: ApprovedActionExecution,
    ) -> ApprovedActionExecutionRead:
        return ApprovedActionExecutionRead(
            id=execution.id,
            approval_request_id=execution.approval_request_id,
            tool_call_id=execution.tool_call_id,
            execution_status=execution.execution_status,
            execution_payload=execution.execution_payload,
            execution_result_payload=execution.execution_result_payload,
            error_code=execution.error_code,
            error_message=execution.error_message,
            executed_at=execution.executed_at,
            created_at=execution.created_at,
        )
