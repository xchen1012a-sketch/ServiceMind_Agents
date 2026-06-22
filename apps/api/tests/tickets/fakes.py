import uuid
from datetime import UTC, datetime

from app.models import Ticket, TicketMessage, TicketStatusEvent


class InMemoryTicketRepository:
    def __init__(self) -> None:
        self.tickets: list[Ticket] = []
        self.messages: list[TicketMessage] = []
        self.status_events: list[TicketStatusEvent] = []
        self.commits = 0

    def add_ticket(self, ticket: Ticket) -> None:
        self._ensure_identity(ticket)
        self.tickets.append(ticket)

    def add_message(self, message: TicketMessage) -> None:
        self._ensure_identity(message)
        self.messages.append(message)

    def add_status_event(self, event: TicketStatusEvent) -> None:
        self._ensure_identity(event)
        self.status_events.append(event)

    def get_ticket(self, tenant_id: uuid.UUID, ticket_id: uuid.UUID) -> Ticket | None:
        return next(
            (
                ticket
                for ticket in self.tickets
                if ticket.tenant_id == tenant_id and ticket.id == ticket_id
            ),
            None,
        )

    def list_tickets(self, tenant_id: uuid.UUID) -> list[Ticket]:
        return [ticket for ticket in self.tickets if ticket.tenant_id == tenant_id]

    def list_messages(self, tenant_id: uuid.UUID, ticket_id: uuid.UUID) -> list[TicketMessage]:
        return [
            message
            for message in self.messages
            if message.tenant_id == tenant_id and message.ticket_id == ticket_id
        ]

    def list_status_events(
        self, tenant_id: uuid.UUID, ticket_id: uuid.UUID
    ) -> list[TicketStatusEvent]:
        return [
            event
            for event in self.status_events
            if event.tenant_id == tenant_id and event.ticket_id == ticket_id
        ]

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        pass

    def _ensure_identity(self, item: Ticket | TicketMessage | TicketStatusEvent) -> None:
        now = datetime.now(UTC)
        if item.id is None:
            item.id = uuid.uuid4()
        if item.created_at is None:
            item.created_at = now
        if hasattr(item, "updated_at") and getattr(item, "updated_at", None) is None:
            item.updated_at = now
