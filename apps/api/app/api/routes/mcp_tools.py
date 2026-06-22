from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.security import RequestContext, get_request_context
from app.db.session import get_db
from app.modules.mcp_tools.repository import SqlAlchemyMcpToolRepository
from app.modules.mcp_tools.schemas import (
    McpToolRead,
    ToolCallCreate,
    ToolCallCreateInput,
    ToolCallRead,
)
from app.modules.mcp_tools.service import (
    McpToolApprovalError,
    McpToolExecutionError,
    McpToolNotFoundError,
    McpToolService,
)

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp-tools"])


def get_mcp_tool_service(db: Session = Depends(get_db)) -> McpToolService:
    return McpToolService(SqlAlchemyMcpToolRepository(db))


@router.get("/tools", response_model=list[McpToolRead])
def list_mcp_tools(
    context: RequestContext = Depends(get_request_context),
    service: McpToolService = Depends(get_mcp_tool_service),
) -> list[McpToolRead]:
    context.require("mcp-tools:read")
    return service.list_tools(context.tenant_id)


@router.post(
    "/tools/{tool_name}/call",
    response_model=ToolCallRead,
    status_code=status.HTTP_201_CREATED,
)
def call_mcp_tool(
    tool_name: str,
    payload: ToolCallCreateInput,
    context: RequestContext = Depends(get_request_context),
    service: McpToolService = Depends(get_mcp_tool_service),
) -> ToolCallRead:
    context.require("mcp-tools:call")
    try:
        return service.call_tool(
            ToolCallCreate(
                **payload.model_dump(),
                tenant_id=context.tenant_id,
                tool_name=tool_name,
            )
        )
    except McpToolNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (McpToolApprovalError, McpToolExecutionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
