import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.security import RequestContext, get_request_context
from app.db.session import get_db
from app.modules.tickets.repository import SqlAlchemyTicketRepository
from app.modules.tickets.schemas import (
    TicketCreate,
    TicketCreateInput,
    TicketDetail,
    TicketListItem,
    TicketStatusChange,
    TicketStatusChangeInput,
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
    payload: TicketCreateInput,
    context: RequestContext = Depends(get_request_context),
    service: TicketService = Depends(get_ticket_service),
) -> TicketDetail:
    context.require("tickets:create")
    return service.create_ticket(
        TicketCreate(
            **payload.model_dump(),
            tenant_id=context.tenant_id,
            created_by_user_id=context.user_id,
        )
    )


@router.get("", response_model=list[TicketListItem])
def list_tickets(
    context: RequestContext = Depends(get_request_context),
    service: TicketService = Depends(get_ticket_service),
) -> list[TicketListItem]:
    context.require("tickets:read")
    return service.list_tickets(context.tenant_id)


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(
    ticket_id: uuid.UUID,
    context: RequestContext = Depends(get_request_context),
    service: TicketService = Depends(get_ticket_service),
) -> TicketDetail:
    context.require("tickets:read")
    try:
        return service.get_ticket(tenant_id=context.tenant_id, ticket_id=ticket_id)
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{ticket_id}/status", response_model=TicketDetail)
def change_ticket_status(
    ticket_id: uuid.UUID,
    payload: TicketStatusChangeInput,
    context: RequestContext = Depends(get_request_context),
    service: TicketService = Depends(get_ticket_service),
) -> TicketDetail:
    context.require("tickets:update")
    try:
        return service.change_status(
            ticket_id=ticket_id,
            payload=TicketStatusChange(
                **payload.model_dump(),
                tenant_id=context.tenant_id,
                changed_by_type="user",
                changed_by_user_id=context.user_id,
            ),
        )
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TicketStateTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
