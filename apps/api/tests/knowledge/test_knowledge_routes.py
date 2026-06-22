import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.routes.knowledge import get_knowledge_service
from app.main import app
from app.modules.knowledge.service import KnowledgeService
from knowledge.fakes import InMemoryKnowledgeRepository


@pytest.fixture
def client() -> Iterator[TestClient]:
    repository = InMemoryKnowledgeRepository()
    service = KnowledgeService(repository)
    app.dependency_overrides[get_knowledge_service] = lambda: service
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_import_document_through_api(client: TestClient) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    headers = _auth_headers(tenant_id, user_id, "knowledge:read,knowledge:write")

    space_response = client.post(
        "/api/v1/knowledge/spaces",
        headers=headers,
        json={
            "name": "Support KB",
            "description_text": "Customer support policy documents",
        },
    )
    assert space_response.status_code == 201
    space = space_response.json()

    import_response = client.post(
        "/api/v1/knowledge/documents/import",
        headers=headers,
        json={
            "knowledge_space_id": space["id"],
            "title": "Refund policy",
            "content_text": "# Refunds\n\nRefunds require an order id.",
            "source_uri": "manual://refund-policy",
        },
    )

    assert import_response.status_code == 201
    document = import_response.json()
    assert document["status"] == "ready"
    assert document["tenant_id"] == str(tenant_id)
    assert document["created_by_user_id"] == str(user_id)
    assert document["current_version"]["parse_status"] == "completed"
    assert document["chunks"][0]["chunk_index"] == 0
    assert document["chunks"][0]["source_anchor"] == "chunk:0"

    detail_response = client.get(
        f"/api/v1/knowledge/documents/{document['id']}",
        headers=headers,
    )

    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == document["id"]

    embedding_response = client.post(
        f"/api/v1/knowledge/documents/{document['id']}/embeddings",
        headers=headers,
        json={},
    )

    assert embedding_response.status_code == 201
    embeddings = embedding_response.json()
    assert embeddings["embedding_model"]["provider_code"] == "local"
    assert embeddings["created_count"] == 1
    assert embeddings["embeddings"][0]["chunk_id"] == document["chunks"][0]["id"]

    search_response = client.post(
        "/api/v1/knowledge/search",
        headers=headers,
        json={
            "query_text": "refund order id",
            "top_k": 3,
            "knowledge_space_id": space["id"],
        },
    )

    assert search_response.status_code == 200
    search_result = search_response.json()
    assert search_result["query_text"] == "refund order id"
    assert search_result["hits"][0]["document_title"] == "Refund policy"
    assert search_result["hits"][0]["rank_no"] == 1


def test_import_document_returns_not_found_for_missing_space(client: TestClient) -> None:
    response = client.post(
        "/api/v1/knowledge/documents/import",
        headers=_auth_headers(uuid.uuid4(), uuid.uuid4(), "knowledge:write"),
        json={
            "knowledge_space_id": str(uuid.uuid4()),
            "title": "Missing space",
            "content_text": "content",
        },
    )

    assert response.status_code == 404


def test_generate_embeddings_returns_not_found_for_missing_document(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/knowledge/documents/{uuid.uuid4()}/embeddings",
        headers=_auth_headers(uuid.uuid4(), uuid.uuid4(), "knowledge:write"),
        json={},
    )

    assert response.status_code == 404


def test_search_without_embeddings_returns_empty_hits(client: TestClient) -> None:
    response = client.post(
        "/api/v1/knowledge/search",
        headers=_auth_headers(uuid.uuid4(), uuid.uuid4(), "knowledge:read"),
        json={"query_text": "anything"},
    )

    assert response.status_code == 200
    assert response.json()["hits"] == []


def test_knowledge_routes_reject_client_controlled_security_fields(client: TestClient) -> None:
    response = client.post(
        "/api/v1/knowledge/spaces",
        headers=_auth_headers(uuid.uuid4(), uuid.uuid4(), "knowledge:write"),
        json={
            "tenant_id": str(uuid.uuid4()),
            "created_by_user_id": str(uuid.uuid4()),
            "name": "伪造空间",
        },
    )

    assert response.status_code == 422


