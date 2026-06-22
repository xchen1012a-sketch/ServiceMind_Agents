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
    user_id = uuid.uuid4()
    headers = _auth_headers(tenant_id, user_id, "tickets:create,tickets:read")

    create_response = client.post(
        "/api/v1/tickets",
        headers=headers,
        json={
            "title": "API 创建工单",
            "description_text": "客户反馈无法查看订单",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["status"] == "new"
    assert created["tenant_id"] == str(tenant_id)
    assert created["created_by_user_id"] == str(user_id)
    assert created["messages"][0]["message_text"] == "客户反馈无法查看订单"
    assert created["status_events"][0]["to_status"] == "new"

    detail_response = client.get(
        f"/api/v1/tickets/{created['id']}",
        headers=headers,
    )

    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == created["id"]


def test_illegal_status_transition_returns_conflict(client: TestClient) -> None:
    tenant_id = uuid.uuid4()
    headers = _auth_headers(tenant_id, uuid.uuid4(), "tickets:create,tickets:update")
    created = client.post(
        "/api/v1/tickets",
        headers=headers,
        json={
            "title": "API 状态流转",
            "description_text": "验证非法状态",
        },
    ).json()

    response = client.post(
        f"/api/v1/tickets/{created['id']}/status",
        headers=headers,
        json={"to_status": "closed"},
    )

    assert response.status_code == 409


def test_ticket_routes_reject_missing_request_context(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tickets",
        json={"title": "无上下文", "description_text": "不能创建"},
    )

    assert response.status_code == 401


def test_ticket_routes_reject_client_controlled_security_fields(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tickets",
        headers=_auth_headers(uuid.uuid4(), uuid.uuid4(), "tickets:create"),
        json={
            "tenant_id": str(uuid.uuid4()),
            "created_by_user_id": str(uuid.uuid4()),
            "title": "伪造租户",
            "description_text": "不能信任前端",
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("category_code", "general;DROP TABLE tickets"),
        ("priority", "urgent OR 1=1"),
        ("risk_level", "critical<script>"),
        ("source_channel", "webhook://external"),
    ],
)
def test_ticket_create_rejects_non_whitelisted_business_values(
    client: TestClient,
    field_name: str,
    field_value: str,
) -> None:
    payload = {
        "title": "非法业务枚举",
        "description_text": "业务枚举必须来自后端白名单",
        field_name: field_value,
    }

    response = client.post(
        "/api/v1/tickets",
        headers=_auth_headers(uuid.uuid4(), uuid.uuid4(), "tickets:create"),
        json=payload,
    )

    assert response.status_code == 422


def test_ticket_create_rejects_oversized_description(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tickets",
        headers=_auth_headers(uuid.uuid4(), uuid.uuid4(), "tickets:create"),
        json={
            "title": "超长描述",
            "description_text": "x" * 20001,
        },
    )

    assert response.status_code == 422


def test_ticket_create_rejects_control_characters_in_free_text(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tickets",
        headers=_auth_headers(uuid.uuid4(), uuid.uuid4(), "tickets:create"),
        json={
            "title": "控制字符",
            "description_text": "正常文本\u0000隐藏内容",
        },
    )

    assert response.status_code == 422


def test_ticket_detail_uses_context_tenant_not_client_supplied_tenant(client: TestClient) -> None:
    tenant_id = uuid.uuid4()
    other_tenant_id = uuid.uuid4()
    create_response = client.post(
        "/api/v1/tickets",
        headers=_auth_headers(tenant_id, uuid.uuid4(), "tickets:create,tickets:read"),
        json={"title": "租户 A 工单", "description_text": "只能租户 A 读取"},
    )
    ticket_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/tickets/{ticket_id}",
        headers=_auth_headers(other_tenant_id, uuid.uuid4(), "tickets:read"),
    )

    assert response.status_code == 404


def test_ticket_status_uses_context_user_for_audit_fields(client: TestClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    headers = _auth_headers(tenant_id, user_id, "tickets:create,tickets:update")
    created = client.post(
        "/api/v1/tickets",
        headers=headers,
        json={"title": "审计字段", "description_text": "变更人必须来自上下文"},
    ).json()

    response = client.post(
        f"/api/v1/tickets/{created['id']}/status",
        headers=headers,
        json={"to_status": "triaged", "changed_by_user_id": str(uuid.uuid4())},
    )

    assert response.status_code == 422


def test_ticket_status_rejects_oversized_reason(client: TestClient) -> None:
    tenant_id = uuid.uuid4()
    headers = _auth_headers(tenant_id, uuid.uuid4(), "tickets:create,tickets:update")
    created = client.post(
        "/api/v1/tickets",
        headers=headers,
        json={"title": "状态原因", "description_text": "原因长度必须受控"},
    ).json()

    response = client.post(
        f"/api/v1/tickets/{created['id']}/status",
        headers=headers,
        json={"to_status": "triaged", "reason_text": "x" * 2001},
    )

    assert response.status_code == 422


def test_ticket_routes_require_permission(client: TestClient) -> None:
    response = client.get(
        "/api/v1/tickets",
        headers=_auth_headers(uuid.uuid4(), uuid.uuid4(), "tickets:create"),
    )

    assert response.status_code == 403


def _auth_headers(tenant_id: uuid.UUID, user_id: uuid.UUID, permissions: str) -> dict[str, str]:
    return {
        "X-ServiceMind-Tenant-Id": str(tenant_id),
        "X-ServiceMind-User-Id": str(user_id),
        "X-ServiceMind-Permissions": permissions,
    }
