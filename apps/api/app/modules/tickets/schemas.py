import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    tenant_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    description_text: str = Field(min_length=1)
    category_code: str = Field(default="general", min_length=1, max_length=80)
    priority: str = Field(default="medium", min_length=1, max_length=40)
    risk_level: str = Field(default="low", min_length=1, max_length=40)
    source_channel: str = Field(default="web", min_length=1, max_length=40)
    requester_name: str | None = Field(default=None, max_length=160)
    requester_contact: str | None = Field(default=None, max_length=240)
    created_by_user_id: uuid.UUID | None = None
    initial_message_text: str | None = None


class TicketStatusChange(BaseModel):
    tenant_id: uuid.UUID
    to_status: str = Field(min_length=1, max_length=40)
    reason_text: str | None = None
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