def test_knowledge_space_rejects_non_whitelisted_visibility(client: TestClient) -> None:
    response = client.post(
        "/api/v1/knowledge/spaces",
        headers=_auth_headers(uuid.uuid4(), uuid.uuid4(), "knowledge:write"),
        json={
            "name": "非法可见性",
            "visibility": "public;DROP TABLE knowledge_spaces",
        },
    )

    assert response.status_code == 422


def test_knowledge_import_rejects_non_whitelisted_source_type(client: TestClient) -> None:
    tenant_id = uuid.uuid4()
    headers = _auth_headers(tenant_id, uuid.uuid4(), "knowledge:write")
    space = client.post(
        "/api/v1/knowledge/spaces",
        headers=headers,
        json={"name": "来源类型"},
    ).json()

    response = client.post(
        "/api/v1/knowledge/documents/import",
        headers=headers,
        json={
            "knowledge_space_id": space["id"],
            "title": "非法来源",
            "content_text": "来源类型必须受控",
            "source_type": "url_fetch",
        },
    )

    assert response.status_code == 422


def test_knowledge_import_rejects_external_source_uri_scheme(client: TestClient) -> None:
    tenant_id = uuid.uuid4()
    headers = _auth_headers(tenant_id, uuid.uuid4(), "knowledge:write")
    space = client.post(
        "/api/v1/knowledge/spaces",
        headers=headers,
        json={"name": "来源 URI"},
    ).json()

    response = client.post(
        "/api/v1/knowledge/documents/import",
        headers=headers,
        json={
            "knowledge_space_id": space["id"],
            "title": "外部来源",
            "content_text": "当前导入接口不执行外部 URL 抓取",
            "source_uri": "http://169.254.169.254/latest/meta-data",
        },
    )

    assert response.status_code == 422


def test_knowledge_import_rejects_oversized_content(client: TestClient) -> None:
    tenant_id = uuid.uuid4()
    headers = _auth_headers(tenant_id, uuid.uuid4(), "knowledge:write")
    space = client.post(
        "/api/v1/knowledge/spaces",
        headers=headers,
        json={"name": "内容长度"},
    ).json()

    response = client.post(
        "/api/v1/knowledge/documents/import",
        headers=headers,
        json={
            "knowledge_space_id": space["id"],
            "title": "超长内容",
            "content_text": "x" * 200001,
        },
    )

    assert response.status_code == 422


def test_knowledge_search_rejects_oversized_query(client: TestClient) -> None:
    response = client.post(
        "/api/v1/knowledge/search",
        headers=_auth_headers(uuid.uuid4(), uuid.uuid4(), "knowledge:read"),
        json={"query_text": "x" * 2001},
    )

    assert response.status_code == 422


def test_public_knowledge_search_rejects_agent_internal_audit_fields(client: TestClient) -> None:
    response = client.post(
        "/api/v1/knowledge/search",
        headers=_auth_headers(uuid.uuid4(), uuid.uuid4(), "knowledge:read"),
        json={
            "query_text": "refund",
            "agent_run_id": str(uuid.uuid4()),
            "agent_run_step_id": str(uuid.uuid4()),
            "used_in_answer": True,
        },
    )

    assert response.status_code == 422


def test_knowledge_routes_require_permission(client: TestClient) -> None:
    response = client.post(
        "/api/v1/knowledge/search",
        headers=_auth_headers(uuid.uuid4(), uuid.uuid4(), "tickets:read"),
        json={"query_text": "anything"},
    )

    assert response.status_code == 403


def _auth_headers(tenant_id: uuid.UUID, user_id: uuid.UUID, permissions: str) -> dict[str, str]:
    return {
        "X-ServiceMind-Tenant-Id": str(tenant_id),
        "X-ServiceMind-User-Id": str(user_id),
        "X-ServiceMind-Permissions": permissions,
    }
