import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.tickets.repository import SqlAlchemyTicketRepository
from app.modules.tickets.schemas import (
    TicketCreate,
    TicketDetail,
    TicketListItem,
    TicketStatusChange,
)
from app.modules.tickets.service import (
    TicketNotFoundError,
    TicketService,
    TicketStateTransitionError,
)

router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])


def get_ticket_service(db: Session = Depends(get_db)) -> TicketService:
    return TicketService(SqlAlchemyTicketRepository(db))


@router.post("", response_model=TicketDetail, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    service: TicketService = Depends(get_ticket_service),
) -> TicketDetail:
    return service.create_ticket(payload)


@router.get("", response_model=list[TicketListItem])
def list_tickets(
    tenant_id: uuid.UUID = Query(...),
    service: TicketService = Depends(get_ticket_service),
) -> list[TicketListItem]:
    return service.list_tickets(tenant_id)


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(
    ticket_id: uuid.UUID,
    tenant_id: uuid.UUID = Query(...),
    service: TicketService = Depends(get_ticket_service),
) -> TicketDetail:
    try:
        return service.get_ticket(tenant_id=tenant_id, ticket_id=ticket_id)
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{ticket_id}/status", response_model=TicketDetail)
def change_ticket_status(
    ticket_id: uuid.UUID,
    payload: TicketStatusChange,
    service: TicketService = Depends(get_ticket_service),
) -> TicketDetail:
    try:
        return service.change_status(ticket_id=ticket_id, payload=payload)
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TicketStateTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
