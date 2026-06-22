import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictInputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


ApprovalDecisionValue = Literal["approved", "rejected"]


class ApprovalDecisionInput(StrictInputModel):
    decision: ApprovalDecisionValue
    decision_reason: str | None = Field(default=None, max_length=2_000)


class ApprovalDecisionCreate(ApprovalDecisionInput):
    tenant_id: uuid.UUID
    decided_by_user_id: uuid.UUID


class ApprovalDecisionRead(BaseModel):
    id: uuid.UUID
    approval_request_id: uuid.UUID
    decision: str
    decision_reason: str | None
    decided_by_user_id: uuid.UUID
    decided_at: datetime
    created_at: datetime


class ApprovedActionExecutionRead(BaseModel):
    id: uuid.UUID
    approval_request_id: uuid.UUID
    tool_call_id: uuid.UUID | None
    execution_status: str
    execution_payload: dict | None
    execution_result_payload: dict | None
    error_code: str | None
    error_message: str | None
    executed_at: datetime | None
    created_at: datetime


class ApprovalRequestRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    ticket_id: uuid.UUID | None
    agent_run_id: uuid.UUID | None
    tool_call_id: uuid.UUID | None
    action_type: str
    risk_level: str
    reason_text: str
    proposed_payload: dict
    status: str
    requested_by_type: str
    requested_by_user_id: uuid.UUID | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    decisions: list[ApprovalDecisionRead] = Field(default_factory=list)
    executions: list[ApprovedActionExecutionRead] = Field(default_factory=list)
