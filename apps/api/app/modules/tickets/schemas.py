import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.input_security import validate_business_text


class StrictInputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


TicketCategoryCode = Literal["general", "billing", "technical", "account", "order", "refund"]
TicketPriority = Literal["low", "medium", "high", "urgent"]
TicketRiskLevel = Literal["low", "medium", "high", "critical"]
TicketSourceChannel = Literal["web", "email", "chat", "phone", "api"]
TicketStatusValue = Literal[
    "new",
    "triaged",
    "in_progress",
    "waiting_customer",
    "resolved",
    "closed",
    "reopened",
    "cancelled",
]


class TicketCreateInput(StrictInputModel):
    title: str = Field(min_length=1, max_length=200)
    description_text: str = Field(min_length=1, max_length=20_000)
    category_code: TicketCategoryCode = "general"
    priority: TicketPriority = "medium"
    risk_level: TicketRiskLevel = "low"
    source_channel: TicketSourceChannel = "web"
    requester_name: str | None = Field(default=None, max_length=160)
    requester_contact: str | None = Field(default=None, max_length=240)
    initial_message_text: str | None = Field(default=None, max_length=20_000)

    @field_validator(
        "title",
        "description_text",
        "requester_name",
        "requester_contact",
        "initial_message_text",
    )
    @classmethod
    def validate_text_fields(cls, value: str | None) -> str | None:
        return validate_business_text(value)


class TicketCreate(TicketCreateInput):
    tenant_id: uuid.UUID
    created_by_user_id: uuid.UUID | None = None


class TicketStatusChangeInput(StrictInputModel):
    to_status: TicketStatusValue
    reason_text: str | None = Field(default=None, max_length=2_000)

    @field_validator("reason_text")
    @classmethod
    def validate_reason_text(cls, value: str | None) -> str | None:
        return validate_business_text(value)


class TicketStatusChange(TicketStatusChangeInput):
    tenant_id: uuid.UUID
    changed_by_type: str = Field(default="user", min_length=1, max_length=40)
    changed_by_user_id: uuid.UUID | None = None


class TicketMessageRead(BaseModel):
    id: uuid.UUID
    sender_type: str
    sender_user_id: uuid.UUID | None
    message_text: str
    message_format: str
    created_at: datetime


class TicketStatusEventRead(BaseModel):
    id: uuid.UUID
    from_status: str | None
    to_status: str
    reason_text: str | None
    changed_by_type: str
    changed_by_user_id: uuid.UUID | None
    created_at: datetime


class TicketListItem(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    ticket_no: str
    title: str
    category_code: str
    priority: str
    risk_level: str
    status: str
    source_channel: str
    requester_name: str | None
    requester_contact: str | None
    created_at: datetime
    updated_at: datetime


class TicketDetail(TicketListItem):
    description_text: str
    assigned_user_id: uuid.UUID | None
    created_by_user_id: uuid.UUID | None
    messages: list[TicketMessageRead]
    status_events: list[TicketStatusEventRead]
