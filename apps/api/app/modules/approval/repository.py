import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApprovalDecision, ApprovalRequest, ApprovedActionExecution


class ApprovalRepository(Protocol):
    def get_approval_request(
        self,
        tenant_id: uuid.UUID,
        approval_request_id: uuid.UUID,
    ) -> ApprovalRequest | None: ...

    def add_decision(self, decision: ApprovalDecision) -> None: ...

    def list_decisions(
        self,
        tenant_id: uuid.UUID,
        approval_request_id: uuid.UUID,
    ) -> list[ApprovalDecision]: ...

    def add_execution(self, execution: ApprovedActionExecution) -> None: ...

    def list_executions(
        self,
        tenant_id: uuid.UUID,
        approval_request_id: uuid.UUID,
    ) -> list[ApprovedActionExecution]: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class SqlAlchemyApprovalRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_approval_request(
        self,
        tenant_id: uuid.UUID,
        approval_request_id: uuid.UUID,
    ) -> ApprovalRequest | None:
        statement = select(ApprovalRequest).where(
            ApprovalRequest.tenant_id == tenant_id,
            ApprovalRequest.id == approval_request_id,
        )
        return self.db.scalar(statement)

    def add_decision(self, decision: ApprovalDecision) -> None:
        self.db.add(decision)
        self.db.flush()

    def list_decisions(
        self,
        tenant_id: uuid.UUID,
        approval_request_id: uuid.UUID,
    ) -> list[ApprovalDecision]:
        statement = (
            select(ApprovalDecision)
            .where(
                ApprovalDecision.tenant_id == tenant_id,
                ApprovalDecision.approval_request_id == approval_request_id,
            )
            .order_by(ApprovalDecision.created_at.asc())
        )
        return list(self.db.scalars(statement).all())

    def add_execution(self, execution: ApprovedActionExecution) -> None:
        self.db.add(execution)
        self.db.flush()

    def list_executions(
        self,
        tenant_id: uuid.UUID,
        approval_request_id: uuid.UUID,
    ) -> list[ApprovedActionExecution]:
        statement = (
            select(ApprovedActionExecution)
            .where(
                ApprovedActionExecution.tenant_id == tenant_id,
                ApprovedActionExecution.approval_request_id == approval_request_id,
            )
            .order_by(ApprovedActionExecution.created_at.asc())
        )
        return list(self.db.scalars(statement).all())

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
