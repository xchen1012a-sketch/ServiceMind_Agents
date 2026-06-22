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

    space_response = client.post(
        "/api/v1/knowledge/spaces",
        json={
            "tenant_id": str(tenant_id),
            "name": "Support KB",
            "description_text": "Customer support policy documents",
        },
    )
    assert space_response.status_code == 201
    space = space_response.json()

    import_response = client.post(
        "/api/v1/knowledge/documents/import",
        json={
            "tenant_id": str(tenant_id),
            "knowledge_space_id": space["id"],
            "title": "Refund policy",
            "content_text": "# Refunds\n\nRefunds require an order id.",
            "source_uri": "manual://refund-policy",
        },
    )

    assert import_response.status_code == 201
    document = import_response.json()
    assert document["status"] == "ready"
    assert document["current_version"]["parse_status"] == "completed"
    assert document["chunks"][0]["chunk_index"] == 0
    assert document["chunks"][0]["source_anchor"] == "chunk:0"

    detail_response = client.get(
        f"/api/v1/knowledge/documents/{document['id']}",
        params={"tenant_id": str(tenant_id)},
    )

    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == document["id"]

    embedding_response = client.post(
        f"/api/v1/knowledge/documents/{document['id']}/embeddings",
        json={"tenant_id": str(tenant_id)},
    )

    assert embedding_response.status_code == 201
    embeddings = embedding_response.json()
    assert embeddings["embedding_model"]["provider_code"] == "local"
    assert embeddings["created_count"] == 1
    assert embeddings["embeddings"][0]["chunk_id"] == document["chunks"][0]["id"]

    search_response = client.post(
        "/api/v1/knowledge/search",
        json={
            "tenant_id": str(tenant_id),
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
        json={
            "tenant_id": str(uuid.uuid4()),
            "knowledge_space_id": str(uuid.uuid4()),
            "title": "Missing space",
            "content_text": "content",
        },
    )

    assert response.status_code == 404


def test_generate_embeddings_returns_not_found_for_missing_document(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/knowledge/documents/{uuid.uuid4()}/embeddings",
        json={"tenant_id": str(uuid.uuid4())},
    )

    assert response.status_code == 404


def test_search_without_embeddings_returns_empty_hits(client: TestClient) -> None:
    response = client.post(
        "/api/v1/knowledge/search",
        json={
            "tenant_id": str(uuid.uuid4()),
            "query_text": "anything",
        },
    )

    assert response.status_code == 200
    assert response.json()["hits"] == []
