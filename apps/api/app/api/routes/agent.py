import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.security import RequestContext, get_request_context
from app.db.session import get_db
from app.modules.agent.repository import SqlAlchemyAgentRepository
from app.modules.agent.schemas import (
    AgentRunRead,
    AgentRunResume,
    AgentRunResumeInput,
    AgentRunStart,
    AgentRunStartInput,
)
from app.modules.agent.service import (
    AgentRunNotFoundError,
    AgentRunResumeError,
    AgentRunService,
    AgentTicketNotFoundError,
)
from app.modules.approval.repository import SqlAlchemyApprovalRepository
from app.modules.approval.service import ApprovalService
from app.modules.knowledge.repository import SqlAlchemyKnowledgeRepository
from app.modules.knowledge.service import KnowledgeService
from app.modules.mcp_tools.repository import SqlAlchemyMcpToolRepository
from app.modules.mcp_tools.service import McpToolService

router = APIRouter(tags=["agent"])


def get_agent_run_service(db: Session = Depends(get_db)) -> AgentRunService:
    mcp_tool_service = McpToolService(SqlAlchemyMcpToolRepository(db))
    return AgentRunService(
        SqlAlchemyAgentRepository(db),
        knowledge_service=KnowledgeService(SqlAlchemyKnowledgeRepository(db)),
        mcp_tool_service=mcp_tool_service,
        approval_service=ApprovalService(SqlAlchemyApprovalRepository(db), mcp_tool_service),
    )


@router.post(
    "/api/v1/tickets/{ticket_id}/agent-runs",
    response_model=AgentRunRead,
    status_code=status.HTTP_201_CREATED,
)
def start_ticket_agent_run(
    ticket_id: uuid.UUID,
    payload: AgentRunStartInput,
    context: RequestContext = Depends(get_request_context),
    service: AgentRunService = Depends(get_agent_run_service),
) -> AgentRunRead:
    context.require("agent:run")
    try:
        return service.start_ticket_run(
            ticket_id=ticket_id,
            payload=AgentRunStart(tenant_id=context.tenant_id),
        )
    except AgentTicketNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/api/v1/agent-runs/{agent_run_id}/resume", response_model=AgentRunRead)
def resume_agent_run(
    agent_run_id: uuid.UUID,
    payload: AgentRunResumeInput,
    context: RequestContext = Depends(get_request_context),
    service: AgentRunService = Depends(get_agent_run_service),
) -> AgentRunRead:
    context.require("agent:approve")
    try:
        return service.resume_run(
            agent_run_id=agent_run_id,
            payload=AgentRunResume(
                **payload.model_dump(),
                tenant_id=context.tenant_id,
                decided_by_user_id=context.user_id,
            ),
        )
    except AgentRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AgentRunResumeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
