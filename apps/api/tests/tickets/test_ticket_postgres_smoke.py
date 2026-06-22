import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.main import app
from app.models import Tenant, Ticket, TicketMessage, TicketStatusEvent

pytestmark = pytest.mark.integration


def test_ticket_workflow_persists_to_postgresql() -> None:
    if os.getenv("SERVICEMIND_RUN_POSTGRES_SMOKE") != "1":
        pytest.skip("set SERVICEMIND_RUN_POSTGRES_SMOKE=1 to run PostgreSQL smoke test")

    tenant_id = uuid.uuid4()
    tenant_slug = f"smoke-ticket-{tenant_id.hex}"

    with SessionLocal() as db:
        db.add(
            Tenant(
                id=tenant_id,
                name="Smoke Ticket Tenant",
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
                "title": "真实库工单冒烟",
                "description_text": "验证工单、消息和状态事件能写入 PostgreSQL",
                "category_code": "smoke",
                "priority": "medium",
                "risk_level": "low",
            },
        )
        assert create_response.status_code == 201
        ticket_id = uuid.UUID(create_response.json()["id"])

        change_response = client.post(
            f"/api/v1/tickets/{ticket_id}/status",
            json={
                "tenant_id": str(tenant_id),
                "to_status": "triaged",
                "reason_text": "PostgreSQL smoke transition",
            },
        )
        assert change_response.status_code == 200

        with SessionLocal() as db:
            ticket = db.scalar(select(Ticket).where(Ticket.id == ticket_id))
            messages = list(
                db.scalars(select(TicketMessage).where(TicketMessage.ticket_id == ticket_id))
            )
            events = list(
                db.scalars(
                    select(TicketStatusEvent)
                    .where(TicketStatusEvent.ticket_id == ticket_id)
                    .order_by(TicketStatusEvent.created_at.asc())
                )
            )

        assert ticket is not None
        assert ticket.status == "triaged"
        assert len(messages) == 1
        assert [event.to_status for event in events] == ["new", "triaged"]
    finally:
        with SessionLocal() as db:
            ticket_ids = list(
                db.scalars(select(Ticket.id).where(Ticket.tenant_id == tenant_id)).all()
            )
            if ticket_ids:
                db.execute(delete(TicketStatusEvent).where(TicketStatusEvent.ticket_id.in_(ticket_ids)))
                db.execute(delete(TicketMessage).where(TicketMessage.ticket_id.in_(ticket_ids)))
                db.execute(delete(Ticket).where(Ticket.id.in_(ticket_ids)))
            db.execute(delete(Tenant).where(Tenant.id == tenant_id, Tenant.slug == tenant_slug))
            db.commit()
