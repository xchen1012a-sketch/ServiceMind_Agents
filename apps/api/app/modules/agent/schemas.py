import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class AgentRunStart(BaseModel):
    tenant_id: uuid.UUID


class AgentRunResume(BaseModel):
    tenant_id: uuid.UUID
    decision: Literal["approved", "rejected"] = "approved"
    decision_reason: str | None = None
    decided_by_user_id: uuid.UUID | None = None


class AgentRunStepRead(BaseModel):
    id: uuid.UUID
    step_name: str
    step_type: str
    step_order: int
    status: str
    input_payload: dict | None
    output_payload: dict | None
    error_code: str | None
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    ticket_id: uuid.UUID | None
    runtime_type: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    error_code: str | None
    error_message: str | None
    steps: list[AgentRunStepRead]
