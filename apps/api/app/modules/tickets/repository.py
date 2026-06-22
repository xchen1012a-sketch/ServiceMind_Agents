import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Ticket, TicketMessage, TicketStatusEvent


class TicketRepository(Protocol):
    def add_ticket(self, ticket: Ticket) -> None: ...

    def add_message(self, message: TicketMessage) -> None: ...

    def add_status_event(self, event: TicketStatusEvent) -> None: ...

    def get_ticket(self, tenant_id: uuid.UUID, ticket_id: uuid.UUID) -> Ticket | None: ...

    def list_tickets(self, tenant_id: uuid.UUID) -> list[Ticket]: ...

    def list_messages(self, tenant_id: uuid.UUID, ticket_id: uuid.UUID) -> list[TicketMessage]: ...

    def list_status_events(
        self, tenant_id: uuid.UUID, ticket_id: uuid.UUID
    ) -> list[TicketStatusEvent]: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class SqlAlchemyTicketRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_ticket(self, ticket: Ticket) -> None:
        self.db.add(ticket)
        self.db.flush()

    def add_message(self, message: TicketMessage) -> None:
        self.db.add(message)
        self.db.flush()

    def add_status_event(self, event: TicketStatusEvent) -> None:
        self.db.add(event)
        self.db.flush()

    def get_ticket(self, tenant_id: uuid.UUID, ticket_id: uuid.UUID) -> Ticket | None:
        statement = select(Ticket).where(
            Ticket.tenant_id == tenant_id,
            Ticket.id == ticket_id,
            Ticket.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def list_tickets(self, tenant_id: uuid.UUID) -> list[Ticket]:
        statement = (
            select(Ticket)
            .where(Ticket.tenant_id == tenant_id, Ticket.deleted_at.is_(None))
            .order_by(Ticket.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def list_messages(self, tenant_id: uuid.UUID, ticket_id: uuid.UUID) -> list[TicketMessage]:
        statement = (
            select(TicketMessage)
            .where(TicketMessage.tenant_id == tenant_id, TicketMessage.ticket_id == ticket_id)
            .order_by(TicketMessage.created_at.asc())
        )
        return list(self.db.scalars(statement).all())

    def list_status_events(
        self, tenant_id: uuid.UUID, ticket_id: uuid.UUID
    ) -> list[TicketStatusEvent]:
        statement = (
            select(TicketStatusEvent)
            .where(
                TicketStatusEvent.tenant_id == tenant_id,
                TicketStatusEvent.ticket_id == ticket_id,
            )
            .order_by(TicketStatusEvent.created_at.asc())
        )
        return list(self.db.scalars(statement).all())

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
