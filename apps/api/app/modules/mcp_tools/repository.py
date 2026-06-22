import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApprovalRequest, McpServer, McpTool, Ticket, TicketStatusEvent, ToolCall


class McpToolRepository(Protocol):
    def get_server_by_code(self, tenant_id: uuid.UUID, code: str) -> McpServer | None: ...

    def add_server(self, server: McpServer) -> None: ...

    def get_tool_by_name(self, tenant_id: uuid.UUID, tool_name: str) -> McpTool | None: ...

    def add_tool(self, tool: McpTool) -> None: ...

    def add_tool_call(self, tool_call: ToolCall) -> None: ...

    def get_tool_call(self, tenant_id: uuid.UUID, tool_call_id: uuid.UUID) -> ToolCall | None: ...

    def add_approval_request(self, approval_request: ApprovalRequest) -> None: ...

    def get_ticket(self, tenant_id: uuid.UUID, ticket_id: uuid.UUID) -> Ticket | None: ...

    def add_status_event(self, event: TicketStatusEvent) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class SqlAlchemyMcpToolRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_server_by_code(self, tenant_id: uuid.UUID, code: str) -> McpServer | None:
        statement = select(McpServer).where(
            McpServer.tenant_id == tenant_id,
            McpServer.code == code,
        )
        return self.db.scalar(statement)

    def add_server(self, server: McpServer) -> None:
        self.db.add(server)
        self.db.flush()

    def get_tool_by_name(self, tenant_id: uuid.UUID, tool_name: str) -> McpTool | None:
        statement = select(McpTool).where(
            McpTool.tenant_id == tenant_id,
            McpTool.tool_name == tool_name,
            McpTool.status == "active",
        )
        return self.db.scalar(statement)

    def add_tool(self, tool: McpTool) -> None:
        self.db.add(tool)
        self.db.flush()

    def add_tool_call(self, tool_call: ToolCall) -> None:
        self.db.add(tool_call)
        self.db.flush()

    def get_tool_call(self, tenant_id: uuid.UUID, tool_call_id: uuid.UUID) -> ToolCall | None:
        statement = select(ToolCall).where(
            ToolCall.tenant_id == tenant_id,
            ToolCall.id == tool_call_id,
        )
        return self.db.scalar(statement)

    def add_approval_request(self, approval_request: ApprovalRequest) -> None:
        self.db.add(approval_request)
        self.db.flush()

    def get_ticket(self, tenant_id: uuid.UUID, ticket_id: uuid.UUID) -> Ticket | None:
        statement = select(Ticket).where(
            Ticket.tenant_id == tenant_id,
            Ticket.id == ticket_id,
            Ticket.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def add_status_event(self, event: TicketStatusEvent) -> None:
        self.db.add(event)
        self.db.flush()

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
