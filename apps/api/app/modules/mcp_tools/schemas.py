import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictInputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


ToolCallStatus = Literal["completed", "waiting_approval", "failed", "rejected"]


class ToolCallCreateInput(StrictInputModel):
    agent_run_id: uuid.UUID
    agent_run_step_id: uuid.UUID | None = None
    input_payload: dict = Field(default_factory=dict)


class ToolCallCreate(ToolCallCreateInput):
    tenant_id: uuid.UUID
    tool_name: str


class McpToolRead(BaseModel):
    id: uuid.UUID
    mcp_server_id: uuid.UUID
    tool_name: str
    display_name: str
    description_text: str | None
    risk_level: str
    requires_approval: bool
    status: str


class ToolCallRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    agent_run_id: uuid.UUID
    agent_run_step_id: uuid.UUID | None
    mcp_server_id: uuid.UUID
    mcp_tool_id: uuid.UUID
    status: ToolCallStatus
    input_payload: dict
    output_payload: dict | None
    error_code: str | None
    error_message: str | None
    approval_request_id: uuid.UUID | None
    created_at: datetime
