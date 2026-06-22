import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.main import app
from app.models import (
    ChunkEmbedding,
    EmbeddingModel,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    KnowledgeSpace,
    RagQuery,
    RagRetrievalHit,
    Tenant,
)

pytestmark = pytest.mark.integration


def test_knowledge_import_persists_to_postgresql() -> None:
    if os.getenv("SERVICEMIND_RUN_POSTGRES_SMOKE") != "1":
        pytest.skip("set SERVICEMIND_RUN_POSTGRES_SMOKE=1 to run PostgreSQL smoke test")

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    tenant_slug = f"smoke-knowledge-{tenant_id.hex}"
    headers = _auth_headers(tenant_id, user_id, "knowledge:read,knowledge:write")

    with SessionLocal() as db:
        db.add(
            Tenant(
                id=tenant_id,
                name="Smoke Knowledge Tenant",
                slug=tenant_slug,
                status="active",
            )
        )
        db.commit()

    try:
        client = TestClient(app)
        space_response = client.post(
            "/api/v1/knowledge/spaces",
            headers=headers,
            json={
                "name": "Smoke KB",
                "description_text": "PostgreSQL knowledge smoke",
            },
        )
        assert space_response.status_code == 201
        space_id = uuid.UUID(space_response.json()["id"])

        import_response = client.post(
            "/api/v1/knowledge/documents/import",
            headers=headers,
            json={
                "knowledge_space_id": str(space_id),
                "title": "Smoke policy",
                "content_text": "# Smoke policy\n\nFirst paragraph.\n\nSecond paragraph.",
                "source_type": "manual",
                "source_uri": "manual://smoke-policy",
            },
        )
        assert import_response.status_code == 201
        document_id = uuid.UUID(import_response.json()["id"])

        embedding_response = client.post(
            f"/api/v1/knowledge/documents/{document_id}/embeddings",
            headers=headers,
            json={},
        )
        assert embedding_response.status_code == 201
        search_response = client.post(
            "/api/v1/knowledge/search",
            headers=headers,
            json={
                "query_text": "smoke policy paragraph",
                "top_k": 5,
                "knowledge_space_id": str(space_id),
            },
        )
        assert search_response.status_code == 200

        with SessionLocal() as db:
            space = db.scalar(select(KnowledgeSpace).where(KnowledgeSpace.id == space_id))
            document = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.id == document_id))
            version = db.scalar(
                select(KnowledgeDocumentVersion).where(
                    KnowledgeDocumentVersion.document_id == document_id
                )
            )
            chunks = list(
                db.scalars(
                    select(KnowledgeChunk)
                    .where(KnowledgeChunk.tenant_id == tenant_id)
                    .order_by(KnowledgeChunk.chunk_index.asc())
                )
            )
            embedding_model = db.scalar(
                select(EmbeddingModel).where(
                    EmbeddingModel.provider_code == "local",
                    EmbeddingModel.model_name == "deterministic-hash-v1",
                )
            )
            chunk_embeddings = list(
                db.scalars(select(ChunkEmbedding).where(ChunkEmbedding.tenant_id == tenant_id))
            )
            rag_query = db.scalar(select(RagQuery).where(RagQuery.tenant_id == tenant_id))
            rag_hits = list(
                db.scalars(select(RagRetrievalHit).where(RagRetrievalHit.tenant_id == tenant_id))
            )

        assert space is not None
        assert document is not None
        assert version is not None
        assert document.current_version_id == version.id
        assert version.parse_status == "completed"
        assert len(chunks) == 1
        assert chunks[0].source_anchor == "chunk:0"
        assert embedding_model is not None
        assert len(chunk_embeddings) == 1
        assert chunk_embeddings[0].chunk_id == chunks[0].id
        assert rag_query is not None
        assert rag_query.query_text == "smoke policy paragraph"
        assert len(rag_hits) == 1
        assert rag_hits[0].chunk_id == chunks[0].id
    finally:
        with SessionLocal() as db:
            query_ids = list(db.scalars(select(RagQuery.id).where(RagQuery.tenant_id == tenant_id)).all())
            if query_ids:
                db.execute(delete(RagRetrievalHit).where(RagRetrievalHit.rag_query_id.in_(query_ids)))
            db.execute(delete(RagQuery).where(RagQuery.tenant_id == tenant_id))
            version_ids = list(
                db.scalars(
                    select(KnowledgeDocumentVersion.id).where(
                        KnowledgeDocumentVersion.tenant_id == tenant_id
                    )
                ).all()
            )
            if version_ids:
                chunk_ids = list(
                    db.scalars(
                        select(KnowledgeChunk.id).where(
                            KnowledgeChunk.document_version_id.in_(version_ids)
                        )
                    ).all()
                )
                if chunk_ids:
                    db.execute(delete(ChunkEmbedding).where(ChunkEmbedding.chunk_id.in_(chunk_ids)))
                db.execute(
                    delete(KnowledgeChunk).where(
                        KnowledgeChunk.document_version_id.in_(version_ids)
                    )
                )
            db.execute(
                delete(KnowledgeDocumentVersion).where(
                    KnowledgeDocumentVersion.tenant_id == tenant_id
                )
            )
            db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.tenant_id == tenant_id))
            db.execute(delete(KnowledgeSpace).where(KnowledgeSpace.tenant_id == tenant_id))
            db.execute(delete(Tenant).where(Tenant.id == tenant_id, Tenant.slug == tenant_slug))
            db.commit()


def _auth_headers(tenant_id: uuid.UUID, user_id: uuid.UUID, permissions: str) -> dict[str, str]:
    return {
        "X-ServiceMind-Tenant-Id": str(tenant_id),
        "X-ServiceMind-User-Id": str(user_id),
        "X-ServiceMind-Permissions": permissions,
    }
