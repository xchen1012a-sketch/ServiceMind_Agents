import uuid
from datetime import UTC, datetime
from time import perf_counter

from app.models import ApprovalRequest, McpServer, McpTool, Ticket, TicketStatusEvent, ToolCall
from app.modules.mcp_tools.repository import McpToolRepository
from app.modules.mcp_tools.schemas import McpToolRead, ToolCallCreate, ToolCallRead

MOCK_SERVER_CODE = "mock_ticket_ops"


class McpToolNotFoundError(Exception):
    pass


class McpToolExecutionError(Exception):
    pass


class McpToolApprovalError(Exception):
    pass


class McpToolService:
    def __init__(self, repository: McpToolRepository) -> None:
        self.repository = repository

    def list_tools(self, tenant_id: uuid.UUID) -> list[McpToolRead]:
        self._ensure_mock_tools(tenant_id)
        return [
            self._tool_to_read(tool)
            for tool_name in ("ticket.get_context", "ticket.transition_status")
            if (tool := self.repository.get_tool_by_name(tenant_id, tool_name)) is not None
        ]

    def call_tool(self, payload: ToolCallCreate) -> ToolCallRead:
        self._ensure_mock_tools(payload.tenant_id)
        tool = self.repository.get_tool_by_name(payload.tenant_id, payload.tool_name)
        if tool is None:
            raise McpToolNotFoundError("mcp tool not found")

        started = perf_counter()
        input_payload = dict(payload.input_payload)
        input_payload["agent_run_id"] = str(payload.agent_run_id)
        tool_call = ToolCall(
            tenant_id=payload.tenant_id,
            agent_run_id=payload.agent_run_id,
            agent_run_step_id=payload.agent_run_step_id,
            mcp_server_id=tool.mcp_server_id,
            mcp_tool_id=tool.id,
            status="waiting_approval" if tool.requires_approval else "completed",
            input_payload=input_payload,
            output_payload=None,
            latency_ms=None,
            created_at=datetime.now(UTC),
        )
        self.repository.add_tool_call(tool_call)

        if tool.requires_approval:
            approval_request = self._create_approval_request(payload, tool_call, tool)
            tool_call.approval_request_id = approval_request.id
            self.repository.commit()
            return self._tool_call_to_read(tool_call)

        try:
            tool_call.output_payload = self._execute_tool(payload.tenant_id, tool.tool_name, input_payload)
            tool_call.latency_ms = int((perf_counter() - started) * 1000)
        except Exception as exc:
            tool_call.status = "failed"
            tool_call.error_code = exc.__class__.__name__
            tool_call.error_message = str(exc)
            self.repository.commit()
            raise

        self.repository.commit()
        return self._tool_call_to_read(tool_call)

    def execute_approved_tool_call(self, tenant_id: uuid.UUID, tool_call_id: uuid.UUID) -> dict:
        tool_call = self.repository.get_tool_call(tenant_id, tool_call_id)
        if tool_call is None:
            raise McpToolNotFoundError("tool call not found")
        if tool_call.status != "waiting_approval":
            raise McpToolApprovalError("only waiting approval tool calls can be executed")

        tool = self._tool_by_id(tenant_id, tool_call.mcp_tool_id)
        started = perf_counter()
        output = self._execute_tool(tenant_id, tool.tool_name, tool_call.input_payload)
        tool_call.status = "completed"
        tool_call.output_payload = output
        tool_call.latency_ms = int((perf_counter() - started) * 1000)
        return output

    def reject_tool_call(self, tenant_id: uuid.UUID, tool_call_id: uuid.UUID) -> None:
        tool_call = self.repository.get_tool_call(tenant_id, tool_call_id)
        if tool_call is None:
            raise McpToolNotFoundError("tool call not found")
        if tool_call.status == "waiting_approval":
            tool_call.status = "rejected"

    def _create_approval_request(
        self,
        payload: ToolCallCreate,
        tool_call: ToolCall,
        tool: McpTool,
    ) -> ApprovalRequest:
        ticket_id = self._ticket_id_from_payload(payload.input_payload)
        approval_request = ApprovalRequest(
            tenant_id=payload.tenant_id,
            ticket_id=ticket_id,
            agent_run_id=payload.agent_run_id,
            tool_call_id=tool_call.id,
            action_type=tool.tool_name,
            risk_level=tool.risk_level,
            reason_text=str(payload.input_payload.get("reason_text") or "high risk tool call"),
            proposed_payload=payload.input_payload,
            status="pending",
            requested_by_type="agent",
            requested_by_user_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.repository.add_approval_request(approval_request)
        return approval_request

    def _execute_tool(self, tenant_id: uuid.UUID, tool_name: str, input_payload: dict) -> dict:
        if tool_name == "ticket.get_context":
            ticket = self._get_ticket_from_payload(tenant_id, input_payload)
            return {
                "ticket_id": str(ticket.id),
                "status": ticket.status,
                "priority": ticket.priority,
                "risk_level": ticket.risk_level,
                "title": ticket.title,
            }
        if tool_name == "ticket.transition_status":
            return self._transition_ticket_status(tenant_id, input_payload)
        raise McpToolNotFoundError("mcp tool not found")

    def _transition_ticket_status(self, tenant_id: uuid.UUID, input_payload: dict) -> dict:
        ticket = self._get_ticket_from_payload(tenant_id, input_payload)
        to_status = str(input_payload.get("to_status") or "")
        if not to_status:
            raise McpToolExecutionError("to_status is required")

        from_status = ticket.status
        ticket.status = to_status
        ticket.updated_at = datetime.now(UTC)
        self.repository.add_status_event(
            TicketStatusEvent(
                tenant_id=tenant_id,
                ticket_id=ticket.id,
                from_status=from_status,
                to_status=to_status,
                reason_text=str(input_payload.get("reason_text") or "approved tool execution"),
                changed_by_type="agent_tool",
                changed_by_user_id=None,
                agent_run_id=uuid.UUID(str(input_payload["agent_run_id"]))
                if input_payload.get("agent_run_id")
                else None,
                created_at=datetime.now(UTC),
            )
        )
        return {
            "ticket_id": str(ticket.id),
            "from_status": from_status,
            "to_status": to_status,
        }

    def _get_ticket_from_payload(self, tenant_id: uuid.UUID, input_payload: dict) -> Ticket:
        ticket_id = self._ticket_id_from_payload(input_payload)
        if ticket_id is None:
            raise McpToolExecutionError("ticket_id is required")
        ticket = self.repository.get_ticket(tenant_id, ticket_id)
        if ticket is None:
            raise McpToolExecutionError("ticket not found")
        return ticket

    def _ticket_id_from_payload(self, input_payload: dict) -> uuid.UUID | None:
        raw_ticket_id = input_payload.get("ticket_id")
        if raw_ticket_id is None:
            return None
        return uuid.UUID(str(raw_ticket_id))

    def _ensure_mock_tools(self, tenant_id: uuid.UUID) -> McpServer:
        server = self.repository.get_server_by_code(tenant_id, MOCK_SERVER_CODE)
        if server is None:
            server = McpServer(
                tenant_id=tenant_id,
                code=MOCK_SERVER_CODE,
                name="Mock Ticket Operations",
                transport_type="in_process",
                endpoint_url=None,
                status="active",
            )
            self.repository.add_server(server)

        for tool in self._default_tools(tenant_id, server.id):
            if self.repository.get_tool_by_name(tenant_id, tool.tool_name) is None:
                self.repository.add_tool(tool)
        return server

    def _default_tools(self, tenant_id: uuid.UUID, server_id: uuid.UUID) -> list[McpTool]:
        return [
            McpTool(
                tenant_id=tenant_id,
                mcp_server_id=server_id,
                tool_name="ticket.get_context",
                display_name="Get ticket context",
                description_text="Read ticket context for Agent reasoning.",
                input_schema_json={"required": ["ticket_id"]},
                output_schema_json={"required": ["ticket_id", "status"]},
                risk_level="low",
                requires_approval=False,
                status="active",
            ),
            McpTool(
                tenant_id=tenant_id,
                mcp_server_id=server_id,
                tool_name="ticket.transition_status",
                display_name="Transition ticket status",
                description_text="Change ticket status after human approval.",
                input_schema_json={"required": ["ticket_id", "to_status"]},
                output_schema_json={"required": ["ticket_id", "from_status", "to_status"]},
                risk_level="high",
                requires_approval=True,
                status="active",
            ),
        ]

    def _tool_by_id(self, tenant_id: uuid.UUID, tool_id: uuid.UUID) -> McpTool:
        for tool_name in ("ticket.get_context", "ticket.transition_status"):
            tool = self.repository.get_tool_by_name(tenant_id, tool_name)
            if tool is not None and tool.id == tool_id:
                return tool
        raise McpToolNotFoundError("mcp tool not found")

    def _tool_to_read(self, tool: McpTool) -> McpToolRead:
        return McpToolRead(
            id=tool.id,
            mcp_server_id=tool.mcp_server_id,
            tool_name=tool.tool_name,
            display_name=tool.display_name,
            description_text=tool.description_text,
            risk_level=tool.risk_level,
            requires_approval=tool.requires_approval,
            status=tool.status,
        )

    def _tool_call_to_read(self, tool_call: ToolCall) -> ToolCallRead:
        return ToolCallRead(
            id=tool_call.id,
            tenant_id=tool_call.tenant_id,
            agent_run_id=tool_call.agent_run_id,
            agent_run_step_id=tool_call.agent_run_step_id,
            mcp_server_id=tool_call.mcp_server_id,
            mcp_tool_id=tool_call.mcp_tool_id,
            status=tool_call.status,
            input_payload=tool_call.input_payload,
            output_payload=tool_call.output_payload,
            error_code=tool_call.error_code,
            error_message=tool_call.error_message,
            approval_request_id=tool_call.approval_request_id,
            created_at=tool_call.created_at,
        )
