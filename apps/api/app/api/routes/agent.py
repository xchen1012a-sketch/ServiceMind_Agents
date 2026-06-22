import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.agent.repository import SqlAlchemyAgentRepository
from app.modules.agent.schemas import AgentRunRead, AgentRunResume, AgentRunStart
from app.modules.agent.service import (
    AgentRunNotFoundError,
    AgentRunResumeError,
    AgentRunService,
    AgentTicketNotFoundError,
)

router = APIRouter(tags=["agent"])


def get_agent_run_service(db: Session = Depends(get_db)) -> AgentRunService:
    return AgentRunService(SqlAlchemyAgentRepository(db))


@router.post(
    "/api/v1/tickets/{ticket_id}/agent-runs",
    response_model=AgentRunRead,
    status_code=status.HTTP_201_CREATED,
)
def start_ticket_agent_run(
    ticket_id: uuid.UUID,
    payload: AgentRunStart,
    service: AgentRunService = Depends(get_agent_run_service),
) -> AgentRunRead:
    try:
        return service.start_ticket_run(ticket_id=ticket_id, payload=payload)
    except AgentTicketNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/api/v1/agent-runs/{agent_run_id}/resume", response_model=AgentRunRead)
def resume_agent_run(
    agent_run_id: uuid.UUID,
    payload: AgentRunResume,
    service: AgentRunService = Depends(get_agent_run_service),
) -> AgentRunRead:
    try:
        return service.resume_run(agent_run_id=agent_run_id, payload=payload)
    except AgentRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AgentRunResumeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
