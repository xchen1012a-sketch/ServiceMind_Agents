import uuid
from datetime import UTC, datetime
from typing import Protocol

from app.models import AgentRun, AgentRunStep, Ticket
from app.modules.agent.repository import AgentRepository
from app.modules.agent.runtime import LangGraphTicketRuntime, RuntimeStep
from app.modules.agent.schemas import AgentRunRead, AgentRunResume, AgentRunStart, AgentRunStepRead
from app.modules.approval.schemas import ApprovalDecisionCreate, ApprovalRequestRead
from app.modules.knowledge.schemas import (
    KnowledgeSearchHitRead,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.modules.mcp_tools.schemas import ToolCallCreate, ToolCallRead


class AgentKnowledgeSearchService(Protocol):
    def search(self, payload: KnowledgeSearchRequest) -> KnowledgeSearchResponse: ...


class AgentMcpToolService(Protocol):
    def call_tool(self, payload: ToolCallCreate) -> ToolCallRead: ...


class AgentApprovalService(Protocol):
    def decide(
        self,
        approval_request_id: uuid.UUID | None,
        payload: ApprovalDecisionCreate,
    ) -> ApprovalRequestRead: ...


class AgentTicketNotFoundError(Exception):
    pass


class AgentRunNotFoundError(Exception):
    pass


class AgentRunResumeError(Exception):
    pass


class AgentRunService:
    def __init__(
        self,
        repository: AgentRepository,
        runtime: LangGraphTicketRuntime | None = None,
        knowledge_service: AgentKnowledgeSearchService | None = None,
        mcp_tool_service: AgentMcpToolService | None = None,
        approval_service: AgentApprovalService | None = None,
    ) -> None:
        self.repository = repository
        self.runtime = runtime or LangGraphTicketRuntime()
        self.knowledge_service = knowledge_service
        self.mcp_tool_service = mcp_tool_service
        self.approval_service = approval_service

    def start_ticket_run(self, ticket_id: uuid.UUID, payload: AgentRunStart) -> AgentRunRead:
        ticket = self.repository.get_ticket(tenant_id=payload.tenant_id, ticket_id=ticket_id)
        if ticket is None:
            raise AgentTicketNotFoundError("ticket not found")

        started_at = datetime.now(UTC)
        run = AgentRun(
            tenant_id=payload.tenant_id,
            ticket_id=ticket.id,
            runtime_type=self.runtime.runtime_type,
            status="running",
            started_at=started_at,
        )
        self.repository.add_run(run)

        try:
            result = self.runtime.run(
                {
                    "ticket_id": str(ticket.id),
                    "title": ticket.title,
                    "category_code": ticket.category_code,
                    "priority": ticket.priority,
                    "risk_level": ticket.risk_level,
                }
            )
            order = 1
            citations: list[dict] = []
            for step in result.steps:
                if step.name == "generate_summary":
                    _, citations = self._add_retrieve_knowledge_step(
                        tenant_id=payload.tenant_id,
                        run=run,
                        ticket=ticket,
                        order=order,
                        used_in_answer=True,
                    )
                    order += 1
                    step = self._step_with_citations(step, citations)
                run_step = self._build_step(payload.tenant_id, run.id, order, step)
                self.repository.add_step(run_step)
                if step.name == "approval_gate" and step.status == "waiting_approval":
                    self._attach_approval_tool_call(payload.tenant_id, run, ticket, run_step)
                order += 1
                if step.name == "classify_ticket":
                    self._add_call_tools_step(payload.tenant_id, run, ticket, order)
                    order += 1
            run.status = result.status
            if result.status != "waiting_approval":
                run.finished_at = datetime.now(UTC)
        except Exception as exc:
            run.status = "failed"
            run.finished_at = datetime.now(UTC)
            run.error_code = exc.__class__.__name__
            run.error_message = str(exc)
            existing_steps = self.repository.list_steps(payload.tenant_id, run.id)
            error_order = max((step.step_order for step in existing_steps), default=0) + 1
            self.repository.add_step(
                AgentRunStep(
                    tenant_id=payload.tenant_id,
                    agent_run_id=run.id,
                    step_name="runtime_error",
                    step_type="error",
                    step_order=error_order,
                    status="failed",
                    input_payload={"ticket_id": str(ticket.id)},
                    output_payload=None,
                    error_code=run.error_code,
                    error_message=run.error_message,
                    started_at=started_at,
                    finished_at=run.finished_at,
                )
            )
        self.repository.commit()
        return self._to_read(run)

    def resume_run(self, agent_run_id: uuid.UUID, payload: AgentRunResume) -> AgentRunRead:
        run = self.repository.get_run(tenant_id=payload.tenant_id, agent_run_id=agent_run_id)
        if run is None:
            raise AgentRunNotFoundError("agent run not found")
        if run.status != "waiting_approval":
            raise AgentRunResumeError("only waiting_approval runs can be resumed")

        steps = self.repository.list_steps(payload.tenant_id, run.id)
        approval_step = next(
            (
                step
                for step in steps
                if step.step_name == "approval_gate" and step.status == "waiting_approval"
            ),
            None,
        )
        if approval_step is None:
            raise AgentRunResumeError("waiting approval step not found")

        now = datetime.now(UTC)
        approval_step.status = "completed" if payload.decision == "approved" else "rejected"
        approval_step.finished_at = now
        approval_result = self._decide_linked_approval(approval_step, payload)

        next_order = max((step.step_order for step in steps), default=0) + 1
        self.repository.add_step(
            AgentRunStep(
                tenant_id=payload.tenant_id,
                agent_run_id=run.id,
                step_name="approval_decision",
                step_type="approval",
                step_order=next_order,
                external_step_ref="approval_decision",
                status="completed" if payload.decision == "approved" else "rejected",
                input_payload={
                    "decision": payload.decision,
                    "decision_reason": payload.decision_reason,
                    "decided_by_user_id": (
                        str(payload.decided_by_user_id) if payload.decided_by_user_id else None
                    ),
                },
                output_payload={
                    "resume": payload.decision == "approved",
                    **approval_result,
                },
                started_at=now,
                finished_at=now,
            )
        )

        if payload.decision == "rejected":
            run.status = "rejected"
            run.finished_at = now
            self.repository.commit()
            return self._to_read(run)

        if run.ticket_id is None:
            raise AgentTicketNotFoundError("ticket not found")
        ticket = self.repository.get_ticket(tenant_id=payload.tenant_id, ticket_id=run.ticket_id)
        if ticket is None:
            raise AgentTicketNotFoundError("ticket not found")

        _, citations = self._add_retrieve_knowledge_step(
            tenant_id=payload.tenant_id,
            run=run,
            ticket=ticket,
            order=next_order + 1,
            used_in_answer=True,
        )
        summary_at = datetime.now(UTC)
        self.repository.add_step(
            AgentRunStep(
                tenant_id=payload.tenant_id,
                agent_run_id=run.id,
                step_name="generate_summary",
                step_type="generation",
                step_order=next_order + 2,
                external_step_ref="generate_summary",
                status="completed",
                input_payload={"approval": "approved", "citation_count": len(citations)},
                output_payload={
                    "summary": "approved ticket is ready for operator review",
                    "citations": citations,
                },
                started_at=summary_at,
                finished_at=summary_at,
            )
        )
        run.status = "completed"
        run.finished_at = summary_at
        self.repository.commit()
        return self._to_read(run)

    def _build_step(
        self,
        tenant_id: uuid.UUID,
        run_id: uuid.UUID,
        order: int,
        step: RuntimeStep,
    ) -> AgentRunStep:
        now = datetime.now(UTC)
        return AgentRunStep(
            tenant_id=tenant_id,
            agent_run_id=run_id,
            step_name=step.name,
            step_type=step.step_type,
            step_order=order,
            external_step_ref=step.name,
            status=step.status,
            input_payload=step.input_payload,
            output_payload=step.output_payload,
            error_code=step.error_code,
            error_message=step.error_message,
            started_at=now,
            finished_at=now if step.status != "waiting_approval" else None,
        )

    def _add_retrieve_knowledge_step(
        self,
        tenant_id: uuid.UUID,
        run: AgentRun,
        ticket: Ticket,
        order: int,
        used_in_answer: bool,
    ) -> tuple[AgentRunStep, list[dict]]:
        query_text = self._knowledge_query_text(ticket)
        now = datetime.now(UTC)
        step = AgentRunStep(
            tenant_id=tenant_id,
            agent_run_id=run.id,
            step_name="retrieve_knowledge",
            step_type="retrieval",
            step_order=order,
            external_step_ref="retrieve_knowledge",
            status="running",
            input_payload={"query_text": query_text, "top_k": 5},
            output_payload=None,
            started_at=now,
            finished_at=None,
        )
        self.repository.add_step(step)

        if self.knowledge_service is None:
            citations: list[dict] = []
            rag_query_id = None
        else:
            search_result = self.knowledge_service.search(
                KnowledgeSearchRequest(
                    tenant_id=tenant_id,
                    query_text=query_text,
                    top_k=5,
                    agent_run_id=run.id,
                    agent_run_step_id=step.id,
                    used_in_answer=used_in_answer,
                )
            )
            citations = [self._citation_to_payload(hit) for hit in search_result.hits]
            rag_query_id = str(search_result.rag_query_id)

        step.status = "completed"
        step.output_payload = {
            "rag_query_id": rag_query_id,
            "query_text": query_text,
            "citations": citations,
        }
        step.finished_at = datetime.now(UTC)
        return step, citations

    def _knowledge_query_text(self, ticket: Ticket) -> str:
        return "\n".join(
            [
                ticket.title,
                ticket.description_text,
                f"category:{ticket.category_code}",
                f"priority:{ticket.priority}",
            ]
        )

    def _step_with_citations(self, step: RuntimeStep, citations: list[dict]) -> RuntimeStep:
        output_payload = dict(step.output_payload or {})
        output_payload["citations"] = citations
        input_payload = dict(step.input_payload)
        input_payload["citation_count"] = len(citations)
        return RuntimeStep(
            name=step.name,
            step_type=step.step_type,
            status=step.status,
            input_payload=input_payload,
            output_payload=output_payload,
            error_code=step.error_code,
            error_message=step.error_message,
        )

    def _citation_to_payload(self, hit: KnowledgeSearchHitRead) -> dict:
        return {
            "document_id": str(hit.document_id),
            "document_title": hit.document_title,
            "document_version_id": str(hit.document_version_id),
            "chunk_id": str(hit.chunk_id),
            "rank_no": hit.rank_no,
            "similarity_score": hit.similarity_score,
            "source_uri": hit.source_uri,
            "used_in_answer": hit.used_in_answer,
            "chunk": {
                "id": str(hit.chunk.id),
                "chunk_index": hit.chunk.chunk_index,
                "source_anchor": hit.chunk.source_anchor,
                "heading_path": hit.chunk.heading_path,
                "chunk_text": hit.chunk.chunk_text,
            },
        }

    def _attach_approval_tool_call(
        self,
        tenant_id: uuid.UUID,
        run: AgentRun,
        ticket: Ticket,
        run_step: AgentRunStep,
    ) -> None:
        if self.mcp_tool_service is None:
            return
        tool_call = self.mcp_tool_service.call_tool(
            ToolCallCreate(
                tenant_id=tenant_id,
                agent_run_id=run.id,
                agent_run_step_id=run_step.id,
                tool_name="ticket.transition_status",
                input_payload={
                    "ticket_id": str(ticket.id),
                    "to_status": self._recommended_status_for_ticket(ticket),
                    "reason_text": "manual approval required before continuing",
                },
            )
        )
        output_payload = dict(run_step.output_payload or {})
        output_payload["tool_call_id"] = str(tool_call.id)
        output_payload["approval_request_id"] = (
            str(tool_call.approval_request_id) if tool_call.approval_request_id else None
        )
        run_step.output_payload = output_payload

    def _add_call_tools_step(
        self,
        tenant_id: uuid.UUID,
        run: AgentRun,
        ticket: Ticket,
        order: int,
    ) -> AgentRunStep | None:
        if self.mcp_tool_service is None:
            return None
        now = datetime.now(UTC)
        step = AgentRunStep(
            tenant_id=tenant_id,
            agent_run_id=run.id,
            step_name="call_tools",
            step_type="tool",
            step_order=order,
            external_step_ref="ticket.get_context",
            status="running",
            input_payload={
                "tool_name": "ticket.get_context",
                "ticket_id": str(ticket.id),
            },
            output_payload=None,
            started_at=now,
            finished_at=None,
        )
        self.repository.add_step(step)
        tool_call = self.mcp_tool_service.call_tool(
            ToolCallCreate(
                tenant_id=tenant_id,
                agent_run_id=run.id,
                agent_run_step_id=step.id,
                tool_name="ticket.get_context",
                input_payload={"ticket_id": str(ticket.id)},
            )
        )
        step.status = tool_call.status
        step.output_payload = {
            "tool_call_id": str(tool_call.id),
            "tool_name": "ticket.get_context",
            "tool_status": tool_call.status,
            "output_payload": tool_call.output_payload,
        }
        step.finished_at = datetime.now(UTC)
        return step

    def _decide_linked_approval(
        self,
        approval_step: AgentRunStep,
        payload: AgentRunResume,
    ) -> dict:
        approval_request_id = self._approval_request_id_from_step(approval_step)
        if approval_request_id is None:
            return {}
        if self.approval_service is None:
            return {
                "approval_request_id": str(approval_request_id),
                "execution_status": None,
            }
        if payload.decided_by_user_id is None:
            raise AgentRunResumeError("decided_by_user_id is required")
        approval = self.approval_service.decide(
            approval_request_id,
            ApprovalDecisionCreate(
                tenant_id=payload.tenant_id,
                decided_by_user_id=payload.decided_by_user_id,
                decision=payload.decision,
                decision_reason=payload.decision_reason,
            ),
        )
        execution_status = approval.executions[-1].execution_status if approval.executions else None
        return {
            "approval_request_id": str(approval.id),
            "approval_status": approval.status,
            "execution_status": execution_status,
        }

    def _approval_request_id_from_step(self, step: AgentRunStep) -> uuid.UUID | None:
        if step.output_payload is None:
            return None
        raw_approval_request_id = step.output_payload.get("approval_request_id")
        if raw_approval_request_id is None:
            return None
        return uuid.UUID(str(raw_approval_request_id))

    def _recommended_status_for_ticket(self, ticket: Ticket) -> str:
        if ticket.status == "new":
            return "triaged"
        if ticket.status == "triaged":
            return "in_progress"
        return ticket.status

    def _to_read(self, run: AgentRun) -> AgentRunRead:
        steps = self.repository.list_steps(run.tenant_id, run.id)
        citations: list[dict] = []
        for step in reversed(steps):
            if step.step_name == "generate_summary" and step.output_payload is not None:
                citations = list(step.output_payload.get("citations", []))
                break
        return AgentRunRead(
            id=run.id,
            tenant_id=run.tenant_id,
            ticket_id=run.ticket_id,
            runtime_type=run.runtime_type,
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            error_code=run.error_code,
            error_message=run.error_message,
            steps=[
                AgentRunStepRead(
                    id=step.id,
                    step_name=step.step_name,
                    step_type=step.step_type,
                    step_order=step.step_order,
                    status=step.status,
                    input_payload=step.input_payload,
                    output_payload=step.output_payload,
                    error_code=step.error_code,
                    error_message=step.error_message,
                    started_at=step.started_at,
                    finished_at=step.finished_at,
                )
                for step in steps
            ],
            citations=citations,
        )
