import uuid

import pytest

from app.modules.knowledge.schemas import (
    KnowledgeDocumentEmbeddingGenerate,
    KnowledgeDocumentImport,
    KnowledgeSearchRequest,
    KnowledgeSpaceCreate,
)
from app.modules.knowledge.service import KnowledgeService, KnowledgeSpaceNotFoundError
from knowledge.fakes import InMemoryKnowledgeRepository


def test_import_document_creates_version_and_chunks() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryKnowledgeRepository()
    service = KnowledgeService(repository)
    space = service.create_space(KnowledgeSpaceCreate(tenant_id=tenant_id, name="Support KB"))

    document = service.import_document(
        KnowledgeDocumentImport(
            tenant_id=tenant_id,
            knowledge_space_id=space.id,
            title="Refund policy",
            content_text="# Refunds\n\nRefunds require an order id.\n\nEscalate high-risk requests.",
            source_uri="manual://refund-policy",
        )
    )

    assert document.status == "ready"
    assert document.current_version is not None
    assert document.current_version.version_no == 1
    assert document.current_version.parse_status == "completed"
    assert document.current_version.content_hash
    assert [chunk.chunk_index for chunk in document.chunks] == [0]
    assert document.chunks[0].source_anchor == "chunk:0"
    assert "Refunds require an order id" in document.chunks[0].chunk_text
    assert repository.commits == 2


def test_import_document_requires_existing_space() -> None:
    service = KnowledgeService(InMemoryKnowledgeRepository())

    with pytest.raises(KnowledgeSpaceNotFoundError):
        service.import_document(
            KnowledgeDocumentImport(
                tenant_id=uuid.uuid4(),
                knowledge_space_id=uuid.uuid4(),
                title="Missing space",
                content_text="content",
            )
        )


def test_generate_document_embeddings_is_idempotent() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryKnowledgeRepository()
    service = KnowledgeService(repository)
    space = service.create_space(KnowledgeSpaceCreate(tenant_id=tenant_id, name="Support KB"))
    document = service.import_document(
        KnowledgeDocumentImport(
            tenant_id=tenant_id,
            knowledge_space_id=space.id,
            title="Escalation policy",
            content_text="# Escalation\n\nEscalate urgent refunds to a specialist.",
        )
    )

    first_result = service.generate_document_embeddings(
        document_id=document.id,
        payload=KnowledgeDocumentEmbeddingGenerate(tenant_id=tenant_id),
    )
    second_result = service.generate_document_embeddings(
        document_id=document.id,
        payload=KnowledgeDocumentEmbeddingGenerate(tenant_id=tenant_id),
    )

    assert first_result.embedding_model.provider_code == "local"
    assert first_result.embedding_model.model_name == "deterministic-hash-v1"
    assert first_result.embedding_model.dimension == 8
    assert first_result.created_count == 1
    assert second_result.created_count == 0
    assert len(repository.embedding_models) == 1
    assert len(repository.chunk_embeddings) == 1
    assert first_result.embeddings[0].embedding_hash == second_result.embeddings[0].embedding_hash


def test_search_returns_ranked_hits_and_audits_query() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryKnowledgeRepository()
    service = KnowledgeService(repository)
    space = service.create_space(KnowledgeSpaceCreate(tenant_id=tenant_id, name="Support KB"))
    refund_document = service.import_document(
        KnowledgeDocumentImport(
            tenant_id=tenant_id,
            knowledge_space_id=space.id,
            title="Refund policy",
            content_text="Refund requests require an order id.",
        )
    )
    service.import_document(
        KnowledgeDocumentImport(
            tenant_id=tenant_id,
            knowledge_space_id=space.id,
            title="Shipping policy",
            content_text="Shipping delays require carrier tracking.",
        )
    )
    service.generate_document_embeddings(
        document_id=refund_document.id,
        payload=KnowledgeDocumentEmbeddingGenerate(tenant_id=tenant_id),
    )

    result = service.search(
        KnowledgeSearchRequest(
            tenant_id=tenant_id,
            query_text="refund order id",
            top_k=3,
            knowledge_space_id=space.id,
        )
    )

    assert result.query_text == "refund order id"
    assert result.retrieval_params_json["knowledge_space_id"] == str(space.id)
    assert len(result.hits) == 1
    assert result.hits[0].document_title == "Refund policy"
    assert result.hits[0].rank_no == 1
    assert result.hits[0].similarity_score is not None
    assert len(repository.rag_queries) == 1
    assert len(repository.rag_retrieval_hits) == 1


def test_search_can_mark_hits_used_in_answer_for_agent_citations() -> None:
    tenant_id = uuid.uuid4()
    repository = InMemoryKnowledgeRepository()
    service = KnowledgeService(repository)
    space = service.create_space(KnowledgeSpaceCreate(tenant_id=tenant_id, name="Support KB"))
    document = service.import_document(
        KnowledgeDocumentImport(
            tenant_id=tenant_id,
            knowledge_space_id=space.id,
            title="Refund policy",
            content_text="Refund requests require an order id.",
        )
    )
    service.generate_document_embeddings(
        document_id=document.id,
        payload=KnowledgeDocumentEmbeddingGenerate(tenant_id=tenant_id),
    )

    result = service.search(
        KnowledgeSearchRequest(
            tenant_id=tenant_id,
            query_text="refund order id",
            used_in_answer=True,
        )
    )

    assert result.hits[0].used_in_answer is True
    assert repository.rag_retrieval_hits[0].used_in_answer is True
