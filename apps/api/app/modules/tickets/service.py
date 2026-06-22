import uuid
from datetime import UTC, datetime

from app.models import Ticket, TicketMessage, TicketStatusEvent
from app.modules.tickets.repository import TicketRepository
from app.modules.tickets.schemas import (
    TicketCreate,
    TicketDetail,
    TicketListItem,
    TicketMessageRead,
    TicketStatusChange,
    TicketStatusEventRead,
)

INITIAL_STATUS = "new"
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "new": {"triaged", "cancelled"},
    "triaged": {"in_progress", "cancelled"},
    "in_progress": {"waiting_customer", "resolved", "cancelled"},
    "waiting_customer": {"in_progress", "resolved", "cancelled"},
    "resolved": {"closed", "reopened"},
    "reopened": {"in_progress", "cancelled"},
    "closed": set(),
    "cancelled": set(),
}


class TicketNotFoundError(Exception):
    pass


class TicketStateTransitionError(Exception):
    pass


class TicketService:
    def __init__(self, repository: TicketRepository) -> None:
        self.repository = repository

    def create_ticket(self, payload: TicketCreate) -> TicketDetail:
        ticket = Ticket(
            tenant_id=payload.tenant_id,
            ticket_no=self._new_ticket_no(),
            title=payload.title,
            description_text=payload.description_text,
            category_code=payload.category_code,
            priority=payload.priority,
            risk_level=payload.risk_level,
            status=INITIAL_STATUS,
            source_channel=payload.source_channel,
            requester_name=payload.requester_name,
            requester_contact=payload.requester_contact,
            created_by_user_id=payload.created_by_user_id,
        )
        self.repository.add_ticket(ticket)

        initial_message = TicketMessage(
            tenant_id=payload.tenant_id,
            ticket_id=ticket.id,
            sender_type="requester",
            sender_user_id=payload.created_by_user_id,
            message_text=payload.initial_message_text or payload.description_text,
            message_format="plain_text",
        )
        self.repository.add_message(initial_message)

        initial_event = TicketStatusEvent(
            tenant_id=payload.tenant_id,
            ticket_id=ticket.id,
            from_status=None,
            to_status=INITIAL_STATUS,
            reason_text="ticket_created",
            changed_by_type="system",
            changed_by_user_id=payload.created_by_user_id,
        )
        self.repository.add_status_event(initial_event)
        self.repository.commit()
        return self.get_ticket(tenant_id=payload.tenant_id, ticket_id=ticket.id)

    def list_tickets(self, tenant_id: uuid.UUID) -> list[TicketListItem]:
        return [self._to_list_item(ticket) for ticket in self.repository.list_tickets(tenant_id)]

    def get_ticket(self, tenant_id: uuid.UUID, ticket_id: uuid.UUID) -> TicketDetail:
        ticket = self.repository.get_ticket(tenant_id=tenant_id, ticket_id=ticket_id)
        if ticket is None:
            raise TicketNotFoundError("ticket not found")
        return self._to_detail(ticket)

    def change_status(self, ticket_id: uuid.UUID, payload: TicketStatusChange) -> TicketDetail:
        ticket = self.repository.get_ticket(tenant_id=payload.tenant_id, ticket_id=ticket_id)
        if ticket is None:
            raise TicketNotFoundError("ticket not found")
        self._ensure_transition_allowed(ticket.status, payload.to_status)

        previous_status = ticket.status
        ticket.status = payload.to_status
        ticket.updated_at = datetime.now(UTC)
        event = TicketStatusEvent(
            tenant_id=payload.tenant_id,
            ticket_id=ticket.id,
            from_status=previous_status,
            to_status=payload.to_status,
            reason_text=payload.reason_text,
            changed_by_type=payload.changed_by_type,
            changed_by_user_id=payload.changed_by_user_id,
        )
        self.repository.add_status_event(event)
        self.repository.commit()
        return self.get_ticket(tenant_id=payload.tenant_id, ticket_id=ticket.id)

    def _ensure_transition_allowed(self, from_status: str, to_status: str) -> None:
        allowed = ALLOWED_TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            raise TicketStateTransitionError(
                f"illegal ticket status transition: {from_status} -> {to_status}"
            )

    def _to_detail(self, ticket: Ticket) -> TicketDetail:
        return TicketDetail(
            **self._to_list_item(ticket).model_dump(),
            description_text=ticket.description_text,
            assigned_user_id=ticket.assigned_user_id,
            created_by_user_id=ticket.created_by_user_id,
            messages=[
                TicketMessageRead(
                    id=message.id,
                    sender_type=message.sender_type,
                    sender_user_id=message.sender_user_id,
                    message_text=message.message_text,
                    message_format=message.message_format,
                    created_at=message.created_at,
                )
                for message in self.repository.list_messages(ticket.tenant_id, ticket.id)
            ],
            status_events=[
                TicketStatusEventRead(
                    id=event.id,
                    from_status=event.from_status,
                    to_status=event.to_status,
                    reason_text=event.reason_text,
                    changed_by_type=event.changed_by_type,
                    changed_by_user_id=event.changed_by_user_id,
                    created_at=event.created_at,
                )
                for event in self.repository.list_status_events(ticket.tenant_id, ticket.id)
            ],
        )

    def _to_list_item(self, ticket: Ticket) -> TicketListItem:
        return TicketListItem(
            id=ticket.id,
            tenant_id=ticket.tenant_id,
            ticket_no=ticket.ticket_no,
            title=ticket.title,
            category_code=ticket.category_code,
            priority=ticket.priority,
            risk_level=ticket.risk_level,
            status=ticket.status,
            source_channel=ticket.source_channel,
            requester_name=ticket.requester_name,
            requester_contact=ticket.requester_contact,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )

    def _new_ticket_no(self) -> str:
        return f"TCK-{datetime.now(UTC):%Y%m%d%H%M%S}-{uuid.uuid4().hex[:8].upper()}"
