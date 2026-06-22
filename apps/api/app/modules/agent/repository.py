import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentRun, AgentRunStep, Ticket


class AgentRepository(Protocol):
    def get_ticket(self, tenant_id: uuid.UUID, ticket_id: uuid.UUID) -> Ticket | None: ...

    def get_run(self, tenant_id: uuid.UUID, agent_run_id: uuid.UUID) -> AgentRun | None: ...

    def add_run(self, run: AgentRun) -> None: ...

    def add_step(self, step: AgentRunStep) -> None: ...

    def list_steps(self, tenant_id: uuid.UUID, agent_run_id: uuid.UUID) -> list[AgentRunStep]: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class SqlAlchemyAgentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_ticket(self, tenant_id: uuid.UUID, ticket_id: uuid.UUID) -> Ticket | None:
        statement = select(Ticket).where(
            Ticket.tenant_id == tenant_id,
            Ticket.id == ticket_id,
            Ticket.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def add_run(self, run: AgentRun) -> None:
        self.db.add(run)
        self.db.flush()

    def get_run(self, tenant_id: uuid.UUID, agent_run_id: uuid.UUID) -> AgentRun | None:
        statement = select(AgentRun).where(AgentRun.tenant_id == tenant_id, AgentRun.id == agent_run_id)
        return self.db.scalar(statement)

    def add_step(self, step: AgentRunStep) -> None:
        self.db.add(step)
        self.db.flush()

    def list_steps(self, tenant_id: uuid.UUID, agent_run_id: uuid.UUID) -> list[AgentRunStep]:
        statement = (
            select(AgentRunStep)
            .where(AgentRunStep.tenant_id == tenant_id, AgentRunStep.agent_run_id == agent_run_id)
            .order_by(AgentRunStep.step_order.asc())
        )
        return list(self.db.scalars(statement).all())

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
