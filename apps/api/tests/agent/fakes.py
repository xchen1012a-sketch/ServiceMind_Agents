import uuid
from datetime import UTC, datetime

from app.models import AgentRun, AgentRunStep, Ticket
from app.modules.agent.runtime import RuntimeResult, RuntimeStep
from app.modules.knowledge.schemas import (
    KnowledgeChunkRead,
    KnowledgeSearchHitRead,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)


class InMemoryAgentRepository:
    def __init__(self) -> None:
        self.tickets: list[Ticket] = []
        self.runs: list[AgentRun] = []
        self.steps: list[AgentRunStep] = []
        self.commits = 0

    def get_ticket(self, tenant_id: uuid.UUID, ticket_id: uuid.UUID) -> Ticket | None:
        return next(
            (
                ticket
                for ticket in self.tickets
                if ticket.tenant_id == tenant_id and ticket.id == ticket_id
            ),
            None,
        )

    def add_run(self, run: AgentRun) -> None:
        self._ensure_identity(run)
        self.runs.append(run)

    def get_run(self, tenant_id: uuid.UUID, agent_run_id: uuid.UUID) -> AgentRun | None:
        return next(
            (
                run
                for run in self.runs
                if run.tenant_id == tenant_id and run.id == agent_run_id
            ),
            None,
        )

    def add_step(self, step: AgentRunStep) -> None:
        self._ensure_identity(step)
        self.steps.append(step)

    def list_steps(self, tenant_id: uuid.UUID, agent_run_id: uuid.UUID) -> list[AgentRunStep]:
        return [
            step
            for step in sorted(self.steps, key=lambda item: item.step_order)
            if step.tenant_id == tenant_id and step.agent_run_id == agent_run_id
        ]

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        pass

    def add_ticket(self, ticket: Ticket) -> Ticket:
        self._ensure_identity(ticket)
        self.tickets.append(ticket)
        return ticket

    def _ensure_identity(self, item: AgentRun | AgentRunStep | Ticket) -> None:
        now = datetime.now(UTC)
        if item.id is None:
            item.id = uuid.uuid4()
        if item.created_at is None:
            item.created_at = now
        if hasattr(item, "updated_at") and getattr(item, "updated_at", None) is None:
            item.updated_at = now


class StaticRuntime:
    runtime_type = "langgraph"

    def __init__(self, result: RuntimeResult | None = None, error: Exception | None = None) -> None:
        self.result = result or RuntimeResult(
            status="completed",
            steps=[
                RuntimeStep(
                    name="classify_ticket",
                    step_type="classification",
                    status="completed",
                    input_payload={"title": "ticket"},
                    output_payload={"classification": "general"},
                ),
                RuntimeStep(
                    name="generate_summary",
                    step_type="generation",
                    status="completed",
                    input_payload={"classification": "general"},
                    output_payload={"summary": "ready"},
                ),
            ],
        )
        self.error = error

    def run(self, state: dict) -> RuntimeResult:
        if self.error is not None:
            raise self.error
        return self.result


class StaticKnowledgeSearchService:
    def __init__(self, hits: list[KnowledgeSearchHitRead] | None = None) -> None:
        self.hits = hits if hits is not None else [make_search_hit()]
        self.requests: list[KnowledgeSearchRequest] = []

    def search(self, payload: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
        self.requests.append(payload)
        return KnowledgeSearchResponse(
            tenant_id=payload.tenant_id,
            rag_query_id=uuid.uuid4(),
            query_text=payload.query_text,
            retrieval_params_json={"top_k": payload.top_k},
            hits=self.hits,
        )


def make_ticket(tenant_id: uuid.UUID | None = None, **overrides: str) -> Ticket:
    now = datetime.now(UTC)
    return Ticket(
        id=uuid.uuid4(),
        tenant_id=tenant_id or uuid.uuid4(),
        ticket_no=f"TCK-{uuid.uuid4().hex[:8]}",
        title=overrides.get("title", "Agent 工单"),
        description_text=overrides.get("description_text", "需要 Agent 处理"),
        category_code=overrides.get("category_code", "general"),
        priority=overrides.get("priority", "medium"),
        risk_level=overrides.get("risk_level", "low"),
        status=overrides.get("status", "new"),
        source_channel=overrides.get("source_channel", "web"),
        created_at=now,
        updated_at=now,
    )


def make_search_hit(**overrides: object) -> KnowledgeSearchHitRead:
    now = datetime.now(UTC)
    chunk_id = overrides.get("chunk_id", uuid.uuid4())
    return KnowledgeSearchHitRead(
        id=overrides.get("id", uuid.uuid4()),
        chunk_id=chunk_id,
        document_id=overrides.get("document_id", uuid.uuid4()),
        document_version_id=overrides.get("document_version_id", uuid.uuid4()),
        document_title=overrides.get("document_title", "Refund policy"),
        source_uri=overrides.get("source_uri", "manual://refund-policy"),
        rank_no=overrides.get("rank_no", 1),
        similarity_score=overrides.get("similarity_score", 0.98),
        used_in_answer=overrides.get("used_in_answer", True),
        chunk=KnowledgeChunkRead(
            id=chunk_id,
            chunk_index=overrides.get("chunk_index", 0),
            chunk_text=overrides.get("chunk_text", "Refunds require an order id."),
            token_count=overrides.get("token_count", 6),
            heading_path=overrides.get("heading_path", "Refunds"),
            page_number=None,
            source_anchor=overrides.get("source_anchor", "chunk:0"),
            metadata_json=None,
            created_at=now,
        ),
        created_at=now,
    )
