import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.security import RequestContext, get_request_context
from app.db.session import get_db
from app.modules.approval.repository import SqlAlchemyApprovalRepository
from app.modules.approval.schemas import (
    ApprovalDecisionCreate,
    ApprovalDecisionInput,
    ApprovalRequestRead,
)
from app.modules.approval.service import (
    ApprovalDecisionError,
    ApprovalNotFoundError,
    ApprovalService,
)
from app.modules.mcp_tools.repository import SqlAlchemyMcpToolRepository
from app.modules.mcp_tools.service import McpToolService

router = APIRouter(prefix="/api/v1/approval-requests", tags=["approval"])


def get_approval_service(db: Session = Depends(get_db)) -> ApprovalService:
    return ApprovalService(
        SqlAlchemyApprovalRepository(db),
        McpToolService(SqlAlchemyMcpToolRepository(db)),
    )


@router.post("/{approval_request_id}/decision", response_model=ApprovalRequestRead)
def decide_approval_request(
    approval_request_id: uuid.UUID,
    payload: ApprovalDecisionInput,
    context: RequestContext = Depends(get_request_context),
    service: ApprovalService = Depends(get_approval_service),
) -> ApprovalRequestRead:
    context.require("approval:decide")
    try:
        return service.decide(
            approval_request_id,
            ApprovalDecisionCreate(
                **payload.model_dump(),
                tenant_id=context.tenant_id,
                decided_by_user_id=context.user_id,
            ),
        )
    except ApprovalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ApprovalDecisionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
