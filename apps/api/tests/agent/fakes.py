import uuid
from datetime import UTC, datetime

from app.models import AgentRun, AgentRunStep, Ticket
from app.modules.agent.runtime import RuntimeResult, RuntimeStep


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
