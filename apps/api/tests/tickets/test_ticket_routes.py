import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from tickets.fakes import InMemoryTicketRepository

from app.api.routes.tickets import get_ticket_service
from app.main import app
from app.modules.tickets.service import TicketService


@pytest.fixture
def client() -> Iterator[TestClient]:
    repository = InMemoryTicketRepository()
    service = TicketService(repository)
    app.dependency_overrides[get_ticket_service] = lambda: service
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_create_and_get_ticket_through_api(client: TestClient) -> None:
    tenant_id = uuid.uuid4()

    create_response = client.post(
        "/api/v1/tickets",
        json={
            "tenant_id": str(tenant_id),
            "title": "API 创建工单",
            "description_text": "客户反馈无法查看订单",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["status"] == "new"
    assert created["messages"][0]["message_text"] == "客户反馈无法查看订单"
    assert created["status_events"][0]["to_status"] == "new"

    detail_response = client.get(
        f"/api/v1/tickets/{created['id']}",
        params={"tenant_id": str(tenant_id)},
    )

    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == created["id"]


def test_illegal_status_transition_returns_conflict(client: TestClient) -> None:
    tenant_id = uuid.uuid4()
    created = client.post(
        "/api/v1/tickets",
        json={
            "tenant_id": str(tenant_id),
            "title": "API 状态流转",
            "description_text": "验证非法状态",
        },
    ).json()

    response = client.post(
        f"/api/v1/tickets/{created['id']}/status",
        json={"tenant_id": str(tenant_id), "to_status": "closed"},
    )

    assert response.status_code == 409
