import uuid
from datetime import UTC, datetime

from app.models import AgentRun, AgentRunStep
from app.modules.agent.repository import AgentRepository
from app.modules.agent.runtime import LangGraphTicketRuntime, RuntimeStep
from app.modules.agent.schemas import AgentRunRead, AgentRunResume, AgentRunStart, AgentRunStepRead


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
    ) -> None:
        self.repository = repository
        self.runtime = runtime or LangGraphTicketRuntime()

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
            for order, step in enumerate(result.steps, start=1):
                self.repository.add_step(self._build_step(payload.tenant_id, run.id, order, step))
            run.status = result.status
            if result.status != "waiting_approval":
                run.finished_at = datetime.now(UTC)
        except Exception as exc:
            run.status = "failed"
            run.finished_at = datetime.now(UTC)
            run.error_code = exc.__class__.__name__
            run.error_message = str(exc)
            self.repository.add_step(
                AgentRunStep(
                    tenant_id=payload.tenant_id,
                    agent_run_id=run.id,
                    step_name="runtime_error",
                    step_type="error",
                    step_order=1,
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
                output_payload={"resume": payload.decision == "approved"},
                started_at=now,
                finished_at=now,
            )
        )

        if payload.decision == "rejected":
            run.status = "rejected"
            run.finished_at = now
            self.repository.commit()
            return self._to_read(run)

        self.repository.add_step(
            AgentRunStep(
                tenant_id=payload.tenant_id,
                agent_run_id=run.id,
                step_name="generate_summary",
                step_type="generation",
                step_order=next_order + 1,
                external_step_ref="generate_summary",
                status="completed",
                input_payload={"approval": "approved"},
                output_payload={"summary": "approved ticket is ready for operator review"},
                started_at=now,
                finished_at=now,
            )
        )
        run.status = "completed"
        run.finished_at = now
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

    def _to_read(self, run: AgentRun) -> AgentRunRead:
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
                for step in self.repository.list_steps(run.tenant_id, run.id)
            ],
        )
