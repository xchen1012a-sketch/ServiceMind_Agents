import uuid
from datetime import UTC, datetime

from app.models import ApprovalRequest, McpServer, McpTool, Ticket, TicketStatusEvent, ToolCall
from app.modules.mcp_tools.schemas import ToolCallCreate
from app.modules.mcp_tools.service import McpToolService


def test_low_risk_tool_call_executes_and_records_output() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryMcpToolRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id))
    service = McpToolService(repository)

    result = service.call_tool(
        ToolCallCreate(
            tenant_id=tenant_id,
            agent_run_id=uuid.uuid4(),
            tool_name="ticket.get_context",
            input_payload={"ticket_id": str(ticket.id)},
        )
    )

    assert result.status == "completed"
    assert result.output_payload == {
        "ticket_id": str(ticket.id),
        "status": "new",
        "priority": "medium",
        "risk_level": "low",
        "title": "MCP 工单",
    }
    assert result.approval_request_id is None
    assert repository.tool_calls[0].status == "completed"


def test_high_risk_tool_call_creates_pending_approval_without_executing() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryMcpToolRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id, status="new"))
    service = McpToolService(repository)

    result = service.call_tool(
        ToolCallCreate(
            tenant_id=tenant_id,
            agent_run_id=uuid.uuid4(),
            agent_run_step_id=uuid.uuid4(),
            tool_name="ticket.transition_status",
            input_payload={
                "ticket_id": str(ticket.id),
                "to_status": "triaged",
                "reason_text": "需要人工确认",
            },
        )
    )

    assert result.status == "waiting_approval"
    assert result.output_payload is None
    assert result.approval_request_id == repository.approval_requests[0].id
    assert repository.approval_requests[0].status == "pending"
    assert repository.approval_requests[0].risk_level == "high"
    assert ticket.status == "new"
    assert repository.status_events == []


def test_execute_approved_high_risk_tool_updates_ticket_and_call() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryMcpToolRepository()
    ticket = repository.add_ticket(make_ticket(tenant_id, status="new"))
    service = McpToolService(repository)
    pending = service.call_tool(
        ToolCallCreate(
            tenant_id=tenant_id,
            agent_run_id=uuid.uuid4(),
            tool_name="ticket.transition_status",
            input_payload={
                "ticket_id": str(ticket.id),
                "to_status": "triaged",
                "reason_text": "审批通过",
            },
        )
    )

    output = service.execute_approved_tool_call(tenant_id, pending.id)

    assert output["ticket_id"] == str(ticket.id)
    assert output["from_status"] == "new"
    assert output["to_status"] == "triaged"
    assert ticket.status == "triaged"
    assert repository.tool_calls[0].status == "completed"
    assert repository.status_events[0].agent_run_id == repository.tool_calls[0].agent_run_id


class InMemoryMcpToolRepository:
    def __init__(self) -> None:
        self.servers: list[McpServer] = []
        self.tools: list[McpTool] = []
        self.tool_calls: list[ToolCall] = []
        self.approval_requests: list[ApprovalRequest] = []
        self.tickets: list[Ticket] = []
        self.status_events: list[TicketStatusEvent] = []
        self.commits = 0

    def get_server_by_code(self, tenant_id: uuid.UUID, code: str) -> McpServer | None:
        return next(
            (
                server
                for server in self.servers
                if server.tenant_id == tenant_id and server.code == code
            ),
            None,
        )

    def add_server(self, server: McpServer) -> None:
        self._ensure_identity(server)
        self.servers.append(server)

    def get_tool_by_name(self, tenant_id: uuid.UUID, tool_name: str) -> McpTool | None:
        return next(
            (
                tool
                for tool in self.tools
                if tool.tenant_id == tenant_id and tool.tool_name == tool_name
            ),
            None,
        )

    def add_tool(self, tool: McpTool) -> None:
        self._ensure_identity(tool)
        self.tools.append(tool)

    def add_tool_call(self, tool_call: ToolCall) -> None:
        self._ensure_identity(tool_call)
        self.tool_calls.append(tool_call)

    def get_tool_call(self, tenant_id: uuid.UUID, tool_call_id: uuid.UUID) -> ToolCall | None:
        return next(
            (
                tool_call
                for tool_call in self.tool_calls
                if tool_call.tenant_id == tenant_id and tool_call.id == tool_call_id
            ),
            None,
        )

    def add_approval_request(self, approval_request: ApprovalRequest) -> None:
        self._ensure_identity(approval_request)
        self.approval_requests.append(approval_request)

    def get_ticket(self, tenant_id: uuid.UUID, ticket_id: uuid.UUID) -> Ticket | None:
        return next(
            (
                ticket
                for ticket in self.tickets
                if ticket.tenant_id == tenant_id and ticket.id == ticket_id
            ),
            None,
        )

    def add_status_event(self, event: TicketStatusEvent) -> None:
        self._ensure_identity(event)
        self.status_events.append(event)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        pass

    def add_ticket(self, ticket: Ticket) -> Ticket:
        self._ensure_identity(ticket)
        self.tickets.append(ticket)
        return ticket

    def _ensure_identity(
        self,
        item: ApprovalRequest | McpServer | McpTool | Ticket | TicketStatusEvent | ToolCall,
    ) -> None:
        now = datetime.now(UTC)
        if item.id is None:
            item.id = uuid.uuid4()
        if getattr(item, "created_at", None) is None:
            item.created_at = now
        if hasattr(item, "updated_at") and getattr(item, "updated_at", None) is None:
            item.updated_at = now


def make_ticket(tenant_id: uuid.UUID, **overrides: str) -> Ticket:
    now = datetime.now(UTC)
    return Ticket(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        ticket_no=f"TCK-{uuid.uuid4().hex[:8]}",
        title=overrides.get("title", "MCP 工单"),
        description_text=overrides.get("description_text", "需要工具处理"),
        category_code=overrides.get("category_code", "general"),
        priority=overrides.get("priority", "medium"),
        risk_level=overrides.get("risk_level", "low"),
        status=overrides.get("status", "new"),
        source_channel=overrides.get("source_channel", "web"),
        created_at=now,
        updated_at=now,
    )
