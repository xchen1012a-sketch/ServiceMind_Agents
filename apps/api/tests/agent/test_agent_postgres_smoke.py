import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.main import app
from app.models import AgentRun, AgentRunStep, Tenant, Ticket, TicketMessage, TicketStatusEvent

pytestmark = pytest.mark.integration


def test_agent_run_persists_to_postgresql() -> None:
    if os.getenv("SERVICEMIND_RUN_POSTGRES_SMOKE") != "1":
        pytest.skip("set SERVICEMIND_RUN_POSTGRES_SMOKE=1 to run PostgreSQL smoke test")

    tenant_id = uuid.uuid4()
    tenant_slug = f"smoke-agent-{tenant_id.hex}"

    with SessionLocal() as db:
        db.add(
            Tenant(
                id=tenant_id,
                name="Smoke Agent Tenant",
                slug=tenant_slug,
                status="active",
            )
        )
        db.commit()

    try:
        client = TestClient(app)
        create_response = client.post(
            "/api/v1/tickets",
            json={
                "tenant_id": str(tenant_id),
                "title": "真实库 Agent 冒烟",
                "description_text": "验证 agent_runs 和 agent_run_steps 能写入 PostgreSQL",
                "category_code": "smoke",
                "priority": "urgent",
                "risk_level": "high",
            },
        )
        assert create_response.status_code == 201
        ticket_id = uuid.UUID(create_response.json()["id"])

        run_response = client.post(
            f"/api/v1/tickets/{ticket_id}/agent-runs",
            json={"tenant_id": str(tenant_id)},
        )
        assert run_response.status_code == 201
        run_id = uuid.UUID(run_response.json()["id"])
        assert run_response.json()["status"] == "waiting_approval"

        resume_response = client.post(
            f"/api/v1/agent-runs/{run_id}/resume",
            json={
                "tenant_id": str(tenant_id),
                "decision": "approved",
                "decision_reason": "postgres smoke approval",
            },
        )
        assert resume_response.status_code == 200
        assert resume_response.json()["status"] == "completed"

        with SessionLocal() as db:
            run = db.scalar(select(AgentRun).where(AgentRun.id == run_id))
            steps = list(
                db.scalars(
                    select(AgentRunStep)
                    .where(AgentRunStep.agent_run_id == run_id)
                    .order_by(AgentRunStep.step_order.asc())
                )
            )

        assert run is not None
        assert run.status == "completed"
        assert run.runtime_type == "langgraph"
        assert [step.step_name for step in steps] == [
            "classify_ticket",
            "risk_review",
            "approval_gate",
            "approval_decision",
            "generate_summary",
        ]
        assert steps[2].status == "completed"
        assert steps[3].input_payload["decision"] == "approved"
    finally:
        with SessionLocal() as db:
            ticket_ids = list(
                db.scalars(select(Ticket.id).where(Ticket.tenant_id == tenant_id)).all()
            )
            run_ids = list(
                db.scalars(select(AgentRun.id).where(AgentRun.tenant_id == tenant_id)).all()
            )
            if run_ids:
                db.execute(delete(AgentRunStep).where(AgentRunStep.agent_run_id.in_(run_ids)))
                db.execute(delete(AgentRun).where(AgentRun.id.in_(run_ids)))
            if ticket_ids:
                db.execute(delete(TicketStatusEvent).where(TicketStatusEvent.ticket_id.in_(ticket_ids)))
                db.execute(delete(TicketMessage).where(TicketMessage.ticket_id.in_(ticket_ids)))
                db.execute(delete(Ticket).where(Ticket.id.in_(ticket_ids)))
            db.execute(delete(Tenant).where(Tenant.id == tenant_id, Tenant.slug == tenant_slug))
            db.commit()
